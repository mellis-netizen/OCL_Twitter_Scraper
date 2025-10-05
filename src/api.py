"""
FastAPI application for TGE Monitor API
RESTful API with authentication, WebSocket support, and comprehensive endpoints
"""

import os
import json
import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Dict, Any
from fastapi import FastAPI, Depends, HTTPException, status, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_, or_
import uvicorn

from .database import DatabaseManager, CacheManager, init_db
from .models import User, Company, Alert, Feed, MonitoringSession, SystemMetrics, APIKey
from .schemas import (
    UserCreate, UserUpdate, UserResponse, LoginRequest, Token,
    CompanyCreate, CompanyUpdate, CompanyResponse, CompanyFilter,
    AlertCreate, AlertUpdate, AlertResponse, AlertFilter, AlertStatistics,
    FeedCreate, FeedUpdate, FeedResponse,
    MonitoringSessionResponse, SystemMetricCreate, SystemMetricResponse,
    APIKeyCreate, APIKeyResponse, BulkAlertUpdate, BulkOperationResult,
    HealthCheck, SystemStatistics, WebSocketMessage, AlertNotification
)
from .auth import (
    AuthManager, authenticate_user, create_user, create_api_key,
    get_current_user, get_current_active_user, get_current_admin_user,
    optional_user, check_rate_limit, create_admin_user_if_not_exists
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPI app
app = FastAPI(
    title="TGE Monitor API",
    description="Token Generation Event monitoring and alert system",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# WebSocket connection manager
class ConnectionManager:
    """WebSocket connection manager for real-time updates"""
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.user_connections: Dict[int, List[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, user_id: Optional[int] = None):
        """Accept WebSocket connection"""
        await websocket.accept()
        self.active_connections.append(websocket)
        
        if user_id:
            if user_id not in self.user_connections:
                self.user_connections[user_id] = []
            self.user_connections[user_id].append(websocket)
    
    def disconnect(self, websocket: WebSocket, user_id: Optional[int] = None):
        """Remove WebSocket connection"""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        
        if user_id and user_id in self.user_connections:
            if websocket in self.user_connections[user_id]:
                self.user_connections[user_id].remove(websocket)
            if not self.user_connections[user_id]:
                del self.user_connections[user_id]
    
    async def broadcast(self, message: dict):
        """Broadcast message to all connections"""
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except:
                pass  # Connection might be closed
    
    async def send_to_user(self, user_id: int, message: dict):
        """Send message to specific user"""
        if user_id in self.user_connections:
            for connection in self.user_connections[user_id]:
                try:
                    await connection.send_json(message)
                except:
                    pass  # Connection might be closed


manager = ConnectionManager()


# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize database and create admin user"""
    try:
        init_db()
        logger.info("Database initialized")
        
        # Create admin user if needed
        with DatabaseManager.get_session() as db:
            create_admin_user_if_not_exists(db)
        
        logger.info("TGE Monitor API started successfully")
    except Exception as e:
        logger.error(f"Failed to initialize application: {e}")
        raise


# Health check endpoint
@app.get("/health", response_model=HealthCheck)
async def health_check():
    """Health check endpoint"""
    db_healthy = DatabaseManager.check_connection()
    redis_healthy = CacheManager.exists("health_check")
    
    # Test Redis
    if not redis_healthy:
        CacheManager.set("health_check", "ok", 60)
        redis_healthy = CacheManager.exists("health_check")
    
    return HealthCheck(
        status="healthy" if db_healthy and redis_healthy else "unhealthy",
        timestamp=datetime.now(timezone.utc),
        database=db_healthy,
        redis=redis_healthy,
        feeds_health={"active": 0, "total": 0},  # TODO: Implement feed health check
        system_metrics={"memory_usage": 0, "cpu_usage": 0}  # TODO: Implement system metrics
    )


# Authentication endpoints
@app.post("/auth/login", response_model=Token)
async def login(
    login_data: LoginRequest,
    db: Session = Depends(DatabaseManager.get_db)
):
    """Authenticate user and return JWT token"""
    check_rate_limit(f"login:{login_data.username}", limit=5, window=300)
    
    user = authenticate_user(db, login_data.username, login_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = AuthManager.create_access_token(
        data={"sub": user.username, "user_id": user.id}
    )
    
    return Token(
        access_token=access_token,
        token_type="bearer",
        expires_in=60 * 60  # 1 hour
    )


@app.post("/auth/register", response_model=UserResponse)
async def register(
    user_data: UserCreate,
    db: Session = Depends(DatabaseManager.get_db),
    current_user: Optional[User] = Depends(optional_user)
):
    """Register new user (admin only or if no users exist)"""
    # Check if this is the first user or if current user is admin
    user_count = db.query(User).count()
    
    if user_count > 0 and (not current_user or not current_user.is_admin):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can create new users"
        )
    
    user = create_user(
        db=db,
        username=user_data.username,
        email=user_data.email,
        password=user_data.password,
        is_admin=(user_count == 0)  # First user is admin
    )
    
    return UserResponse.from_orm(user)


# API Key endpoints
@app.post("/auth/api-keys", response_model=APIKeyResponse)
async def create_api_key_endpoint(
    api_key_data: APIKeyCreate,
    db: Session = Depends(DatabaseManager.get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Create new API key"""
    db_api_key, api_key = create_api_key(
        db=db,
        user_id=current_user.id,
        name=api_key_data.name,
        expires_in_days=api_key_data.expires_in_days
    )
    
    response = APIKeyResponse.from_orm(db_api_key)
    response.key = api_key  # Only show the key on creation
    return response


@app.get("/auth/api-keys", response_model=List[APIKeyResponse])
async def list_api_keys(
    db: Session = Depends(DatabaseManager.get_db),
    current_user: User = Depends(get_current_active_user)
):
    """List user's API keys"""
    api_keys = db.query(APIKey).filter(APIKey.user_id == current_user.id).all()
    return [APIKeyResponse.from_orm(key) for key in api_keys]


@app.delete("/auth/api-keys/{key_id}")
async def delete_api_key(
    key_id: int,
    db: Session = Depends(DatabaseManager.get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Delete API key"""
    api_key = db.query(APIKey).filter(
        APIKey.id == key_id,
        APIKey.user_id == current_user.id
    ).first()
    
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found"
        )
    
    db.delete(api_key)
    db.commit()
    
    return {"message": "API key deleted successfully"}


# User management endpoints
@app.get("/users/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_active_user)):
    """Get current user information"""
    return UserResponse.from_orm(current_user)


@app.put("/users/me", response_model=UserResponse)
async def update_current_user(
    user_update: UserUpdate,
    db: Session = Depends(DatabaseManager.get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Update current user information"""
    update_data = user_update.dict(exclude_unset=True)
    
    for field, value in update_data.items():
        setattr(current_user, field, value)
    
    db.commit()
    db.refresh(current_user)
    
    return UserResponse.from_orm(current_user)


@app.get("/users", response_model=List[UserResponse])
async def list_users(
    db: Session = Depends(DatabaseManager.get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """List all users (admin only)"""
    users = db.query(User).all()
    return [UserResponse.from_orm(user) for user in users]


# Company endpoints
@app.get("/companies", response_model=List[CompanyResponse])
async def list_companies(
    filters: CompanyFilter = Depends(),
    db: Session = Depends(DatabaseManager.get_db),
    current_user: Optional[User] = Depends(optional_user)
):
    """List companies with optional filtering"""
    query = db.query(Company)
    
    if filters.priority:
        query = query.filter(Company.priority == filters.priority)
    
    if filters.status:
        query = query.filter(Company.status == filters.status)
    
    if filters.has_tokens is not None:
        if filters.has_tokens:
            query = query.filter(Company.tokens.isnot(None))
        else:
            query = query.filter(Company.tokens.is_(None))
    
    companies = query.offset(filters.offset).limit(filters.limit).all()
    return [CompanyResponse.from_orm(company) for company in companies]


@app.get("/companies/{company_id}", response_model=CompanyResponse)
async def get_company(
    company_id: int,
    db: Session = Depends(DatabaseManager.get_db),
    current_user: Optional[User] = Depends(optional_user)
):
    """Get company by ID"""
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company not found"
        )
    return CompanyResponse.from_orm(company)


@app.post("/companies", response_model=CompanyResponse)
async def create_company(
    company_data: CompanyCreate,
    db: Session = Depends(DatabaseManager.get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Create new company (admin only)"""
    # Check if company already exists
    existing = db.query(Company).filter(Company.name == company_data.name).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Company already exists"
        )
    
    company = Company(**company_data.dict())
    db.add(company)
    db.commit()
    db.refresh(company)
    
    return CompanyResponse.from_orm(company)


@app.put("/companies/{company_id}", response_model=CompanyResponse)
async def update_company(
    company_id: int,
    company_update: CompanyUpdate,
    db: Session = Depends(DatabaseManager.get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Update company (admin only)"""
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company not found"
        )
    
    update_data = company_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(company, field, value)
    
    db.commit()
    db.refresh(company)
    
    return CompanyResponse.from_orm(company)


# Alert endpoints
@app.get("/alerts", response_model=List[AlertResponse])
async def list_alerts(
    filters: AlertFilter = Depends(),
    db: Session = Depends(DatabaseManager.get_db),
    current_user: Optional[User] = Depends(optional_user)
):
    """List alerts with filtering"""
    check_rate_limit(f"alerts:{current_user.id if current_user else 'anonymous'}", limit=1000, window=3600)
    
    query = db.query(Alert)
    
    if filters.company_id:
        query = query.filter(Alert.company_id == filters.company_id)
    
    if filters.source:
        query = query.filter(Alert.source == filters.source)
    
    if filters.min_confidence is not None:
        query = query.filter(Alert.confidence >= filters.min_confidence)
    
    if filters.max_confidence is not None:
        query = query.filter(Alert.confidence <= filters.max_confidence)
    
    if filters.urgency_level:
        query = query.filter(Alert.urgency_level == filters.urgency_level)
    
    if filters.status:
        query = query.filter(Alert.status == filters.status)
    
    if filters.from_date:
        query = query.filter(Alert.created_at >= filters.from_date)
    
    if filters.to_date:
        query = query.filter(Alert.created_at <= filters.to_date)
    
    if filters.keywords:
        # Search in title and content
        keyword_filters = []
        for keyword in filters.keywords:
            keyword_filters.append(Alert.title.ilike(f"%{keyword}%"))
            keyword_filters.append(Alert.content.ilike(f"%{keyword}%"))
        query = query.filter(or_(*keyword_filters))
    
    alerts = query.order_by(desc(Alert.created_at)).offset(filters.offset).limit(filters.limit).all()
    return [AlertResponse.from_orm(alert) for alert in alerts]


@app.get("/alerts/{alert_id}", response_model=AlertResponse)
async def get_alert(
    alert_id: int,
    db: Session = Depends(DatabaseManager.get_db),
    current_user: Optional[User] = Depends(optional_user)
):
    """Get alert by ID"""
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert not found"
        )
    return AlertResponse.from_orm(alert)


@app.post("/alerts", response_model=AlertResponse)
async def create_alert(
    alert_data: AlertCreate,
    db: Session = Depends(DatabaseManager.get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Create new alert"""
    alert = Alert(**alert_data.dict(), user_id=current_user.id)
    db.add(alert)
    db.commit()
    db.refresh(alert)
    
    # Send real-time notification
    notification = AlertNotification(
        alert_id=alert.id,
        title=alert.title,
        company_name=alert.company.name if alert.company else None,
        confidence=alert.confidence,
        urgency_level=alert.urgency_level,
        source=alert.source,
        created_at=alert.created_at
    )
    
    await manager.broadcast({
        "type": "alert",
        "data": notification.dict(),
        "timestamp": datetime.now(timezone.utc).isoformat()
    })
    
    return AlertResponse.from_orm(alert)


@app.put("/alerts/{alert_id}", response_model=AlertResponse)
async def update_alert(
    alert_id: int,
    alert_update: AlertUpdate,
    db: Session = Depends(DatabaseManager.get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Update alert"""
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert not found"
        )
    
    update_data = alert_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(alert, field, value)
    
    db.commit()
    db.refresh(alert)
    
    return AlertResponse.from_orm(alert)


@app.put("/alerts/bulk", response_model=BulkOperationResult)
async def bulk_update_alerts(
    bulk_update: BulkAlertUpdate,
    db: Session = Depends(DatabaseManager.get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Bulk update alerts"""
    success_count = 0
    error_count = 0
    errors = []
    
    for alert_id in bulk_update.alert_ids:
        try:
            alert = db.query(Alert).filter(Alert.id == alert_id).first()
            if alert:
                if bulk_update.status:
                    alert.status = bulk_update.status
                if bulk_update.urgency_level:
                    alert.urgency_level = bulk_update.urgency_level
                success_count += 1
            else:
                error_count += 1
                errors.append({"alert_id": alert_id, "error": "Alert not found"})
        except Exception as e:
            error_count += 1
            errors.append({"alert_id": alert_id, "error": str(e)})
    
    db.commit()
    
    return BulkOperationResult(
        success_count=success_count,
        error_count=error_count,
        errors=errors
    )


# Statistics endpoints
@app.get("/statistics/alerts", response_model=AlertStatistics)
async def get_alert_statistics(
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(DatabaseManager.get_db),
    current_user: Optional[User] = Depends(optional_user)
):
    """Get alert statistics"""
    # Calculate date range
    end_date = datetime.now(timezone.utc)
    start_date = end_date - timedelta(days=days)
    
    # Total alerts
    total_alerts = db.query(Alert).filter(Alert.created_at >= start_date).count()
    
    # Alerts by source
    source_stats = db.query(
        Alert.source,
        func.count(Alert.id)
    ).filter(Alert.created_at >= start_date).group_by(Alert.source).all()
    
    alerts_by_source = {source: count for source, count in source_stats}
    
    # Other statistics would be calculated similarly...
    
    return AlertStatistics(
        total_alerts=total_alerts,
        alerts_by_source=alerts_by_source,
        alerts_by_confidence={},
        alerts_by_urgency={},
        alerts_by_company={},
        recent_trend={}
    )


@app.get("/statistics/system", response_model=SystemStatistics)
async def get_system_statistics(
    db: Session = Depends(DatabaseManager.get_db),
    current_user: Optional[User] = Depends(optional_user)
):
    """Get system statistics"""
    total_companies = db.query(Company).count()
    total_feeds = db.query(Feed).count()
    active_feeds = db.query(Feed).filter(Feed.is_active == True).count()
    total_alerts = db.query(Alert).count()
    
    # Recent alerts
    alerts_last_24h = db.query(Alert).filter(
        Alert.created_at >= datetime.now(timezone.utc) - timedelta(hours=24)
    ).count()
    
    alerts_last_7d = db.query(Alert).filter(
        Alert.created_at >= datetime.now(timezone.utc) - timedelta(days=7)
    ).count()
    
    # Average confidence
    avg_confidence_result = db.query(func.avg(Alert.confidence)).scalar()
    avg_confidence = float(avg_confidence_result) if avg_confidence_result else 0.0
    
    return SystemStatistics(
        total_companies=total_companies,
        total_feeds=total_feeds,
        active_feeds=active_feeds,
        total_alerts=total_alerts,
        alerts_last_24h=alerts_last_24h,
        alerts_last_7d=alerts_last_7d,
        avg_confidence=avg_confidence,
        system_uptime=0.0,  # TODO: Implement uptime tracking
        last_monitoring_session=None  # TODO: Implement session tracking
    )


# WebSocket endpoint for real-time updates
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates"""
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection alive and handle ping/pong
            data = await websocket.receive_text()
            message = json.loads(data)
            
            if message.get("type") == "ping":
                await websocket.send_json({
                    "type": "pong",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                })
    except WebSocketDisconnect:
        manager.disconnect(websocket)


if __name__ == "__main__":
    # Run the API server
    uvicorn.run(
        "api:app",
        host="0.0.0.0",
        port=int(os.getenv("API_PORT", "8000")),
        reload=os.getenv("DEBUG", "false").lower() == "true"
    )
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
from .seed_data import seed_all_data

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
            except (WebSocketDisconnect, ConnectionError) as e:
                logger.debug(f"Connection closed during broadcast: {e}")
                self.disconnect(connection)
            except Exception as e:
                logger.error(f"Unexpected error broadcasting message: {e}", exc_info=True)
    
    async def send_to_user(self, user_id: int, message: dict):
        """Send message to specific user"""
        if user_id in self.user_connections:
            for connection in self.user_connections[user_id]:
                try:
                    await connection.send_json(message)
                except (WebSocketDisconnect, ConnectionError) as e:
                    logger.debug(f"Connection closed during user message: {e}")
                    self.disconnect(connection, user_id)
                except Exception as e:
                    logger.error(f"Unexpected error sending to user: {e}", exc_info=True)


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
async def health_check(db: Session = Depends(DatabaseManager.get_db)):
    """Health check endpoint"""
    db_healthy = DatabaseManager.check_connection()
    redis_healthy = CacheManager.exists("health_check")

    # Test Redis
    if not redis_healthy:
        CacheManager.set("health_check", "ok", 60)
        redis_healthy = CacheManager.exists("health_check")

    # Get feed health statistics
    feeds_health = {"active": 0, "total": 0, "error_rate": 0.0, "inactive": 0}
    try:
        total_feeds = db.query(Feed).count()
        active_feeds = db.query(Feed).filter(Feed.is_active == True).count()
        feeds_with_errors = db.query(Feed).filter(Feed.failure_count > 0).count()

        feeds_health = {
            "total": total_feeds,
            "active": active_feeds,
            "inactive": total_feeds - active_feeds,
            "error_rate": feeds_with_errors / total_feeds if total_feeds > 0 else 0.0
        }
    except Exception as e:
        logger.error(f"Error getting feed health: {e}")

    # Get system metrics
    system_metrics = {"memory_percent": 0.0, "cpu_percent": 0.0, "disk_percent": 0.0}
    try:
        import psutil
        system_metrics = {
            "memory_percent": psutil.virtual_memory().percent,
            "cpu_percent": psutil.cpu_percent(interval=0.1),
            "disk_percent": psutil.disk_usage('/').percent
        }
    except (ImportError, Exception) as e:
        # psutil not available or error getting metrics
        logger.debug(f"System metrics unavailable: {e}")

    return HealthCheck(
        status="healthy" if db_healthy and redis_healthy else "unhealthy",
        timestamp=datetime.now(timezone.utc),
        database=db_healthy,
        redis=redis_healthy,
        feeds_health=feeds_health,
        system_metrics=system_metrics
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
    current_user: Optional[User] = Depends(optional_user)
):
    """Create new company (public access)"""
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
    current_user: Optional[User] = Depends(optional_user)
):
    """Update company (public access)"""
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


@app.delete("/companies/{company_id}")
async def delete_company(
    company_id: int,
    db: Session = Depends(DatabaseManager.get_db),
    current_user: Optional[User] = Depends(optional_user)
):
    """Delete company (public access)"""
    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company not found"
        )

    db.delete(company)
    db.commit()

    return {"message": "Company deleted successfully"}


# Feed endpoints
@app.get("/feeds", response_model=List[FeedResponse])
async def list_feeds(
    limit: int = Query(100, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(DatabaseManager.get_db),
    current_user: Optional[User] = Depends(optional_user)
):
    """List feeds (public access)"""
    feeds = db.query(Feed).offset(offset).limit(limit).all()
    return [FeedResponse.from_orm(feed) for feed in feeds]


@app.get("/feeds/{feed_id}", response_model=FeedResponse)
async def get_feed(
    feed_id: int,
    db: Session = Depends(DatabaseManager.get_db),
    current_user: Optional[User] = Depends(optional_user)
):
    """Get feed by ID (public access)"""
    feed = db.query(Feed).filter(Feed.id == feed_id).first()
    if not feed:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Feed not found"
        )
    return FeedResponse.from_orm(feed)


@app.post("/feeds", response_model=FeedResponse)
async def create_feed(
    feed_data: FeedCreate,
    db: Session = Depends(DatabaseManager.get_db),
    current_user: Optional[User] = Depends(optional_user)
):
    """Create new feed (public access)"""
    # Check if feed already exists
    existing = db.query(Feed).filter(Feed.url == feed_data.url).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Feed with this URL already exists"
        )

    feed = Feed(**feed_data.dict())
    db.add(feed)
    db.commit()
    db.refresh(feed)

    return FeedResponse.from_orm(feed)


@app.put("/feeds/{feed_id}", response_model=FeedResponse)
async def update_feed(
    feed_id: int,
    feed_update: FeedUpdate,
    db: Session = Depends(DatabaseManager.get_db),
    current_user: Optional[User] = Depends(optional_user)
):
    """Update feed (public access)"""
    feed = db.query(Feed).filter(Feed.id == feed_id).first()
    if not feed:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Feed not found"
        )

    update_data = feed_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(feed, field, value)

    db.commit()
    db.refresh(feed)

    return FeedResponse.from_orm(feed)


@app.delete("/feeds/{feed_id}")
async def delete_feed(
    feed_id: int,
    db: Session = Depends(DatabaseManager.get_db),
    current_user: Optional[User] = Depends(optional_user)
):
    """Delete feed (public access)"""
    feed = db.query(Feed).filter(Feed.id == feed_id).first()
    if not feed:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Feed not found"
        )

    db.delete(feed)
    db.commit()

    return {"message": "Feed deleted successfully"}


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

    # Alerts by confidence (group by 10% buckets)
    confidence_stats = db.query(
        func.floor(Alert.confidence * 10) / 10,
        func.count(Alert.id)
    ).filter(Alert.created_at >= start_date).group_by(
        func.floor(Alert.confidence * 10) / 10
    ).all()
    alerts_by_confidence = {f"{int(conf*100)}%": count for conf, count in confidence_stats}

    # Alerts by urgency
    urgency_stats = db.query(
        Alert.urgency_level,
        func.count(Alert.id)
    ).filter(Alert.created_at >= start_date).group_by(Alert.urgency_level).all()
    alerts_by_urgency = {urgency or 'none': count for urgency, count in urgency_stats}

    # Alerts by company
    company_stats = db.query(
        Company.name,
        func.count(Alert.id)
    ).join(Alert, Company.id == Alert.company_id).filter(
        Alert.created_at >= start_date
    ).group_by(Company.name).limit(20).all()
    alerts_by_company = {company: count for company, count in company_stats}

    # Recent trend (last 7 days)
    recent_trend = {}
    for i in range(min(days, 7)):
        day = end_date - timedelta(days=i)
        day_start = day.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day.replace(hour=23, minute=59, second=59, microsecond=999999)
        count = db.query(Alert).filter(
            Alert.created_at.between(day_start, day_end)
        ).count()
        recent_trend[day.strftime("%Y-%m-%d")] = count

    return AlertStatistics(
        total_alerts=total_alerts,
        alerts_by_source=alerts_by_source,
        alerts_by_confidence=alerts_by_confidence,
        alerts_by_urgency=alerts_by_urgency,
        alerts_by_company=alerts_by_company,
        recent_trend=recent_trend
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

    # Get last monitoring session
    last_session = db.query(MonitoringSession).order_by(
        desc(MonitoringSession.start_time)
    ).first()

    # Calculate uptime from session history
    total_sessions = db.query(MonitoringSession).count()
    failed_sessions = db.query(MonitoringSession).filter(
        MonitoringSession.status == 'failed'
    ).count()

    system_uptime = 100.0
    if total_sessions > 0:
        system_uptime = ((total_sessions - failed_sessions) / total_sessions) * 100

    last_monitoring_session = last_session.start_time if last_session else None

    return SystemStatistics(
        total_companies=total_companies,
        total_feeds=total_feeds,
        active_feeds=active_feeds,
        total_alerts=total_alerts,
        alerts_last_24h=alerts_last_24h,
        alerts_last_7d=alerts_last_7d,
        avg_confidence=avg_confidence,
        system_uptime=system_uptime,
        last_monitoring_session=last_monitoring_session
    )


# Seed data endpoint
@app.post("/seed-data")
async def seed_database():
    """Seed database with initial data from config.py (public access)"""
    try:
        result = seed_all_data()
        return result
    except Exception as e:
        logger.error(f"Error seeding data: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to seed data: {str(e)}"
        )


# Monitoring endpoints
@app.post("/monitoring/trigger")
async def trigger_monitoring_cycle(db: Session = Depends(DatabaseManager.get_db)):
    """Trigger a manual monitoring cycle (public access)"""
    try:
        import uuid
        import sys
        from pathlib import Path

        # Add parent directory to sys.path so config.py can be imported
        project_root = Path(__file__).parent.parent
        if str(project_root) not in sys.path:
            sys.path.insert(0, str(project_root))

        # Import the monitor after fixing sys.path
        from .main_optimized import OptimizedCryptoTGEMonitor

        # Generate session ID for this monitoring run
        session_id = str(uuid.uuid4())

        # Create monitoring session in database
        monitoring_session = MonitoringSession(
            session_id=session_id,
            status="running"
        )
        db.add(monitoring_session)
        db.commit()
        db.refresh(monitoring_session)

        # Run monitoring cycle in background with timeout
        def run_cycle():
            db_session = None
            try:
                import time
                import signal
                import threading
                start_time = time.time()

                # Set maximum execution time (5 minutes)
                MAX_EXECUTION_TIME = 300
                cycle_completed = threading.Event()

                def execute_cycle():
                    nonlocal db_session
                    try:
                        # Get database session for real-time updates
                        db_session = DatabaseManager.SessionLocal()
                        logger.info(f"Database session created for {session_id}")

                        # Update progress IMMEDIATELY to show we started
                        session = db_session.query(MonitoringSession).filter(
                            MonitoringSession.session_id == session_id
                        ).first()
                        if session:
                            session.performance_metrics = {'phase': 'initializing', 'timestamp': datetime.now(timezone.utc).isoformat()}
                            db_session.commit()
                            logger.info(f"Initial progress updated for {session_id}")

                        # Create monitor instance with session_id and db_session
                        logger.info(f"Creating monitor for session {session_id}...")
                        monitor = OptimizedCryptoTGEMonitor(swarm_enabled=False)
                        logger.info(f"Monitor instance created for {session_id}")

                        monitor.session_id = session_id
                        monitor.db_session = db_session
                        logger.info(f"Monitor configured, starting cycle for session {session_id}")

                        # Run monitoring cycle (will update session in real-time)
                        monitor.run_monitoring_cycle()
                        cycle_completed.set()
                        logger.info(f"Monitoring cycle completed for {session_id}")
                    except Exception as e:
                        logger.error(f"Error in execute_cycle for {session_id}: {str(e)}", exc_info=True)
                        raise

                # Start cycle in thread
                cycle_thread = threading.Thread(target=execute_cycle, daemon=True)
                cycle_thread.start()

                # Wait for completion or timeout
                cycle_thread.join(timeout=MAX_EXECUTION_TIME)

                if not cycle_completed.is_set():
                    logger.error(f"Monitoring cycle {session_id} timed out after {MAX_EXECUTION_TIME}s")
                    raise TimeoutError(f"Scraping cycle exceeded maximum execution time of {MAX_EXECUTION_TIME}s")

                # Final update with complete results
                session = db_session.query(MonitoringSession).filter(
                    MonitoringSession.session_id == session_id
                ).first()

                if session:
                    session.end_time = datetime.now(timezone.utc)
                    session.status = "completed"
                    session.articles_processed = monitor.current_cycle_stats['articles_processed']
                    session.tweets_processed = monitor.current_cycle_stats['tweets_processed']
                    session.alerts_generated = monitor.current_cycle_stats['alerts_generated']
                    session.feeds_processed = monitor.current_cycle_stats['feeds_processed']
                    session.errors_encountered = monitor.current_cycle_stats['errors_encountered']

                    # Update performance metrics
                    if not session.performance_metrics:
                        session.performance_metrics = {}

                    session.performance_metrics.update({
                        "cycle_time": time.time() - start_time,
                        "total_articles": monitor.current_cycle_stats['articles_processed'],
                        "total_tweets": monitor.current_cycle_stats['tweets_processed'],
                        "total_feeds": monitor.current_cycle_stats['feeds_processed'],
                        "total_alerts": monitor.current_cycle_stats['alerts_generated'],
                        "total_errors": monitor.current_cycle_stats['errors_encountered']
                    })

                    db_session.commit()

                logger.info(f"Monitoring cycle {session_id} completed successfully")

            except Exception as e:
                logger.error(f"Error in monitoring cycle {session_id}: {str(e)}", exc_info=True)

                # Update session as failed
                if db_session:
                    try:
                        session = db_session.query(MonitoringSession).filter(
                            MonitoringSession.session_id == session_id
                        ).first()
                        if session:
                            session.end_time = datetime.now(timezone.utc)
                            session.status = "failed"
                            session.errors_encountered = (session.errors_encountered or 0) + 1

                            error_entry = {
                                "error": str(e),
                                "timestamp": datetime.now(timezone.utc).isoformat(),
                                "type": type(e).__name__
                            }

                            if session.error_log:
                                session.error_log.append(error_entry)
                            else:
                                session.error_log = [error_entry]

                            db_session.commit()
                    except Exception as update_error:
                        logger.error(f"Error updating failed session: {str(update_error)}")

            finally:
                if db_session:
                    db_session.close()

        # Start background thread
        import threading
        thread = threading.Thread(target=run_cycle, daemon=True)
        thread.start()

        return {
            "message": "Monitoring cycle started successfully",
            "session_id": session_id
        }
    except Exception as e:
        logger.error(f"Error starting monitoring cycle: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start monitoring cycle: {str(e)}"
        )


@app.get("/monitoring/session/{session_id}")
async def get_monitoring_session(
    session_id: str,
    db: Session = Depends(DatabaseManager.get_db)
):
    """Get monitoring session results"""
    session = db.query(MonitoringSession).filter(
        MonitoringSession.session_id == session_id
    ).first()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Monitoring session not found"
        )

    return session.to_dict()


@app.get("/monitoring/session/{session_id}/progress")
async def get_monitoring_session_progress(
    session_id: str,
    db: Session = Depends(DatabaseManager.get_db)
):
    """Get real-time progress of monitoring session"""
    session = db.query(MonitoringSession).filter(
        MonitoringSession.session_id == session_id
    ).first()

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Monitoring session not found"
        )

    # Calculate progress percentage
    progress_percentage = 0
    current_phase = "starting"

    if session.performance_metrics:
        current_phase = session.performance_metrics.get('phase', 'starting')

        # Estimate progress based on phase
        phase_progress = {
            'starting': 5,
            'scraping_news': 15,
            'processing_news': 35,
            'news_complete': 45,
            'scraping_twitter': 55,
            'processing_twitter': 75,
            'twitter_complete': 80,
            'updating_feeds': 85,
            'processing_alerts': 90,
            'saving_alerts': 95,
            'sending_email': 97,
            'completed': 100
        }

        progress_percentage = phase_progress.get(current_phase, 0)

    # Build progress response
    response = {
        "session_id": session.session_id,
        "status": session.status,
        "progress_percentage": progress_percentage,
        "current_phase": current_phase,
        "start_time": session.start_time.isoformat() if session.start_time else None,
        "end_time": session.end_time.isoformat() if session.end_time else None,
        "metrics": {
            "articles_processed": session.articles_processed or 0,
            "tweets_processed": session.tweets_processed or 0,
            "feeds_processed": session.feeds_processed or 0,
            "alerts_generated": session.alerts_generated or 0,
            "errors_encountered": session.errors_encountered or 0
        },
        "performance_metrics": session.performance_metrics or {},
        "error_log": session.error_log or [],
        "debug_info": {
            "session_age_seconds": (datetime.now(timezone.utc) - session.start_time).total_seconds() if session.start_time else 0,
            "has_performance_metrics": bool(session.performance_metrics)
        }
    }

    return response


@app.get("/monitoring/sessions/recent")
async def get_recent_monitoring_sessions(
    limit: int = Query(10, le=100),
    db: Session = Depends(DatabaseManager.get_db)
):
    """Get recent monitoring sessions"""
    sessions = db.query(MonitoringSession).order_by(
        desc(MonitoringSession.start_time)
    ).limit(limit).all()

    return [session.to_dict() for session in sessions]


@app.post("/monitoring/email-summary")
async def send_email_summary():
    """Send email summary of recent alerts (public access)"""
    try:
        import sys
        from pathlib import Path

        # Add parent directory to sys.path so config.py can be imported
        project_root = Path(__file__).parent.parent
        if str(project_root) not in sys.path:
            sys.path.insert(0, str(project_root))

        # Import the monitor after fixing sys.path
        from .main_optimized import OptimizedCryptoTGEMonitor

        # Run email summary in background
        def send_summary():
            try:
                monitor = OptimizedCryptoTGEMonitor(swarm_enabled=False)
                monitor.send_weekly_summary()
                logger.info("Email summary sent successfully")
            except Exception as e:
                logger.error(f"Error sending email summary: {str(e)}")

        # Start background thread
        import threading
        thread = threading.Thread(target=send_summary, daemon=True)
        thread.start()

        return {
            "message": "Email summary is being sent"
        }
    except Exception as e:
        logger.error(f"Error sending email summary: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send email summary: {str(e)}"
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
"""
Pydantic schemas for TGE Monitor API
Request/response models with validation
"""

from pydantic import BaseModel, EmailStr, field_validator, model_validator, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class Priority(str, Enum):
    """Priority enumeration"""
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class UrgencyLevel(str, Enum):
    """Urgency level enumeration"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class SourceType(str, Enum):
    """Source type enumeration"""
    TWITTER = "twitter"
    NEWS = "news"
    MANUAL = "manual"


class AlertStatus(str, Enum):
    """Alert status enumeration"""
    ACTIVE = "active"
    ARCHIVED = "archived"
    FALSE_POSITIVE = "false_positive"


# User schemas
class UserBase(BaseModel):
    """Base user schema"""
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr


class UserCreate(UserBase):
    """User creation schema"""
    password: str = Field(..., min_length=8)

    @field_validator('password')
    @classmethod
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        return v


class UserUpdate(BaseModel):
    """User update schema"""
    username: Optional[str] = Field(None, min_length=3, max_length=50)
    email: Optional[EmailStr] = None
    is_active: Optional[bool] = None


class UserResponse(UserBase):
    """User response schema"""
    id: int
    is_active: bool
    is_admin: bool
    created_at: Optional[datetime]
    last_login: Optional[datetime]
    
    class Config:
        from_attributes = True


# Authentication schemas
class Token(BaseModel):
    """JWT token response"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class TokenData(BaseModel):
    """Token data schema"""
    username: Optional[str] = None
    user_id: Optional[int] = None


class LoginRequest(BaseModel):
    """Login request schema"""
    username: str
    password: str


# API Key schemas
class APIKeyCreate(BaseModel):
    """API key creation schema"""
    name: str = Field(..., min_length=1, max_length=100)
    expires_in_days: Optional[int] = Field(None, ge=1, le=365)


class APIKeyResponse(BaseModel):
    """API key response schema"""
    id: int
    name: str
    key: Optional[str] = None  # Only provided on creation
    is_active: bool
    created_at: datetime
    expires_at: Optional[datetime]
    last_used: Optional[datetime]
    usage_count: int
    
    class Config:
        from_attributes = True


# Company schemas
class CompanyBase(BaseModel):
    """Base company schema"""
    name: str = Field(..., min_length=1, max_length=100)
    aliases: List[str] = Field(default_factory=list)
    tokens: List[str] = Field(default_factory=list)
    priority: Priority = Priority.MEDIUM
    status: str = "active"
    website: Optional[str] = None
    twitter_handle: Optional[str] = None
    description: Optional[str] = None
    exclusions: List[str] = Field(default_factory=list)

    @field_validator('aliases', 'tokens', 'exclusions', mode='before')
    @classmethod
    def convert_none_to_list(cls, v):
        """Convert None to empty list for database compatibility"""
        return v if v is not None else []


class CompanyCreate(CompanyBase):
    """Company creation schema"""
    pass


class CompanyUpdate(BaseModel):
    """Company update schema"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    aliases: Optional[List[str]] = None
    tokens: Optional[List[str]] = None
    priority: Optional[Priority] = None
    status: Optional[str] = None
    website: Optional[str] = None
    twitter_handle: Optional[str] = None
    description: Optional[str] = None
    exclusions: Optional[List[str]] = None


class CompanyResponse(CompanyBase):
    """Company response schema"""
    id: int
    created_at: Optional[datetime]
    updated_at: Optional[datetime]
    
    class Config:
        from_attributes = True


# Alert schemas
class AlertBase(BaseModel):
    """Base alert schema"""
    title: str = Field(..., max_length=500)
    content: str
    source: SourceType
    source_url: Optional[str] = None
    confidence: float = Field(..., ge=0.0, le=1.0)
    company_id: Optional[int] = None
    keywords_matched: Optional[List[str]] = None
    tokens_mentioned: Optional[List[str]] = None
    analysis_data: Optional[Dict[str, Any]] = None
    sentiment_score: Optional[float] = Field(None, ge=-1.0, le=1.0)
    urgency_level: UrgencyLevel = UrgencyLevel.MEDIUM


class AlertCreate(AlertBase):
    """Alert creation schema"""
    pass


class AlertUpdate(BaseModel):
    """Alert update schema"""
    title: Optional[str] = Field(None, max_length=500)
    status: Optional[AlertStatus] = None
    urgency_level: Optional[UrgencyLevel] = None
    sentiment_score: Optional[float] = Field(None, ge=-1.0, le=1.0)


class AlertResponse(AlertBase):
    """Alert response schema"""
    id: int
    status: AlertStatus
    company: Optional[CompanyResponse] = None
    created_at: Optional[datetime]
    updated_at: Optional[datetime]
    
    class Config:
        from_attributes = True


# Feed schemas
class FeedBase(BaseModel):
    """Base feed schema"""
    name: str = Field(..., max_length=200)
    url: str = Field(..., max_length=1000)
    type: str = "rss"
    priority: int = Field(default=3, ge=1, le=5)
    is_active: bool = True


class FeedCreate(FeedBase):
    """Feed creation schema"""
    pass


class FeedUpdate(BaseModel):
    """Feed update schema"""
    name: Optional[str] = Field(None, max_length=200)
    url: Optional[str] = Field(None, max_length=1000)
    type: Optional[str] = None
    priority: Optional[int] = Field(None, ge=1, le=5)
    is_active: Optional[bool] = None


class FeedResponse(FeedBase):
    """Feed response schema"""
    id: int
    success_count: int
    failure_count: int
    last_fetch: Optional[datetime]
    last_success: Optional[datetime]
    last_failure: Optional[datetime]
    last_error: Optional[str]
    articles_found: int
    tge_alerts_found: int
    created_at: Optional[datetime]
    updated_at: Optional[datetime]
    
    class Config:
        from_attributes = True


# Monitoring session schemas
class MonitoringSessionResponse(BaseModel):
    """Monitoring session response schema"""
    id: int
    session_id: str
    start_time: Optional[datetime]
    end_time: Optional[datetime]
    status: str
    feeds_processed: int
    articles_processed: int
    tweets_processed: int
    alerts_generated: int
    errors_encountered: int
    performance_metrics: Dict[str, Any]
    error_log: List[Dict[str, Any]]
    
    class Config:
        from_attributes = True


# System metrics schemas
class SystemMetricCreate(BaseModel):
    """System metric creation schema"""
    metric_type: str = Field(..., max_length=50)
    metric_name: str = Field(..., max_length=100)
    value: float
    unit: Optional[str] = Field(None, max_length=20)
    tags: Optional[Dict[str, Any]] = None


class SystemMetricResponse(BaseModel):
    """System metric response schema"""
    id: int
    timestamp: datetime
    metric_type: str
    metric_name: str
    value: float
    unit: Optional[str]
    tags: Dict[str, Any]
    
    class Config:
        from_attributes = True


# Search and filter schemas
class AlertFilter(BaseModel):
    """Alert filtering schema"""
    company_id: Optional[int] = None
    source: Optional[SourceType] = None
    min_confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    max_confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    urgency_level: Optional[UrgencyLevel] = None
    status: Optional[AlertStatus] = None
    from_date: Optional[datetime] = None
    to_date: Optional[datetime] = None
    keywords: Optional[List[str]] = None
    limit: int = Field(default=100, ge=1, le=1000)
    offset: int = Field(default=0, ge=0)

    @model_validator(mode='after')
    def convert_none_to_list_keywords(self):
        """Convert None to empty list for compatibility"""
        if self.keywords is None:
            self.keywords = []
        return self


class CompanyFilter(BaseModel):
    """Company filtering schema"""
    priority: Optional[Priority] = None
    status: Optional[str] = None
    has_tokens: Optional[bool] = None
    limit: int = Field(default=100, ge=1, le=1000)
    offset: int = Field(default=0, ge=0)


# Statistics schemas
class AlertStatistics(BaseModel):
    """Alert statistics schema"""
    total_alerts: int
    alerts_by_source: Dict[str, int]
    alerts_by_confidence: Dict[str, int]
    alerts_by_urgency: Dict[str, int]
    alerts_by_company: Dict[str, int]
    recent_trend: Dict[str, int]  # Last 7 days


class SystemStatistics(BaseModel):
    """System statistics schema"""
    total_companies: int
    total_feeds: int
    active_feeds: int
    total_alerts: int
    alerts_last_24h: int
    alerts_last_7d: int
    avg_confidence: float
    system_uptime: float
    last_monitoring_session: Optional[datetime]


# Real-time schemas for WebSocket
class WebSocketMessage(BaseModel):
    """WebSocket message schema"""
    type: str  # alert, status, error, ping
    data: Dict[str, Any]
    timestamp: datetime


class AlertNotification(BaseModel):
    """Real-time alert notification"""
    alert_id: int
    title: str
    company_name: Optional[str]
    confidence: float
    urgency_level: UrgencyLevel
    source: SourceType
    created_at: datetime


# Bulk operation schemas
class BulkAlertUpdate(BaseModel):
    """Bulk alert update schema"""
    alert_ids: List[int]
    status: Optional[AlertStatus] = None
    urgency_level: Optional[UrgencyLevel] = None


class BulkOperationResult(BaseModel):
    """Bulk operation result schema"""
    success_count: int
    error_count: int
    errors: List[Dict[str, Any]] = Field(default_factory=list)


# Health check schemas
class HealthCheck(BaseModel):
    """Health check response schema"""
    status: str
    timestamp: datetime
    database: bool
    redis: bool
    feeds_health: Dict[str, Any]
    system_metrics: Dict[str, Any]


# Export schemas
class ExportRequest(BaseModel):
    """Data export request schema"""
    format: str = Field(default="json", pattern="^(json|csv|xlsx)$")
    filters: Optional[AlertFilter] = None
    include_analysis: bool = False


class ExportResponse(BaseModel):
    """Data export response schema"""
    export_id: str
    status: str
    download_url: Optional[str] = None
    created_at: datetime
    expires_at: datetime
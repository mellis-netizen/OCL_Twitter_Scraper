"""
SQLAlchemy models for TGE Monitor database
Enhanced data models with relationships and indexing
"""

from sqlalchemy import Column, Integer, String, DateTime, Float, Text, Boolean, JSON, ForeignKey, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime, timezone
from typing import Dict, List, Optional
import json

from .database import Base


class User(Base):
    """User model for API authentication"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_login = Column(DateTime(timezone=True))
    
    # Relationships
    alerts = relationship("Alert", back_populates="user")
    api_keys = relationship("APIKey", back_populates="user")
    
    def to_dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "is_active": self.is_active,
            "is_admin": self.is_admin,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_login": self.last_login.isoformat() if self.last_login else None
        }


class APIKey(Base):
    """API key model for authenticated access"""
    __tablename__ = "api_keys"
    
    id = Column(Integer, primary_key=True, index=True)
    key_hash = Column(String(255), unique=True, index=True, nullable=False)
    name = Column(String(100), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True))
    last_used = Column(DateTime(timezone=True))
    usage_count = Column(Integer, default=0)
    
    # Relationships
    user = relationship("User", back_populates="api_keys")
    
    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "user_id": self.user_id,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "last_used": self.last_used.isoformat() if self.last_used else None,
            "usage_count": self.usage_count
        }


class Company(Base):
    """Company model for tracking monitored companies"""
    __tablename__ = "companies"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, index=True, nullable=False)
    aliases = Column(JSON)  # List of company aliases
    tokens = Column(JSON)   # List of token symbols
    priority = Column(String(20), index=True, default="MEDIUM")  # HIGH, MEDIUM, LOW
    status = Column(String(30), index=True, default="active")    # active, pre_token, has_token, etc.
    website = Column(String(255))
    twitter_handle = Column(String(50))
    description = Column(Text)
    exclusions = Column(JSON)  # List of exclusion patterns
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    alerts = relationship("Alert", back_populates="company")
    
    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "aliases": self.aliases or [],
            "tokens": self.tokens or [],
            "priority": self.priority,
            "status": self.status,
            "website": self.website,
            "twitter_handle": self.twitter_handle,
            "description": self.description,
            "exclusions": self.exclusions or [],
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }


class Alert(Base):
    """Alert model for TGE alerts and notifications"""
    __tablename__ = "alerts"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(500), nullable=False)
    content = Column(Text, nullable=False)
    source = Column(String(50), index=True, nullable=False)  # twitter, news, manual
    source_url = Column(String(1000))
    confidence = Column(Float, index=True, nullable=False)
    company_id = Column(Integer, ForeignKey("companies.id"))
    keywords_matched = Column(JSON)  # List of matched keywords
    tokens_mentioned = Column(JSON) # List of token symbols found
    analysis_data = Column(JSON)    # Full analysis results
    sentiment_score = Column(Float)
    urgency_level = Column(String(20), index=True, default="medium")  # low, medium, high, critical
    status = Column(String(20), index=True, default="active")  # active, archived, false_positive
    user_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    company = relationship("Company", back_populates="alerts")
    user = relationship("User", back_populates="alerts")
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_alerts_company_created', 'company_id', 'created_at'),
        Index('idx_alerts_confidence_created', 'confidence', 'created_at'),
        Index('idx_alerts_source_created', 'source', 'created_at'),
    )
    
    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "content": self.content,
            "source": self.source,
            "source_url": self.source_url,
            "confidence": self.confidence,
            "company_id": self.company_id,
            "company": self.company.to_dict() if self.company else None,
            "keywords_matched": self.keywords_matched or [],
            "tokens_mentioned": self.tokens_mentioned or [],
            "analysis_data": self.analysis_data or {},
            "sentiment_score": self.sentiment_score,
            "urgency_level": self.urgency_level,
            "status": self.status,
            "user_id": self.user_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }


class Feed(Base):
    """Feed model for tracking news sources"""
    __tablename__ = "feeds"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    url = Column(String(1000), unique=True, index=True, nullable=False)
    type = Column(String(50), default="rss")  # rss, atom, json
    priority = Column(Integer, default=3)  # 1=highest, 5=lowest
    is_active = Column(Boolean, default=True)
    success_count = Column(Integer, default=0)
    failure_count = Column(Integer, default=0)
    last_fetch = Column(DateTime(timezone=True))
    last_success = Column(DateTime(timezone=True))
    last_failure = Column(DateTime(timezone=True))
    last_error = Column(Text)
    articles_found = Column(Integer, default=0)
    tge_alerts_found = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "url": self.url,
            "type": self.type,
            "priority": self.priority,
            "is_active": self.is_active,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "last_fetch": self.last_fetch.isoformat() if self.last_fetch else None,
            "last_success": self.last_success.isoformat() if self.last_success else None,
            "last_failure": self.last_failure.isoformat() if self.last_failure else None,
            "last_error": self.last_error,
            "articles_found": self.articles_found,
            "tge_alerts_found": self.tge_alerts_found,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }


class MonitoringSession(Base):
    """Monitoring session model for tracking runs"""
    __tablename__ = "monitoring_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(100), unique=True, index=True, nullable=False)
    start_time = Column(DateTime(timezone=True), server_default=func.now())
    end_time = Column(DateTime(timezone=True))
    status = Column(String(20), index=True, default="running")  # running, completed, failed
    feeds_processed = Column(Integer, default=0)
    articles_processed = Column(Integer, default=0)
    tweets_processed = Column(Integer, default=0)
    alerts_generated = Column(Integer, default=0)
    errors_encountered = Column(Integer, default=0)
    performance_metrics = Column(JSON)
    error_log = Column(JSON)
    
    def to_dict(self):
        return {
            "id": self.id,
            "session_id": self.session_id,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "status": self.status,
            "feeds_processed": self.feeds_processed,
            "articles_processed": self.articles_processed,
            "tweets_processed": self.tweets_processed,
            "alerts_generated": self.alerts_generated,
            "errors_encountered": self.errors_encountered,
            "performance_metrics": self.performance_metrics or {},
            "error_log": self.error_log or []
        }


class SystemMetrics(Base):
    """System metrics model for performance monitoring"""
    __tablename__ = "system_metrics"
    
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    metric_type = Column(String(50), index=True, nullable=False)  # cpu, memory, api_calls, etc.
    metric_name = Column(String(100), index=True, nullable=False)
    value = Column(Float, nullable=False)
    unit = Column(String(20))  # %, MB, requests/min, etc.
    tags = Column(JSON)  # Additional metadata
    
    # Index for time-series queries
    __table_args__ = (
        Index('idx_metrics_type_time', 'metric_type', 'timestamp'),
        Index('idx_metrics_name_time', 'metric_name', 'timestamp'),
    )
    
    def to_dict(self):
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "metric_type": self.metric_type,
            "metric_name": self.metric_name,
            "value": self.value,
            "unit": self.unit,
            "tags": self.tags or {}
        }


# Database initialization utilities
def create_sample_data():
    """Create sample data for development/testing"""
    from .database import SessionLocal
    
    db = SessionLocal()
    try:
        # Create sample companies if they don't exist
        companies_data = [
            {
                "name": "Caldera",
                "aliases": ["Caldera Labs", "Caldera Protocol"],
                "tokens": ["CAL"],
                "priority": "HIGH",
                "status": "pre_token",
                "twitter_handle": "@CalderaXYZ"
            },
            {
                "name": "Fabric",
                "aliases": ["Fabric Protocol", "Fabric Labs"],
                "tokens": ["FAB"],
                "priority": "HIGH",
                "status": "pre_token",
                "twitter_handle": "@fabric_xyz"
            }
        ]
        
        for company_data in companies_data:
            existing = db.query(Company).filter(Company.name == company_data["name"]).first()
            if not existing:
                company = Company(**company_data)
                db.add(company)
        
        # Create sample feeds
        feeds_data = [
            {
                "name": "The Block",
                "url": "https://www.theblock.co/rss.xml",
                "priority": 1
            },
            {
                "name": "Decrypt",
                "url": "https://decrypt.co/feed",
                "priority": 1
            }
        ]
        
        for feed_data in feeds_data:
            existing = db.query(Feed).filter(Feed.url == feed_data["url"]).first()
            if not existing:
                feed = Feed(**feed_data)
                db.add(feed)
        
        db.commit()
        print("Sample data created successfully")
        
    except Exception as e:
        db.rollback()
        print(f"Error creating sample data: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    # Test model creation
    from .database import init_db
    
    print("Creating database tables...")
    init_db()
    
    print("Creating sample data...")
    create_sample_data()
    
    print("Database setup complete!")
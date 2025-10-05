"""
Database configuration and connection management for TGE Monitor
PostgreSQL with SQLAlchemy ORM for enhanced data persistence
"""

import os
import logging
from sqlalchemy import create_engine, MetaData
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from typing import Generator
import redis
from contextlib import contextmanager

logger = logging.getLogger(__name__)

# Database configuration from environment
DATABASE_URL = os.getenv(
    'DATABASE_URL', 
    'postgresql://computer@localhost:5432/tge_monitor'
)

# Redis configuration for caching
REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')

# SQLAlchemy setup
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=300,
    echo=False  # Set to True for SQL logging in development
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Redis client
try:
    redis_client = redis.from_url(REDIS_URL, decode_responses=True)
    redis_client.ping()  # Test connection
    logger.info("Redis connection established")
except Exception as e:
    logger.warning(f"Redis connection failed: {e}. Caching will be disabled.")
    redis_client = None


class DatabaseManager:
    """Database connection and session management"""
    
    @staticmethod
    def get_db() -> Generator:
        """Get database session dependency for FastAPI"""
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()
    
    @staticmethod
    @contextmanager
    def get_session():
        """Get database session for direct use"""
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()
    
    @staticmethod
    def create_tables():
        """Create all database tables"""
        try:
            Base.metadata.create_all(bind=engine)
            logger.info("Database tables created successfully")
        except Exception as e:
            logger.error(f"Failed to create database tables: {e}")
            raise
    
    @staticmethod
    def drop_tables():
        """Drop all database tables (use with caution)"""
        try:
            Base.metadata.drop_all(bind=engine)
            logger.info("Database tables dropped successfully")
        except Exception as e:
            logger.error(f"Failed to drop database tables: {e}")
            raise
    
    @staticmethod
    def check_connection():
        """Check database connectivity"""
        try:
            with engine.connect() as conn:
                from sqlalchemy import text
                conn.execute(text("SELECT 1"))
            return True
        except Exception as e:
            logger.error(f"Database connection check failed: {e}")
            return False


class CacheManager:
    """Redis cache management"""
    
    @staticmethod
    def get(key: str) -> str:
        """Get value from cache"""
        if not redis_client:
            return None
        try:
            return redis_client.get(key)
        except Exception as e:
            logger.warning(f"Cache get failed for key {key}: {e}")
            return None
    
    @staticmethod
    def set(key: str, value: str, expire: int = 3600):
        """Set value in cache with expiration"""
        if not redis_client:
            return False
        try:
            return redis_client.setex(key, expire, value)
        except Exception as e:
            logger.warning(f"Cache set failed for key {key}: {e}")
            return False
    
    @staticmethod
    def delete(key: str):
        """Delete key from cache"""
        if not redis_client:
            return False
        try:
            return redis_client.delete(key)
        except Exception as e:
            logger.warning(f"Cache delete failed for key {key}: {e}")
            return False
    
    @staticmethod
    def exists(key: str) -> bool:
        """Check if key exists in cache"""
        if not redis_client:
            return False
        try:
            return redis_client.exists(key)
        except Exception as e:
            logger.warning(f"Cache exists check failed for key {key}: {e}")
            return False
    
    @staticmethod
    def get_keys(pattern: str = "*"):
        """Get all keys matching pattern"""
        if not redis_client:
            return []
        try:
            return redis_client.keys(pattern)
        except Exception as e:
            logger.warning(f"Cache keys retrieval failed: {e}")
            return []


# Initialize database tables if needed
def init_db():
    """Initialize database with tables"""
    if DatabaseManager.check_connection():
        DatabaseManager.create_tables()
        logger.info("Database initialized successfully")
    else:
        logger.error("Database initialization failed - no connection")


if __name__ == "__main__":
    # Test database and cache connections
    logging.basicConfig(level=logging.INFO)
    
    print("Testing database connection...")
    if DatabaseManager.check_connection():
        print("✓ Database connection successful")
    else:
        print("✗ Database connection failed")
    
    print("Testing Redis connection...")
    if redis_client and redis_client.ping():
        print("✓ Redis connection successful")
    else:
        print("✗ Redis connection failed")
    
    print("Initializing database tables...")
    init_db()
    print("✓ Database initialization complete")
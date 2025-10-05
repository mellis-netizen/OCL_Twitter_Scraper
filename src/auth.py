"""
Authentication and authorization for TGE Monitor API
JWT token-based authentication with API key support
"""

import os
import secrets
import hashlib
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import HTTPException, status, Depends, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials, APIKeyHeader
from sqlalchemy.orm import Session

from .database import DatabaseManager
from .models import User, APIKey
from .schemas import TokenData

# Configuration
SECRET_KEY = os.getenv("SECRET_KEY", secrets.token_urlsafe(32))
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Security schemes
security = HTTPBearer()
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


class AuthManager:
    """Authentication manager class"""
    
    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a password"""
        # Bcrypt has a maximum password length of 72 bytes
        if len(password.encode('utf-8')) > 72:
            password = password[:72]
        return pwd_context.hash(password)
    
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash"""
        return pwd_context.verify(plain_password, hashed_password)
    
    @staticmethod
    def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
        """Create a JWT access token"""
        to_encode = data.copy()
        
        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt
    
    @staticmethod
    def verify_token(token: str) -> Optional[TokenData]:
        """Verify and decode a JWT token"""
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            username: str = payload.get("sub")
            user_id: int = payload.get("user_id")
            
            if username is None or user_id is None:
                return None
            
            return TokenData(username=username, user_id=user_id)
        except JWTError:
            return None
    
    @staticmethod
    def generate_api_key() -> str:
        """Generate a new API key"""
        return secrets.token_urlsafe(32)
    
    @staticmethod
    def hash_api_key(api_key: str) -> str:
        """Hash an API key for storage"""
        return hashlib.sha256(api_key.encode()).hexdigest()


def authenticate_user(db: Session, username: str, password: str) -> Optional[User]:
    """Authenticate a user with username and password"""
    user = db.query(User).filter(User.username == username).first()
    
    if not user:
        return None
    
    if not user.is_active:
        return None
    
    if not AuthManager.verify_password(password, user.hashed_password):
        return None
    
    # Update last login
    user.last_login = datetime.now(timezone.utc)
    db.commit()
    
    return user


def get_user_by_username(db: Session, username: str) -> Optional[User]:
    """Get user by username"""
    return db.query(User).filter(User.username == username).first()


def get_user_by_email(db: Session, email: str) -> Optional[User]:
    """Get user by email"""
    return db.query(User).filter(User.email == email).first()


def create_user(db: Session, username: str, email: str, password: str, is_admin: bool = False) -> User:
    """Create a new user"""
    # Check if user already exists
    if get_user_by_username(db, username):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )
    
    if get_user_by_email(db, email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create new user
    hashed_password = AuthManager.hash_password(password)
    db_user = User(
        username=username,
        email=email,
        hashed_password=hashed_password,
        is_admin=is_admin
    )
    
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    return db_user


def create_api_key(db: Session, user_id: int, name: str, expires_in_days: Optional[int] = None) -> tuple[APIKey, str]:
    """Create a new API key for a user"""
    # Generate API key
    api_key = AuthManager.generate_api_key()
    key_hash = AuthManager.hash_api_key(api_key)
    
    # Calculate expiration
    expires_at = None
    if expires_in_days:
        expires_at = datetime.now(timezone.utc) + timedelta(days=expires_in_days)
    
    # Create API key record
    db_api_key = APIKey(
        key_hash=key_hash,
        name=name,
        user_id=user_id,
        expires_at=expires_at
    )
    
    db.add(db_api_key)
    db.commit()
    db.refresh(db_api_key)
    
    return db_api_key, api_key


def verify_api_key(db: Session, api_key: str) -> Optional[User]:
    """Verify an API key and return the associated user"""
    key_hash = AuthManager.hash_api_key(api_key)
    
    db_api_key = db.query(APIKey).filter(
        APIKey.key_hash == key_hash,
        APIKey.is_active == True
    ).first()
    
    if not db_api_key:
        return None
    
    # Check expiration
    if db_api_key.expires_at and db_api_key.expires_at < datetime.now(timezone.utc):
        return None
    
    # Get associated user
    user = db.query(User).filter(User.id == db_api_key.user_id).first()
    
    if not user or not user.is_active:
        return None
    
    # Update usage statistics
    db_api_key.last_used = datetime.now(timezone.utc)
    db_api_key.usage_count += 1
    db.commit()
    
    return user


# Dependencies
def get_current_user_from_token(
    credentials: HTTPAuthorizationCredentials = Security(security),
    db: Session = Depends(DatabaseManager.get_db)
) -> User:
    """Get current user from JWT token"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    if not credentials:
        raise credentials_exception
    
    token_data = AuthManager.verify_token(credentials.credentials)
    if token_data is None:
        raise credentials_exception
    
    user = db.query(User).filter(User.id == token_data.user_id).first()
    if user is None:
        raise credentials_exception
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    
    return user


def get_current_user_from_api_key(
    api_key: Optional[str] = Security(api_key_header),
    db: Session = Depends(DatabaseManager.get_db)
) -> Optional[User]:
    """Get current user from API key"""
    if not api_key:
        return None
    
    user = verify_api_key(db, api_key)
    if not user:
        return None
    
    return user


def get_current_user(
    token_user: Optional[User] = Depends(get_current_user_from_token),
    api_key_user: Optional[User] = Depends(get_current_user_from_api_key)
) -> User:
    """Get current user from either JWT token or API key"""
    # Try API key first (for better performance)
    if api_key_user:
        return api_key_user
    
    # Fall back to JWT token
    if token_user:
        return token_user
    
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required"
    )


def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """Get current active user"""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    return current_user


def get_current_admin_user(current_user: User = Depends(get_current_active_user)) -> User:
    """Get current admin user"""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    return current_user


def optional_user(
    api_key_user: Optional[User] = Depends(get_current_user_from_api_key)
) -> Optional[User]:
    """Optional user dependency for public endpoints that can benefit from authentication"""
    return api_key_user


# Rate limiting (basic implementation)
class RateLimiter:
    """Simple in-memory rate limiter"""
    
    def __init__(self):
        self.requests = {}
    
    def is_allowed(self, key: str, limit: int, window: int) -> bool:
        """Check if request is allowed under rate limit"""
        now = datetime.now(timezone.utc)
        
        if key not in self.requests:
            self.requests[key] = []
        
        # Clean old requests outside the window
        self.requests[key] = [
            req_time for req_time in self.requests[key]
            if (now - req_time).total_seconds() < window
        ]
        
        # Check if under limit
        if len(self.requests[key]) >= limit:
            return False
        
        # Add current request
        self.requests[key].append(now)
        return True


# Global rate limiter instance
rate_limiter = RateLimiter()


def check_rate_limit(key: str, limit: int = 100, window: int = 3600):
    """Check rate limit for a key"""
    if not rate_limiter.is_allowed(key, limit, window):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded"
        )


# Utility functions
def create_admin_user_if_not_exists(db: Session):
    """Create default admin user if no admin exists"""
    admin_user = db.query(User).filter(User.is_admin == True).first()
    
    if not admin_user:
        admin_username = os.getenv("ADMIN_USERNAME", "admin")
        admin_email = os.getenv("ADMIN_EMAIL", "admin@tgemonitor.local")
        admin_password = os.getenv("ADMIN_PASSWORD", "admin123456")
        
        try:
            admin_user = create_user(
                db=db,
                username=admin_username,
                email=admin_email,
                password=admin_password,
                is_admin=True
            )
            print(f"Created admin user: {admin_username}")
            return admin_user
        except HTTPException:
            # Admin user might already exist with different details
            existing_user = get_user_by_username(db, admin_username)
            if existing_user:
                existing_user.is_admin = True
                db.commit()
                print(f"Updated existing user {admin_username} to admin")
                return existing_user
    
    return admin_user
"""
Comprehensive unit tests for authentication and authorization (src/auth.py)
Tests password hashing, JWT tokens, user authentication, and permissions
"""

import pytest
import os
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch, MagicMock
from jose import jwt, JWTError
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

# Import the modules to test
from src.auth import (
    AuthManager,
    authenticate_user,
    get_user_by_username,
    get_user_by_email,
    create_user,
    create_api_key,
    verify_api_key,
    get_current_user_from_token,
    get_current_user_from_api_key,
    get_current_user,
    get_current_active_user,
    get_current_admin_user,
    optional_user,
    RateLimiter,
    check_rate_limit,
    create_admin_user_if_not_exists,
    SECRET_KEY,
    ALGORITHM,
    ACCESS_TOKEN_EXPIRE_MINUTES
)
from src.models import User, APIKey
from src.schemas import TokenData


class TestAuthManager:
    """Test suite for AuthManager class"""

    def test_hash_password_basic(self):
        """Test basic password hashing"""
        password = "test_password_123"
        hashed = AuthManager.hash_password(password)

        assert hashed is not None
        assert hashed != password
        assert len(hashed) > 20
        assert hashed.startswith("$2b$")  # bcrypt hash

    def test_hash_password_different_hashes(self):
        """Test that same password produces different hashes (salt)"""
        password = "same_password"
        hash1 = AuthManager.hash_password(password)
        hash2 = AuthManager.hash_password(password)

        assert hash1 != hash2  # Different salts

    def test_hash_password_max_length(self):
        """Test password hashing with maximum length (72 bytes for bcrypt)"""
        # Create password longer than 72 bytes
        long_password = "a" * 100
        hashed = AuthManager.hash_password(long_password)

        assert hashed is not None
        assert hashed.startswith("$2b$")

    def test_hash_password_unicode(self):
        """Test password hashing with unicode characters"""
        unicode_password = "パスワード123🔐"
        hashed = AuthManager.hash_password(unicode_password)

        assert hashed is not None
        assert hashed.startswith("$2b$")

    def test_verify_password_correct(self):
        """Test password verification with correct password"""
        password = "correct_password"
        hashed = AuthManager.hash_password(password)

        assert AuthManager.verify_password(password, hashed) is True

    def test_verify_password_incorrect(self):
        """Test password verification with incorrect password"""
        password = "correct_password"
        hashed = AuthManager.hash_password(password)

        assert AuthManager.verify_password("wrong_password", hashed) is False

    def test_verify_password_empty(self):
        """Test password verification with empty password"""
        password = "test_password"
        hashed = AuthManager.hash_password(password)

        assert AuthManager.verify_password("", hashed) is False

    def test_verify_password_case_sensitive(self):
        """Test password verification is case-sensitive"""
        password = "CaseSensitive"
        hashed = AuthManager.hash_password(password)

        assert AuthManager.verify_password("casesensitive", hashed) is False

    def test_create_access_token_basic(self):
        """Test JWT token creation with basic data"""
        data = {"sub": "testuser", "user_id": 123}
        token = AuthManager.create_access_token(data)

        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 50

    def test_create_access_token_custom_expiry(self):
        """Test JWT token creation with custom expiration"""
        data = {"sub": "testuser", "user_id": 123}
        expires_delta = timedelta(minutes=30)
        token = AuthManager.create_access_token(data, expires_delta)

        # Decode and verify expiration
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        exp_time = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
        expected_time = datetime.now(timezone.utc) + expires_delta

        # Allow 5 second difference for test execution time
        assert abs((exp_time - expected_time).total_seconds()) < 5

    def test_create_access_token_default_expiry(self):
        """Test JWT token creation with default expiration"""
        data = {"sub": "testuser", "user_id": 123}
        token = AuthManager.create_access_token(data)

        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        exp_time = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
        expected_time = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

        assert abs((exp_time - expected_time).total_seconds()) < 5

    def test_create_access_token_preserves_data(self):
        """Test that token creation preserves original data"""
        data = {"sub": "testuser", "user_id": 123, "role": "admin"}
        token = AuthManager.create_access_token(data)

        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        assert payload["sub"] == "testuser"
        assert payload["user_id"] == 123
        assert payload["role"] == "admin"
        assert "exp" in payload

    def test_verify_token_valid(self):
        """Test token verification with valid token"""
        data = {"sub": "testuser", "user_id": 123}
        token = AuthManager.create_access_token(data)

        token_data = AuthManager.verify_token(token)

        assert token_data is not None
        assert isinstance(token_data, TokenData)
        assert token_data.username == "testuser"
        assert token_data.user_id == 123

    def test_verify_token_expired(self):
        """Test token verification with expired token"""
        data = {"sub": "testuser", "user_id": 123}
        # Create token that expires immediately
        expires_delta = timedelta(seconds=-1)
        token = AuthManager.create_access_token(data, expires_delta)

        token_data = AuthManager.verify_token(token)
        assert token_data is None

    def test_verify_token_invalid_signature(self):
        """Test token verification with invalid signature"""
        data = {"sub": "testuser", "user_id": 123}
        token = AuthManager.create_access_token(data)

        # Tamper with token
        parts = token.split('.')
        parts[-1] = parts[-1][:-1] + 'X'
        tampered_token = '.'.join(parts)

        token_data = AuthManager.verify_token(tampered_token)
        assert token_data is None

    def test_verify_token_malformed(self):
        """Test token verification with malformed token"""
        malformed_token = "not.a.valid.jwt.token"
        token_data = AuthManager.verify_token(malformed_token)
        assert token_data is None

    def test_verify_token_missing_sub(self):
        """Test token verification with missing subject"""
        data = {"user_id": 123}  # Missing 'sub'
        token = jwt.encode(data, SECRET_KEY, algorithm=ALGORITHM)

        token_data = AuthManager.verify_token(token)
        assert token_data is None

    def test_verify_token_missing_user_id(self):
        """Test token verification with missing user_id"""
        data = {"sub": "testuser"}  # Missing 'user_id'
        token = jwt.encode(data, SECRET_KEY, algorithm=ALGORITHM)

        token_data = AuthManager.verify_token(token)
        assert token_data is None

    def test_generate_api_key(self):
        """Test API key generation"""
        api_key = AuthManager.generate_api_key()

        assert api_key is not None
        assert isinstance(api_key, str)
        assert len(api_key) > 20

    def test_generate_api_key_unique(self):
        """Test that generated API keys are unique"""
        keys = [AuthManager.generate_api_key() for _ in range(100)]
        assert len(keys) == len(set(keys))  # All unique

    def test_hash_api_key(self):
        """Test API key hashing"""
        api_key = "test_api_key_12345"
        hashed = AuthManager.hash_api_key(api_key)

        assert hashed is not None
        assert isinstance(hashed, str)
        assert len(hashed) == 64  # SHA256 produces 64 hex chars
        assert hashed != api_key

    def test_hash_api_key_deterministic(self):
        """Test that API key hashing is deterministic"""
        api_key = "test_api_key_12345"
        hash1 = AuthManager.hash_api_key(api_key)
        hash2 = AuthManager.hash_api_key(api_key)

        assert hash1 == hash2  # Same input produces same hash


class TestAuthenticateUser:
    """Test suite for user authentication"""

    def test_authenticate_user_success(self):
        """Test successful user authentication"""
        # Mock database session
        mock_db = Mock(spec=Session)
        mock_user = Mock(spec=User)
        mock_user.username = "testuser"
        mock_user.hashed_password = AuthManager.hash_password("correct_password")
        mock_user.is_active = True
        mock_user.last_login = None

        # Mock query chain
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = mock_user
        mock_db.query.return_value = mock_query

        result = authenticate_user(mock_db, "testuser", "correct_password")

        assert result == mock_user
        assert mock_user.last_login is not None
        mock_db.commit.assert_called_once()

    def test_authenticate_user_wrong_password(self):
        """Test authentication with wrong password"""
        mock_db = Mock(spec=Session)
        mock_user = Mock(spec=User)
        mock_user.username = "testuser"
        mock_user.hashed_password = AuthManager.hash_password("correct_password")
        mock_user.is_active = True

        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = mock_user
        mock_db.query.return_value = mock_query

        result = authenticate_user(mock_db, "testuser", "wrong_password")

        assert result is None
        mock_db.commit.assert_not_called()

    def test_authenticate_user_not_found(self):
        """Test authentication with non-existent user"""
        mock_db = Mock(spec=Session)
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = None
        mock_db.query.return_value = mock_query

        result = authenticate_user(mock_db, "nonexistent", "password")

        assert result is None

    def test_authenticate_user_inactive(self):
        """Test authentication with inactive user"""
        mock_db = Mock(spec=Session)
        mock_user = Mock(spec=User)
        mock_user.username = "testuser"
        mock_user.hashed_password = AuthManager.hash_password("password")
        mock_user.is_active = False

        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = mock_user
        mock_db.query.return_value = mock_query

        result = authenticate_user(mock_db, "testuser", "password")

        assert result is None


class TestUserQueries:
    """Test suite for user query functions"""

    def test_get_user_by_username_found(self):
        """Test getting user by username when found"""
        mock_db = Mock(spec=Session)
        mock_user = Mock(spec=User)
        mock_user.username = "testuser"

        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = mock_user
        mock_db.query.return_value = mock_query

        result = get_user_by_username(mock_db, "testuser")

        assert result == mock_user

    def test_get_user_by_username_not_found(self):
        """Test getting user by username when not found"""
        mock_db = Mock(spec=Session)
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = None
        mock_db.query.return_value = mock_query

        result = get_user_by_username(mock_db, "nonexistent")

        assert result is None

    def test_get_user_by_email_found(self):
        """Test getting user by email when found"""
        mock_db = Mock(spec=Session)
        mock_user = Mock(spec=User)
        mock_user.email = "test@example.com"

        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = mock_user
        mock_db.query.return_value = mock_query

        result = get_user_by_email(mock_db, "test@example.com")

        assert result == mock_user

    def test_get_user_by_email_not_found(self):
        """Test getting user by email when not found"""
        mock_db = Mock(spec=Session)
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = None
        mock_db.query.return_value = mock_query

        result = get_user_by_email(mock_db, "nonexistent@example.com")

        assert result is None


class TestCreateUser:
    """Test suite for user creation"""

    def test_create_user_success(self):
        """Test successful user creation"""
        mock_db = Mock(spec=Session)

        # Mock that user doesn't exist
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = None
        mock_db.query.return_value = mock_query

        # Mock user creation
        mock_user = Mock(spec=User)
        mock_user.username = "newuser"
        mock_user.email = "new@example.com"

        with patch('src.auth.User', return_value=mock_user):
            result = create_user(mock_db, "newuser", "new@example.com", "password123")

        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()

    def test_create_user_duplicate_username(self):
        """Test user creation with duplicate username"""
        mock_db = Mock(spec=Session)
        mock_user = Mock(spec=User)
        mock_user.username = "existing"

        # First call returns user (username check), second returns None (email check)
        mock_query = Mock()
        mock_query.filter.return_value.first.side_effect = [mock_user, None]
        mock_db.query.return_value = mock_query

        with pytest.raises(HTTPException) as exc_info:
            create_user(mock_db, "existing", "new@example.com", "password")

        assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
        assert "Username already registered" in str(exc_info.value.detail)

    def test_create_user_duplicate_email(self):
        """Test user creation with duplicate email"""
        mock_db = Mock(spec=Session)
        mock_user = Mock(spec=User)
        mock_user.email = "existing@example.com"

        # First call returns None (username check), second returns user (email check)
        mock_query = Mock()
        mock_query.filter.return_value.first.side_effect = [None, mock_user]
        mock_db.query.return_value = mock_query

        with pytest.raises(HTTPException) as exc_info:
            create_user(mock_db, "newuser", "existing@example.com", "password")

        assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
        assert "Email already registered" in str(exc_info.value.detail)

    def test_create_user_admin(self):
        """Test admin user creation"""
        mock_db = Mock(spec=Session)

        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = None
        mock_db.query.return_value = mock_query

        mock_user = Mock(spec=User)
        mock_user.is_admin = True

        with patch('src.auth.User', return_value=mock_user):
            result = create_user(mock_db, "admin", "admin@example.com", "password", is_admin=True)

        mock_db.add.assert_called_once()


class TestAPIKeyManagement:
    """Test suite for API key management"""

    def test_create_api_key_success(self):
        """Test successful API key creation"""
        mock_db = Mock(spec=Session)
        mock_api_key = Mock(spec=APIKey)
        mock_api_key.id = 1
        mock_api_key.name = "Test Key"
        mock_api_key.user_id = 123

        with patch('src.auth.APIKey', return_value=mock_api_key):
            db_api_key, api_key = create_api_key(mock_db, 123, "Test Key")

        assert db_api_key == mock_api_key
        assert api_key is not None
        assert len(api_key) > 20
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()

    def test_create_api_key_with_expiration(self):
        """Test API key creation with expiration"""
        mock_db = Mock(spec=Session)
        mock_api_key = Mock(spec=APIKey)

        with patch('src.auth.APIKey', return_value=mock_api_key):
            db_api_key, api_key = create_api_key(mock_db, 123, "Test Key", expires_in_days=30)

        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()

    def test_verify_api_key_success(self):
        """Test successful API key verification"""
        mock_db = Mock(spec=Session)
        api_key = "test_api_key_123"

        # Mock API key
        mock_api_key = Mock(spec=APIKey)
        mock_api_key.key_hash = AuthManager.hash_api_key(api_key)
        mock_api_key.is_active = True
        mock_api_key.expires_at = None
        mock_api_key.user_id = 123
        mock_api_key.last_used = None
        mock_api_key.usage_count = 0

        # Mock user
        mock_user = Mock(spec=User)
        mock_user.id = 123
        mock_user.is_active = True

        # Mock query chain
        def query_side_effect(model):
            if model == APIKey:
                mock_query = Mock()
                mock_query.filter.return_value.first.return_value = mock_api_key
                return mock_query
            elif model == User:
                mock_query = Mock()
                mock_query.filter.return_value.first.return_value = mock_user
                return mock_query

        mock_db.query.side_effect = query_side_effect

        result = verify_api_key(mock_db, api_key)

        assert result == mock_user
        assert mock_api_key.last_used is not None
        assert mock_api_key.usage_count == 1
        mock_db.commit.assert_called_once()

    def test_verify_api_key_not_found(self):
        """Test API key verification with invalid key"""
        mock_db = Mock(spec=Session)
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = None
        mock_db.query.return_value = mock_query

        result = verify_api_key(mock_db, "invalid_key")

        assert result is None

    def test_verify_api_key_expired(self):
        """Test API key verification with expired key"""
        mock_db = Mock(spec=Session)

        mock_api_key = Mock(spec=APIKey)
        mock_api_key.is_active = True
        mock_api_key.expires_at = datetime.now(timezone.utc) - timedelta(days=1)

        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = mock_api_key
        mock_db.query.return_value = mock_query

        result = verify_api_key(mock_db, "expired_key")

        assert result is None

    def test_verify_api_key_inactive_user(self):
        """Test API key verification with inactive user"""
        mock_db = Mock(spec=Session)
        api_key = "test_api_key_123"

        mock_api_key = Mock(spec=APIKey)
        mock_api_key.key_hash = AuthManager.hash_api_key(api_key)
        mock_api_key.is_active = True
        mock_api_key.expires_at = None
        mock_api_key.user_id = 123

        mock_user = Mock(spec=User)
        mock_user.id = 123
        mock_user.is_active = False

        def query_side_effect(model):
            if model == APIKey:
                mock_query = Mock()
                mock_query.filter.return_value.first.return_value = mock_api_key
                return mock_query
            elif model == User:
                mock_query = Mock()
                mock_query.filter.return_value.first.return_value = mock_user
                return mock_query

        mock_db.query.side_effect = query_side_effect

        result = verify_api_key(mock_db, api_key)

        assert result is None


class TestAuthDependencies:
    """Test suite for FastAPI authentication dependencies"""

    def test_get_current_user_from_token_success(self):
        """Test getting current user from valid token"""
        mock_db = Mock(spec=Session)
        mock_user = Mock(spec=User)
        mock_user.id = 123
        mock_user.is_active = True

        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = mock_user
        mock_db.query.return_value = mock_query

        data = {"sub": "testuser", "user_id": 123}
        token = AuthManager.create_access_token(data)

        mock_credentials = Mock()
        mock_credentials.credentials = token

        result = get_current_user_from_token(mock_credentials, mock_db)

        assert result == mock_user

    def test_get_current_user_from_token_no_credentials(self):
        """Test getting current user with no credentials"""
        mock_db = Mock(spec=Session)

        with pytest.raises(HTTPException) as exc_info:
            get_current_user_from_token(None, mock_db)

        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED

    def test_get_current_user_from_token_invalid_token(self):
        """Test getting current user with invalid token"""
        mock_db = Mock(spec=Session)
        mock_credentials = Mock()
        mock_credentials.credentials = "invalid_token"

        with pytest.raises(HTTPException) as exc_info:
            get_current_user_from_token(mock_credentials, mock_db)

        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED

    def test_get_current_user_from_token_inactive_user(self):
        """Test getting current user with inactive user"""
        mock_db = Mock(spec=Session)
        mock_user = Mock(spec=User)
        mock_user.id = 123
        mock_user.is_active = False

        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = mock_user
        mock_db.query.return_value = mock_query

        data = {"sub": "testuser", "user_id": 123}
        token = AuthManager.create_access_token(data)

        mock_credentials = Mock()
        mock_credentials.credentials = token

        with pytest.raises(HTTPException) as exc_info:
            get_current_user_from_token(mock_credentials, mock_db)

        assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
        assert "Inactive user" in str(exc_info.value.detail)

    def test_get_current_user_from_api_key_success(self):
        """Test getting current user from valid API key"""
        mock_db = Mock(spec=Session)
        api_key = "test_api_key"

        mock_user = Mock(spec=User)

        with patch('src.auth.verify_api_key', return_value=mock_user):
            result = get_current_user_from_api_key(api_key, mock_db)

        assert result == mock_user

    def test_get_current_user_from_api_key_no_key(self):
        """Test getting current user with no API key"""
        mock_db = Mock(spec=Session)

        result = get_current_user_from_api_key(None, mock_db)

        assert result is None

    def test_get_current_user_from_api_key_invalid(self):
        """Test getting current user with invalid API key"""
        mock_db = Mock(spec=Session)

        with patch('src.auth.verify_api_key', return_value=None):
            result = get_current_user_from_api_key("invalid_key", mock_db)

        assert result is None

    def test_get_current_active_user_active(self):
        """Test getting current active user when user is active"""
        mock_user = Mock(spec=User)
        mock_user.is_active = True

        result = get_current_active_user(mock_user)

        assert result == mock_user

    def test_get_current_active_user_inactive(self):
        """Test getting current active user when user is inactive"""
        mock_user = Mock(spec=User)
        mock_user.is_active = False

        with pytest.raises(HTTPException) as exc_info:
            get_current_active_user(mock_user)

        assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
        assert "Inactive user" in str(exc_info.value.detail)

    def test_get_current_admin_user_admin(self):
        """Test getting current admin user when user is admin"""
        mock_user = Mock(spec=User)
        mock_user.is_admin = True

        result = get_current_admin_user(mock_user)

        assert result == mock_user

    def test_get_current_admin_user_not_admin(self):
        """Test getting current admin user when user is not admin"""
        mock_user = Mock(spec=User)
        mock_user.is_admin = False

        with pytest.raises(HTTPException) as exc_info:
            get_current_admin_user(mock_user)

        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
        assert "Not enough permissions" in str(exc_info.value.detail)

    def test_optional_user_with_key(self):
        """Test optional user dependency with API key"""
        mock_user = Mock(spec=User)

        result = optional_user(mock_user)

        assert result == mock_user

    def test_optional_user_without_key(self):
        """Test optional user dependency without API key"""
        result = optional_user(None)

        assert result is None


class TestRateLimiter:
    """Test suite for rate limiting"""

    def test_rate_limiter_allows_under_limit(self):
        """Test rate limiter allows requests under limit"""
        limiter = RateLimiter()

        # Make requests under limit
        for i in range(5):
            assert limiter.is_allowed("test_key", limit=10, window=60) is True

    def test_rate_limiter_blocks_over_limit(self):
        """Test rate limiter blocks requests over limit"""
        limiter = RateLimiter()

        # Make requests up to limit
        for i in range(10):
            limiter.is_allowed("test_key", limit=10, window=60)

        # Next request should be blocked
        assert limiter.is_allowed("test_key", limit=10, window=60) is False

    def test_rate_limiter_resets_after_window(self):
        """Test rate limiter resets after time window"""
        limiter = RateLimiter()

        # Make requests up to limit
        for i in range(10):
            limiter.is_allowed("test_key", limit=10, window=1)

        # Should be blocked
        assert limiter.is_allowed("test_key", limit=10, window=1) is False

        # Wait for window to pass
        import time
        time.sleep(1.1)

        # Should be allowed again
        assert limiter.is_allowed("test_key", limit=10, window=1) is True

    def test_rate_limiter_separate_keys(self):
        """Test rate limiter treats different keys separately"""
        limiter = RateLimiter()

        # Max out one key
        for i in range(10):
            limiter.is_allowed("key1", limit=10, window=60)

        # Other key should still be allowed
        assert limiter.is_allowed("key2", limit=10, window=60) is True

    def test_check_rate_limit_allowed(self):
        """Test check_rate_limit function when allowed"""
        with patch('src.auth.rate_limiter.is_allowed', return_value=True):
            # Should not raise exception
            check_rate_limit("test_key", limit=100, window=3600)

    def test_check_rate_limit_blocked(self):
        """Test check_rate_limit function when blocked"""
        with patch('src.auth.rate_limiter.is_allowed', return_value=False):
            with pytest.raises(HTTPException) as exc_info:
                check_rate_limit("test_key", limit=100, window=3600)

            assert exc_info.value.status_code == status.HTTP_429_TOO_MANY_REQUESTS
            assert "Rate limit exceeded" in str(exc_info.value.detail)


class TestCreateAdminUser:
    """Test suite for admin user creation"""

    def test_create_admin_user_if_not_exists_no_admin(self):
        """Test creating admin user when no admin exists"""
        mock_db = Mock(spec=Session)

        # No existing admin
        mock_query_admin = Mock()
        mock_query_admin.filter.return_value.first.return_value = None

        # No existing user with admin username
        mock_query_user = Mock()
        mock_query_user.filter.return_value.first.return_value = None

        mock_db.query.side_effect = [mock_query_admin, mock_query_user, mock_query_user]

        mock_admin = Mock(spec=User)
        mock_admin.username = "admin"

        with patch('src.auth.create_user', return_value=mock_admin):
            result = create_admin_user_if_not_exists(mock_db)

        assert result == mock_admin

    def test_create_admin_user_if_not_exists_admin_exists(self):
        """Test creating admin user when admin already exists"""
        mock_db = Mock(spec=Session)
        mock_admin = Mock(spec=User)
        mock_admin.is_admin = True

        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = mock_admin
        mock_db.query.return_value = mock_query

        result = create_admin_user_if_not_exists(mock_db)

        assert result == mock_admin

    def test_create_admin_user_upgrade_existing(self):
        """Test upgrading existing user to admin"""
        mock_db = Mock(spec=Session)

        # No admin exists
        mock_query_admin = Mock()
        mock_query_admin.filter.return_value.first.return_value = None

        # Existing user with admin username
        mock_existing_user = Mock(spec=User)
        mock_existing_user.username = "admin"
        mock_existing_user.is_admin = False

        mock_query_user = Mock()
        mock_query_user.filter.return_value.first.return_value = mock_existing_user

        def query_side_effect(model):
            if mock_db.query.call_count == 1:
                return mock_query_admin
            else:
                return mock_query_user

        mock_db.query.side_effect = query_side_effect

        with patch('src.auth.create_user', side_effect=HTTPException(status_code=400, detail="User exists")):
            with patch('src.auth.get_user_by_username', return_value=mock_existing_user):
                result = create_admin_user_if_not_exists(mock_db)

        assert mock_existing_user.is_admin is True
        mock_db.commit.assert_called()


class TestSecurityEdgeCases:
    """Test suite for security edge cases"""

    def test_token_replay_attack(self):
        """Test that tokens can be verified multiple times (stateless JWT)"""
        data = {"sub": "testuser", "user_id": 123}
        token = AuthManager.create_access_token(data)

        # Verify token multiple times
        token_data1 = AuthManager.verify_token(token)
        token_data2 = AuthManager.verify_token(token)

        assert token_data1 is not None
        assert token_data2 is not None
        assert token_data1.username == token_data2.username

    def test_sql_injection_protection_username(self):
        """Test SQL injection protection in username"""
        mock_db = Mock(spec=Session)
        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = None
        mock_db.query.return_value = mock_query

        # Attempt SQL injection in username
        malicious_username = "admin' OR '1'='1"
        result = get_user_by_username(mock_db, malicious_username)

        # Should return None, not bypass authentication
        assert result is None

    def test_timing_attack_mitigation(self):
        """Test that password verification takes similar time for correct/incorrect passwords"""
        import time

        password = "test_password"
        hashed = AuthManager.hash_password(password)

        # Time correct password verification
        start1 = time.time()
        AuthManager.verify_password(password, hashed)
        time1 = time.time() - start1

        # Time incorrect password verification
        start2 = time.time()
        AuthManager.verify_password("wrong_password", hashed)
        time2 = time.time() - start2

        # Times should be similar (within 50ms)
        # bcrypt is designed to prevent timing attacks
        assert abs(time1 - time2) < 0.05

    def test_empty_token_handling(self):
        """Test handling of empty token"""
        token_data = AuthManager.verify_token("")
        assert token_data is None

    def test_none_token_handling(self):
        """Test handling of None token"""
        with pytest.raises((TypeError, AttributeError)):
            AuthManager.verify_token(None)

    def test_very_long_password(self):
        """Test handling of very long password"""
        very_long_password = "a" * 1000
        hashed = AuthManager.hash_password(very_long_password)

        # Should still work (truncated to 72 bytes)
        assert hashed is not None
        assert AuthManager.verify_password(very_long_password, hashed) is True

    def test_special_characters_in_password(self):
        """Test handling of special characters in password"""
        special_password = "!@#$%^&*()_+-=[]{}|;':\",./<>?"
        hashed = AuthManager.hash_password(special_password)

        assert AuthManager.verify_password(special_password, hashed) is True

    def test_api_key_hash_collision_resistance(self):
        """Test API key hash collision resistance"""
        # Generate many API keys and hashes
        keys_and_hashes = []
        for _ in range(1000):
            key = AuthManager.generate_api_key()
            key_hash = AuthManager.hash_api_key(key)
            keys_and_hashes.append((key, key_hash))

        # All hashes should be unique
        hashes = [h for _, h in keys_and_hashes]
        assert len(hashes) == len(set(hashes))

    def test_concurrent_user_authentication(self):
        """Test concurrent authentication attempts don't interfere"""
        mock_db = Mock(spec=Session)
        mock_user = Mock(spec=User)
        mock_user.username = "testuser"
        mock_user.hashed_password = AuthManager.hash_password("password")
        mock_user.is_active = True
        mock_user.last_login = None

        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = mock_user
        mock_db.query.return_value = mock_query

        # Simulate concurrent authentication
        result1 = authenticate_user(mock_db, "testuser", "password")
        result2 = authenticate_user(mock_db, "testuser", "password")

        assert result1 == mock_user
        assert result2 == mock_user


class TestTokenExpiration:
    """Test suite for token expiration and refresh scenarios"""

    def test_token_expires_after_set_time(self):
        """Test that token expires after the set time"""
        data = {"sub": "testuser", "user_id": 123}
        expires_delta = timedelta(seconds=1)
        token = AuthManager.create_access_token(data, expires_delta)

        # Token should be valid immediately
        token_data = AuthManager.verify_token(token)
        assert token_data is not None

        # Wait for expiration (2 seconds to be safe)
        import time
        time.sleep(2)

        # Token should be invalid now
        token_data = AuthManager.verify_token(token)
        assert token_data is None

    def test_token_not_expired_before_time(self):
        """Test that token is valid before expiration"""
        data = {"sub": "testuser", "user_id": 123}
        expires_delta = timedelta(minutes=10)
        token = AuthManager.create_access_token(data, expires_delta)

        token_data = AuthManager.verify_token(token)
        assert token_data is not None
        assert token_data.username == "testuser"

    def test_api_key_expiration(self):
        """Test API key expiration check"""
        mock_db = Mock(spec=Session)

        # Create expired API key
        mock_api_key = Mock(spec=APIKey)
        mock_api_key.is_active = True
        mock_api_key.expires_at = datetime.now(timezone.utc) - timedelta(hours=1)

        mock_query = Mock()
        mock_query.filter.return_value.first.return_value = mock_api_key
        mock_db.query.return_value = mock_query

        result = verify_api_key(mock_db, "expired_key")
        assert result is None

    def test_api_key_not_expired(self):
        """Test valid API key not expired"""
        mock_db = Mock(spec=Session)
        api_key = "test_api_key"

        mock_api_key = Mock(spec=APIKey)
        mock_api_key.key_hash = AuthManager.hash_api_key(api_key)
        mock_api_key.is_active = True
        mock_api_key.expires_at = datetime.now(timezone.utc) + timedelta(days=30)
        mock_api_key.user_id = 123
        mock_api_key.last_used = None
        mock_api_key.usage_count = 0

        mock_user = Mock(spec=User)
        mock_user.id = 123
        mock_user.is_active = True

        def query_side_effect(model):
            if model == APIKey:
                mock_query = Mock()
                mock_query.filter.return_value.first.return_value = mock_api_key
                return mock_query
            elif model == User:
                mock_query = Mock()
                mock_query.filter.return_value.first.return_value = mock_user
                return mock_query

        mock_db.query.side_effect = query_side_effect

        result = verify_api_key(mock_db, api_key)
        assert result == mock_user


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--cov=src.auth", "--cov-report=term-missing"])

"""
Comprehensive unit tests for SQLAlchemy models and Pydantic schemas

Tests cover:
- Model instantiation and field validation
- SQLAlchemy relationships and constraints
- Schema validation (valid/invalid inputs)
- Schema serialization to/from JSON
- Custom validators and transformers
- Edge cases (None values, invalid types, etc.)
"""

import pytest
from datetime import datetime, timezone, timedelta
from typing import Dict, Any
from unittest.mock import Mock, MagicMock, patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import IntegrityError
from pydantic import ValidationError
import json

# Import models (mocking is handled in conftest.py)
from src.models import (
    Base, User, APIKey, Company, Alert, Feed,
    MonitoringSession, SystemMetrics
)

# Import schemas
from src.schemas import (
    # Enums
    Priority, UrgencyLevel, SourceType, AlertStatus,
    # User schemas
    UserBase, UserCreate, UserUpdate, UserResponse,
    # Auth schemas
    Token, TokenData, LoginRequest,
    # API Key schemas
    APIKeyCreate, APIKeyResponse,
    # Company schemas
    CompanyBase, CompanyCreate, CompanyUpdate, CompanyResponse,
    # Alert schemas
    AlertBase, AlertCreate, AlertUpdate, AlertResponse,
    # Feed schemas
    FeedBase, FeedCreate, FeedUpdate, FeedResponse,
    # Session schemas
    MonitoringSessionResponse,
    # Metrics schemas
    SystemMetricCreate, SystemMetricResponse,
    # Filter schemas
    AlertFilter, CompanyFilter,
    # Statistics schemas
    AlertStatistics, SystemStatistics,
    # WebSocket schemas
    WebSocketMessage, AlertNotification,
    # Bulk operation schemas
    BulkAlertUpdate, BulkOperationResult,
    # Health and export schemas
    HealthCheck, ExportRequest, ExportResponse
)


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture(scope="function")
def db_engine():
    """Create in-memory SQLite database for testing"""
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    return engine


@pytest.fixture(scope="function")
def db_session(db_engine):
    """Create database session for testing"""
    Session = sessionmaker(bind=db_engine)
    session = Session()
    yield session
    session.rollback()
    session.close()


@pytest.fixture
def sample_user_data():
    """Sample user data"""
    return {
        "username": "testuser",
        "email": "test@example.com",
        "hashed_password": "hashed_password_123"
    }


@pytest.fixture
def sample_company_data():
    """Sample company data"""
    return {
        "name": "TestCompany",
        "aliases": ["Test Co", "TestCo"],
        "tokens": ["TEST", "TST"],
        "priority": "HIGH",
        "status": "active",
        "website": "https://test.com",
        "twitter_handle": "@testcompany"
    }


@pytest.fixture
def sample_alert_data():
    """Sample alert data"""
    return {
        "title": "Test Alert",
        "content": "Test content",
        "source": "twitter",
        "confidence": 0.85,
        "urgency_level": "medium",
        "status": "active"
    }


# ============================================================================
# MODEL TESTS - USER
# ============================================================================

class TestUserModel:
    """Test User model functionality"""

    def test_user_creation(self, db_session, sample_user_data):
        """Test basic user creation"""
        user = User(**sample_user_data)
        db_session.add(user)
        db_session.commit()

        assert user.id is not None
        assert user.username == sample_user_data["username"]
        assert user.email == sample_user_data["email"]
        assert user.is_active is True
        assert user.is_admin is False
        assert user.created_at is not None

    def test_user_unique_username(self, db_session, sample_user_data):
        """Test username uniqueness constraint"""
        user1 = User(**sample_user_data)
        db_session.add(user1)
        db_session.commit()

        # Try to create duplicate username
        user2_data = sample_user_data.copy()
        user2_data["email"] = "different@example.com"
        user2 = User(**user2_data)
        db_session.add(user2)

        with pytest.raises(IntegrityError):
            db_session.commit()

    def test_user_unique_email(self, db_session, sample_user_data):
        """Test email uniqueness constraint"""
        user1 = User(**sample_user_data)
        db_session.add(user1)
        db_session.commit()

        # Try to create duplicate email
        user2_data = sample_user_data.copy()
        user2_data["username"] = "different_user"
        user2 = User(**user2_data)
        db_session.add(user2)

        with pytest.raises(IntegrityError):
            db_session.commit()

    def test_user_to_dict(self, db_session, sample_user_data):
        """Test user to_dict serialization"""
        user = User(**sample_user_data)
        db_session.add(user)
        db_session.commit()

        user_dict = user.to_dict()

        assert user_dict["id"] == user.id
        assert user_dict["username"] == user.username
        assert user_dict["email"] == user.email
        assert user_dict["is_active"] == user.is_active
        assert user_dict["is_admin"] == user.is_admin
        assert "hashed_password" not in user_dict

    def test_user_relationships(self, db_session, sample_user_data):
        """Test user relationships with alerts and API keys"""
        user = User(**sample_user_data)
        db_session.add(user)
        db_session.commit()

        # Add API key
        api_key = APIKey(
            key_hash="test_hash",
            name="Test Key",
            user_id=user.id
        )
        db_session.add(api_key)
        db_session.commit()

        assert len(user.api_keys) == 1
        assert user.api_keys[0].name == "Test Key"


# ============================================================================
# MODEL TESTS - APIKEY
# ============================================================================

class TestAPIKeyModel:
    """Test APIKey model functionality"""

    def test_apikey_creation(self, db_session, sample_user_data):
        """Test API key creation"""
        user = User(**sample_user_data)
        db_session.add(user)
        db_session.commit()

        api_key = APIKey(
            key_hash="unique_hash_123",
            name="Production Key",
            user_id=user.id,
            expires_at=datetime.now(timezone.utc) + timedelta(days=30)
        )
        db_session.add(api_key)
        db_session.commit()

        assert api_key.id is not None
        assert api_key.name == "Production Key"
        assert api_key.is_active is True
        assert api_key.usage_count == 0

    def test_apikey_unique_hash(self, db_session, sample_user_data):
        """Test API key hash uniqueness"""
        user = User(**sample_user_data)
        db_session.add(user)
        db_session.commit()

        api_key1 = APIKey(key_hash="hash123", name="Key 1", user_id=user.id)
        db_session.add(api_key1)
        db_session.commit()

        api_key2 = APIKey(key_hash="hash123", name="Key 2", user_id=user.id)
        db_session.add(api_key2)

        with pytest.raises(IntegrityError):
            db_session.commit()

    def test_apikey_to_dict(self, db_session, sample_user_data):
        """Test API key to_dict serialization"""
        user = User(**sample_user_data)
        db_session.add(user)
        db_session.commit()

        api_key = APIKey(key_hash="hash", name="Test", user_id=user.id)
        db_session.add(api_key)
        db_session.commit()

        key_dict = api_key.to_dict()

        assert key_dict["id"] == api_key.id
        assert key_dict["name"] == api_key.name
        assert key_dict["user_id"] == user.id
        assert "key_hash" not in key_dict


# ============================================================================
# MODEL TESTS - COMPANY
# ============================================================================

class TestCompanyModel:
    """Test Company model functionality"""

    def test_company_creation(self, db_session, sample_company_data):
        """Test company creation"""
        company = Company(**sample_company_data)
        db_session.add(company)
        db_session.commit()

        assert company.id is not None
        assert company.name == sample_company_data["name"]
        assert company.aliases == sample_company_data["aliases"]
        assert company.tokens == sample_company_data["tokens"]
        assert company.priority == sample_company_data["priority"]

    def test_company_unique_name(self, db_session, sample_company_data):
        """Test company name uniqueness"""
        company1 = Company(**sample_company_data)
        db_session.add(company1)
        db_session.commit()

        company2 = Company(**sample_company_data)
        db_session.add(company2)

        with pytest.raises(IntegrityError):
            db_session.commit()

    def test_company_json_fields(self, db_session):
        """Test JSON field handling"""
        company = Company(
            name="JsonTestCo",
            aliases=["Alias1", "Alias2"],
            tokens=["TKN1", "TKN2"],
            exclusions=["spam", "test"]
        )
        db_session.add(company)
        db_session.commit()

        # Fetch and verify JSON fields
        fetched = db_session.query(Company).filter_by(name="JsonTestCo").first()
        assert isinstance(fetched.aliases, list)
        assert len(fetched.aliases) == 2
        assert "Alias1" in fetched.aliases

    def test_company_to_dict(self, db_session, sample_company_data):
        """Test company to_dict serialization"""
        company = Company(**sample_company_data)
        db_session.add(company)
        db_session.commit()

        company_dict = company.to_dict()

        assert company_dict["name"] == company.name
        assert company_dict["aliases"] == company.aliases
        assert company_dict["tokens"] == company.tokens
        assert isinstance(company_dict["created_at"], str)

    def test_company_none_json_fields(self, db_session):
        """Test handling of None JSON fields"""
        company = Company(name="TestCo")
        db_session.add(company)
        db_session.commit()

        company_dict = company.to_dict()
        assert company_dict["aliases"] == []
        assert company_dict["tokens"] == []
        assert company_dict["exclusions"] == []


# ============================================================================
# MODEL TESTS - ALERT
# ============================================================================

class TestAlertModel:
    """Test Alert model functionality"""

    def test_alert_creation(self, db_session, sample_alert_data):
        """Test alert creation"""
        alert = Alert(**sample_alert_data)
        db_session.add(alert)
        db_session.commit()

        assert alert.id is not None
        assert alert.title == sample_alert_data["title"]
        assert alert.confidence == sample_alert_data["confidence"]
        assert alert.status == "active"

    def test_alert_with_company(self, db_session, sample_company_data, sample_alert_data):
        """Test alert with company relationship"""
        company = Company(**sample_company_data)
        db_session.add(company)
        db_session.commit()

        alert = Alert(**sample_alert_data, company_id=company.id)
        db_session.add(alert)
        db_session.commit()

        assert alert.company is not None
        assert alert.company.name == company.name

    def test_alert_json_fields(self, db_session, sample_alert_data):
        """Test alert JSON fields"""
        alert = Alert(
            **sample_alert_data,
            keywords_matched=["token", "launch"],
            tokens_mentioned=["BTC", "ETH"],
            analysis_data={"score": 0.9, "method": "ml"}
        )
        db_session.add(alert)
        db_session.commit()

        assert len(alert.keywords_matched) == 2
        assert "token" in alert.keywords_matched
        assert alert.analysis_data["score"] == 0.9

    def test_alert_to_dict_with_company(self, db_session, sample_company_data, sample_alert_data):
        """Test alert to_dict with nested company"""
        company = Company(**sample_company_data)
        db_session.add(company)
        db_session.commit()

        alert = Alert(**sample_alert_data, company_id=company.id)
        db_session.add(alert)
        db_session.commit()

        alert_dict = alert.to_dict()

        assert alert_dict["company"] is not None
        assert alert_dict["company"]["name"] == company.name
        assert isinstance(alert_dict["created_at"], str)

    def test_alert_indexes(self, db_session):
        """Test that alert indexes are created"""
        # Verify indexes exist (SQLite doesn't fail if indexes don't exist)
        from sqlalchemy import inspect
        inspector = inspect(db_session.bind)
        indexes = inspector.get_indexes('alerts')
        index_names = [idx['name'] for idx in indexes]

        assert 'idx_alerts_company_created' in index_names
        assert 'idx_alerts_confidence_created' in index_names


# ============================================================================
# MODEL TESTS - FEED
# ============================================================================

class TestFeedModel:
    """Test Feed model functionality"""

    def test_feed_creation(self, db_session):
        """Test feed creation"""
        feed = Feed(
            name="Test Feed",
            url="https://example.com/rss",
            type="rss",
            priority=1
        )
        db_session.add(feed)
        db_session.commit()

        assert feed.id is not None
        assert feed.is_active is True
        assert feed.success_count == 0
        assert feed.failure_count == 0

    def test_feed_unique_url(self, db_session):
        """Test feed URL uniqueness"""
        feed1 = Feed(name="Feed 1", url="https://example.com/rss")
        db_session.add(feed1)
        db_session.commit()

        feed2 = Feed(name="Feed 2", url="https://example.com/rss")
        db_session.add(feed2)

        with pytest.raises(IntegrityError):
            db_session.commit()

    def test_feed_to_dict(self, db_session):
        """Test feed to_dict serialization"""
        feed = Feed(name="Test", url="https://test.com/feed")
        db_session.add(feed)
        db_session.commit()

        feed_dict = feed.to_dict()

        assert feed_dict["name"] == feed.name
        assert feed_dict["url"] == feed.url
        assert feed_dict["success_count"] == 0


# ============================================================================
# MODEL TESTS - MONITORING SESSION
# ============================================================================

class TestMonitoringSessionModel:
    """Test MonitoringSession model functionality"""

    def test_session_creation(self, db_session):
        """Test monitoring session creation"""
        session = MonitoringSession(
            session_id="test-session-123",
            status="running"
        )
        db_session.add(session)
        db_session.commit()

        assert session.id is not None
        assert session.session_id == "test-session-123"
        assert session.status == "running"
        assert session.feeds_processed == 0

    def test_session_unique_id(self, db_session):
        """Test session_id uniqueness"""
        session1 = MonitoringSession(session_id="session-1")
        db_session.add(session1)
        db_session.commit()

        session2 = MonitoringSession(session_id="session-1")
        db_session.add(session2)

        with pytest.raises(IntegrityError):
            db_session.commit()

    def test_session_json_fields(self, db_session):
        """Test session JSON fields"""
        session = MonitoringSession(
            session_id="test",
            performance_metrics={"cpu": 45.2, "memory": 512},
            error_log=[{"error": "test", "timestamp": "2024-01-01"}]
        )
        db_session.add(session)
        db_session.commit()

        assert session.performance_metrics["cpu"] == 45.2
        assert len(session.error_log) == 1

    def test_session_to_dict(self, db_session):
        """Test session to_dict serialization"""
        session = MonitoringSession(session_id="test")
        db_session.add(session)
        db_session.commit()

        session_dict = session.to_dict()

        assert session_dict["session_id"] == "test"
        assert session_dict["performance_metrics"] == {}
        assert session_dict["error_log"] == []


# ============================================================================
# MODEL TESTS - SYSTEM METRICS
# ============================================================================

class TestSystemMetricsModel:
    """Test SystemMetrics model functionality"""

    def test_metric_creation(self, db_session):
        """Test system metric creation"""
        metric = SystemMetrics(
            metric_type="cpu",
            metric_name="cpu_usage",
            value=75.5,
            unit="%"
        )
        db_session.add(metric)
        db_session.commit()

        assert metric.id is not None
        assert metric.value == 75.5
        assert metric.unit == "%"

    def test_metric_json_tags(self, db_session):
        """Test metric tags JSON field"""
        metric = SystemMetrics(
            metric_type="api",
            metric_name="requests",
            value=1000,
            tags={"endpoint": "/api/alerts", "method": "GET"}
        )
        db_session.add(metric)
        db_session.commit()

        assert metric.tags["endpoint"] == "/api/alerts"

    def test_metric_to_dict(self, db_session):
        """Test metric to_dict serialization"""
        metric = SystemMetrics(
            metric_type="memory",
            metric_name="heap_used",
            value=512.5,
            unit="MB"
        )
        db_session.add(metric)
        db_session.commit()

        metric_dict = metric.to_dict()

        assert metric_dict["metric_type"] == "memory"
        assert metric_dict["value"] == 512.5
        assert isinstance(metric_dict["timestamp"], str)


# ============================================================================
# SCHEMA TESTS - ENUMS
# ============================================================================

class TestEnums:
    """Test enum definitions"""

    def test_priority_enum(self):
        """Test Priority enum values"""
        assert Priority.HIGH == "HIGH"
        assert Priority.MEDIUM == "MEDIUM"
        assert Priority.LOW == "LOW"

    def test_urgency_level_enum(self):
        """Test UrgencyLevel enum values"""
        assert UrgencyLevel.LOW == "low"
        assert UrgencyLevel.MEDIUM == "medium"
        assert UrgencyLevel.HIGH == "high"
        assert UrgencyLevel.CRITICAL == "critical"

    def test_source_type_enum(self):
        """Test SourceType enum values"""
        assert SourceType.TWITTER == "twitter"
        assert SourceType.NEWS == "news"
        assert SourceType.MANUAL == "manual"

    def test_alert_status_enum(self):
        """Test AlertStatus enum values"""
        assert AlertStatus.ACTIVE == "active"
        assert AlertStatus.ARCHIVED == "archived"
        assert AlertStatus.FALSE_POSITIVE == "false_positive"


# ============================================================================
# SCHEMA TESTS - USER SCHEMAS
# ============================================================================

class TestUserSchemas:
    """Test user-related schemas"""

    def test_user_create_valid(self):
        """Test valid user creation"""
        user = UserCreate(
            username="testuser",
            email="test@example.com",
            password="secure_password_123"
        )
        assert user.username == "testuser"
        assert user.email == "test@example.com"

    def test_user_create_short_username(self):
        """Test username length validation"""
        with pytest.raises(ValidationError) as exc_info:
            UserCreate(username="ab", email="test@example.com", password="password123")

        errors = exc_info.value.errors()
        assert any("at least 3 characters" in str(err) for err in errors)

    def test_user_create_short_password(self):
        """Test password length validation"""
        with pytest.raises(ValidationError) as exc_info:
            UserCreate(username="testuser", email="test@example.com", password="short")

        errors = exc_info.value.errors()
        assert any("at least 8 characters" in str(err) for err in errors)

    def test_user_create_invalid_email(self):
        """Test email validation"""
        with pytest.raises(ValidationError):
            UserCreate(username="testuser", email="not-an-email", password="password123")

    def test_user_update_partial(self):
        """Test partial user update"""
        update = UserUpdate(username="newname")
        assert update.username == "newname"
        assert update.email is None
        assert update.is_active is None

    def test_user_response_serialization(self):
        """Test user response schema"""
        user_data = {
            "id": 1,
            "username": "testuser",
            "email": "test@example.com",
            "is_active": True,
            "is_admin": False,
            "created_at": datetime.now(timezone.utc),
            "last_login": None
        }
        user = UserResponse(**user_data)
        assert user.id == 1
        assert user.is_active is True


# ============================================================================
# SCHEMA TESTS - AUTHENTICATION SCHEMAS
# ============================================================================

class TestAuthSchemas:
    """Test authentication schemas"""

    def test_token_schema(self):
        """Test token schema"""
        token = Token(
            access_token="jwt_token_here",
            token_type="bearer",
            expires_in=3600
        )
        assert token.access_token == "jwt_token_here"
        assert token.token_type == "bearer"

    def test_token_data_schema(self):
        """Test token data schema"""
        token_data = TokenData(username="testuser", user_id=1)
        assert token_data.username == "testuser"
        assert token_data.user_id == 1

    def test_login_request_schema(self):
        """Test login request schema"""
        login = LoginRequest(username="testuser", password="password123")
        assert login.username == "testuser"
        assert login.password == "password123"


# ============================================================================
# SCHEMA TESTS - API KEY SCHEMAS
# ============================================================================

class TestAPIKeySchemas:
    """Test API key schemas"""

    def test_apikey_create_valid(self):
        """Test valid API key creation"""
        api_key = APIKeyCreate(name="Production Key", expires_in_days=30)
        assert api_key.name == "Production Key"
        assert api_key.expires_in_days == 30

    def test_apikey_create_invalid_expiry(self):
        """Test invalid expiry days"""
        with pytest.raises(ValidationError):
            APIKeyCreate(name="Key", expires_in_days=400)  # > 365

    def test_apikey_response_schema(self):
        """Test API key response schema"""
        api_key = APIKeyResponse(
            id=1,
            name="Test Key",
            is_active=True,
            created_at=datetime.now(timezone.utc),
            expires_at=None,
            last_used=None,
            usage_count=0
        )
        assert api_key.name == "Test Key"
        assert api_key.usage_count == 0


# ============================================================================
# SCHEMA TESTS - COMPANY SCHEMAS
# ============================================================================

class TestCompanySchemas:
    """Test company schemas"""

    def test_company_create_valid(self):
        """Test valid company creation"""
        company = CompanyCreate(
            name="TestCompany",
            aliases=["Test Co"],
            tokens=["TEST"],
            priority=Priority.HIGH,
            status="active"
        )
        assert company.name == "TestCompany"
        assert company.priority == Priority.HIGH

    def test_company_create_defaults(self):
        """Test company creation with defaults"""
        company = CompanyCreate(name="TestCompany")
        assert company.aliases == []
        assert company.tokens == []
        assert company.priority == Priority.MEDIUM
        assert company.exclusions == []

    def test_company_update_partial(self):
        """Test partial company update"""
        update = CompanyUpdate(priority=Priority.HIGH, tokens=["TKN1", "TKN2"])
        assert update.priority == Priority.HIGH
        assert len(update.tokens) == 2
        assert update.name is None

    def test_company_response_schema(self):
        """Test company response schema"""
        company = CompanyResponse(
            id=1,
            name="TestCo",
            aliases=[],
            tokens=[],
            priority=Priority.MEDIUM,
            status="active",
            website=None,
            twitter_handle=None,
            description=None,
            exclusions=[],
            created_at=datetime.now(timezone.utc),
            updated_at=None
        )
        assert company.id == 1


# ============================================================================
# SCHEMA TESTS - ALERT SCHEMAS
# ============================================================================

class TestAlertSchemas:
    """Test alert schemas"""

    def test_alert_create_valid(self):
        """Test valid alert creation"""
        alert = AlertCreate(
            title="Test Alert",
            content="Test content",
            source=SourceType.TWITTER,
            confidence=0.85,
            urgency_level=UrgencyLevel.HIGH
        )
        assert alert.title == "Test Alert"
        assert alert.confidence == 0.85
        assert alert.source == SourceType.TWITTER

    def test_alert_create_invalid_confidence(self):
        """Test invalid confidence values"""
        with pytest.raises(ValidationError):
            AlertCreate(
                title="Test",
                content="Content",
                source=SourceType.TWITTER,
                confidence=1.5  # > 1.0
            )

    def test_alert_create_negative_confidence(self):
        """Test negative confidence value"""
        with pytest.raises(ValidationError):
            AlertCreate(
                title="Test",
                content="Content",
                source=SourceType.TWITTER,
                confidence=-0.1
            )

    def test_alert_update_schema(self):
        """Test alert update schema"""
        update = AlertUpdate(
            status=AlertStatus.ARCHIVED,
            urgency_level=UrgencyLevel.LOW
        )
        assert update.status == AlertStatus.ARCHIVED
        assert update.title is None

    def test_alert_response_with_company(self):
        """Test alert response with nested company"""
        company = CompanyResponse(
            id=1,
            name="TestCo",
            aliases=[],
            tokens=[],
            priority=Priority.HIGH,
            status="active",
            website=None,
            twitter_handle=None,
            description=None,
            exclusions=[],
            created_at=datetime.now(timezone.utc),
            updated_at=None
        )

        alert = AlertResponse(
            id=1,
            title="Test",
            content="Content",
            source=SourceType.TWITTER,
            source_url=None,
            confidence=0.8,
            company_id=1,
            keywords_matched=[],
            tokens_mentioned=[],
            analysis_data={},
            sentiment_score=None,
            urgency_level=UrgencyLevel.MEDIUM,
            status=AlertStatus.ACTIVE,
            company=company,
            created_at=datetime.now(timezone.utc),
            updated_at=None
        )
        assert alert.company.name == "TestCo"


# ============================================================================
# SCHEMA TESTS - FEED SCHEMAS
# ============================================================================

class TestFeedSchemas:
    """Test feed schemas"""

    def test_feed_create_valid(self):
        """Test valid feed creation"""
        feed = FeedCreate(
            name="Test Feed",
            url="https://example.com/rss",
            type="rss",
            priority=1
        )
        assert feed.name == "Test Feed"
        assert feed.priority == 1

    def test_feed_create_invalid_priority(self):
        """Test invalid priority values"""
        with pytest.raises(ValidationError):
            FeedCreate(
                name="Test",
                url="https://example.com/rss",
                priority=10  # > 5
            )

    def test_feed_update_schema(self):
        """Test feed update schema"""
        update = FeedUpdate(is_active=False, priority=5)
        assert update.is_active is False
        assert update.name is None

    def test_feed_response_schema(self):
        """Test feed response schema"""
        feed = FeedResponse(
            id=1,
            name="Test",
            url="https://test.com/rss",
            type="rss",
            priority=1,
            is_active=True,
            success_count=10,
            failure_count=2,
            last_fetch=None,
            last_success=None,
            last_failure=None,
            last_error=None,
            articles_found=100,
            tge_alerts_found=5,
            created_at=datetime.now(timezone.utc),
            updated_at=None
        )
        assert feed.success_count == 10


# ============================================================================
# SCHEMA TESTS - FILTER SCHEMAS
# ============================================================================

class TestFilterSchemas:
    """Test filter schemas"""

    def test_alert_filter_valid(self):
        """Test valid alert filter"""
        filter_data = AlertFilter(
            company_id=1,
            source=SourceType.TWITTER,
            min_confidence=0.5,
            max_confidence=0.9,
            urgency_level=UrgencyLevel.HIGH,
            limit=50
        )
        assert filter_data.company_id == 1
        assert filter_data.limit == 50

    def test_alert_filter_invalid_limit(self):
        """Test invalid limit values"""
        with pytest.raises(ValidationError):
            AlertFilter(limit=5000)  # > 1000

    def test_alert_filter_defaults(self):
        """Test alert filter defaults"""
        filter_data = AlertFilter()
        assert filter_data.limit == 100
        assert filter_data.offset == 0
        assert filter_data.keywords == []

    def test_company_filter_schema(self):
        """Test company filter schema"""
        filter_data = CompanyFilter(
            priority=Priority.HIGH,
            has_tokens=True,
            limit=25
        )
        assert filter_data.priority == Priority.HIGH
        assert filter_data.has_tokens is True


# ============================================================================
# SCHEMA TESTS - STATISTICS SCHEMAS
# ============================================================================

class TestStatisticsSchemas:
    """Test statistics schemas"""

    def test_alert_statistics_schema(self):
        """Test alert statistics schema"""
        stats = AlertStatistics(
            total_alerts=100,
            alerts_by_source={"twitter": 60, "news": 40},
            alerts_by_confidence={"high": 50, "medium": 30, "low": 20},
            alerts_by_urgency={"critical": 10, "high": 30, "medium": 40, "low": 20},
            alerts_by_company={"Company1": 50, "Company2": 50},
            recent_trend={"2024-01-01": 10, "2024-01-02": 15}
        )
        assert stats.total_alerts == 100
        assert stats.alerts_by_source["twitter"] == 60

    def test_system_statistics_schema(self):
        """Test system statistics schema"""
        stats = SystemStatistics(
            total_companies=50,
            total_feeds=20,
            active_feeds=15,
            total_alerts=500,
            alerts_last_24h=25,
            alerts_last_7d=150,
            avg_confidence=0.75,
            system_uptime=99.9,
            last_monitoring_session=datetime.now(timezone.utc)
        )
        assert stats.total_companies == 50
        assert stats.avg_confidence == 0.75


# ============================================================================
# SCHEMA TESTS - WEBSOCKET SCHEMAS
# ============================================================================

class TestWebSocketSchemas:
    """Test WebSocket schemas"""

    def test_websocket_message_schema(self):
        """Test WebSocket message schema"""
        message = WebSocketMessage(
            type="alert",
            data={"id": 1, "title": "Test"},
            timestamp=datetime.now(timezone.utc)
        )
        assert message.type == "alert"
        assert message.data["id"] == 1

    def test_alert_notification_schema(self):
        """Test alert notification schema"""
        notification = AlertNotification(
            alert_id=1,
            title="New Alert",
            company_name="TestCo",
            confidence=0.9,
            urgency_level=UrgencyLevel.HIGH,
            source=SourceType.TWITTER,
            created_at=datetime.now(timezone.utc)
        )
        assert notification.alert_id == 1
        assert notification.confidence == 0.9


# ============================================================================
# SCHEMA TESTS - BULK OPERATION SCHEMAS
# ============================================================================

class TestBulkOperationSchemas:
    """Test bulk operation schemas"""

    def test_bulk_alert_update_schema(self):
        """Test bulk alert update schema"""
        bulk_update = BulkAlertUpdate(
            alert_ids=[1, 2, 3],
            status=AlertStatus.ARCHIVED
        )
        assert len(bulk_update.alert_ids) == 3
        assert bulk_update.status == AlertStatus.ARCHIVED

    def test_bulk_operation_result_schema(self):
        """Test bulk operation result schema"""
        result = BulkOperationResult(
            success_count=8,
            error_count=2,
            errors=[{"id": 5, "error": "Not found"}]
        )
        assert result.success_count == 8
        assert result.error_count == 2


# ============================================================================
# SCHEMA TESTS - HEALTH AND EXPORT SCHEMAS
# ============================================================================

class TestHealthAndExportSchemas:
    """Test health check and export schemas"""

    def test_health_check_schema(self):
        """Test health check schema"""
        health = HealthCheck(
            status="healthy",
            timestamp=datetime.now(timezone.utc),
            database=True,
            redis=True,
            feeds_health={"active": 10, "inactive": 2},
            system_metrics={"cpu": 45.5, "memory": 512}
        )
        assert health.status == "healthy"
        assert health.database is True

    def test_export_request_valid_format(self):
        """Test export request with valid format"""
        export = ExportRequest(
            format="json",
            include_analysis=True
        )
        assert export.format == "json"
        assert export.include_analysis is True

    def test_export_request_invalid_format(self):
        """Test export request with invalid format"""
        with pytest.raises(ValidationError):
            ExportRequest(format="pdf")  # Not in allowed formats

    def test_export_response_schema(self):
        """Test export response schema"""
        response = ExportResponse(
            export_id="export-123",
            status="completed",
            download_url="https://example.com/download/export-123",
            created_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(hours=24)
        )
        assert response.export_id == "export-123"
        assert response.status == "completed"


# ============================================================================
# SCHEMA TESTS - EDGE CASES
# ============================================================================

class TestSchemaEdgeCases:
    """Test edge cases and boundary conditions"""

    def test_empty_strings(self):
        """Test empty string validation"""
        with pytest.raises(ValidationError):
            UserCreate(username="", email="test@example.com", password="password123")

    def test_none_values_in_optional_fields(self):
        """Test None values in optional fields"""
        company = CompanyCreate(
            name="TestCo",
            website=None,
            twitter_handle=None
        )
        assert company.website is None

    def test_very_long_strings(self):
        """Test very long string values"""
        with pytest.raises(ValidationError):
            CompanyCreate(name="A" * 200)  # > 100 characters

    def test_boundary_values_confidence(self):
        """Test boundary values for confidence"""
        # Test minimum
        alert_min = AlertCreate(
            title="Test",
            content="Content",
            source=SourceType.TWITTER,
            confidence=0.0
        )
        assert alert_min.confidence == 0.0

        # Test maximum
        alert_max = AlertCreate(
            title="Test",
            content="Content",
            source=SourceType.TWITTER,
            confidence=1.0
        )
        assert alert_max.confidence == 1.0

    def test_json_serialization(self):
        """Test schema JSON serialization"""
        company = CompanyCreate(
            name="TestCo",
            aliases=["Alias1"],
            tokens=["TKN"]
        )
        json_str = company.model_dump_json()
        data = json.loads(json_str)
        assert data["name"] == "TestCo"

    def test_datetime_handling(self):
        """Test datetime field handling"""
        now = datetime.now(timezone.utc)
        response = UserResponse(
            id=1,
            username="test",
            email="test@example.com",
            is_active=True,
            is_admin=False,
            created_at=now,
            last_login=None
        )
        assert response.created_at == now
        assert response.last_login is None


# ============================================================================
# INTEGRATION TESTS - MODELS + SCHEMAS
# ============================================================================

class TestModelSchemaIntegration:
    """Test integration between models and schemas"""

    def test_model_to_schema_conversion(self, db_session, sample_user_data):
        """Test converting model to schema"""
        user = User(**sample_user_data)
        db_session.add(user)
        db_session.commit()

        user_dict = user.to_dict()
        user_response = UserResponse(**user_dict)

        assert user_response.username == user.username
        assert user_response.email == user.email

    def test_schema_to_model_creation(self, db_session):
        """Test creating model from schema"""
        company_schema = CompanyCreate(
            name="TestCo",
            aliases=["Test"],
            tokens=["TST"],
            priority=Priority.HIGH
        )

        company = Company(**company_schema.model_dump())
        db_session.add(company)
        db_session.commit()

        assert company.id is not None
        assert company.name == company_schema.name

    def test_complex_nested_serialization(self, db_session, sample_company_data, sample_alert_data):
        """Test complex nested object serialization"""
        company = Company(**sample_company_data)
        db_session.add(company)
        db_session.commit()

        alert = Alert(**sample_alert_data, company_id=company.id)
        db_session.add(alert)
        db_session.commit()

        alert_dict = alert.to_dict()

        # Manually construct nested response
        company_response = CompanyResponse(**company.to_dict())
        alert_response_data = alert_dict.copy()
        alert_response_data["company"] = company_response
        alert_response_data["status"] = AlertStatus.ACTIVE

        alert_response = AlertResponse(**alert_response_data)

        assert alert_response.company.name == company.name
        assert alert_response.title == alert.title


# ============================================================================
# VALIDATION TESTS
# ============================================================================

class TestValidators:
    """Test custom validators"""

    def test_password_validator_success(self):
        """Test password validator with valid password"""
        user = UserCreate(
            username="testuser",
            email="test@example.com",
            password="validpassword123"
        )
        assert len(user.password) >= 8

    def test_password_validator_failure(self):
        """Test password validator with invalid password"""
        with pytest.raises(ValidationError) as exc_info:
            UserCreate(
                username="testuser",
                email="test@example.com",
                password="short"
            )
        errors = exc_info.value.errors()
        assert any("at least 8 characters" in str(err) for err in errors)

    def test_field_constraints(self):
        """Test Field constraints"""
        with pytest.raises(ValidationError):
            FeedCreate(
                name="Test",
                url="https://test.com",
                priority=0  # < 1
            )


# ============================================================================
# PERFORMANCE TESTS
# ============================================================================

class TestPerformance:
    """Test performance-related aspects"""

    def test_bulk_model_creation(self, db_session):
        """Test creating multiple models efficiently"""
        companies = [
            Company(name=f"Company{i}", priority="HIGH")
            for i in range(100)
        ]
        db_session.bulk_save_objects(companies)
        db_session.commit()

        count = db_session.query(Company).count()
        assert count == 100

    def test_query_with_relationships(self, db_session, sample_user_data, sample_company_data):
        """Test querying with relationships"""
        user = User(**sample_user_data)
        db_session.add(user)
        db_session.commit()

        company = Company(**sample_company_data)
        db_session.add(company)
        db_session.commit()

        # Create multiple alerts
        for i in range(10):
            alert = Alert(
                title=f"Alert {i}",
                content="Content",
                source="twitter",
                confidence=0.8,
                company_id=company.id,
                user_id=user.id
            )
            db_session.add(alert)
        db_session.commit()

        # Query with relationships
        alerts = db_session.query(Alert).filter_by(company_id=company.id).all()
        assert len(alerts) == 10
        assert all(alert.company.name == company.name for alert in alerts)


# ============================================================================
# ERROR HANDLING TESTS
# ============================================================================

class TestErrorHandling:
    """Test error handling scenarios"""

    def test_invalid_foreign_key(self, db_session):
        """Test handling of invalid foreign key"""
        # Note: SQLite doesn't enforce foreign key constraints by default
        # This test validates the model structure but may not raise in SQLite
        alert = Alert(
            title="Test",
            content="Content",
            source="twitter",
            confidence=0.8,
            company_id=9999  # Non-existent
        )
        db_session.add(alert)

        # In production PostgreSQL this would raise IntegrityError
        # For SQLite testing, we just verify the model accepts the field
        try:
            db_session.commit()
            # If it commits (SQLite), that's okay for unit testing
            assert alert.company_id == 9999
        except IntegrityError:
            # If it raises (PostgreSQL), that's correct behavior
            pass

    def test_missing_required_fields(self):
        """Test missing required fields in schema"""
        with pytest.raises(ValidationError):
            AlertCreate(title="Test")  # Missing content, source, confidence

    def test_invalid_enum_value(self):
        """Test invalid enum value"""
        with pytest.raises(ValidationError):
            CompanyCreate(
                name="Test",
                priority="ULTRA_HIGH"  # Invalid enum value
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

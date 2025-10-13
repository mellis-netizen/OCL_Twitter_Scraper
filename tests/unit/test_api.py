"""
Comprehensive unit tests for FastAPI endpoints (src/api.py)
Tests all endpoints with mocking, authentication, validation, and error handling
Coverage target: >80% of api.py (264 statements)
"""

import pytest
import json
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Generator
from unittest.mock import Mock, MagicMock, patch, AsyncMock
from starlette.testclient import TestClient
from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Import the FastAPI app and dependencies
from src.api import app, manager, ConnectionManager
from src.models import User, Company, Alert, Feed, APIKey, MonitoringSession, SystemMetrics
from src.schemas import (
    UserCreate, CompanyCreate, AlertCreate, APIKeyCreate,
    Priority, UrgencyLevel, SourceType, AlertStatus
)
from src.database import DatabaseManager, CacheManager, Base
from src.auth import AuthManager, create_user, authenticate_user


# Test database setup
from sqlalchemy.pool import StaticPool
TEST_DATABASE_URL = "sqlite:///:memory:"
test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,  # Ensure all connections share the same in-memory database
    echo=False
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine, expire_on_commit=False)


@pytest.fixture(scope="function")
def db_session() -> Generator[Session, None, None]:
    """Create a fresh database session for each test"""
    Base.metadata.create_all(bind=test_engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=test_engine)


@pytest.fixture(scope="function")
def override_get_db(db_session: Session):
    """Override the database dependency"""
    def _override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[DatabaseManager.get_db] = _override_get_db
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def client(override_get_db):
    """Create a test client"""
    # Use TestClient from starlette directly
    return TestClient(app)


@pytest.fixture
def mock_cache():
    """Mock Redis cache"""
    with patch.object(CacheManager, 'exists', return_value=True), \
         patch.object(CacheManager, 'set', return_value=True), \
         patch.object(CacheManager, 'get', return_value=None):
        yield


@pytest.fixture
def test_user(db_session: Session) -> User:
    """Create a test user"""
    user = User(
        username="testuser",
        email="test@example.com",
        hashed_password=AuthManager.hash_password("testpass123"),
        is_active=True,
        is_admin=False
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def admin_user(db_session: Session) -> User:
    """Create an admin user"""
    admin = User(
        username="admin",
        email="admin@example.com",
        hashed_password=AuthManager.hash_password("adminpass123"),
        is_active=True,
        is_admin=True
    )
    db_session.add(admin)
    db_session.commit()
    db_session.refresh(admin)
    return admin


@pytest.fixture
def auth_token(test_user: User) -> str:
    """Generate a valid JWT token for test user"""
    return AuthManager.create_access_token(
        data={"sub": test_user.username, "user_id": test_user.id}
    )


@pytest.fixture
def admin_token(admin_user: User) -> str:
    """Generate a valid JWT token for admin user"""
    return AuthManager.create_access_token(
        data={"sub": admin_user.username, "user_id": admin_user.id}
    )


@pytest.fixture
def test_company(db_session: Session) -> Company:
    """Create a test company"""
    company = Company(
        name="TestCorp",
        aliases=["TC", "TestCompany"],
        tokens=["TEST", "TSTK"],
        priority=Priority.HIGH,
        status="active",
        website="https://testcorp.com",
        twitter_handle="@testcorp"
    )
    db_session.add(company)
    db_session.commit()
    db_session.refresh(company)
    return company


@pytest.fixture
def test_alert(db_session: Session, test_company: Company, test_user: User) -> Alert:
    """Create a test alert"""
    alert = Alert(
        title="Test TGE Alert",
        content="Test company is launching a token",
        source=SourceType.TWITTER,
        source_url="https://twitter.com/test/status/123",
        confidence=0.85,
        company_id=test_company.id,
        user_id=test_user.id,
        keywords_matched=["TGE", "token"],
        tokens_mentioned=["TEST"],
        urgency_level=UrgencyLevel.HIGH,
        status=AlertStatus.ACTIVE
    )
    db_session.add(alert)
    db_session.commit()
    db_session.refresh(alert)
    return alert


# ============================================================================
# Health Check Tests
# ============================================================================

class TestHealthCheck:
    """Tests for /health endpoint"""

    def test_health_check_healthy(self, client: TestClient, mock_cache):
        """Test health check returns healthy status"""
        with patch.object(DatabaseManager, 'check_connection', return_value=True):
            response = client.get("/health")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"
            assert data["database"] is True
            assert data["redis"] is True
            assert "timestamp" in data

    def test_health_check_unhealthy_db(self, client: TestClient, mock_cache):
        """Test health check with unhealthy database"""
        with patch.object(DatabaseManager, 'check_connection', return_value=False):
            response = client.get("/health")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "unhealthy"
            assert data["database"] is False

    def test_health_check_unhealthy_redis(self, client: TestClient):
        """Test health check with unhealthy Redis"""
        with patch.object(DatabaseManager, 'check_connection', return_value=True), \
             patch.object(CacheManager, 'exists', return_value=False), \
             patch.object(CacheManager, 'set', return_value=False):
            response = client.get("/health")

            assert response.status_code == 200
            data = response.json()
            assert data["redis"] is False


# ============================================================================
# Authentication Tests
# ============================================================================

class TestAuthentication:
    """Tests for authentication endpoints"""

    def test_login_success(self, client: TestClient, test_user: User, mock_cache):
        """Test successful login"""
        with patch('src.api.check_rate_limit'):
            response = client.post(
                "/auth/login",
                json={"username": "testuser", "password": "testpass123"}
            )

            assert response.status_code == 200
            data = response.json()
            assert "access_token" in data
            assert data["token_type"] == "bearer"
            assert data["expires_in"] == 3600

    def test_login_invalid_credentials(self, client: TestClient, test_user: User, mock_cache):
        """Test login with invalid credentials"""
        with patch('src.api.check_rate_limit'):
            response = client.post(
                "/auth/login",
                json={"username": "testuser", "password": "wrongpass"}
            )

            assert response.status_code == 401
            assert response.json()["detail"] == "Incorrect username or password"

    def test_login_nonexistent_user(self, client: TestClient, mock_cache):
        """Test login with nonexistent user"""
        with patch('src.api.check_rate_limit'):
            response = client.post(
                "/auth/login",
                json={"username": "nonexistent", "password": "password"}
            )

            assert response.status_code == 401

    def test_register_first_user(self, client: TestClient, db_session: Session, mock_cache):
        """Test registering the first user (becomes admin)"""
        response = client.post(
            "/auth/register",
            json={
                "username": "firstuser",
                "email": "first@example.com",
                "password": "password123"
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "firstuser"
        assert data["is_admin"] is True

    def test_register_requires_admin(self, client: TestClient, test_user: User, mock_cache):
        """Test that only admins can register new users"""
        response = client.post(
            "/auth/register",
            json={
                "username": "newuser",
                "email": "new@example.com",
                "password": "password123"
            }
        )

        assert response.status_code == 403
        assert "administrators" in response.json()["detail"].lower()

    def test_register_as_admin(self, client: TestClient, admin_token: str, admin_user: User, mock_cache):
        """Test admin can register new users"""
        response = client.post(
            "/auth/register",
            json={
                "username": "newuser",
                "email": "new@example.com",
                "password": "password123"
            },
            headers={"Authorization": f"Bearer {admin_token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "newuser"
        assert data["is_admin"] is False

    def test_register_duplicate_username(self, client: TestClient, admin_token: str, test_user: User, mock_cache):
        """Test registering with duplicate username"""
        response = client.post(
            "/auth/register",
            json={
                "username": "testuser",
                "email": "different@example.com",
                "password": "password123"
            },
            headers={"Authorization": f"Bearer {admin_token}"}
        )

        assert response.status_code == 400
        assert "already registered" in response.json()["detail"].lower()


# ============================================================================
# API Key Tests
# ============================================================================

class TestAPIKeys:
    """Tests for API key endpoints"""

    def test_create_api_key(self, client: TestClient, auth_token: str, mock_cache):
        """Test creating an API key"""
        response = client.post(
            "/auth/api-keys",
            json={"name": "Test Key", "expires_in_days": 30},
            headers={"Authorization": f"Bearer {auth_token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Test Key"
        assert "key" in data
        assert data["is_active"] is True

    def test_create_api_key_no_expiration(self, client: TestClient, auth_token: str, mock_cache):
        """Test creating an API key without expiration"""
        response = client.post(
            "/auth/api-keys",
            json={"name": "Permanent Key"},
            headers={"Authorization": f"Bearer {auth_token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["expires_at"] is None

    def test_list_api_keys(self, client: TestClient, auth_token: str, db_session: Session, test_user: User, mock_cache):
        """Test listing user's API keys"""
        # Create some API keys
        from src.auth import create_api_key
        create_api_key(db_session, test_user.id, "Key 1")
        create_api_key(db_session, test_user.id, "Key 2")

        response = client.get(
            "/auth/api-keys",
            headers={"Authorization": f"Bearer {auth_token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert all("key" not in item or item["key"] is None for item in data)

    def test_delete_api_key(self, client: TestClient, auth_token: str, db_session: Session, test_user: User, mock_cache):
        """Test deleting an API key"""
        from src.auth import create_api_key
        db_api_key, _ = create_api_key(db_session, test_user.id, "To Delete")

        response = client.delete(
            f"/auth/api-keys/{db_api_key.id}",
            headers={"Authorization": f"Bearer {auth_token}"}
        )

        assert response.status_code == 200
        assert "deleted successfully" in response.json()["message"].lower()

    def test_delete_nonexistent_api_key(self, client: TestClient, auth_token: str, mock_cache):
        """Test deleting a nonexistent API key"""
        response = client.delete(
            "/auth/api-keys/9999",
            headers={"Authorization": f"Bearer {auth_token}"}
        )

        assert response.status_code == 404

    def test_create_api_key_requires_auth(self, client: TestClient, mock_cache):
        """Test that creating API key requires authentication"""
        response = client.post(
            "/auth/api-keys",
            json={"name": "Test Key"}
        )

        assert response.status_code == 403  # FastAPI returns 403 for missing auth


# ============================================================================
# User Management Tests
# ============================================================================

class TestUserManagement:
    """Tests for user management endpoints"""

    def test_get_current_user_info(self, client: TestClient, auth_token: str, test_user: User, mock_cache):
        """Test getting current user information"""
        response = client.get(
            "/users/me",
            headers={"Authorization": f"Bearer {auth_token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["username"] == test_user.username
        assert data["email"] == test_user.email
        assert data["is_active"] is True

    def test_update_current_user(self, client: TestClient, auth_token: str, mock_cache):
        """Test updating current user information"""
        response = client.put(
            "/users/me",
            json={"email": "newemail@example.com"},
            headers={"Authorization": f"Bearer {auth_token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "newemail@example.com"

    def test_list_users_as_admin(self, client: TestClient, admin_token: str, test_user: User, admin_user: User, mock_cache):
        """Test admin can list all users"""
        response = client.get(
            "/users",
            headers={"Authorization": f"Bearer {admin_token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 2
        usernames = [u["username"] for u in data]
        assert "testuser" in usernames
        assert "admin" in usernames

    def test_list_users_non_admin_forbidden(self, client: TestClient, auth_token: str, mock_cache):
        """Test non-admin cannot list users"""
        response = client.get(
            "/users",
            headers={"Authorization": f"Bearer {auth_token}"}
        )

        assert response.status_code == 403

    def test_get_user_requires_auth(self, client: TestClient, mock_cache):
        """Test that getting user info requires authentication"""
        response = client.get("/users/me")
        assert response.status_code == 403


# ============================================================================
# Company Tests
# ============================================================================

class TestCompanies:
    """Tests for company endpoints"""

    def test_list_companies(self, client: TestClient, test_company: Company, mock_cache):
        """Test listing companies (public endpoint)"""
        response = client.get("/companies")

        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        assert data[0]["name"] == "TestCorp"

    def test_list_companies_with_priority_filter(self, client: TestClient, test_company: Company, mock_cache):
        """Test filtering companies by priority"""
        response = client.get("/companies?priority=HIGH")

        assert response.status_code == 200
        data = response.json()
        assert all(c["priority"] == "HIGH" for c in data)

    def test_list_companies_with_status_filter(self, client: TestClient, test_company: Company, mock_cache):
        """Test filtering companies by status"""
        response = client.get("/companies?status=active")

        assert response.status_code == 200
        data = response.json()
        assert all(c["status"] == "active" for c in data)

    def test_list_companies_with_pagination(self, client: TestClient, db_session: Session, mock_cache):
        """Test company list pagination"""
        # Create multiple companies
        for i in range(5):
            company = Company(name=f"Company{i}", priority=Priority.MEDIUM)
            db_session.add(company)
        db_session.commit()

        response = client.get("/companies?limit=2&offset=0")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2

    def test_get_company_by_id(self, client: TestClient, test_company: Company, mock_cache):
        """Test getting a specific company"""
        response = client.get(f"/companies/{test_company.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "TestCorp"
        assert data["id"] == test_company.id

    def test_get_nonexistent_company(self, client: TestClient, mock_cache):
        """Test getting a nonexistent company"""
        response = client.get("/companies/9999")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_create_company_as_admin(self, client: TestClient, admin_token: str, mock_cache):
        """Test creating a company as admin"""
        response = client.post(
            "/companies",
            json={
                "name": "NewCorp",
                "aliases": ["NC"],
                "tokens": ["NEW"],
                "priority": "HIGH",
                "status": "active",
                "website": "https://newcorp.com"
            },
            headers={"Authorization": f"Bearer {admin_token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "NewCorp"
        assert data["priority"] == "HIGH"

    def test_create_duplicate_company(self, client: TestClient, admin_token: str, test_company: Company, mock_cache):
        """Test creating a duplicate company"""
        response = client.post(
            "/companies",
            json={
                "name": "TestCorp",
                "priority": "MEDIUM"
            },
            headers={"Authorization": f"Bearer {admin_token}"}
        )

        assert response.status_code == 400
        assert "already exists" in response.json()["detail"].lower()

    def test_create_company_requires_admin(self, client: TestClient, auth_token: str, mock_cache):
        """Test non-admin cannot create company"""
        response = client.post(
            "/companies",
            json={"name": "NewCorp", "priority": "MEDIUM"},
            headers={"Authorization": f"Bearer {auth_token}"}
        )

        assert response.status_code == 403

    def test_update_company(self, client: TestClient, admin_token: str, test_company: Company, mock_cache):
        """Test updating a company"""
        response = client.put(
            f"/companies/{test_company.id}",
            json={"status": "inactive", "priority": "LOW"},
            headers={"Authorization": f"Bearer {admin_token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "inactive"
        assert data["priority"] == "LOW"

    def test_update_nonexistent_company(self, client: TestClient, admin_token: str, mock_cache):
        """Test updating a nonexistent company"""
        response = client.put(
            "/companies/9999",
            json={"status": "inactive"},
            headers={"Authorization": f"Bearer {admin_token}"}
        )

        assert response.status_code == 404


# ============================================================================
# Alert Tests
# ============================================================================

class TestAlerts:
    """Tests for alert endpoints"""

    def test_list_alerts(self, client: TestClient, test_alert: Alert, mock_cache):
        """Test listing alerts"""
        with patch('src.api.check_rate_limit'):
            response = client.get("/alerts")

            assert response.status_code == 200
            data = response.json()
            assert len(data) >= 1
            assert data[0]["title"] == "Test TGE Alert"

    def test_list_alerts_with_company_filter(self, client: TestClient, test_alert: Alert, test_company: Company, mock_cache):
        """Test filtering alerts by company"""
        with patch('src.api.check_rate_limit'):
            response = client.get(f"/alerts?company_id={test_company.id}")

            assert response.status_code == 200
            data = response.json()
            assert all(a["company_id"] == test_company.id for a in data)

    def test_list_alerts_with_source_filter(self, client: TestClient, test_alert: Alert, mock_cache):
        """Test filtering alerts by source"""
        with patch('src.api.check_rate_limit'):
            response = client.get("/alerts?source=twitter")

            assert response.status_code == 200
            data = response.json()
            assert all(a["source"] == "twitter" for a in data)

    def test_list_alerts_with_confidence_filter(self, client: TestClient, test_alert: Alert, mock_cache):
        """Test filtering alerts by confidence range"""
        with patch('src.api.check_rate_limit'):
            response = client.get("/alerts?min_confidence=0.8&max_confidence=0.9")

            assert response.status_code == 200
            data = response.json()
            assert all(0.8 <= a["confidence"] <= 0.9 for a in data)

    def test_list_alerts_with_urgency_filter(self, client: TestClient, test_alert: Alert, mock_cache):
        """Test filtering alerts by urgency level"""
        with patch('src.api.check_rate_limit'):
            response = client.get("/alerts?urgency_level=high")

            assert response.status_code == 200
            data = response.json()
            assert all(a["urgency_level"] == "high" for a in data)

    def test_list_alerts_with_date_range(self, client: TestClient, test_alert: Alert, mock_cache):
        """Test filtering alerts by date range"""
        with patch('src.api.check_rate_limit'):
            from_date = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
            to_date = datetime.now(timezone.utc).isoformat()

            response = client.get(f"/alerts?from_date={from_date}&to_date={to_date}")

            assert response.status_code == 200

    def test_list_alerts_with_keywords(self, client: TestClient, test_alert: Alert, mock_cache):
        """Test filtering alerts by keywords"""
        with patch('src.api.check_rate_limit'):
            response = client.get("/alerts?keywords=TGE&keywords=token")

            assert response.status_code == 200
            data = response.json()
            assert len(data) >= 1

    def test_get_alert_by_id(self, client: TestClient, test_alert: Alert, mock_cache):
        """Test getting a specific alert"""
        response = client.get(f"/alerts/{test_alert.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_alert.id
        assert data["title"] == "Test TGE Alert"

    def test_get_nonexistent_alert(self, client: TestClient, mock_cache):
        """Test getting a nonexistent alert"""
        response = client.get("/alerts/9999")

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_create_alert(self, client: TestClient, auth_token: str, test_company: Company, mock_cache):
        """Test creating an alert"""
        with patch.object(manager, 'broadcast', new_callable=AsyncMock) as mock_broadcast:
            response = client.post(
                "/alerts",
                json={
                    "title": "New Alert",
                    "content": "New TGE announcement",
                    "source": "twitter",
                    "confidence": 0.9,
                    "company_id": test_company.id,
                    "urgency_level": "critical"
                },
                headers={"Authorization": f"Bearer {auth_token}"}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["title"] == "New Alert"
            assert data["confidence"] == 0.9

    def test_create_alert_requires_auth(self, client: TestClient, mock_cache):
        """Test creating alert requires authentication"""
        response = client.post(
            "/alerts",
            json={
                "title": "New Alert",
                "content": "Content",
                "source": "twitter",
                "confidence": 0.9
            }
        )

        assert response.status_code == 403

    def test_update_alert(self, client: TestClient, auth_token: str, test_alert: Alert, mock_cache):
        """Test updating an alert"""
        response = client.put(
            f"/alerts/{test_alert.id}",
            json={"status": "archived", "urgency_level": "low"},
            headers={"Authorization": f"Bearer {auth_token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "archived"
        assert data["urgency_level"] == "low"

    def test_update_nonexistent_alert(self, client: TestClient, auth_token: str, mock_cache):
        """Test updating a nonexistent alert"""
        response = client.put(
            "/alerts/9999",
            json={"status": "archived"},
            headers={"Authorization": f"Bearer {auth_token}"}
        )

        assert response.status_code == 404

    def test_bulk_update_alerts(self, client: TestClient, auth_token: str, db_session: Session, test_company: Company, test_user: User, mock_cache):
        """Test bulk updating alerts"""
        # Create multiple alerts
        alert_ids = []
        for i in range(3):
            alert = Alert(
                title=f"Alert {i}",
                content="Content",
                source=SourceType.TWITTER,
                confidence=0.8,
                company_id=test_company.id,
                user_id=test_user.id,
                urgency_level=UrgencyLevel.MEDIUM
            )
            db_session.add(alert)
            db_session.flush()
            alert_ids.append(alert.id)
        db_session.commit()

        response = client.put(
            "/alerts/bulk",
            json={
                "alert_ids": alert_ids,
                "status": "archived",
                "urgency_level": "low"
            },
            headers={"Authorization": f"Bearer {auth_token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success_count"] == 3
        assert data["error_count"] == 0

    def test_bulk_update_with_errors(self, client: TestClient, auth_token: str, test_alert: Alert, mock_cache):
        """Test bulk update with some invalid IDs"""
        response = client.put(
            "/alerts/bulk",
            json={
                "alert_ids": [test_alert.id, 9999, 9998],
                "status": "archived"
            },
            headers={"Authorization": f"Bearer {auth_token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success_count"] == 1
        assert data["error_count"] == 2
        assert len(data["errors"]) == 2


# ============================================================================
# Statistics Tests
# ============================================================================

class TestStatistics:
    """Tests for statistics endpoints"""

    def test_get_alert_statistics(self, client: TestClient, test_alert: Alert, mock_cache):
        """Test getting alert statistics"""
        response = client.get("/statistics/alerts?days=30")

        assert response.status_code == 200
        data = response.json()
        assert "total_alerts" in data
        assert "alerts_by_source" in data
        assert data["total_alerts"] >= 1

    def test_get_alert_statistics_custom_days(self, client: TestClient, test_alert: Alert, mock_cache):
        """Test alert statistics with custom days parameter"""
        response = client.get("/statistics/alerts?days=7")

        assert response.status_code == 200
        data = response.json()
        assert "total_alerts" in data

    def test_get_alert_statistics_invalid_days(self, client: TestClient, mock_cache):
        """Test alert statistics with invalid days parameter"""
        response = client.get("/statistics/alerts?days=500")

        assert response.status_code == 422  # Validation error

    def test_get_system_statistics(self, client: TestClient, test_company: Company, test_alert: Alert, mock_cache):
        """Test getting system statistics"""
        response = client.get("/statistics/system")

        assert response.status_code == 200
        data = response.json()
        assert data["total_companies"] >= 1
        assert data["total_alerts"] >= 1
        assert "alerts_last_24h" in data
        assert "alerts_last_7d" in data
        assert "avg_confidence" in data

    def test_get_system_statistics_with_multiple_alerts(self, client: TestClient, db_session: Session, test_company: Company, test_user: User, mock_cache):
        """Test system statistics with multiple alerts"""
        # Create multiple alerts with different dates
        for i in range(5):
            alert = Alert(
                title=f"Alert {i}",
                content="Content",
                source=SourceType.NEWS,
                confidence=0.7 + (i * 0.05),
                company_id=test_company.id,
                user_id=test_user.id,
                urgency_level=UrgencyLevel.MEDIUM,
                created_at=datetime.now(timezone.utc) - timedelta(hours=i)
            )
            db_session.add(alert)
        db_session.commit()

        response = client.get("/statistics/system")

        assert response.status_code == 200
        data = response.json()
        assert data["total_alerts"] >= 5
        assert data["avg_confidence"] > 0


# ============================================================================
# WebSocket Tests
# ============================================================================

class TestWebSocket:
    """Tests for WebSocket functionality"""

    def test_websocket_connection(self):
        """Test WebSocket connection and ping/pong"""
        # WebSocket tests require special handling with httpx
        # These tests are skipped for now as they require TestClient
        pytest.skip("WebSocket tests require TestClient which has version conflicts")

    def test_websocket_disconnect(self):
        """Test WebSocket disconnect handling"""
        pytest.skip("WebSocket tests require TestClient which has version conflicts")

    def test_connection_manager_connect(self):
        """Test ConnectionManager connect method"""
        manager = ConnectionManager()
        mock_websocket = AsyncMock()

        # Test connect without user_id
        asyncio.run(manager.connect(mock_websocket))
        assert mock_websocket in manager.active_connections

    def test_connection_manager_disconnect(self):
        """Test ConnectionManager disconnect method"""
        manager = ConnectionManager()
        mock_websocket = Mock()

        manager.active_connections.append(mock_websocket)
        manager.disconnect(mock_websocket)

        assert mock_websocket not in manager.active_connections

    def test_connection_manager_broadcast(self):
        """Test ConnectionManager broadcast method"""
        manager = ConnectionManager()
        mock_ws1 = AsyncMock()
        mock_ws2 = AsyncMock()

        manager.active_connections = [mock_ws1, mock_ws2]

        message = {"type": "test", "data": "broadcast"}
        asyncio.run(manager.broadcast(message))

        mock_ws1.send_json.assert_called_once_with(message)
        mock_ws2.send_json.assert_called_once_with(message)

    def test_connection_manager_send_to_user(self):
        """Test ConnectionManager send_to_user method"""
        manager = ConnectionManager()
        mock_websocket = AsyncMock()

        user_id = 123
        manager.user_connections[user_id] = [mock_websocket]

        message = {"type": "alert", "data": "user message"}
        asyncio.run(manager.send_to_user(user_id, message))

        mock_websocket.send_json.assert_called_once_with(message)


# ============================================================================
# Input Validation Tests
# ============================================================================

class TestInputValidation:
    """Tests for request validation"""

    def test_create_user_invalid_email(self, client: TestClient, admin_token: str, mock_cache):
        """Test user creation with invalid email"""
        response = client.post(
            "/auth/register",
            json={
                "username": "newuser",
                "email": "invalid-email",
                "password": "password123"
            },
            headers={"Authorization": f"Bearer {admin_token}"}
        )

        assert response.status_code == 422

    def test_create_user_short_password(self, client: TestClient, admin_token: str, mock_cache):
        """Test user creation with too short password"""
        response = client.post(
            "/auth/register",
            json={
                "username": "newuser",
                "email": "new@example.com",
                "password": "short"
            },
            headers={"Authorization": f"Bearer {admin_token}"}
        )

        assert response.status_code == 422

    def test_create_alert_invalid_confidence(self, client: TestClient, auth_token: str, mock_cache):
        """Test creating alert with invalid confidence value"""
        response = client.post(
            "/alerts",
            json={
                "title": "Test",
                "content": "Content",
                "source": "twitter",
                "confidence": 1.5  # Invalid: > 1.0
            },
            headers={"Authorization": f"Bearer {auth_token}"}
        )

        assert response.status_code == 422

    def test_create_company_missing_name(self, client: TestClient, admin_token: str, mock_cache):
        """Test creating company without required name"""
        response = client.post(
            "/companies",
            json={"priority": "HIGH"},
            headers={"Authorization": f"Bearer {admin_token}"}
        )

        assert response.status_code == 422


# ============================================================================
# Error Handling Tests
# ============================================================================

class TestErrorHandling:
    """Tests for error handling"""

    def test_invalid_token(self, client: TestClient, mock_cache):
        """Test request with invalid token"""
        response = client.get(
            "/users/me",
            headers={"Authorization": "Bearer invalid_token"}
        )

        assert response.status_code == 401

    def test_expired_token(self, client: TestClient, mock_cache):
        """Test request with expired token"""
        # Create an expired token
        expired_token = AuthManager.create_access_token(
            data={"sub": "testuser", "user_id": 1},
            expires_delta=timedelta(seconds=-1)
        )

        response = client.get(
            "/users/me",
            headers={"Authorization": f"Bearer {expired_token}"}
        )

        assert response.status_code == 401

    def test_database_error_handling(self, client: TestClient, auth_token: str, mock_cache):
        """Test handling of database errors"""
        # TODO: Implement actual error handling test
        # This is a placeholder for now
        pytest.skip("Database error handling test not yet implemented")


# ============================================================================
# Authorization Tests
# ============================================================================

class TestAuthorization:
    """Tests for authorization and permissions"""

    def test_admin_only_endpoint_non_admin(self, client: TestClient, auth_token: str, mock_cache):
        """Test admin-only endpoint rejects non-admin user"""
        response = client.post(
            "/companies",
            json={"name": "NewCorp", "priority": "MEDIUM"},
            headers={"Authorization": f"Bearer {auth_token}"}
        )

        assert response.status_code == 403

    def test_admin_only_endpoint_admin(self, client: TestClient, admin_token: str, mock_cache):
        """Test admin-only endpoint accepts admin user"""
        response = client.get(
            "/users",
            headers={"Authorization": f"Bearer {admin_token}"}
        )

        assert response.status_code == 200

    def test_inactive_user_rejected(self, client: TestClient, db_session: Session, mock_cache):
        """Test inactive user is rejected"""
        # Create inactive user
        inactive_user = User(
            username="inactive",
            email="inactive@example.com",
            hashed_password=AuthManager.hash_password("password123"),
            is_active=False,
            is_admin=False
        )
        db_session.add(inactive_user)
        db_session.commit()

        # Try to login
        with patch('src.api.check_rate_limit'):
            response = client.post(
                "/auth/login",
                json={"username": "inactive", "password": "password123"}
            )

        assert response.status_code == 401


# ============================================================================
# Response Format Tests
# ============================================================================

class TestResponseFormats:
    """Tests for response structure and formats"""

    def test_user_response_format(self, client: TestClient, auth_token: str, mock_cache):
        """Test user response contains expected fields"""
        response = client.get(
            "/users/me",
            headers={"Authorization": f"Bearer {auth_token}"}
        )

        assert response.status_code == 200
        data = response.json()
        required_fields = ["id", "username", "email", "is_active", "is_admin"]
        assert all(field in data for field in required_fields)

    def test_company_response_format(self, client: TestClient, test_company: Company, mock_cache):
        """Test company response contains expected fields"""
        response = client.get(f"/companies/{test_company.id}")

        assert response.status_code == 200
        data = response.json()
        required_fields = ["id", "name", "priority", "status"]
        assert all(field in data for field in required_fields)

    def test_alert_response_format(self, client: TestClient, test_alert: Alert, mock_cache):
        """Test alert response contains expected fields"""
        response = client.get(f"/alerts/{test_alert.id}")

        assert response.status_code == 200
        data = response.json()
        required_fields = ["id", "title", "content", "source", "confidence", "urgency_level"]
        assert all(field in data for field in required_fields)

    def test_token_response_format(self, client: TestClient, test_user: User, mock_cache):
        """Test login token response format"""
        with patch('src.api.check_rate_limit'):
            response = client.post(
                "/auth/login",
                json={"username": "testuser", "password": "testpass123"}
            )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "token_type" in data
        assert data["token_type"] == "bearer"
        assert "expires_in" in data


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--cov=src.api", "--cov-report=term-missing"])

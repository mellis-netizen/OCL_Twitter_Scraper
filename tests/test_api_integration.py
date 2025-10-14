"""
API Integration Tests for Scraping Workflow
Tests all API endpoints used in the scraping cycle
"""

import pytest
import time
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.api import app
from src.database import Base
from src.models import MonitoringSession, Alert, Feed, Company, User
from src.auth import AuthManager


TEST_DATABASE_URL = "sqlite:///test_api_integration.db"
test_engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestSessionLocal = sessionmaker(bind=test_engine)


@pytest.fixture(scope="function")
def test_db():
    """Create test database"""
    Base.metadata.create_all(bind=test_engine)
    db = TestSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def client():
    """Test client"""
    return TestClient(app)


class TestMonitoringTriggerAPI:
    """Test /monitoring/trigger endpoint"""

    def test_trigger_returns_200(self, client):
        """Test trigger endpoint returns 200 OK"""
        response = client.post("/monitoring/trigger")
        assert response.status_code == 200

    def test_trigger_returns_session_id(self, client):
        """Test trigger returns valid session ID"""
        response = client.post("/monitoring/trigger")
        data = response.json()

        assert "session_id" in data
        assert isinstance(data["session_id"], str)
        assert len(data["session_id"]) > 0

    def test_trigger_returns_message(self, client):
        """Test trigger returns success message"""
        response = client.post("/monitoring/trigger")
        data = response.json()

        assert "message" in data
        assert "successfully" in data["message"].lower()

    def test_trigger_is_non_blocking(self, client):
        """Test trigger returns immediately (non-blocking)"""
        start_time = time.time()
        response = client.post("/monitoring/trigger")
        elapsed = time.time() - start_time

        assert response.status_code == 200
        assert elapsed < 2.0  # Should return in less than 2 seconds


class TestSessionProgressAPI:
    """Test /monitoring/session/{id}/progress endpoint"""

    def test_get_progress_with_valid_session(self, client, test_db):
        """Test getting progress for valid session"""
        # Create session
        session = MonitoringSession(
            session_id="test-session-123",
            status="running",
            performance_metrics={"phase": "scraping_news"}
        )
        test_db.add(session)
        test_db.commit()

        # Get progress
        response = client.get("/monitoring/session/test-session-123/progress")

        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == "test-session-123"
        assert data["status"] == "running"
        assert "progress_percentage" in data
        assert "current_phase" in data

    def test_get_progress_with_invalid_session(self, client):
        """Test getting progress for non-existent session"""
        response = client.get("/monitoring/session/invalid-session-id/progress")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_progress_includes_all_metrics(self, client, test_db):
        """Test progress response includes all expected metrics"""
        session = MonitoringSession(
            session_id="test-session-456",
            status="running",
            articles_processed=10,
            tweets_processed=20,
            alerts_generated=3,
            feeds_processed=5,
            errors_encountered=1,
            performance_metrics={"phase": "processing_twitter"}
        )
        test_db.add(session)
        test_db.commit()

        response = client.get("/monitoring/session/test-session-456/progress")
        data = response.json()

        assert "metrics" in data
        metrics = data["metrics"]
        assert metrics["articles_processed"] == 10
        assert metrics["tweets_processed"] == 20
        assert metrics["alerts_generated"] == 3
        assert metrics["feeds_processed"] == 5
        assert metrics["errors_encountered"] == 1


class TestSessionRetrievalAPI:
    """Test /monitoring/session/{id} endpoint"""

    def test_get_session_results(self, client, test_db):
        """Test getting complete session results"""
        session = MonitoringSession(
            session_id="completed-session-789",
            status="completed",
            start_time=datetime.now(timezone.utc) - timedelta(minutes=5),
            end_time=datetime.now(timezone.utc),
            articles_processed=25,
            tweets_processed=50,
            alerts_generated=5,
            feeds_processed=10,
            errors_encountered=0
        )
        test_db.add(session)
        test_db.commit()

        response = client.get("/monitoring/session/completed-session-789")

        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == "completed-session-789"
        assert data["status"] == "completed"

    def test_get_recent_sessions(self, client, test_db):
        """Test getting list of recent sessions"""
        # Create multiple sessions
        for i in range(5):
            session = MonitoringSession(
                session_id=f"session-{i}",
                status="completed",
                start_time=datetime.now(timezone.utc) - timedelta(hours=i)
            )
            test_db.add(session)
        test_db.commit()

        response = client.get("/monitoring/sessions/recent?limit=5")

        assert response.status_code == 200
        sessions = response.json()
        assert len(sessions) <= 5
        assert isinstance(sessions, list)


class TestStatisticsAPI:
    """Test statistics endpoints"""

    def test_get_system_statistics(self, client, test_db):
        """Test /statistics/system endpoint"""
        response = client.get("/statistics/system")

        assert response.status_code == 200
        data = response.json()

        # Check required fields
        assert "total_companies" in data
        assert "total_feeds" in data
        assert "total_alerts" in data
        assert "alerts_last_24h" in data
        assert "system_uptime" in data

    def test_statistics_update_after_alerts_created(self, client, test_db):
        """Test that statistics reflect new alerts"""
        # Get initial count
        response1 = client.get("/statistics/system")
        initial_count = response1.json()["total_alerts"]

        # Create alert
        alert = Alert(
            title="Test Alert",
            content="Test content",
            source="news",
            confidence=0.85,
            urgency_level="high"
        )
        test_db.add(alert)
        test_db.commit()

        # Get updated count
        response2 = client.get("/statistics/system")
        updated_count = response2.json()["total_alerts"]

        assert updated_count == initial_count + 1

    def test_get_alert_statistics(self, client, test_db):
        """Test /statistics/alerts endpoint"""
        # Create sample alerts
        for i in range(10):
            alert = Alert(
                title=f"Alert {i}",
                content="Test",
                source="twitter" if i % 2 == 0 else "news",
                confidence=0.8,
                urgency_level="medium"
            )
            test_db.add(alert)
        test_db.commit()

        response = client.get("/statistics/alerts?days=7")

        assert response.status_code == 200
        data = response.json()

        assert "total_alerts" in data
        assert "alerts_by_source" in data
        assert "alerts_by_urgency" in data


class TestAlertsAPI:
    """Test alerts endpoints"""

    def test_list_alerts(self, client, test_db):
        """Test GET /alerts endpoint"""
        response = client.get("/alerts?limit=10")

        assert response.status_code == 200
        alerts = response.json()
        assert isinstance(alerts, list)

    def test_filter_alerts_by_source(self, client, test_db):
        """Test filtering alerts by source"""
        # Create mixed alerts
        for source in ["twitter", "news"]:
            for i in range(3):
                alert = Alert(
                    title=f"{source} Alert {i}",
                    content="Test",
                    source=source,
                    confidence=0.8,
                    urgency_level="medium"
                )
                test_db.add(alert)
        test_db.commit()

        # Filter by twitter
        response = client.get("/alerts?source=twitter")
        alerts = response.json()

        assert len(alerts) >= 3
        for alert in alerts:
            assert alert["source"] == "twitter"

    def test_filter_alerts_by_urgency(self, client, test_db):
        """Test filtering alerts by urgency level"""
        # Create alerts with different urgency
        for urgency in ["low", "medium", "high", "critical"]:
            alert = Alert(
                title=f"{urgency} Alert",
                content="Test",
                source="news",
                confidence=0.8,
                urgency_level=urgency
            )
            test_db.add(alert)
        test_db.commit()

        # Filter by high urgency
        response = client.get("/alerts?urgency_level=high")
        alerts = response.json()

        for alert in alerts:
            assert alert["urgency_level"] == "high"


class TestFeedsAPI:
    """Test feeds endpoints"""

    def test_list_feeds(self, client, test_db):
        """Test GET /feeds endpoint"""
        response = client.get("/feeds")

        assert response.status_code == 200
        feeds = response.json()
        assert isinstance(feeds, list)

    def test_feeds_show_scraping_statistics(self, client, test_db):
        """Test that feeds include scraping statistics"""
        # Create feed with stats
        feed = Feed(
            name="Test Feed",
            url="https://example.com/feed",
            feed_type="news",
            is_active=True,
            success_count=10,
            failure_count=2,
            tge_alerts_found=5,
            last_fetch=datetime.now(timezone.utc)
        )
        test_db.add(feed)
        test_db.commit()

        response = client.get("/feeds")
        feeds = response.json()

        test_feed = next((f for f in feeds if f["name"] == "Test Feed"), None)
        assert test_feed is not None
        assert test_feed["success_count"] == 10
        assert test_feed["failure_count"] == 2


class TestHealthCheckAPI:
    """Test health check endpoint"""

    def test_health_endpoint(self, client):
        """Test /health endpoint"""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()

        assert "status" in data
        assert "timestamp" in data
        assert "database" in data

    def test_health_includes_feed_stats(self, client, test_db):
        """Test health check includes feed statistics"""
        # Create sample feeds
        for i in range(3):
            feed = Feed(
                name=f"Feed {i}",
                url=f"https://example{i}.com/feed",
                feed_type="news",
                is_active=True
            )
            test_db.add(feed)
        test_db.commit()

        response = client.get("/health")
        data = response.json()

        assert "feeds_health" in data
        feeds_health = data["feeds_health"]
        assert feeds_health["total"] >= 3
        assert "active" in feeds_health
        assert "error_rate" in feeds_health


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

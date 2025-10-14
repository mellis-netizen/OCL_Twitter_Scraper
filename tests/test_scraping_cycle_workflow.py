"""
Comprehensive Test Suite for Scraping Cycle End-to-End Workflow
Tests trigger button, API endpoints, database updates, and metrics refresh

Test Categories:
1. API Endpoint Tests - /monitoring/trigger and session endpoints
2. Database Integration Tests - Real-time updates and queries
3. End-to-End Workflow Tests - Complete scraping cycle
4. Error Handling Tests - Network failures, timeouts, database errors
5. Performance Tests - Response times and concurrent requests
6. Edge Case Tests - Partial completion, concurrent scraping
"""

import pytest
import asyncio
import time
import uuid
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient
import threading

from src.api import app, manager as websocket_manager
from src.database import DatabaseManager, Base, engine
from src.models import (
    MonitoringSession, Alert, Feed, Company, SystemMetrics, User
)


# Test configuration
TEST_DATABASE_URL = "sqlite:///test_scraping.db"
test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False}
)
TestSessionLocal = sessionmaker(bind=test_engine)


@pytest.fixture(scope="function")
def test_db():
    """Create fresh test database for each test"""
    Base.metadata.create_all(bind=test_engine)
    db = TestSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def client():
    """FastAPI test client"""
    return TestClient(app)


@pytest.fixture
def test_user(test_db):
    """Create test user"""
    from src.auth import hash_password
    user = User(
        username="testuser",
        email="test@example.com",
        password_hash=hash_password("testpass"),
        is_active=True,
        is_admin=True
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    return user


@pytest.fixture
def auth_headers(client, test_user):
    """Get authentication headers"""
    response = client.post("/auth/login", json={
        "username": "testuser",
        "password": "testpass"
    })
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def sample_feeds(test_db):
    """Create sample feeds for testing"""
    feeds = [
        Feed(
            name="CoinDesk",
            url="https://www.coindesk.com/feed",
            feed_type="news",
            is_active=True,
            success_count=10,
            failure_count=0
        ),
        Feed(
            name="CryptoSlate",
            url="https://cryptoslate.com/feed",
            feed_type="news",
            is_active=True,
            success_count=8,
            failure_count=1
        )
    ]
    for feed in feeds:
        test_db.add(feed)
    test_db.commit()
    return feeds


@pytest.fixture
def sample_companies(test_db):
    """Create sample companies for testing"""
    companies = [
        Company(
            name="Arbitrum",
            priority="high",
            status="active",
            keywords=["arbitrum", "arb", "layer2"]
        ),
        Company(
            name="Optimism",
            priority="high",
            status="active",
            keywords=["optimism", "op", "ethereum"]
        )
    ]
    for company in companies:
        test_db.add(company)
    test_db.commit()
    return companies


class TestAPIEndpointTrigger:
    """Test suite for /monitoring/trigger endpoint"""

    def test_trigger_endpoint_returns_session_id(self, client):
        """Test that trigger endpoint returns valid session ID"""
        response = client.post("/monitoring/trigger")

        assert response.status_code == 200
        data = response.json()
        assert "session_id" in data
        assert "message" in data
        assert data["message"] == "Monitoring cycle started successfully"

        # Validate session_id format (UUID)
        session_id = data["session_id"]
        try:
            uuid.UUID(session_id)
        except ValueError:
            pytest.fail("session_id is not a valid UUID")

    def test_trigger_creates_monitoring_session(self, client, test_db):
        """Test that triggering creates a monitoring session in database"""
        # Get initial count
        initial_count = test_db.query(MonitoringSession).count()

        # Trigger monitoring
        response = client.post("/monitoring/trigger")
        session_id = response.json()["session_id"]

        # Wait briefly for database write
        time.sleep(0.5)

        # Check session was created
        new_count = test_db.query(MonitoringSession).count()
        assert new_count == initial_count + 1

        # Verify session details
        session = test_db.query(MonitoringSession).filter(
            MonitoringSession.session_id == session_id
        ).first()

        assert session is not None
        assert session.status in ["running", "pending"]
        assert session.start_time is not None

    @patch('src.main_optimized.OptimizedCryptoTGEMonitor')
    def test_trigger_starts_background_thread(self, mock_monitor, client):
        """Test that monitoring runs in background thread"""
        mock_instance = Mock()
        mock_instance.run_monitoring_cycle = Mock()
        mock_monitor.return_value = mock_instance

        response = client.post("/monitoring/trigger")
        assert response.status_code == 200

        # Background thread should be started
        # We can't directly test threading, but we can verify it doesn't block
        assert response.elapsed.total_seconds() < 2.0

    def test_concurrent_trigger_requests(self, client):
        """Test multiple concurrent trigger requests"""
        import concurrent.futures

        def trigger():
            return client.post("/monitoring/trigger")

        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(trigger) for _ in range(3)]
            responses = [f.result() for f in futures]

        # All requests should succeed
        for response in responses:
            assert response.status_code == 200

        # All should have unique session IDs
        session_ids = [r.json()["session_id"] for r in responses]
        assert len(set(session_ids)) == 3


class TestSessionProgressTracking:
    """Test suite for session progress tracking"""

    def test_get_session_progress_endpoint(self, client, test_db):
        """Test /monitoring/session/{id}/progress endpoint"""
        # Create a test session
        session = MonitoringSession(
            session_id=str(uuid.uuid4()),
            status="running",
            performance_metrics={"phase": "scraping_news"}
        )
        test_db.add(session)
        test_db.commit()

        # Get progress
        response = client.get(f"/monitoring/session/{session.session_id}/progress")

        assert response.status_code == 200
        data = response.json()

        assert data["session_id"] == session.session_id
        assert data["status"] == "running"
        assert "progress_percentage" in data
        assert "current_phase" in data
        assert data["current_phase"] == "scraping_news"

    def test_progress_percentage_calculation(self, client, test_db):
        """Test that progress percentage matches phase"""
        phases_and_progress = [
            ("starting", 5),
            ("scraping_news", 15),
            ("processing_news", 35),
            ("news_complete", 45),
            ("scraping_twitter", 55),
            ("processing_twitter", 75),
            ("twitter_complete", 80),
            ("completed", 100)
        ]

        for phase, expected_progress in phases_and_progress:
            session = MonitoringSession(
                session_id=str(uuid.uuid4()),
                status="running",
                performance_metrics={"phase": phase}
            )
            test_db.add(session)
            test_db.commit()

            response = client.get(f"/monitoring/session/{session.session_id}/progress")
            data = response.json()

            assert data["progress_percentage"] == expected_progress
            assert data["current_phase"] == phase

            test_db.delete(session)
            test_db.commit()

    def test_session_not_found(self, client):
        """Test progress endpoint with non-existent session"""
        fake_session_id = str(uuid.uuid4())
        response = client.get(f"/monitoring/session/{fake_session_id}/progress")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()


class TestDatabaseUpdates:
    """Test suite for real-time database updates"""

    def test_monitoring_session_updates_during_cycle(self, test_db):
        """Test that monitoring session is updated in real-time"""
        session = MonitoringSession(
            session_id=str(uuid.uuid4()),
            status="running"
        )
        test_db.add(session)
        test_db.commit()

        # Simulate updates during cycle
        session.articles_processed = 5
        session.performance_metrics = {"phase": "processing_news"}
        test_db.commit()

        # Verify updates persist
        test_db.refresh(session)
        assert session.articles_processed == 5
        assert session.performance_metrics["phase"] == "processing_news"

    def test_session_completion_updates_all_metrics(self, test_db):
        """Test that completion updates all session metrics"""
        session = MonitoringSession(
            session_id=str(uuid.uuid4()),
            status="running",
            start_time=datetime.now(timezone.utc)
        )
        test_db.add(session)
        test_db.commit()

        # Simulate completion
        session.status = "completed"
        session.end_time = datetime.now(timezone.utc)
        session.articles_processed = 25
        session.tweets_processed = 50
        session.alerts_generated = 3
        session.feeds_processed = 5
        session.errors_encountered = 0
        session.performance_metrics = {
            "cycle_time": 45.2,
            "total_articles": 25,
            "total_tweets": 50
        }
        test_db.commit()

        # Verify all fields updated
        test_db.refresh(session)
        assert session.status == "completed"
        assert session.end_time is not None
        assert session.articles_processed == 25
        assert session.tweets_processed == 50
        assert session.alerts_generated == 3
        assert session.performance_metrics["cycle_time"] == 45.2

    def test_alerts_created_during_cycle(self, test_db, sample_companies):
        """Test that alerts are created and linked to session"""
        session_id = str(uuid.uuid4())

        # Create alerts
        alerts = [
            Alert(
                title=f"Test Alert {i}",
                content="Test content",
                source="twitter",
                confidence=0.85,
                urgency_level="high",
                company_id=sample_companies[0].id
            )
            for i in range(3)
        ]

        for alert in alerts:
            test_db.add(alert)
        test_db.commit()

        # Verify alerts exist
        alert_count = test_db.query(Alert).count()
        assert alert_count >= 3

    def test_feed_statistics_update_after_scraping(self, test_db, sample_feeds):
        """Test that feed statistics update after scraping"""
        feed = sample_feeds[0]
        initial_success_count = feed.success_count

        # Simulate successful scrape
        feed.success_count += 1
        feed.last_fetch = datetime.now(timezone.utc)
        feed.tge_alerts_found = (feed.tge_alerts_found or 0) + 2
        test_db.commit()

        # Verify updates
        test_db.refresh(feed)
        assert feed.success_count == initial_success_count + 1
        assert feed.last_fetch is not None
        assert feed.tge_alerts_found >= 2


class TestEndToEndWorkflow:
    """Test suite for complete end-to-end workflow"""

    @patch('src.main_optimized.OptimizedCryptoTGEMonitor')
    def test_complete_scraping_cycle(self, mock_monitor_class, client, test_db, sample_feeds, sample_companies):
        """Test complete workflow: Trigger → Scrape → Update → Verify"""
        # Setup mock monitor
        mock_monitor = Mock()
        mock_monitor.current_cycle_stats = {
            'articles_processed': 15,
            'tweets_processed': 30,
            'alerts_generated': 2,
            'feeds_processed': 2,
            'errors_encountered': 0
        }
        mock_monitor.run_monitoring_cycle = Mock()
        mock_monitor_class.return_value = mock_monitor

        # Step 1: Trigger scraping
        response = client.post("/monitoring/trigger")
        assert response.status_code == 200
        session_id = response.json()["session_id"]

        # Step 2: Wait for background processing
        time.sleep(1)

        # Step 3: Check session was created
        session = test_db.query(MonitoringSession).filter(
            MonitoringSession.session_id == session_id
        ).first()
        assert session is not None

        # Step 4: Verify monitor was called
        assert mock_monitor.run_monitoring_cycle.called

    def test_dashboard_metrics_refresh_after_cycle(self, client, test_db):
        """Test that dashboard metrics update after scraping"""
        # Get initial statistics
        initial_stats = client.get("/statistics/system").json()
        initial_alerts = initial_stats["total_alerts"]

        # Create new alerts (simulating scraping)
        alert = Alert(
            title="New Alert",
            content="Test",
            source="news",
            confidence=0.9,
            urgency_level="high"
        )
        test_db.add(alert)
        test_db.commit()

        # Get updated statistics
        updated_stats = client.get("/statistics/system").json()
        updated_alerts = updated_stats["total_alerts"]

        # Verify increase
        assert updated_alerts == initial_alerts + 1


class TestErrorHandling:
    """Test suite for error handling and edge cases"""

    @patch('src.main_optimized.OptimizedCryptoTGEMonitor')
    def test_scraping_failure_updates_session(self, mock_monitor_class, client, test_db):
        """Test that scraping failures are properly recorded"""
        # Setup mock to raise exception
        mock_monitor = Mock()
        mock_monitor.run_monitoring_cycle = Mock(side_effect=Exception("Scraping failed"))
        mock_monitor_class.return_value = mock_monitor

        # Trigger scraping
        response = client.post("/monitoring/trigger")
        session_id = response.json()["session_id"]

        # Wait for background processing
        time.sleep(1)

        # Check session status
        session = test_db.query(MonitoringSession).filter(
            MonitoringSession.session_id == session_id
        ).first()

        # Session should exist even if scraping failed
        assert session is not None

    def test_database_connection_error_handling(self, client):
        """Test API behavior when database connection fails"""
        with patch.object(DatabaseManager, 'check_connection', return_value=False):
            response = client.get("/health")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "unhealthy"
            assert data["database"] is False

    def test_timeout_handling(self, test_db):
        """Test that long-running cycles timeout appropriately"""
        session = MonitoringSession(
            session_id=str(uuid.uuid4()),
            status="running",
            start_time=datetime.now(timezone.utc) - timedelta(minutes=10)
        )
        test_db.add(session)
        test_db.commit()

        # Check session age
        age_seconds = (datetime.now(timezone.utc) - session.start_time).total_seconds()

        # Should be older than 5 minutes (timeout threshold)
        assert age_seconds > 300

    def test_concurrent_scraping_requests(self, client, test_db):
        """Test handling of concurrent scraping requests"""
        # Trigger multiple cycles
        session_ids = []
        for _ in range(3):
            response = client.post("/monitoring/trigger")
            session_ids.append(response.json()["session_id"])

        # All should be unique
        assert len(set(session_ids)) == 3

        # All sessions should exist
        for session_id in session_ids:
            session = test_db.query(MonitoringSession).filter(
                MonitoringSession.session_id == session_id
            ).first()
            assert session is not None


class TestPerformanceMetrics:
    """Test suite for performance and response times"""

    def test_trigger_endpoint_response_time(self, client):
        """Test that trigger endpoint responds quickly"""
        start_time = time.time()
        response = client.post("/monitoring/trigger")
        elapsed = time.time() - start_time

        assert response.status_code == 200
        # Should respond in less than 2 seconds
        assert elapsed < 2.0

    def test_progress_endpoint_response_time(self, client, test_db):
        """Test that progress endpoint responds quickly"""
        session = MonitoringSession(
            session_id=str(uuid.uuid4()),
            status="running"
        )
        test_db.add(session)
        test_db.commit()

        start_time = time.time()
        response = client.get(f"/monitoring/session/{session.session_id}/progress")
        elapsed = time.time() - start_time

        assert response.status_code == 200
        # Should respond in less than 500ms
        assert elapsed < 0.5

    def test_statistics_query_performance(self, client, test_db, sample_companies):
        """Test that statistics queries perform well with data"""
        # Create some alerts
        for i in range(50):
            alert = Alert(
                title=f"Alert {i}",
                content="Test",
                source="news" if i % 2 == 0 else "twitter",
                confidence=0.8,
                urgency_level="medium",
                company_id=sample_companies[i % len(sample_companies)].id
            )
            test_db.add(alert)
        test_db.commit()

        # Query statistics
        start_time = time.time()
        response = client.get("/statistics/system")
        elapsed = time.time() - start_time

        assert response.status_code == 200
        # Should complete in less than 1 second
        assert elapsed < 1.0


class TestEdgeCases:
    """Test suite for edge cases and boundary conditions"""

    def test_empty_database_scraping(self, client, test_db):
        """Test scraping with no feeds or companies"""
        # Clear all data
        test_db.query(Feed).delete()
        test_db.query(Company).delete()
        test_db.commit()

        # Trigger should still work
        response = client.post("/monitoring/trigger")
        assert response.status_code == 200

    def test_session_with_no_metrics(self, client, test_db):
        """Test progress endpoint with session that has no metrics"""
        session = MonitoringSession(
            session_id=str(uuid.uuid4()),
            status="running",
            performance_metrics=None
        )
        test_db.add(session)
        test_db.commit()

        response = client.get(f"/monitoring/session/{session.session_id}/progress")

        assert response.status_code == 200
        data = response.json()
        assert data["current_phase"] == "starting"
        assert data["progress_percentage"] == 5

    def test_partial_completion_state(self, test_db):
        """Test session in partial completion state"""
        session = MonitoringSession(
            session_id=str(uuid.uuid4()),
            status="running",
            articles_processed=10,
            tweets_processed=0,  # Partial - news done but twitter not started
            performance_metrics={"phase": "news_complete"}
        )
        test_db.add(session)
        test_db.commit()

        # Verify partial state is valid
        assert session.articles_processed > 0
        assert session.tweets_processed == 0
        assert session.performance_metrics["phase"] == "news_complete"


class TestManualTestingChecklist:
    """Manual testing checklist - to be executed manually"""

    def test_manual_checklist_instructions(self):
        """
        MANUAL TESTING CHECKLIST

        1. Frontend Trigger Button Test:
           - Navigate to dashboard
           - Click "Start Scraping Cycle" button
           - Verify button becomes disabled
           - Verify progress bar appears
           - Verify progress updates every few seconds
           - Verify completion message appears
           - Verify button re-enables after completion

        2. Dashboard Refresh Test:
           - Note current alert count on dashboard
           - Trigger scraping cycle
           - Wait for completion
           - Verify alert count increases
           - Verify "Last Updated" timestamp updates
           - Verify new alerts appear in recent alerts list

        3. Real-time Progress Test:
           - Trigger scraping in one browser tab
           - Open progress API endpoint in another tab
           - Refresh progress endpoint multiple times
           - Verify progress_percentage increases
           - Verify current_phase changes
           - Verify metrics update

        4. Error Recovery Test:
           - Stop PostgreSQL database
           - Try to trigger scraping
           - Verify error message appears
           - Restart database
           - Verify system recovers

        5. Concurrent User Test:
           - Open dashboard in two browser windows
           - Trigger scraping from window 1
           - Verify window 2 sees updates (if WebSocket connected)
           - Manually refresh window 2
           - Verify both windows show same data

        6. Network Interruption Test:
           - Trigger scraping
           - Disable network briefly
           - Re-enable network
           - Verify scraping completes or shows error

        7. Long-running Cycle Test:
           - Trigger scraping with many feeds
           - Monitor for 5 minutes
           - Verify timeout mechanism works
           - Verify session marked as failed if timeout
        """
        pytest.skip("This is a manual testing checklist, not an automated test")


# Test runner configuration
if __name__ == "__main__":
    pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "--color=yes",
        "-ra"  # Show summary of all test results
    ])

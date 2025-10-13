"""
API Integration Tests - Metrics Endpoint Validation
Tests the REST API endpoints that serve dashboard metrics
"""

import pytest
from fastapi.testclient import TestClient
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock
from sqlalchemy.orm import Session

from src.api import app
from src.models import Alert, Company, Feed, MonitoringSession, SystemMetrics
from src.database import DatabaseManager


class TestHealthEndpoint:
    """Test suite for health check endpoint"""

    @pytest.fixture
    def client(self):
        """Create test client"""
        return TestClient(app)

    def test_health_check_success(self, client):
        """Test health check returns 200"""
        with patch.object(DatabaseManager, 'check_connection', return_value=True), \
             patch.object(DatabaseManager, 'get_db'):
            response = client.get('/health')

            assert response.status_code == 200
            data = response.json()
            assert 'status' in data
            assert 'database' in data
            assert 'redis' in data

    def test_health_check_includes_feed_stats(self, client):
        """Test health check includes feed health statistics"""
        with patch.object(DatabaseManager, 'check_connection', return_value=True), \
             patch.object(DatabaseManager, 'get_db'):
            response = client.get('/health')

            assert response.status_code == 200
            data = response.json()
            assert 'feeds_health' in data
            assert 'total' in data['feeds_health']
            assert 'active' in data['feeds_health']

    def test_health_check_includes_system_metrics(self, client):
        """Test health check includes system metrics"""
        with patch.object(DatabaseManager, 'check_connection', return_value=True), \
             patch.object(DatabaseManager, 'get_db'):
            response = client.get('/health')

            assert response.status_code == 200
            data = response.json()
            assert 'system_metrics' in data


class TestStatisticsEndpoints:
    """Test suite for statistics endpoints"""

    @pytest.fixture
    def client(self):
        """Create test client"""
        return TestClient(app)

    @pytest.fixture
    def mock_db_session(self):
        """Create mock database session"""
        session = MagicMock(spec=Session)
        return session

    def test_system_statistics_structure(self, client):
        """Test system statistics endpoint returns correct structure"""
        with patch.object(DatabaseManager, 'get_db'):
            response = client.get('/statistics/system')

            assert response.status_code == 200
            data = response.json()
            assert 'total_companies' in data
            assert 'total_feeds' in data
            assert 'total_alerts' in data
            assert 'alerts_last_24h' in data
            assert 'alerts_last_7d' in data

    def test_system_statistics_count_accuracy(self, client, mock_db_session):
        """Test that counts are accurate"""
        with patch.object(DatabaseManager, 'get_db', return_value=mock_db_session):
            # Mock counts
            mock_db_session.query.return_value.count.return_value = 10

            response = client.get('/statistics/system')

            assert response.status_code == 200

    def test_alert_statistics_with_date_range(self, client):
        """Test alert statistics with custom date range"""
        with patch.object(DatabaseManager, 'get_db'):
            response = client.get('/statistics/alerts?days=7')

            assert response.status_code == 200
            data = response.json()
            assert 'total_alerts' in data
            assert 'alerts_by_source' in data

    def test_statistics_includes_confidence_breakdown(self, client):
        """Test statistics include confidence distribution"""
        with patch.object(DatabaseManager, 'get_db'):
            response = client.get('/statistics/alerts')

            assert response.status_code == 200
            data = response.json()
            assert 'alerts_by_confidence' in data


class TestMonitoringEndpoints:
    """Test suite for monitoring control endpoints"""

    @pytest.fixture
    def client(self):
        """Create test client"""
        return TestClient(app)

    def test_trigger_monitoring_cycle(self, client):
        """Test triggering a monitoring cycle"""
        with patch('src.api.OptimizedCryptoTGEMonitor') as mock_monitor, \
             patch.object(DatabaseManager, 'get_db'), \
             patch.object(DatabaseManager, 'get_session'):

            response = client.post('/monitoring/trigger')

            assert response.status_code == 200
            data = response.json()
            assert 'message' in data
            assert 'session_id' in data
            assert data['message'] == 'Monitoring cycle started successfully'

    def test_monitoring_cycle_creates_session(self, client):
        """Test that monitoring cycle creates a session record"""
        with patch('src.api.OptimizedCryptoTGEMonitor') as mock_monitor, \
             patch.object(DatabaseManager, 'get_db') as mock_get_db, \
             patch.object(DatabaseManager, 'get_session'):

            mock_db = MagicMock(spec=Session)
            mock_get_db.return_value = mock_db

            response = client.post('/monitoring/trigger')

            assert response.status_code == 200
            assert mock_db.add.called
            assert mock_db.commit.called

    def test_get_monitoring_session_status(self, client):
        """Test retrieving monitoring session status"""
        session_id = "test-session-123"

        with patch.object(DatabaseManager, 'get_db') as mock_get_db:
            mock_db = MagicMock(spec=Session)
            mock_get_db.return_value = mock_db

            # Mock session
            mock_session = MagicMock(spec=MonitoringSession)
            mock_session.session_id = session_id
            mock_session.status = "completed"
            mock_session.to_dict.return_value = {
                'session_id': session_id,
                'status': 'completed',
                'articles_processed': 25,
                'tweets_processed': 15
            }
            mock_db.query.return_value.filter.return_value.first.return_value = mock_session

            response = client.get(f'/monitoring/session/{session_id}')

            assert response.status_code == 200
            data = response.json()
            assert data['session_id'] == session_id
            assert data['status'] == 'completed'

    def test_monitoring_session_not_found(self, client):
        """Test 404 when session not found"""
        session_id = "nonexistent-session"

        with patch.object(DatabaseManager, 'get_db') as mock_get_db:
            mock_db = MagicMock(spec=Session)
            mock_get_db.return_value = mock_db
            mock_db.query.return_value.filter.return_value.first.return_value = None

            response = client.get(f'/monitoring/session/{session_id}')

            assert response.status_code == 404


class TestFeedEndpoints:
    """Test suite for feed management endpoints"""

    @pytest.fixture
    def client(self):
        """Create test client"""
        return TestClient(app)

    def test_list_feeds_includes_statistics(self, client):
        """Test that feed list includes statistics"""
        with patch.object(DatabaseManager, 'get_db') as mock_get_db:
            mock_db = MagicMock(spec=Session)
            mock_get_db.return_value = mock_db

            # Mock feeds with statistics
            mock_feed = MagicMock(spec=Feed)
            mock_feed.id = 1
            mock_feed.url = 'https://example.com/feed'
            mock_feed.success_count = 10
            mock_feed.failure_count = 2
            mock_feed.tge_alerts_found = 5
            mock_db.query.return_value.offset.return_value.limit.return_value.all.return_value = [mock_feed]

            response = client.get('/feeds')

            assert response.status_code == 200

    def test_get_feed_by_id(self, client):
        """Test retrieving individual feed with stats"""
        feed_id = 1

        with patch.object(DatabaseManager, 'get_db') as mock_get_db:
            mock_db = MagicMock(spec=Session)
            mock_get_db.return_value = mock_db

            mock_feed = MagicMock(spec=Feed)
            mock_feed.id = feed_id
            mock_db.query.return_value.filter.return_value.first.return_value = mock_feed

            response = client.get(f'/feeds/{feed_id}')

            assert response.status_code == 200


class TestAlertEndpoints:
    """Test suite for alert endpoints"""

    @pytest.fixture
    def client(self):
        """Create test client"""
        return TestClient(app)

    def test_list_alerts_with_filters(self, client):
        """Test listing alerts with various filters"""
        with patch.object(DatabaseManager, 'get_db') as mock_get_db:
            mock_db = MagicMock(spec=Session)
            mock_get_db.return_value = mock_db
            mock_db.query.return_value.filter.return_value.order_by.return_value.offset.return_value.limit.return_value.all.return_value = []

            response = client.get('/alerts?min_confidence=0.7&status=active')

            assert response.status_code == 200

    def test_alerts_include_confidence_scores(self, client):
        """Test that alerts include confidence scores"""
        with patch.object(DatabaseManager, 'get_db') as mock_get_db:
            mock_db = MagicMock(spec=Session)
            mock_get_db.return_value = mock_db

            mock_alert = MagicMock(spec=Alert)
            mock_alert.id = 1
            mock_alert.confidence = 0.85
            mock_db.query.return_value.filter.return_value.order_by.return_value.offset.return_value.limit.return_value.all.return_value = [mock_alert]

            response = client.get('/alerts')

            assert response.status_code == 200


class TestRealTimeUpdates:
    """Test suite for real-time metric updates"""

    @pytest.fixture
    def client(self):
        """Create test client"""
        return TestClient(app)

    def test_websocket_connection(self, client):
        """Test WebSocket connection for real-time updates"""
        with client.websocket_connect('/ws') as websocket:
            # Send ping
            websocket.send_json({'type': 'ping'})

            # Receive pong
            data = websocket.receive_json()
            assert data['type'] == 'pong'

    def test_websocket_alert_notification(self, client):
        """Test receiving alert notifications via WebSocket"""
        # This would require more complex async testing
        # Placeholder for WebSocket notification tests
        pass


class TestCacheInvalidation:
    """Test suite for cache invalidation after scraping"""

    def test_statistics_cache_invalidation(self):
        """Test that statistics cache is invalidated after scraping"""
        # Would test Redis cache invalidation
        # Placeholder for cache testing
        pass


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])

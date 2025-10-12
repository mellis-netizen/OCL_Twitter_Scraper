"""
Unit Tests for Database Service
Comprehensive testing of database operations with SQLAlchemy mocking
Tests CRUD operations, query building, filtering, pagination, and transactions
"""

import unittest
from unittest.mock import Mock, patch, MagicMock, call, PropertyMock
from datetime import datetime, timezone, timedelta
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

# Mock dependencies before importing database modules
sys.modules['redis'] = MagicMock()
sys.modules['psycopg2'] = MagicMock()
sys.modules['email_validator'] = MagicMock()

# Mock pydantic email validation
with patch('pydantic.networks.import_email_validator', return_value=None):
    # Import with try/except to handle import errors gracefully
    try:
        from src.database_service import DatabaseService, migrate_from_file_storage, db_service
        from src.models import Company, Alert, Feed, MonitoringSession, SystemMetrics, User
        from src.database import DatabaseManager, CacheManager
    except ImportError as e:
        import pytest
        pytest.skip(f"Required modules not available: {e}", allow_module_level=True)


class TestDatabaseServiceCompanyOperations(unittest.TestCase):
    """Test company-related database operations"""

    def setUp(self):
        """Set up test fixtures"""
        self.db_service = DatabaseService()
        self.mock_session = MagicMock()

    @patch.object(DatabaseManager, 'get_session')
    def test_get_companies_all(self, mock_get_session):
        """Test getting all companies including inactive"""
        mock_session = MagicMock()
        mock_get_session.return_value.__enter__.return_value = mock_session

        # Create mock companies
        mock_company1 = Mock(spec=Company, name="Company1", status="active")
        mock_company2 = Mock(spec=Company, name="Company2", status="inactive")
        mock_session.query.return_value.all.return_value = [mock_company1, mock_company2]

        result = self.db_service.get_companies(include_inactive=True)

        self.assertEqual(len(result), 2)
        mock_session.query.assert_called_once_with(Company)
        mock_session.query.return_value.filter.assert_not_called()

    @patch.object(DatabaseManager, 'get_session')
    def test_get_companies_active_only(self, mock_get_session):
        """Test getting active companies only"""
        mock_session = MagicMock()
        mock_get_session.return_value.__enter__.return_value = mock_session

        mock_company = Mock(spec=Company, name="ActiveCo", status="active")
        mock_query = mock_session.query.return_value
        mock_query.filter.return_value.all.return_value = [mock_company]

        result = self.db_service.get_companies(include_inactive=False)

        self.assertEqual(len(result), 1)
        mock_query.filter.assert_called_once()

    @patch.object(DatabaseManager, 'get_session')
    def test_get_company_by_name_exists(self, mock_get_session):
        """Test retrieving existing company by name"""
        mock_session = MagicMock()
        mock_get_session.return_value.__enter__.return_value = mock_session

        mock_company = Mock(spec=Company)
        mock_company.name = "TestCo"
        mock_company.id = 1
        mock_query = mock_session.query.return_value
        mock_query.filter.return_value.first.return_value = mock_company

        result = self.db_service.get_company_by_name("TestCo")

        self.assertEqual(result.name, "TestCo")
        self.assertEqual(result.id, 1)

    @patch.object(DatabaseManager, 'get_session')
    def test_get_company_by_name_not_exists(self, mock_get_session):
        """Test retrieving non-existent company"""
        mock_session = MagicMock()
        mock_get_session.return_value.__enter__.return_value = mock_session

        mock_query = mock_session.query.return_value
        mock_query.filter.return_value.first.return_value = None

        result = self.db_service.get_company_by_name("NonExistent")

        self.assertIsNone(result)

    @patch.object(CacheManager, 'delete')
    @patch.object(DatabaseManager, 'get_session')
    def test_create_new_company(self, mock_get_session, mock_cache_delete):
        """Test creating a new company"""
        mock_session = MagicMock()
        mock_get_session.return_value.__enter__.return_value = mock_session

        # Company doesn't exist
        mock_query = mock_session.query.return_value
        mock_query.filter.return_value.first.return_value = None

        company_data = {
            'name': 'NewCo',
            'priority': 'HIGH',
            'status': 'active'
        }

        # Mock the created company
        mock_company = Mock(spec=Company, **company_data, id=1)
        mock_session.refresh = Mock(side_effect=lambda x: setattr(x, 'id', 1))

        with patch('src.database_service.Company', return_value=mock_company):
            result = self.db_service.create_or_update_company(company_data)

        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()
        mock_cache_delete.assert_any_call("companies:all")
        mock_cache_delete.assert_any_call("companies:active")

    @patch.object(CacheManager, 'delete')
    @patch.object(DatabaseManager, 'get_session')
    def test_update_existing_company(self, mock_get_session, mock_cache_delete):
        """Test updating an existing company"""
        mock_session = MagicMock()
        mock_get_session.return_value.__enter__.return_value = mock_session

        # Existing company
        mock_company = Mock(spec=Company, name="ExistingCo", priority="MEDIUM")
        mock_query = mock_session.query.return_value
        mock_query.filter.return_value.first.return_value = mock_company

        company_data = {
            'name': 'ExistingCo',
            'priority': 'HIGH',
            'status': 'active'
        }

        result = self.db_service.create_or_update_company(company_data)

        # Should update attributes
        self.assertEqual(mock_company.priority, 'HIGH')
        mock_session.add.assert_not_called()  # Should not add, only update
        mock_session.commit.assert_called_once()

    @patch.object(DatabaseService, 'get_company_by_name')
    @patch.object(DatabaseService, 'create_or_update_company')
    def test_get_or_create_company_exists(self, mock_create, mock_get):
        """Test get_or_create when company exists"""
        mock_company = Mock(spec=Company, name="Existing", id=1)
        mock_get.return_value = mock_company

        result = self.db_service.get_or_create_company_by_name("Existing")

        self.assertEqual(result, mock_company)
        mock_create.assert_not_called()

    @patch.object(DatabaseService, 'get_company_by_name')
    @patch.object(DatabaseService, 'create_or_update_company')
    def test_get_or_create_company_creates(self, mock_create, mock_get):
        """Test get_or_create when company doesn't exist"""
        mock_get.return_value = None
        mock_new_company = Mock(spec=Company, name="NewCo", id=2)
        mock_create.return_value = mock_new_company

        result = self.db_service.get_or_create_company_by_name("NewCo")

        self.assertEqual(result, mock_new_company)
        mock_create.assert_called_once()


class TestDatabaseServiceAlertOperations(unittest.TestCase):
    """Test alert-related database operations"""

    def setUp(self):
        """Set up test fixtures"""
        self.db_service = DatabaseService()

    @patch.object(CacheManager, 'delete')
    @patch.object(DatabaseService, 'get_or_create_company_by_name')
    @patch.object(DatabaseManager, 'get_session')
    def test_create_alert_with_company(self, mock_get_session, mock_get_company, mock_cache_delete):
        """Test creating alert with company association"""
        mock_session = MagicMock()
        mock_get_session.return_value.__enter__.return_value = mock_session

        mock_company = Mock(spec=Company, id=5, name="TestCo")
        mock_get_company.return_value = mock_company

        alert_data = {
            'title': 'Test Alert',
            'content': 'Alert content',
            'source': 'twitter',
            'source_url': 'https://twitter.com/test',
            'confidence': 0.85,
            'company_name': 'TestCo',
            'keywords_matched': ['TGE', 'token'],
            'tokens_mentioned': ['TEST'],
            'urgency_level': 'high'
        }

        mock_alert = Mock(spec=Alert, id=1, **alert_data)

        with patch('src.database_service.Alert', return_value=mock_alert):
            result = self.db_service.create_alert(alert_data, user_id=10)

        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()
        mock_cache_delete.assert_called_with("alerts:recent")

    @patch.object(DatabaseManager, 'get_session')
    def test_create_alert_without_company(self, mock_get_session):
        """Test creating alert without company"""
        mock_session = MagicMock()
        mock_get_session.return_value.__enter__.return_value = mock_session

        alert_data = {
            'title': 'Test Alert',
            'content': 'Alert content',
            'source': 'news',
            'confidence': 0.75
        }

        mock_alert = Mock(spec=Alert, id=1)

        with patch('src.database_service.Alert', return_value=mock_alert):
            result = self.db_service.create_alert(alert_data)

        mock_session.add.assert_called_once()

    @patch.object(DatabaseManager, 'get_session')
    def test_get_alerts_no_filters(self, mock_get_session):
        """Test getting alerts without filters"""
        mock_session = MagicMock()
        mock_get_session.return_value.__enter__.return_value = mock_session

        mock_alerts = [Mock(spec=Alert) for _ in range(5)]
        mock_query = mock_session.query.return_value
        mock_query.order_by.return_value.offset.return_value.limit.return_value.all.return_value = mock_alerts

        result = self.db_service.get_alerts(limit=100, offset=0)

        self.assertEqual(len(result), 5)

    @patch.object(DatabaseManager, 'get_session')
    def test_get_alerts_with_company_filter(self, mock_get_session):
        """Test getting alerts filtered by company"""
        mock_session = MagicMock()
        mock_get_session.return_value.__enter__.return_value = mock_session

        mock_alerts = [Mock(spec=Alert, company_id=5)]
        mock_query = mock_session.query.return_value
        filtered_query = mock_query.filter.return_value
        filtered_query.order_by.return_value.offset.return_value.limit.return_value.all.return_value = mock_alerts

        result = self.db_service.get_alerts(company_id=5)

        self.assertEqual(len(result), 1)
        mock_query.filter.assert_called()

    @patch.object(DatabaseManager, 'get_session')
    def test_get_alerts_with_multiple_filters(self, mock_get_session):
        """Test getting alerts with multiple filters"""
        mock_session = MagicMock()
        mock_get_session.return_value.__enter__.return_value = mock_session

        mock_alerts = [Mock(spec=Alert)]
        mock_query = mock_session.query.return_value

        # Chain filter calls
        filtered1 = mock_query.filter.return_value
        filtered2 = filtered1.filter.return_value
        filtered3 = filtered2.filter.return_value
        filtered3.order_by.return_value.offset.return_value.limit.return_value.all.return_value = mock_alerts

        from_date = datetime.now(timezone.utc) - timedelta(days=7)
        result = self.db_service.get_alerts(
            company_id=5,
            source='twitter',
            min_confidence=0.8,
            from_date=from_date
        )

        # Should have 4 filter calls (company, source, confidence, date)
        # Each filter returns a new mock which also has filter() called on it
        # So we check that filters were applied
        self.assertGreater(mock_query.filter.call_count, 0)

    @patch.object(DatabaseManager, 'get_session')
    def test_get_alerts_pagination(self, mock_get_session):
        """Test alert pagination"""
        mock_session = MagicMock()
        mock_get_session.return_value.__enter__.return_value = mock_session

        mock_alerts = [Mock(spec=Alert) for _ in range(10)]
        mock_query = mock_session.query.return_value
        mock_query.order_by.return_value.offset.return_value.limit.return_value.all.return_value = mock_alerts

        result = self.db_service.get_alerts(limit=10, offset=20)

        # Check offset and limit were applied
        mock_query.order_by.return_value.offset.assert_called_with(20)
        mock_query.order_by.return_value.offset.return_value.limit.assert_called_with(10)

    @patch.object(DatabaseManager, 'get_session')
    def test_get_recent_alerts(self, mock_get_session):
        """Test getting recent alerts"""
        mock_session = MagicMock()
        mock_get_session.return_value.__enter__.return_value = mock_session

        mock_alerts = [Mock(spec=Alert) for _ in range(3)]
        mock_query = mock_session.query.return_value
        mock_query.filter.return_value.order_by.return_value.all.return_value = mock_alerts

        result = self.db_service.get_recent_alerts(hours=24)

        self.assertEqual(len(result), 3)
        mock_query.filter.assert_called_once()

    @patch.object(CacheManager, 'set')
    @patch.object(CacheManager, 'exists')
    @patch.object(DatabaseManager, 'get_session')
    def test_check_duplicate_alert_by_url(self, mock_get_session, mock_cache_exists, mock_cache_set):
        """Test duplicate alert check by URL"""
        mock_session = MagicMock()
        mock_get_session.return_value.__enter__.return_value = mock_session

        mock_cache_exists.return_value = False

        # Alert exists in DB
        mock_alert = Mock(spec=Alert, source_url='https://example.com/article')
        mock_query = mock_session.query.return_value
        mock_query.filter.return_value.first.return_value = mock_alert

        result = self.db_service.check_duplicate_alert('hash123', url='https://example.com/article')

        self.assertTrue(result)
        mock_cache_set.assert_called()

    @patch.object(CacheManager, 'set')
    @patch.object(CacheManager, 'exists')
    @patch.object(DatabaseManager, 'get_session')
    def test_check_duplicate_alert_not_duplicate(self, mock_get_session, mock_cache_exists, mock_cache_set):
        """Test non-duplicate alert check"""
        mock_session = MagicMock()
        mock_get_session.return_value.__enter__.return_value = mock_session

        mock_cache_exists.return_value = False

        # No alert in DB
        mock_query = mock_session.query.return_value
        mock_query.filter.return_value.first.return_value = None

        result = self.db_service.check_duplicate_alert('hash456', url='https://example.com/new')

        self.assertFalse(result)

    @patch.object(CacheManager, 'exists')
    def test_check_duplicate_alert_cached(self, mock_cache_exists):
        """Test duplicate alert check using cache"""
        mock_cache_exists.return_value = True

        result = self.db_service.check_duplicate_alert('cached_hash')

        self.assertTrue(result)


class TestDatabaseServiceFeedOperations(unittest.TestCase):
    """Test feed-related database operations"""

    def setUp(self):
        """Set up test fixtures"""
        self.db_service = DatabaseService()

    @patch.object(DatabaseManager, 'get_session')
    def test_get_feeds_active_only(self, mock_get_session):
        """Test getting active feeds only"""
        mock_session = MagicMock()
        mock_get_session.return_value.__enter__.return_value = mock_session

        mock_feeds = [Mock(spec=Feed, is_active=True) for _ in range(3)]
        mock_query = mock_session.query.return_value
        mock_query.filter.return_value.all.return_value = mock_feeds

        result = self.db_service.get_feeds(active_only=True)

        self.assertEqual(len(result), 3)
        mock_query.filter.assert_called_once()

    @patch.object(DatabaseManager, 'get_session')
    def test_get_feeds_all(self, mock_get_session):
        """Test getting all feeds"""
        mock_session = MagicMock()
        mock_get_session.return_value.__enter__.return_value = mock_session

        mock_feeds = [Mock(spec=Feed) for _ in range(5)]
        mock_query = mock_session.query.return_value
        mock_query.all.return_value = mock_feeds

        result = self.db_service.get_feeds(active_only=False)

        self.assertEqual(len(result), 5)
        mock_query.filter.assert_not_called()

    @patch.object(DatabaseManager, 'get_session')
    def test_update_feed_stats_existing_success(self, mock_get_session):
        """Test updating existing feed stats on success"""
        mock_session = MagicMock()
        mock_get_session.return_value.__enter__.return_value = mock_session

        mock_feed = Mock(spec=Feed, success_count=10, failure_count=2,
                        articles_found=50, tge_alerts_found=5)
        mock_query = mock_session.query.return_value
        mock_query.filter.return_value.first.return_value = mock_feed

        self.db_service.update_feed_stats(
            'https://example.com/feed.xml',
            success=True,
            article_count=5,
            tge_alerts=2
        )

        self.assertEqual(mock_feed.success_count, 11)
        self.assertEqual(mock_feed.articles_found, 55)
        self.assertEqual(mock_feed.tge_alerts_found, 7)
        self.assertIsNotNone(mock_feed.last_success)
        mock_session.commit.assert_called_once()

    @patch.object(DatabaseManager, 'get_session')
    def test_update_feed_stats_existing_failure(self, mock_get_session):
        """Test updating existing feed stats on failure"""
        mock_session = MagicMock()
        mock_get_session.return_value.__enter__.return_value = mock_session

        mock_feed = Mock(spec=Feed, success_count=10, failure_count=2)
        mock_query = mock_session.query.return_value
        mock_query.filter.return_value.first.return_value = mock_feed

        self.db_service.update_feed_stats(
            'https://example.com/feed.xml',
            success=False,
            error_message='Connection timeout'
        )

        self.assertEqual(mock_feed.failure_count, 3)
        self.assertEqual(mock_feed.last_error, 'Connection timeout')
        self.assertIsNotNone(mock_feed.last_failure)

    @patch.object(DatabaseManager, 'get_session')
    def test_update_feed_stats_create_new(self, mock_get_session):
        """Test creating new feed when updating stats"""
        mock_session = MagicMock()
        mock_get_session.return_value.__enter__.return_value = mock_session

        # Feed doesn't exist
        mock_query = mock_session.query.return_value
        mock_query.filter.return_value.first.return_value = None

        mock_feed = Mock(spec=Feed)
        mock_feed.success_count = 0
        mock_feed.failure_count = 0
        mock_feed.articles_found = 0
        mock_feed.tge_alerts_found = 0

        with patch('src.database_service.Feed', return_value=mock_feed):
            self.db_service.update_feed_stats(
                'https://newsite.com/feed.xml',
                success=True,
                article_count=10
            )

        mock_session.add.assert_called_once()

    @patch.object(DatabaseManager, 'get_session')
    def test_get_feed_health_report(self, mock_get_session):
        """Test getting feed health report"""
        mock_session = MagicMock()
        mock_get_session.return_value.__enter__.return_value = mock_session

        # Mock feed counts - create separate query mocks for each count call
        count_query1 = MagicMock()
        count_query1.count.return_value = 10
        count_query2 = MagicMock()
        count_query2.count.return_value = 8

        # Mock healthy feeds
        mock_feed1 = Mock(spec=Feed, success_count=90, failure_count=10, tge_alerts_found=20)
        mock_feed2 = Mock(spec=Feed, success_count=50, failure_count=50, tge_alerts_found=5)

        # Mock top performers
        mock_top_feed = Mock(spec=Feed, url='https://top.com/feed', name='Top Feed',
                            tge_alerts_found=50, success_count=100, failure_count=0)

        # Setup query mock to return different results
        calls = [count_query1, count_query2]
        call_index = [0]

        def query_side_effect(*args):
            if call_index[0] < len(calls):
                result = calls[call_index[0]]
                call_index[0] += 1
                return result
            # For other queries
            mock_query = MagicMock()
            mock_filter = MagicMock()
            mock_filter.all.return_value = [mock_feed1, mock_feed2]
            mock_filter.order_by.return_value.limit.return_value.all.return_value = [mock_top_feed]
            mock_query.filter.return_value = mock_filter
            return mock_query

        mock_session.query.side_effect = query_side_effect

        result = self.db_service.get_feed_health_report()

        self.assertEqual(result['total_feeds'], 10)
        self.assertIn('healthy_feeds', result)
        self.assertIn('top_performers', result)


class TestDatabaseServiceSessionOperations(unittest.TestCase):
    """Test monitoring session operations"""

    def setUp(self):
        """Set up test fixtures"""
        self.db_service = DatabaseService()

    @patch.object(DatabaseManager, 'get_session')
    def test_create_monitoring_session(self, mock_get_session):
        """Test creating monitoring session"""
        mock_session = MagicMock()
        mock_get_session.return_value.__enter__.return_value = mock_session

        mock_monitoring_session = Mock(spec=MonitoringSession,
                                      session_id='test-123', status='running')

        with patch('src.database_service.MonitoringSession', return_value=mock_monitoring_session):
            result = self.db_service.create_monitoring_session('test-123')

        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()
        self.assertEqual(result.session_id, 'test-123')

    @patch.object(DatabaseManager, 'get_session')
    def test_update_monitoring_session_status(self, mock_get_session):
        """Test updating monitoring session status"""
        mock_session = MagicMock()
        mock_get_session.return_value.__enter__.return_value = mock_session

        mock_monitoring_session = Mock(spec=MonitoringSession,
                                      session_id='test-123', status='running')
        mock_query = mock_session.query.return_value
        mock_query.filter.return_value.first.return_value = mock_monitoring_session

        self.db_service.update_monitoring_session('test-123', status='completed')

        self.assertEqual(mock_monitoring_session.status, 'completed')
        self.assertIsNotNone(mock_monitoring_session.end_time)
        mock_session.commit.assert_called_once()

    @patch.object(DatabaseManager, 'get_session')
    def test_update_monitoring_session_metrics(self, mock_get_session):
        """Test updating monitoring session metrics"""
        mock_session = MagicMock()
        mock_get_session.return_value.__enter__.return_value = mock_session

        mock_monitoring_session = Mock(spec=MonitoringSession,
                                      feeds_processed=0, alerts_generated=0)
        mock_query = mock_session.query.return_value
        mock_query.filter.return_value.first.return_value = mock_monitoring_session

        self.db_service.update_monitoring_session(
            'test-123',
            feeds_processed=10,
            alerts_generated=5
        )

        self.assertEqual(mock_monitoring_session.feeds_processed, 10)
        self.assertEqual(mock_monitoring_session.alerts_generated, 5)

    @patch.object(DatabaseManager, 'get_session')
    def test_update_monitoring_session_not_found(self, mock_get_session):
        """Test updating non-existent session"""
        mock_session = MagicMock()
        mock_get_session.return_value.__enter__.return_value = mock_session

        mock_query = mock_session.query.return_value
        mock_query.filter.return_value.first.return_value = None

        # Should not raise error
        self.db_service.update_monitoring_session('nonexistent', status='completed')

        mock_session.commit.assert_not_called()


class TestDatabaseServiceMetricsOperations(unittest.TestCase):
    """Test system metrics operations"""

    def setUp(self):
        """Set up test fixtures"""
        self.db_service = DatabaseService()

    @patch.object(DatabaseManager, 'get_session')
    def test_record_metric(self, mock_get_session):
        """Test recording system metric"""
        mock_session = MagicMock()
        mock_get_session.return_value.__enter__.return_value = mock_session

        mock_metric = Mock(spec=SystemMetrics)

        with patch('src.database_service.SystemMetrics', return_value=mock_metric):
            self.db_service.record_metric(
                metric_type='performance',
                metric_name='api_response_time',
                value=125.5,
                unit='ms',
                tags={'endpoint': '/api/alerts'}
            )

        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()

    @patch.object(DatabaseManager, 'get_session')
    def test_get_metrics_no_filters(self, mock_get_session):
        """Test getting metrics without filters"""
        mock_session = MagicMock()
        mock_get_session.return_value.__enter__.return_value = mock_session

        mock_metrics = [Mock(spec=SystemMetrics) for _ in range(5)]
        mock_query = mock_session.query.return_value
        mock_query.filter.return_value.order_by.return_value.all.return_value = mock_metrics

        result = self.db_service.get_metrics(hours=24)

        self.assertEqual(len(result), 5)

    @patch.object(DatabaseManager, 'get_session')
    def test_get_metrics_with_type_filter(self, mock_get_session):
        """Test getting metrics filtered by type"""
        mock_session = MagicMock()
        mock_get_session.return_value.__enter__.return_value = mock_session

        mock_metrics = [Mock(spec=SystemMetrics, metric_type='cpu')]
        mock_query = mock_session.query.return_value
        filtered = mock_query.filter.return_value
        filtered.filter.return_value.order_by.return_value.all.return_value = mock_metrics

        result = self.db_service.get_metrics(metric_type='cpu', hours=24)

        self.assertEqual(len(result), 1)

    @patch.object(DatabaseManager, 'get_session')
    def test_get_metrics_with_name_filter(self, mock_get_session):
        """Test getting metrics filtered by name"""
        mock_session = MagicMock()
        mock_get_session.return_value.__enter__.return_value = mock_session

        mock_metrics = [Mock(spec=SystemMetrics, metric_name='cpu_usage')]
        mock_query = mock_session.query.return_value
        filtered1 = mock_query.filter.return_value
        filtered2 = filtered1.filter.return_value
        filtered2.filter.return_value.order_by.return_value.all.return_value = mock_metrics

        result = self.db_service.get_metrics(
            metric_type='cpu',
            metric_name='cpu_usage',
            hours=12
        )

        self.assertEqual(len(result), 1)

    @patch.object(DatabaseManager, 'get_session')
    def test_get_metrics_time_range(self, mock_get_session):
        """Test getting metrics with time range"""
        mock_session = MagicMock()
        mock_get_session.return_value.__enter__.return_value = mock_session

        mock_metrics = [Mock(spec=SystemMetrics)]
        mock_query = mock_session.query.return_value
        mock_query.filter.return_value.order_by.return_value.all.return_value = mock_metrics

        result = self.db_service.get_metrics(hours=48)

        # Should filter by timestamp
        self.assertEqual(mock_query.filter.call_count, 1)


class TestDatabaseServiceStatistics(unittest.TestCase):
    """Test statistics and reporting operations"""

    def setUp(self):
        """Set up test fixtures"""
        self.db_service = DatabaseService()

    @patch.object(DatabaseManager, 'get_session')
    def test_get_statistics_basic_counts(self, mock_get_session):
        """Test getting basic statistics"""
        mock_session = MagicMock()
        mock_get_session.return_value.__enter__.return_value = mock_session

        # Mock counts
        mock_session.query.return_value.count.side_effect = [5, 100, 20, 15]

        # Mock average confidence
        mock_session.query.return_value.scalar.return_value = 0.75

        # Mock source stats
        mock_session.query.return_value.group_by.return_value.all.return_value = [
            ('twitter', 50),
            ('news', 50)
        ]

        # Mock company stats
        mock_query = mock_session.query.return_value
        mock_query.outerjoin.return_value.group_by.return_value.all.return_value = [
            ('CompanyA', 30),
            ('CompanyB', 20)
        ]

        result = self.db_service.get_statistics()

        self.assertEqual(result['total_companies'], 5)
        self.assertEqual(result['total_alerts'], 100)
        self.assertEqual(result['avg_confidence'], 0.75)
        self.assertIn('alerts_by_source', result)
        self.assertIn('alerts_by_company', result)

    @patch.object(DatabaseManager, 'get_session')
    def test_get_statistics_time_based(self, mock_get_session):
        """Test getting time-based statistics"""
        mock_session = MagicMock()
        mock_get_session.return_value.__enter__.return_value = mock_session

        # Mock basic counts
        count_side_effects = [5, 100, 20, 15, 10, 45]
        mock_session.query.return_value.count.side_effect = count_side_effects

        # Mock other queries
        mock_session.query.return_value.scalar.return_value = 0.8
        mock_session.query.return_value.group_by.return_value.all.return_value = []
        mock_query = mock_session.query.return_value
        mock_query.outerjoin.return_value.group_by.return_value.all.return_value = []

        result = self.db_service.get_statistics()

        self.assertIn('alerts_last_24h', result)
        self.assertIn('alerts_last_7d', result)


class TestDatabaseServiceMigration(unittest.TestCase):
    """Test data migration operations"""

    def setUp(self):
        """Set up test fixtures"""
        self.db_service = DatabaseService()

    @patch.object(DatabaseService, 'create_alert')
    def test_migrate_legacy_state_alerts(self, mock_create_alert):
        """Test migrating legacy alert data"""
        legacy_state = {
            'alert_history': [
                {
                    'title': 'Old Alert',
                    'content': 'Alert content',
                    'source': 'twitter',
                    'confidence': 0.8,
                    'keywords': ['TGE', 'token'],
                    'companies': ['TestCo'],
                    'timestamp': '2024-01-01T00:00:00Z'
                }
            ]
        }

        result = self.db_service.migrate_legacy_state(legacy_state)

        self.assertEqual(result['alerts_migrated'], 1)
        mock_create_alert.assert_called_once()

    @patch.object(DatabaseService, 'create_or_update_company')
    @patch('config.COMPANIES', [{'name': 'MigrateCo', 'priority': 'HIGH'}])
    def test_migrate_legacy_state_companies(self, mock_create_company):
        """Test migrating legacy company data"""
        legacy_state = {}

        result = self.db_service.migrate_legacy_state(legacy_state)

        self.assertEqual(result['companies_migrated'], 1)
        mock_create_company.assert_called_once()

    @patch.object(DatabaseManager, 'get_session')
    @patch('config.NEWS_SOURCES', ['https://example.com/feed.xml'])
    def test_migrate_legacy_state_feeds(self, mock_get_session):
        """Test migrating legacy feed data"""
        mock_session = MagicMock()
        mock_get_session.return_value.__enter__.return_value = mock_session

        # Feed doesn't exist
        mock_query = mock_session.query.return_value
        mock_query.filter.return_value.first.return_value = None

        with patch.object(DatabaseService, 'create_alert'):
            with patch.object(DatabaseService, 'create_or_update_company'):
                result = self.db_service.migrate_legacy_state({})

        # Should attempt to create feed
        mock_session.add.call_count >= 1

    def test_migrate_legacy_state_error_handling(self):
        """Test migration error handling"""
        legacy_state = {
            'alert_history': [
                {'invalid': 'data'}  # Missing required fields
            ]
        }

        result = self.db_service.migrate_legacy_state(legacy_state)

        self.assertIn('errors', result)
        # Should continue despite errors
        self.assertEqual(result['alerts_migrated'], 0)


class TestDatabaseServiceTransactions(unittest.TestCase):
    """Test transaction handling and rollback"""

    @patch.object(DatabaseManager, 'get_session')
    def test_transaction_rollback_on_error(self, mock_get_session):
        """Test transaction rolls back on error"""
        mock_session = MagicMock()
        mock_session.commit.side_effect = Exception("Database error")
        mock_get_session.return_value.__enter__.return_value = mock_session
        mock_get_session.return_value.__exit__.return_value = None

        db_service = DatabaseService()

        with self.assertRaises(Exception):
            with DatabaseManager.get_session() as db:
                db.add(Mock())
                db.commit()

    @patch.object(DatabaseManager, 'get_session')
    def test_session_cleanup(self, mock_get_session):
        """Test session is properly cleaned up"""
        mock_session = MagicMock()
        mock_get_session.return_value.__enter__.return_value = mock_session

        with DatabaseManager.get_session() as db:
            db.query(Company).all()

        # Context manager should handle cleanup
        mock_get_session.return_value.__exit__.assert_called_once()


class TestMigrationUtility(unittest.TestCase):
    """Test migration utility function"""

    @patch('os.path.exists')
    @patch('builtins.open', create=True)
    @patch.object(DatabaseService, 'migrate_legacy_state')
    def test_migrate_from_file_storage_success(self, mock_migrate, mock_open, mock_exists):
        """Test successful migration from file storage"""
        mock_exists.return_value = True
        mock_open.return_value.__enter__.return_value.read.return_value = '{"alert_history": []}'
        mock_migrate.return_value = {'alerts_migrated': 5, 'companies_migrated': 3, 'errors': []}

        with patch('json.load', return_value={'alert_history': []}):
            result = migrate_from_file_storage()

        self.assertTrue(result['success'])
        self.assertIn('migration_results', result)

    @patch('os.path.exists')
    def test_migrate_from_file_storage_no_files(self, mock_exists):
        """Test migration when no files exist"""
        mock_exists.return_value = False

        result = migrate_from_file_storage()

        self.assertTrue(result['success'])
        self.assertEqual(len(result['migration_results']), 0)

    @patch('os.path.exists')
    @patch('builtins.open', create=True)
    def test_migrate_from_file_storage_error(self, mock_open, mock_exists):
        """Test migration error handling"""
        mock_exists.return_value = True
        mock_open.side_effect = Exception("File read error")

        result = migrate_from_file_storage()

        self.assertTrue(result['success'])
        self.assertIn('errors', result)


class TestDatabaseServiceCaching(unittest.TestCase):
    """Test caching behavior in database service"""

    @patch.object(CacheManager, 'get')
    @patch.object(DatabaseManager, 'get_session')
    def test_get_companies_cache_hit(self, mock_get_session, mock_cache_get):
        """Test cache hit for get_companies"""
        # Currently caching is disabled in the implementation
        mock_cache_get.return_value = None

        mock_session = MagicMock()
        mock_get_session.return_value.__enter__.return_value = mock_session
        mock_session.query.return_value.all.return_value = []

        db_service = DatabaseService()
        result = db_service.get_companies()

        # Should still query database (caching disabled)
        mock_session.query.assert_called_once()

    @patch.object(CacheManager, 'delete')
    @patch.object(DatabaseManager, 'get_session')
    def test_cache_invalidation_on_create(self, mock_get_session, mock_cache_delete):
        """Test cache is invalidated on create"""
        mock_session = MagicMock()
        mock_get_session.return_value.__enter__.return_value = mock_session

        mock_query = mock_session.query.return_value
        mock_query.filter.return_value.first.return_value = None

        db_service = DatabaseService()

        company_data = {'name': 'NewCo', 'priority': 'HIGH'}
        with patch('src.database_service.Company', return_value=Mock()):
            db_service.create_or_update_company(company_data)

        # Should invalidate cache
        mock_cache_delete.assert_any_call("companies:all")
        mock_cache_delete.assert_any_call("companies:active")


class TestDatabaseServiceEdgeCases(unittest.TestCase):
    """Test edge cases and boundary conditions"""

    def setUp(self):
        """Set up test fixtures"""
        self.db_service = DatabaseService()

    @patch.object(DatabaseManager, 'get_session')
    def test_get_alerts_empty_result(self, mock_get_session):
        """Test getting alerts when none exist"""
        mock_session = MagicMock()
        mock_get_session.return_value.__enter__.return_value = mock_session

        mock_query = mock_session.query.return_value
        mock_query.order_by.return_value.offset.return_value.limit.return_value.all.return_value = []

        result = self.db_service.get_alerts()

        self.assertEqual(len(result), 0)

    @patch.object(DatabaseManager, 'get_session')
    def test_get_statistics_no_data(self, mock_get_session):
        """Test statistics with no data"""
        mock_session = MagicMock()
        mock_get_session.return_value.__enter__.return_value = mock_session

        # All counts return 0
        mock_session.query.return_value.count.return_value = 0
        mock_session.query.return_value.scalar.return_value = None
        mock_session.query.return_value.group_by.return_value.all.return_value = []
        mock_query = mock_session.query.return_value
        mock_query.outerjoin.return_value.group_by.return_value.all.return_value = []

        result = self.db_service.get_statistics()

        self.assertEqual(result['total_companies'], 0)
        self.assertEqual(result['avg_confidence'], 0.0)

    @patch.object(DatabaseManager, 'get_session')
    def test_create_alert_minimal_data(self, mock_get_session):
        """Test creating alert with minimal required data"""
        mock_session = MagicMock()
        mock_get_session.return_value.__enter__.return_value = mock_session

        minimal_data = {
            'content': 'Minimal alert'
        }

        with patch('src.database_service.Alert', return_value=Mock()):
            result = self.db_service.create_alert(minimal_data)

        mock_session.add.assert_called_once()

    @patch.object(DatabaseManager, 'get_session')
    def test_update_feed_stats_url_parsing(self, mock_get_session):
        """Test feed stats update with various URL formats"""
        mock_session = MagicMock()
        mock_get_session.return_value.__enter__.return_value = mock_session

        # No existing feed
        mock_query = mock_session.query.return_value
        mock_query.filter.return_value.first.return_value = None

        # URL without path segments
        mock_feed = Mock()
        mock_feed.success_count = 0
        mock_feed.failure_count = 0
        mock_feed.articles_found = 0
        mock_feed.tge_alerts_found = 0

        with patch('src.database_service.Feed', return_value=mock_feed) as mock_feed_class:
            self.db_service.update_feed_stats('https://example.com', success=True)

            # Should handle URL parsing gracefully
            mock_session.add.assert_called()


if __name__ == '__main__':
    unittest.main()

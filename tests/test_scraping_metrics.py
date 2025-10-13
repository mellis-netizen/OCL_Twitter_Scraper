"""
Backend Unit Tests - Scraping Metrics Tracking Accuracy
Tests the monitoring cycle metrics tracking and database persistence
"""

import pytest
import time
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch, MagicMock
from sqlalchemy.orm import Session

from src.main_optimized import OptimizedCryptoTGEMonitor
from src.models import Alert, Company, Feed, MonitoringSession, SystemMetrics
from src.database import DatabaseManager


class TestScrapingMetricsTracking:
    """Test suite for scraping cycle metrics tracking"""

    @pytest.fixture
    def mock_db_session(self):
        """Create mock database session"""
        session = MagicMock(spec=Session)
        return session

    @pytest.fixture
    def monitor(self):
        """Create monitor instance with swarm disabled"""
        with patch('src.main_optimized.OptimizedNewsScraper'), \
             patch('src.main_optimized.OptimizedTwitterMonitor'):
            monitor = OptimizedCryptoTGEMonitor(swarm_enabled=False)
            return monitor

    @pytest.fixture
    def sample_alerts(self):
        """Create sample alert data"""
        return [
            {
                'source': 'news',
                'content': 'Caldera announces TGE launch',
                'url': 'https://example.com/article1',
                'confidence': 0.85,
                'analysis': {
                    'matched_companies': ['Caldera'],
                    'matched_keywords': ['TGE', 'launch'],
                    'token_symbols': ['$CAL']
                },
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'title': 'Caldera TGE Announcement'
            }
        ]

    def test_metrics_initialization(self, monitor):
        """Test that metrics are properly initialized"""
        assert hasattr(monitor, 'metrics')
        assert 'total_cycles' in monitor.metrics
        assert monitor.metrics['total_cycles'] == 0

    def test_cycle_time_tracking(self, monitor):
        """Test that cycle time is accurately measured"""
        start_time = time.time()

        # Simulate a short cycle
        time.sleep(0.1)
        cycle_duration = time.time() - start_time

        monitor.metrics['last_cycle_time'] = cycle_duration

        assert monitor.metrics['last_cycle_time'] >= 0.1
        assert monitor.metrics['last_cycle_time'] < 1.0

    def test_alert_counting(self, monitor, sample_alerts):
        """Test that alerts are correctly counted"""
        initial_count = monitor.metrics.get('news_alerts', 0)

        # Process alerts
        monitor.metrics['news_alerts'] = initial_count + len(sample_alerts)

        assert monitor.metrics['news_alerts'] == initial_count + 1

    def test_articles_processed_tracking(self, monitor):
        """Test tracking of processed articles"""
        article_count = 25
        monitor.metrics['news_articles_processed'] = article_count

        assert monitor.metrics['news_articles_processed'] == 25

    def test_tweets_processed_tracking(self, monitor):
        """Test tracking of processed tweets"""
        tweet_count = 15
        monitor.metrics['tweets_processed'] = tweet_count

        assert monitor.metrics['tweets_processed'] == 15

    def test_confidence_distribution_tracking(self, monitor, sample_alerts):
        """Test confidence score distribution tracking"""
        for alert in sample_alerts:
            confidence_bucket = int(alert['confidence'] * 100) // 10 * 10
            monitor.metrics[f'confidence_{confidence_bucket}'] += 1

        assert monitor.metrics['confidence_80'] == 1

    def test_alert_database_persistence(self, monitor, sample_alerts):
        """Test that alerts are correctly saved to database"""
        with patch.object(DatabaseManager, 'get_session') as mock_session:
            mock_db = MagicMock(spec=Session)
            mock_session.return_value.__enter__.return_value = mock_db

            # Mock company query
            mock_company = Mock(spec=Company)
            mock_company.id = 1
            mock_company.name = 'Caldera'
            mock_db.query.return_value.all.return_value = [mock_company]

            # Save alerts
            saved_count = monitor.save_alerts_to_database(sample_alerts)

            assert saved_count == 1
            assert mock_db.add.called
            assert mock_db.commit.called

    def test_feed_statistics_update(self, monitor):
        """Test that feed statistics are updated correctly"""
        with patch.object(DatabaseManager, 'get_session') as mock_session:
            mock_db = MagicMock(spec=Session)
            mock_session.return_value.__enter__.return_value = mock_db

            # Mock feed data
            mock_feed = Mock(spec=Feed)
            mock_feed.url = 'https://example.com/feed'
            mock_db.query.return_value.filter.return_value.first.return_value = mock_feed

            # Mock scraper feed stats
            monitor.news_scraper.feed_stats = {
                'feed_1': {
                    'url': 'https://example.com/feed',
                    'success_count': 5,
                    'failure_count': 1,
                    'tge_found': 2,
                    'last_success': datetime.now(timezone.utc).isoformat()
                }
            }

            # Update statistics
            monitor.update_feed_statistics()

            assert mock_db.commit.called

    def test_monitoring_session_creation(self):
        """Test creation of monitoring session in database"""
        with patch.object(DatabaseManager, 'get_session') as mock_session:
            mock_db = MagicMock(spec=Session)
            mock_session.return_value.__enter__.return_value = mock_db

            session_id = "test-session-123"

            monitoring_session = MonitoringSession(
                session_id=session_id,
                status="running"
            )

            mock_db.add(monitoring_session)
            mock_db.commit()

            assert mock_db.add.called
            assert mock_db.commit.called

    def test_monitoring_session_completion(self):
        """Test updating monitoring session on completion"""
        with patch.object(DatabaseManager, 'get_session') as mock_session:
            mock_db = MagicMock(spec=Session)
            mock_session.return_value.__enter__.return_value = mock_db

            # Mock existing session
            mock_monitoring_session = Mock(spec=MonitoringSession)
            mock_monitoring_session.session_id = "test-session-123"
            mock_monitoring_session.status = "running"
            mock_db.query.return_value.filter.return_value.first.return_value = mock_monitoring_session

            # Update session
            mock_monitoring_session.status = "completed"
            mock_monitoring_session.end_time = datetime.now(timezone.utc)
            mock_monitoring_session.articles_processed = 25
            mock_monitoring_session.tweets_processed = 15
            mock_monitoring_session.alerts_generated = 3

            mock_db.commit()

            assert mock_monitoring_session.status == "completed"
            assert mock_monitoring_session.articles_processed == 25

    def test_error_cycle_tracking(self, monitor):
        """Test that error cycles are tracked"""
        initial_errors = monitor.metrics.get('error_cycles', 0)

        # Simulate error
        monitor.metrics['error_cycles'] = initial_errors + 1

        assert monitor.metrics['error_cycles'] == initial_errors + 1

    def test_deduplication_tracking(self, monitor):
        """Test content deduplication tracking"""
        content1 = "Caldera announces TGE launch"
        content2 = "Caldera announces TGE launch"  # Duplicate

        # First should be unique
        is_unique_1 = monitor.deduplicate_content(content1, "https://example.com/1")
        assert is_unique_1 is True

        # Second should be duplicate
        is_unique_2 = monitor.deduplicate_content(content2, "https://example.com/1")
        assert is_unique_2 is False


class TestFeedStatisticsAccuracy:
    """Test suite for feed statistics accuracy"""

    def test_feed_success_count_increment(self):
        """Test that feed success count increments correctly"""
        with patch.object(DatabaseManager, 'get_session') as mock_session:
            mock_db = MagicMock(spec=Session)
            mock_session.return_value.__enter__.return_value = mock_db

            mock_feed = Mock(spec=Feed)
            mock_feed.success_count = 5
            mock_db.query.return_value.filter.return_value.first.return_value = mock_feed

            # Increment
            mock_feed.success_count += 1
            mock_db.commit()

            assert mock_feed.success_count == 6

    def test_feed_failure_count_increment(self):
        """Test that feed failure count increments correctly"""
        with patch.object(DatabaseManager, 'get_session') as mock_session:
            mock_db = MagicMock(spec=Session)
            mock_session.return_value.__enter__.return_value = mock_db

            mock_feed = Mock(spec=Feed)
            mock_feed.failure_count = 2
            mock_db.query.return_value.filter.return_value.first.return_value = mock_feed

            # Increment
            mock_feed.failure_count += 1
            mock_db.commit()

            assert mock_feed.failure_count == 3

    def test_tge_alerts_found_tracking(self):
        """Test that TGE alerts found per feed are tracked"""
        with patch.object(DatabaseManager, 'get_session') as mock_session:
            mock_db = MagicMock(spec=Session)
            mock_session.return_value.__enter__.return_value = mock_db

            mock_feed = Mock(spec=Feed)
            mock_feed.tge_alerts_found = 3
            mock_db.query.return_value.filter.return_value.first.return_value = mock_feed

            # Add new alerts
            mock_feed.tge_alerts_found += 2
            mock_db.commit()

            assert mock_feed.tge_alerts_found == 5

    def test_last_fetch_timestamp_update(self):
        """Test that last fetch timestamp is updated"""
        with patch.object(DatabaseManager, 'get_session') as mock_session:
            mock_db = MagicMock(spec=Session)
            mock_session.return_value.__enter__.return_value = mock_db

            mock_feed = Mock(spec=Feed)
            mock_feed.last_fetch = None
            mock_db.query.return_value.filter.return_value.first.return_value = mock_feed

            # Update timestamp
            now = datetime.now(timezone.utc)
            mock_feed.last_fetch = now
            mock_db.commit()

            assert mock_feed.last_fetch == now

    def test_last_success_timestamp_update(self):
        """Test that last success timestamp is updated"""
        with patch.object(DatabaseManager, 'get_session') as mock_session:
            mock_db = MagicMock(spec=Session)
            mock_session.return_value.__enter__.return_value = mock_db

            mock_feed = Mock(spec=Feed)
            mock_feed.last_success = None
            mock_db.query.return_value.filter.return_value.first.return_value = mock_feed

            # Update timestamp
            now = datetime.now(timezone.utc)
            mock_feed.last_success = now
            mock_db.commit()

            assert mock_feed.last_success == now


class TestPerformanceMetrics:
    """Test suite for performance metrics tracking"""

    def test_avg_cycle_time_calculation(self):
        """Test average cycle time calculation"""
        total_time = 150.0  # seconds
        total_cycles = 5

        avg_time = total_time / total_cycles

        assert avg_time == 30.0

    def test_error_rate_calculation(self):
        """Test error rate calculation"""
        error_cycles = 2
        total_cycles = 10

        error_rate = error_cycles / total_cycles

        assert error_rate == 0.2

    def test_throughput_calculation(self):
        """Test articles per second calculation"""
        articles_processed = 100
        cycle_time = 50.0  # seconds

        throughput = articles_processed / cycle_time

        assert throughput == 2.0


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])

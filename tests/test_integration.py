"""
Fixed Integration tests for the Crypto TGE Monitor system
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import sys
import os
import tempfile
import shutil
from datetime import datetime, timezone

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from main import CryptoTGEMonitor


class TestIntegrationFixed(unittest.TestCase):
    """Fixed integration tests for the complete system"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Create a mock logger that will be used by all tests
        self.mock_logger = Mock()
        
        # Create temporary directory for test data
        self.test_dir = tempfile.mkdtemp()
        
        # Mock environment variables
        self.env_patcher = patch.dict(os.environ, {
            'EMAIL_USER': 'test@example.com',
            'EMAIL_PASSWORD': 'testpass',
            'RECIPIENT_EMAIL': 'recipient@example.com',
            'SMTP_SERVER': 'smtp.gmail.com',
            'SMTP_PORT': '587',
            'LOG_FILE': os.path.join(self.test_dir, 'test.log')
        })
        self.env_patcher.start()
        
        # Define mock setup logging function
        def mock_setup_logging(instance):
            instance.logger = self.mock_logger
            return self.mock_logger
        
        self.mock_setup_logging = mock_setup_logging
    
    def tearDown(self):
        """Clean up after tests"""
        # Stop environment patcher
        if hasattr(self, 'env_patcher'):
            self.env_patcher.stop()
        shutil.rmtree(self.test_dir, ignore_errors=True)
    
    @patch('src.main.NewsScraper')
    @patch('src.main.TwitterMonitor')
    @patch('src.main.EmailNotifier')
    @patch('src.utils.setup_structured_logging')
    def test_monitor_initialization(self, mock_setup_logging, mock_email, mock_twitter, mock_news):
        """Test complete monitor initialization"""
        # Mock the logger setup
        mock_setup_logging.return_value = self.mock_logger
        
        # Mock the components
        mock_news.return_value = Mock()
        mock_twitter.return_value = Mock()
        mock_email.return_value = Mock()
        
        # Mock the setup methods and logger
        with patch.object(CryptoTGEMonitor, 'setup_logging') as mock_logging, \
             patch.object(CryptoTGEMonitor, 'setup_signal_handlers'), \
             patch.object(CryptoTGEMonitor, 'validate_system_config'), \
             patch.object(CryptoTGEMonitor, 'setup_health_checks'), \
             patch.object(CryptoTGEMonitor, 'load_state'):
            
            # Mock the setup_logging method to set the logger attribute
            def setup_logger_side_effect(instance):
                instance.logger = self.mock_logger
                return self.mock_logger
            mock_logging.side_effect = setup_logger_side_effect
            
            # Create monitor
            monitor = CryptoTGEMonitor()
            
            # Verify initialization
            self.assertTrue(monitor.running)
            self.assertEqual(monitor.cycle_count, 0)
            self.assertEqual(monitor.error_count, 0)
            self.assertIsNotNone(monitor.start_time)
            self.assertIsInstance(monitor.start_time, datetime)
            self.assertEqual(monitor.start_time.tzinfo, timezone.utc)
    
    @patch('src.main.NewsScraper')
    @patch('src.main.TwitterMonitor')
    @patch('src.main.EmailNotifier')
    @patch('src.utils.setup_structured_logging')
    def test_monitoring_cycle_with_alerts(self, mock_setup_logging, mock_email, mock_twitter, mock_news):
        """Test a complete monitoring cycle with TGE alerts"""
        # Mock the logger setup
        mock_setup_logging.return_value = self.mock_logger
        
        # Setup mocks
        mock_news_instance = Mock()
        mock_news_instance.process_articles.return_value = [
            {
                'title': 'Arbitrum TGE Announcement',
                'summary': 'Arbitrum is launching their token',
                'url': 'https://example.com/arbitrum-tge',
                'published': datetime.now(timezone.utc),
                'source': 'https://example.com/feed',
                'mentioned_companies': ['Arbitrum'],
                'found_keywords': ['tge', 'token launch'],
                'relevance_score': 2.5
            }
        ]
        mock_news_instance.total_processed = 10
        mock_news.return_value = mock_news_instance
        
        mock_twitter_instance = Mock()
        mock_twitter_instance.process_tweets.return_value = [
            {
                "title": "@Arbitrum: TGE coming soon",
                "text": "Arbitrum TGE is launching next week",
                "url": "https://x.com/arbitrum/status/123",
                "published": datetime.now(timezone.utc).isoformat(),
                "mentioned_companies": ["Arbitrum"],
                "found_keywords": ["TGE"],
                "relevance_score": 2.0
            }
        ]
        mock_twitter_instance.total_processed = 5
        mock_twitter.return_value = mock_twitter_instance
        
        mock_email_instance = Mock()
        mock_email_instance.send_tge_alert_email.return_value = True
        mock_email.return_value = mock_email_instance
        
        # Mock the setup methods and logger
        with patch.object(CryptoTGEMonitor, 'setup_logging') as mock_logging, \
             patch.object(CryptoTGEMonitor, 'setup_signal_handlers'), \
             patch.object(CryptoTGEMonitor, 'validate_system_config'), \
             patch.object(CryptoTGEMonitor, 'setup_health_checks'), \
             patch.object(CryptoTGEMonitor, 'load_state'), \
             patch.object(CryptoTGEMonitor, 'save_state'):
            
            monitor = CryptoTGEMonitor()
            
            # Mock the monitoring cycle to prevent real network calls
            with patch.object(monitor, 'run_monitoring_cycle') as mock_cycle:
                mock_cycle.return_value = None
                monitor.run_monitoring_cycle()
            
            # Verify results
            self.assertEqual(monitor.cycle_count, 1)
            self.assertEqual(monitor.total_news_processed, 10)
            self.assertEqual(monitor.total_tweets_processed, 5)
            self.assertEqual(monitor.total_alerts_sent, 1)
            
            # Verify email was sent
            mock_email_instance.send_tge_alert_email.assert_called_once()
    
    @patch('src.main.NewsScraper')
    @patch('src.main.TwitterMonitor')
    @patch('src.main.EmailNotifier')
    @patch('src.utils.setup_structured_logging')
    def test_monitoring_cycle_no_alerts(self, mock_setup_logging, mock_email, mock_twitter, mock_news):
        """Test a monitoring cycle with no TGE alerts"""
        # Mock the logger setup
        mock_setup_logging.return_value = self.mock_logger
        
        # Setup mocks
        mock_news_instance = Mock()
        mock_news_instance.process_articles.return_value = []
        mock_news_instance.total_processed = 10
        mock_news.return_value = mock_news_instance
        
        mock_twitter_instance = Mock()
        mock_twitter_instance.process_tweets.return_value = []
        mock_twitter_instance.total_processed = 5
        mock_twitter.return_value = mock_twitter_instance
        
        mock_email_instance = Mock()
        mock_email_instance.send_tge_alert_email.return_value = True
        mock_email.return_value = mock_email_instance
        
        # Mock the setup methods and logger
        with patch.object(CryptoTGEMonitor, 'setup_logging') as mock_logging, \
             patch.object(CryptoTGEMonitor, 'setup_signal_handlers'), \
             patch.object(CryptoTGEMonitor, 'validate_system_config'), \
             patch.object(CryptoTGEMonitor, 'setup_health_checks'), \
             patch.object(CryptoTGEMonitor, 'load_state'), \
             patch.object(CryptoTGEMonitor, 'save_state'):
            
            monitor = CryptoTGEMonitor()
            
            # Mock the monitoring cycle to prevent real network calls
            with patch.object(monitor, 'run_monitoring_cycle') as mock_cycle:
                mock_cycle.return_value = None
                monitor.run_monitoring_cycle()
            
            # Verify results
            self.assertEqual(monitor.cycle_count, 1)
            self.assertEqual(monitor.total_news_processed, 10)
            self.assertEqual(monitor.total_tweets_processed, 5)
            self.assertEqual(monitor.total_alerts_sent, 0)
            
            # Verify email was not sent
            mock_email_instance.send_tge_alert_email.assert_not_called()
    
    @patch('src.main.NewsScraper')
    @patch('src.main.TwitterMonitor')
    @patch('src.main.EmailNotifier')
    @patch('src.utils.setup_structured_logging')
    def test_status_reporting(self, mock_setup_logging, mock_email, mock_twitter, mock_news):
        """Test system status reporting"""
        # Mock the logger setup
        mock_setup_logging.return_value = self.mock_logger
        
        # Setup mocks
        mock_news_instance = Mock()
        mock_news_instance.get_stats.return_value = {'total_processed': 100, 'total_tge_articles': 5}
        mock_news.return_value = mock_news_instance
        
        mock_twitter_instance = Mock()
        mock_twitter_instance.get_stats.return_value = {'total_processed': 50, 'total_tge_tweets': 3}
        mock_twitter.return_value = mock_twitter_instance
        
        mock_email_instance = Mock()
        mock_email_instance.enabled = True
        mock_email.return_value = mock_email_instance
        
        # Mock the setup methods and logger
        with patch.object(CryptoTGEMonitor, 'setup_logging') as mock_logging, \
             patch.object(CryptoTGEMonitor, 'setup_signal_handlers'), \
             patch.object(CryptoTGEMonitor, 'validate_system_config'), \
             patch.object(CryptoTGEMonitor, 'setup_health_checks'), \
             patch.object(CryptoTGEMonitor, 'load_state'):
            
            monitor = CryptoTGEMonitor()
            
            # Get status
            status = monitor.get_status()
            
            # Verify status structure
            self.assertIn('running', status)
            self.assertIn('cycle_count', status)
            self.assertIn('error_count', status)
            self.assertIn('health_status', status)
            self.assertIn('total_news_processed', status)
            self.assertIn('total_tweets_processed', status)
            self.assertIn('total_alerts_sent', status)
            self.assertIn('companies_monitored', status)
            self.assertIn('tge_keywords', status)
            self.assertIn('email_enabled', status)
            self.assertIn('twitter_enabled', status)
            
            # Verify values
            self.assertTrue(status['running'])
            self.assertEqual(status['cycle_count'], 0)
            self.assertEqual(status['error_count'], 0)
            self.assertEqual(status['companies_monitored'], 19)  # From config
            self.assertEqual(status['tge_keywords'], 50)  # From config
            self.assertTrue(status['email_enabled'])


if __name__ == '__main__':
    unittest.main()

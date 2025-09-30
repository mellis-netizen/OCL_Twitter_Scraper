"""
Unit tests for main.py module
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from main import CryptoTGEMonitor, matches_company_and_keyword, alert_key


class TestMainModule(unittest.TestCase):
    """Test cases for main module functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Mock environment variables
        self.env_patcher = patch.dict(os.environ, {
            'EMAIL_USER': 'test@example.com',
            'EMAIL_PASSWORD': 'testpass',
            'RECIPIENT_EMAIL': 'recipient@example.com',
            'SMTP_SERVER': 'smtp.gmail.com',
            'SMTP_PORT': '587'
        })
        self.env_patcher.start()
    
    def tearDown(self):
        """Clean up after tests"""
        self.env_patcher.stop()
    
    def test_matches_company_and_keyword_valid_alert(self):
        """Test that valid TGE alerts are detected"""
        alert = {
            "title": "Caldera announces TGE launch",
            "summary": "Caldera is launching their token generation event next week",
            "text": "",
            "content": ""
        }
        result = matches_company_and_keyword(alert)
        self.assertTrue(result[0])  # Check the boolean result
        self.assertGreater(result[1]['confidence_score'], 0)  # Check confidence score
    
    def test_matches_company_and_keyword_invalid_alert(self):
        """Test that non-TGE alerts are rejected"""
        alert = {
            "title": "Bitcoin price reaches new high",
            "summary": "Bitcoin has reached a new all-time high",
            "text": "",
            "content": ""
        }
        result = matches_company_and_keyword(alert)
        self.assertFalse(result[0])  # Check the boolean result
        self.assertEqual(result[1]['confidence_score'], 0)  # Check confidence score is 0
    
    def test_matches_company_and_keyword_malformed_alert(self):
        """Test that malformed alerts are handled gracefully"""
        # Test with non-dict input
        result = matches_company_and_keyword("not a dict")
        self.assertFalse(result[0])
        
        # Test with empty text
        alert = {"title": "", "summary": "", "text": "", "content": ""}
        result = matches_company_and_keyword(alert)
        self.assertFalse(result[0])
        
        # Test with suspicious content
        alert = {"title": "<script>alert('xss')</script>", "summary": "", "text": "", "content": ""}
        result = matches_company_and_keyword(alert)
        self.assertFalse(result[0])
    
    def test_alert_key_generation(self):
        """Test that alert keys are generated consistently"""
        alert1 = {
            "url": "https://example.com/article1",
            "title": "Test Article",
            "source": "example.com",
            "published": "2024-01-01"
        }
        alert2 = {
            "url": "https://example.com/article1",
            "title": "Test Article",
            "source": "example.com",
            "published": "2024-01-01"
        }
        
        key1 = alert_key(alert1)
        key2 = alert_key(alert2)
        
        self.assertEqual(key1, key2)
        self.assertIsInstance(key1, str)
        self.assertEqual(len(key1), 40)  # SHA-1 hash length
    
    def test_alert_key_without_url(self):
        """Test alert key generation when URL is missing"""
        alert = {
            "title": "Test Article",
            "source": "example.com",
            "published": "2024-01-01"
        }
        
        key = alert_key(alert)
        self.assertIsInstance(key, str)
        self.assertEqual(len(key), 40)
    
    @patch('src.main.NewsScraper')
    @patch('src.main.TwitterMonitor')
    @patch('src.main.EmailNotifier')
    def test_monitor_initialization(self, mock_email, mock_twitter, mock_news):
        """Test that monitor initializes correctly"""
        # Mock the components
        mock_news.return_value = Mock()
        mock_twitter.return_value = Mock()
        mock_email.return_value = Mock()
        
        # Mock the setup methods and logger
        mock_logger = Mock()
        
        def mock_setup_logging(self):
            self.logger = mock_logger
            return mock_logger
        
        with patch.object(CryptoTGEMonitor, 'setup_logging', mock_setup_logging), \
             patch.object(CryptoTGEMonitor, 'setup_signal_handlers'), \
             patch.object(CryptoTGEMonitor, 'validate_system_config'), \
             patch.object(CryptoTGEMonitor, 'setup_health_checks'), \
             patch.object(CryptoTGEMonitor, 'load_state'):
            
            monitor = CryptoTGEMonitor()
            
            self.assertTrue(monitor.running)
            self.assertEqual(monitor.cycle_count, 0)
            self.assertEqual(monitor.error_count, 0)
            self.assertIsNotNone(monitor.start_time)
    
    def test_strong_tge_keywords_detection(self):
        """Test that strong TGE keywords are detected without company match"""
        alert = {
            "title": "Token Generation Event announced",
            "summary": "A major TGE is happening next month",
            "text": "",
            "content": ""
        }
        self.assertTrue(matches_company_and_keyword(alert))
    
    def test_company_context_words_detection(self):
        """Test that company + context words are detected"""
        alert = {
            "title": "Caldera launch coming soon",
            "summary": "Caldera is preparing for their upcoming launch",
            "text": "",
            "content": ""
        }
        self.assertTrue(matches_company_and_keyword(alert))


if __name__ == '__main__':
    unittest.main()


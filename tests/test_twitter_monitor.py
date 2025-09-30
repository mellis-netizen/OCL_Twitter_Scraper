"""
Unit tests for twitter_monitor.py module
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from twitter_monitor import TwitterMonitor, _has_token, _matches_company_and_keyword


class TestTwitterMonitor(unittest.TestCase):
    """Test cases for Twitter monitor functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Mock environment variables
        self.env_patcher = patch.dict(os.environ, {
            'TWITTER_BEARER_TOKEN': '12345678901234567890123456789012345678901234567890'
        })
        self.env_patcher.start()
    
    def tearDown(self):
        """Clean up after tests"""
        self.env_patcher.stop()
    
    def test_has_token(self):
        """Test token matching functionality"""
        text = "Caldera is launching their token generation event"
        
        # Test exact match
        self.assertTrue(_has_token(text, "Caldera"))
        self.assertTrue(_has_token(text, "token generation event"))
        
        # Test case insensitive
        self.assertTrue(_has_token(text, "caldera"))
        self.assertTrue(_has_token(text, "TOKEN GENERATION EVENT"))
        
        # Test word boundary matching
        self.assertFalse(_has_token(text, "CalderaX"))  # Should not match
        self.assertFalse(_has_token(text, "XCaldera"))  # Should not match
        
        # Test empty/invalid tokens
        self.assertFalse(_has_token(text, ""))
        self.assertFalse(_has_token(text, "   "))
        self.assertFalse(_has_token("", "Caldera"))
    
    def test_matches_company_and_keyword(self):
        """Test company and keyword matching"""
        # Test valid match
        text = "Caldera is launching their token generation event"
        self.assertTrue(_matches_company_and_keyword(text))
        
        # Test company only (should not match)
        text = "Caldera is a great project"
        self.assertFalse(_matches_company_and_keyword(text))
        
        # Test keyword only (should not match)
        text = "Token generation event is happening"
        self.assertFalse(_matches_company_and_keyword(text))
        
        # Test empty text
        self.assertFalse(_matches_company_and_keyword(""))
        self.assertFalse(_matches_company_and_keyword(None))
    
    def test_bearer_token_validation(self):
        """Test bearer token validation"""
        monitor = TwitterMonitor()
        
        # Test valid token (without "Bearer " prefix)
        self.assertTrue(monitor._validate_bearer_token("12345678901234567890123456789012345678901234567890"))
        
        # Test invalid tokens
        self.assertFalse(monitor._validate_bearer_token(""))
        self.assertFalse(monitor._validate_bearer_token("short"))
        self.assertFalse(monitor._validate_bearer_token("your_bearer_token"))
        self.assertFalse(monitor._validate_bearer_token("placeholder"))
        self.assertFalse(monitor._validate_bearer_token(None))
    
    @patch.dict(os.environ, {'TWITTER_BEARER_TOKEN': ''})
    def test_monitor_initialization_no_token(self):
        """Test monitor initialization without bearer token"""
        monitor = TwitterMonitor()
        
        self.assertIsNone(monitor.client)
        self.assertIsNone(monitor.api)
        self.assertEqual(monitor.accounts, [])
        self.assertFalse(monitor.search_enabled)
    
    @patch.dict(os.environ, {'TWITTER_BEARER_TOKEN': '12345678901234567890123456789012345678901234567890'})
    def test_monitor_initialization_with_token(self):
        """Test monitor initialization with valid token"""
        with patch('twitter_monitor.tweepy.Client') as mock_client:
            monitor = TwitterMonitor()
            
            self.assertIsNotNone(monitor.client)
            self.assertIsNotNone(monitor.api)
            self.assertIsInstance(monitor.accounts, list)
    
    def test_get_stats(self):
        """Test statistics retrieval"""
        monitor = TwitterMonitor()
        stats = monitor.get_stats()
        
        self.assertIn("total_processed", stats)
        self.assertIn("total_tge_tweets", stats)
        self.assertIsInstance(stats["total_processed"], int)
        self.assertIsInstance(stats["total_tge_tweets"], int)
    
    def test_get_recent_tge_tweets_empty(self):
        """Test recent tweets retrieval when no tweets cached"""
        monitor = TwitterMonitor()
        recent = monitor.get_recent_tge_tweets(24)
        
        self.assertEqual(recent, [])
    
    def test_get_recent_tge_tweets_with_data(self):
        """Test recent tweets retrieval with cached data"""
        monitor = TwitterMonitor()
        
        # Add some mock tweets to cache
        from datetime import datetime, timezone, timedelta
        now = datetime.now(timezone.utc)
        
        monitor._recent_tweets = [
            {
                "published": (now - timedelta(hours=1)).isoformat(),
                "text": "Caldera TGE announcement"
            },
            {
                "published": (now - timedelta(hours=25)).isoformat(),
                "text": "Old tweet"
            }
        ]
        
        recent = monitor.get_recent_tge_tweets(24)
        
        # Should only return the recent tweet
        self.assertEqual(len(recent), 1)
        self.assertIn("Caldera TGE announcement", recent[0]["text"])


if __name__ == '__main__':
    unittest.main()


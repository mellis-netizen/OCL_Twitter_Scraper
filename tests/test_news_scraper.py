"""
Unit tests for news_scraper.py module
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import sys
import os
from datetime import datetime, timezone

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from news_scraper import NewsScraper, fetch_feed, to_aware_utc


class TestNewsScraper(unittest.TestCase):
    """Test cases for news scraper functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.scraper = NewsScraper()
    
    def test_to_aware_utc_with_timezone(self):
        """Test datetime conversion with timezone"""
        dt = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        result = to_aware_utc(dt)
        self.assertEqual(result, dt)
    
    def test_to_aware_utc_naive_datetime(self):
        """Test datetime conversion with naive datetime"""
        dt = datetime(2024, 1, 1, 12, 0, 0)
        result = to_aware_utc(dt)
        self.assertEqual(result.tzinfo, timezone.utc)
        self.assertEqual(result.replace(tzinfo=None), dt)
    
    def test_to_aware_utc_string(self):
        """Test datetime conversion with string input"""
        dt_str = "2024-01-01T12:00:00Z"
        result = to_aware_utc(dt_str)
        self.assertIsInstance(result, datetime)
        self.assertEqual(result.tzinfo, timezone.utc)
    
    def test_to_aware_utc_invalid_input(self):
        """Test datetime conversion with invalid input"""
        result = to_aware_utc(None)
        self.assertIsNone(result)
        
        result = to_aware_utc("invalid date")
        self.assertIsNone(result)
    
    @patch('news_scraper.get_session')
    def test_fetch_feed_success(self, mock_get_session):
        """Test successful feed fetching"""
        # Mock response
        mock_response = Mock()
        mock_response.content = b'<?xml version="1.0"?><rss><channel><item><title>Test</title></item></channel></rss>'
        mock_response.raise_for_status.return_value = None
        
        # Mock session
        mock_session = Mock()
        mock_session.get.return_value = mock_response
        mock_get_session.return_value = mock_session
        
        result = fetch_feed("https://example.com/feed")
        
        self.assertIsInstance(result, list)
        mock_session.get.assert_called_once()
    
    def test_fetch_feed_invalid_url(self):
        """Test feed fetching with invalid URL"""
        result = fetch_feed("")
        self.assertEqual(result, [])
        
        result = fetch_feed("not-a-url")
        self.assertEqual(result, [])
    
    def test_fetch_feed_url_too_long(self):
        """Test feed fetching with URL that's too long"""
        long_url = "https://example.com/" + "x" * 3000
        result = fetch_feed(long_url)
        self.assertEqual(result, [])
    
    def test_matches_company_and_keyword(self):
        """Test TGE matching logic"""
        # Test valid TGE alert
        alert = {
            "title": "Caldera TGE announcement",
            "summary": "Caldera is launching their token",
            "text": "",
            "content": ""
        }
        self.assertTrue(self.scraper._matches_company_and_keyword(alert))
        
        # Test invalid alert
        alert = {
            "title": "Bitcoin price news",
            "summary": "Bitcoin reaches new high",
            "text": "",
            "content": ""
        }
        self.assertFalse(self.scraper._matches_company_and_keyword(alert))
    
    def test_extract_mentioned_companies(self):
        """Test company extraction from text"""
        text = "Caldera and Fabric are launching tokens"
        companies = self.scraper._extract_mentioned_companies(text)
        self.assertIn("Caldera", companies)
        self.assertIn("Fabric", companies)
    
    def test_extract_found_keywords(self):
        """Test keyword extraction from text"""
        text = "token generation event and airdrop announced"
        keywords = self.scraper._extract_found_keywords(text)
        self.assertIn("token generation event", keywords)
        self.assertIn("airdrop", keywords)
    
    def test_get_stats(self):
        """Test statistics retrieval"""
        stats = self.scraper.get_stats()
        self.assertIn("total_processed", stats)
        self.assertIn("total_tge_articles", stats)
        self.assertIsInstance(stats["total_processed"], int)
        self.assertIsInstance(stats["total_tge_articles"], int)


if __name__ == '__main__':
    unittest.main()


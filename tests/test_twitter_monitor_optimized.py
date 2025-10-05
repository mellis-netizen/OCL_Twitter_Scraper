"""
Comprehensive unit tests for twitter_monitor_optimized.py module
Enhanced test coverage for rate limiting, batch operations, and advanced search strategies
"""

import unittest
from unittest.mock import Mock, patch, MagicMock, PropertyMock
import sys
import os
import json
import time
from datetime import datetime, timezone, timedelta
from concurrent.futures import TimeoutError as FuturesTimeoutError

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

try:
    from twitter_monitor_optimized import OptimizedTwitterMonitor
except ImportError:
    # Skip tests if optimized module not available
    import pytest
    pytest.skip("twitter_monitor_optimized module not available", allow_module_level=True)


class TestOptimizedTwitterMonitor(unittest.TestCase):
    """Comprehensive test cases for OptimizedTwitterMonitor functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.bearer_token = "test_bearer_token_1234567890123456789012345678901234567890"
        self.companies = [
            {
                "name": "Caldera",
                "aliases": ["Caldera Labs", "Caldera Protocol"],
                "tokens": ["CAL"],
                "priority": "HIGH"
            },
            {
                "name": "Fabric",
                "aliases": ["Fabric Protocol"],
                "tokens": ["FAB"],
                "priority": "MEDIUM"
            }
        ]
        self.keywords = ["TGE", "token generation event", "airdrop", "token launch"]
        
        # Mock file system operations
        self.file_patches = [
            patch('os.path.exists', return_value=False),
            patch('builtins.open', mock_open()),
            patch('os.makedirs'),
        ]
        for patcher in self.file_patches:
            patcher.start()
    
    def tearDown(self):
        """Clean up after tests"""
        for patcher in self.file_patches:
            patcher.stop()
    
    def mock_open(self, mock_content="{}"):
        """Helper to create mock file operations"""
        from unittest.mock import mock_open as base_mock_open
        return base_mock_open(read_data=mock_content)
    
    @patch('twitter_monitor_optimized.tweepy.Client')
    def test_initialization_success(self, mock_client):
        """Test successful monitor initialization"""
        with patch('builtins.open', self.mock_open()):
            monitor = OptimizedTwitterMonitor(
                self.bearer_token, self.companies, self.keywords
            )
        
        self.assertIsNotNone(monitor.client)
        self.assertEqual(monitor.companies, self.companies)
        self.assertEqual(monitor.keywords, self.keywords)
        mock_client.assert_called_once()
    
    @patch('twitter_monitor_optimized.tweepy.Client')
    def test_initialization_failure(self, mock_client):
        """Test monitor initialization with client failure"""
        mock_client.side_effect = Exception("API Error")
        
        with patch('builtins.open', self.mock_open()):
            monitor = OptimizedTwitterMonitor(
                self.bearer_token, self.companies, self.keywords
            )
        
        self.assertIsNone(monitor.client)
    
    def test_compile_company_patterns(self):
        """Test regex pattern compilation for companies"""
        with patch('builtins.open', self.mock_open()):
            monitor = OptimizedTwitterMonitor(
                self.bearer_token, self.companies, self.keywords
            )
        
        patterns = monitor._compile_company_patterns()
        self.assertIn("Caldera", patterns)
        self.assertIn("Fabric", patterns)
        
        # Test pattern matching
        caldera_pattern = patterns["Caldera"]
        self.assertTrue(caldera_pattern.search("Caldera is launching"))
        self.assertTrue(caldera_pattern.search("Check out Caldera Protocol"))
        self.assertFalse(caldera_pattern.search("Calderaish"))  # Should not match
    
    def test_token_pattern_matching(self):
        """Test token symbol pattern matching"""
        with patch('builtins.open', self.mock_open()):
            monitor = OptimizedTwitterMonitor(
                self.bearer_token, self.companies, self.keywords
            )
        
        # Test valid token matches
        text1 = "The $CAL token is launching soon"
        matches1 = monitor.token_pattern.findall(text1)
        self.assertIn("$CAL", matches1)
        
        text2 = "Excited for $FAB and $CAL tokens"
        matches2 = monitor.token_pattern.findall(text2)
        self.assertIn("$FAB", matches2)
        self.assertIn("$CAL", matches2)
        
        # Test invalid matches
        text3 = "No tokens here"
        matches3 = monitor.token_pattern.findall(text3)
        self.assertEqual(len(matches3), 0)
    
    def test_rate_limit_tracking(self):
        """Test rate limit tracking functionality"""
        with patch('builtins.open', self.mock_open()):
            monitor = OptimizedTwitterMonitor(
                self.bearer_token, self.companies, self.keywords
            )
        
        # Test rate limit recording
        endpoint = "tweets/search/recent"
        monitor._record_rate_limit(endpoint, 150, 100, int(time.time()) + 900)
        
        self.assertIn(endpoint, monitor.rate_limits)
        self.assertEqual(monitor.rate_limits[endpoint]['limit'], 150)
        self.assertEqual(monitor.rate_limits[endpoint]['remaining'], 100)
    
    def test_should_wait_for_rate_limit(self):
        """Test rate limit waiting logic"""
        with patch('builtins.open', self.mock_open()):
            monitor = OptimizedTwitterMonitor(
                self.bearer_token, self.companies, self.keywords
            )
        
        endpoint = "tweets/search/recent"
        
        # Test when rate limit is not exceeded
        monitor.rate_limits[endpoint] = {
            'remaining': 50,
            'reset_time': int(time.time()) + 900
        }
        self.assertFalse(monitor._should_wait_for_rate_limit(endpoint))
        
        # Test when rate limit is exceeded
        monitor.rate_limits[endpoint] = {
            'remaining': 0,
            'reset_time': int(time.time()) + 900
        }
        self.assertTrue(monitor._should_wait_for_rate_limit(endpoint))
        
        # Test when rate limit has reset
        monitor.rate_limits[endpoint] = {
            'remaining': 0,
            'reset_time': int(time.time()) - 100
        }
        self.assertFalse(monitor._should_wait_for_rate_limit(endpoint))
    
    @patch('twitter_monitor_optimized.tweepy.Client')
    def test_enhanced_content_analysis(self, mock_client):
        """Test enhanced content analysis functionality"""
        with patch('builtins.open', self.mock_open()):
            monitor = OptimizedTwitterMonitor(
                self.bearer_token, self.companies, self.keywords
            )
        
        # Test high-confidence content
        high_confidence_text = "Caldera is launching their TGE next week! $CAL token will be available"
        is_relevant, confidence, analysis = monitor.enhanced_content_analysis(high_confidence_text)
        
        self.assertTrue(is_relevant)
        self.assertGreater(confidence, 0.7)
        self.assertIn("Caldera", analysis['matched_companies'])
        self.assertIn("$CAL", analysis['token_symbols'])
        self.assertIn("TGE", analysis['matched_keywords'])
        
        # Test low-confidence content
        low_confidence_text = "Just another day in crypto"
        is_relevant, confidence, analysis = monitor.enhanced_content_analysis(low_confidence_text)
        
        self.assertFalse(is_relevant)
        self.assertLess(confidence, 0.4)
        
        # Test company without keywords
        company_only_text = "Fabric is a great protocol"
        is_relevant, confidence, analysis = monitor.enhanced_content_analysis(company_only_text)
        
        self.assertLess(confidence, 0.5)  # Should have lower confidence without TGE keywords
    
    @patch('twitter_monitor_optimized.tweepy.Client')
    def test_deduplication(self, mock_client):
        """Test content deduplication functionality"""
        with patch('builtins.open', self.mock_open()):
            monitor = OptimizedTwitterMonitor(
                self.bearer_token, self.companies, self.keywords
            )
        
        content = "Caldera TGE announcement"
        url = "https://twitter.com/caldera/status/123"
        
        # First time should be unique
        self.assertTrue(monitor.deduplicate_content(content, url))
        
        # Second time should be duplicate
        self.assertFalse(monitor.deduplicate_content(content, url))
        
        # Similar content should also be caught
        similar_content = "Caldera TGE announcement with minor changes"
        self.assertFalse(monitor.deduplicate_content(similar_content))
    
    @patch('twitter_monitor_optimized.tweepy.Client')
    def test_batch_search_queries(self, mock_client):
        """Test batch search query generation"""
        with patch('builtins.open', self.mock_open()):
            monitor = OptimizedTwitterMonitor(
                self.bearer_token, self.companies, self.keywords
            )
        
        queries = monitor._generate_batch_queries()
        
        # Should generate multiple queries
        self.assertGreater(len(queries), 0)
        
        # Each query should be within Twitter's character limit
        for query in queries:
            self.assertLessEqual(len(query), 512)
        
        # Should include company and keyword combinations
        query_text = " ".join(queries)
        self.assertIn("Caldera", query_text)
        self.assertIn("TGE", query_text)
    
    @patch('twitter_monitor_optimized.tweepy.Client')
    def test_parallel_processing(self, mock_client):
        """Test parallel tweet processing"""
        # Mock tweet data
        mock_tweets = [
            {
                'id': '123',
                'text': 'Caldera TGE announcement',
                'created_at': datetime.now(timezone.utc),
                'author_id': 'user1',
                'public_metrics': {'retweet_count': 10}
            },
            {
                'id': '124',
                'text': 'Another crypto update',
                'created_at': datetime.now(timezone.utc),
                'author_id': 'user2',
                'public_metrics': {'retweet_count': 5}
            }
        ]
        
        with patch('builtins.open', self.mock_open()):
            monitor = OptimizedTwitterMonitor(
                self.bearer_token, self.companies, self.keywords
            )
        
        # Test parallel processing
        processed_tweets = monitor._process_tweets_parallel(mock_tweets)
        
        self.assertIsInstance(processed_tweets, list)
        # Should process the TGE-related tweet
        tge_tweets = [t for t in processed_tweets if 'Caldera' in t.get('text', '')]
        self.assertGreater(len(tge_tweets), 0)
    
    @patch('twitter_monitor_optimized.tweepy.Client')
    def test_fetch_all_tweets_timeout(self, mock_client):
        """Test timeout handling in fetch_all_tweets"""
        # Configure mock client to cause timeout
        mock_client_instance = Mock()
        mock_client_instance.search_recent_tweets.side_effect = FuturesTimeoutError()
        mock_client.return_value = mock_client_instance
        
        with patch('builtins.open', self.mock_open()):
            monitor = OptimizedTwitterMonitor(
                self.bearer_token, self.companies, self.keywords
            )
            monitor.client = mock_client_instance
        
        # Should handle timeout gracefully
        tweets = monitor.fetch_all_tweets(timeout=1)
        self.assertEqual(tweets, [])
    
    @patch('twitter_monitor_optimized.tweepy.Client')
    def test_save_and_load_state(self, mock_client):
        """Test state persistence functionality"""
        test_state = {
            'seen_tweets': {'123': {'timestamp': '2024-01-01T00:00:00Z'}},
            'rate_limits': {'search': {'remaining': 100}},
            'stats': {'total_processed': 50}
        }
        
        with patch('builtins.open', self.mock_open(json.dumps(test_state))):
            monitor = OptimizedTwitterMonitor(
                self.bearer_token, self.companies, self.keywords
            )
        
        # Should load state correctly
        self.assertIn('seen_tweets', monitor.state)
        self.assertIn('rate_limits', monitor.state)
        self.assertIn('stats', monitor.state)
    
    def test_performance_metrics(self):
        """Test performance tracking functionality"""
        with patch('builtins.open', self.mock_open()):
            monitor = OptimizedTwitterMonitor(
                self.bearer_token, self.companies, self.keywords
            )
        
        # Test metrics initialization
        metrics = monitor.get_performance_metrics()
        self.assertIn('total_searches', metrics)
        self.assertIn('total_tweets_processed', metrics)
        self.assertIn('avg_processing_time', metrics)
        
        # Test metrics update
        monitor._update_metrics('search_completed', 1.5)
        updated_metrics = monitor.get_performance_metrics()
        self.assertGreater(updated_metrics['total_searches'], 0)
    
    @patch('twitter_monitor_optimized.tweepy.Client')
    def test_circuit_breaker(self, mock_client):
        """Test circuit breaker functionality for API failures"""
        # Configure mock to simulate repeated failures
        mock_client_instance = Mock()
        mock_client_instance.search_recent_tweets.side_effect = Exception("API Error")
        mock_client.return_value = mock_client_instance
        
        with patch('builtins.open', self.mock_open()):
            monitor = OptimizedTwitterMonitor(
                self.bearer_token, self.companies, self.keywords
            )
            monitor.client = mock_client_instance
        
        # Trigger multiple failures to activate circuit breaker
        for _ in range(5):
            tweets = monitor.fetch_all_tweets()
        
        # Circuit breaker should prevent further API calls
        self.assertTrue(monitor._is_circuit_breaker_open())
    
    def test_keyword_proximity_scoring(self):
        """Test proximity-based confidence scoring"""
        with patch('builtins.open', self.mock_open()):
            monitor = OptimizedTwitterMonitor(
                self.bearer_token, self.companies, self.keywords
            )
        
        # Test close proximity (should boost confidence)
        close_text = "Caldera TGE is happening next week"
        _, close_confidence, close_analysis = monitor.enhanced_content_analysis(close_text)
        
        # Test far proximity (should have lower boost)
        far_text = "Caldera is a great protocol. " + "x " * 100 + "TGE announcements are common"
        _, far_confidence, far_analysis = monitor.enhanced_content_analysis(far_text)
        
        # Close proximity should have higher confidence
        self.assertGreater(close_confidence, far_confidence)
        self.assertIn('proximity_boost', close_analysis['strategy'])


class TestOptimizedTwitterMonitorIntegration(unittest.TestCase):
    """Integration tests for OptimizedTwitterMonitor"""
    
    def setUp(self):
        """Set up integration test fixtures"""
        self.bearer_token = "test_bearer_token_1234567890123456789012345678901234567890"
        self.companies = [{"name": "TestCorp", "tokens": ["TEST"], "priority": "HIGH"}]
        self.keywords = ["TGE", "token launch"]
    
    @patch('twitter_monitor_optimized.tweepy.Client')
    def test_full_monitoring_cycle(self, mock_client):
        """Test complete monitoring cycle"""
        # Mock successful API responses
        mock_response = Mock()
        mock_response.data = [
            Mock(id='123', text='TestCorp TGE announcement', created_at=datetime.now(timezone.utc))
        ]
        mock_response.includes = {'users': [Mock(id='user1', username='testcorp')]}
        mock_response.meta = {'result_count': 1}
        
        mock_client_instance = Mock()
        mock_client_instance.search_recent_tweets.return_value = mock_response
        mock_client.return_value = mock_client_instance
        
        with patch('builtins.open', mock_open(read_data="{}")):
            with patch('os.path.exists', return_value=False):
                with patch('os.makedirs'):
                    monitor = OptimizedTwitterMonitor(
                        self.bearer_token, self.companies, self.keywords
                    )
                    monitor.client = mock_client_instance
                    
                    # Run monitoring cycle
                    tweets = monitor.fetch_all_tweets()
                    
                    # Should return processed tweets
                    self.assertIsInstance(tweets, list)


if __name__ == '__main__':
    # Set up test environment
    os.environ['TWITTER_BEARER_TOKEN'] = 'test_token'
    
    unittest.main()
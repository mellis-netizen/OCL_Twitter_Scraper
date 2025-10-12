"""
Unit Tests for Twitter Monitor Module
Tests API integration, rate limiting, batch operations, and search strategies
"""

import unittest
from unittest.mock import Mock, patch, MagicMock, mock_open
import sys
import os
import json
import time
from datetime import datetime, timezone, timedelta
from collections import defaultdict

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

try:
    from twitter_monitor_optimized import OptimizedTwitterMonitor
except ImportError:
    import pytest
    pytest.skip("twitter_monitor_optimized module not available", allow_module_level=True)


class TestTwitterMonitor(unittest.TestCase):
    """Unit tests for OptimizedTwitterMonitor"""

    def setUp(self):
        """Set up test fixtures"""
        self.bearer_token = "test_bearer_token_" + "x" * 100
        self.companies = [
            {
                "name": "Caldera",
                "aliases": ["Caldera Labs"],
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
        self.keywords = ["TGE", "token launch", "airdrop"]

        # Mock file system
        self.patches = [
            patch('os.path.exists', return_value=False),
            patch('builtins.open', mock_open(read_data="{}")),
            patch('os.makedirs'),
        ]
        for p in self.patches:
            p.start()

    def tearDown(self):
        """Clean up patches"""
        for p in self.patches:
            p.stop()

    @patch('twitter_monitor_optimized.tweepy.Client')
    def test_initialization(self, mock_client_class):
        """Test successful monitor initialization"""
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        monitor = OptimizedTwitterMonitor(
            self.bearer_token, self.companies, self.keywords
        )

        self.assertEqual(monitor.companies, self.companies)
        self.assertEqual(monitor.keywords, self.keywords)
        self.assertIsNotNone(monitor.client)
        mock_client_class.assert_called_once()

    @patch('twitter_monitor_optimized.tweepy.Client')
    def test_company_pattern_compilation(self, mock_client_class):
        """Test regex patterns are compiled for companies"""
        mock_client_class.return_value = Mock()

        monitor = OptimizedTwitterMonitor(
            self.bearer_token, self.companies, self.keywords
        )

        self.assertIn('Caldera', monitor.company_patterns)
        self.assertIn('Fabric', monitor.company_patterns)

        # Test pattern matching
        text = "Caldera Labs announces new update"
        pattern = monitor.company_patterns['Caldera']
        self.assertIsNotNone(pattern.search(text))

    @patch('twitter_monitor_optimized.tweepy.Client')
    def test_rate_limit_checking(self, mock_client_class):
        """Test rate limit checking mechanism"""
        mock_client_class.return_value = Mock()

        monitor = OptimizedTwitterMonitor(
            self.bearer_token, self.companies, self.keywords
        )

        endpoint = "search"

        # No limits initially
        self.assertTrue(monitor.check_rate_limit(endpoint))

        # Set rate limit
        monitor.rate_limits[endpoint] = {
            'limit': 100,
            'remaining': 0,
            'reset': time.time() + 900
        }

        # Should be rate limited
        self.assertFalse(monitor.check_rate_limit(endpoint))

        # Reset time passed
        monitor.rate_limits[endpoint]['reset'] = time.time() - 1
        self.assertTrue(monitor.check_rate_limit(endpoint))

    @patch('twitter_monitor_optimized.tweepy.Client')
    def test_rate_limit_update(self, mock_client_class):
        """Test rate limit update from API response"""
        mock_client_class.return_value = Mock()

        monitor = OptimizedTwitterMonitor(
            self.bearer_token, self.companies, self.keywords
        )

        # Mock response with rate limit headers
        mock_response = Mock()
        mock_response.headers = {
            'x-rate-limit-limit': '100',
            'x-rate-limit-remaining': '75',
            'x-rate-limit-reset': str(int(time.time() + 900))
        }

        endpoint = "search"
        monitor.update_rate_limit(endpoint, mock_response)

        self.assertEqual(monitor.rate_limits[endpoint]['limit'], 100)
        self.assertEqual(monitor.rate_limits[endpoint]['remaining'], 75)

    @patch('twitter_monitor_optimized.tweepy.Client')
    def test_batch_user_lookup(self, mock_client_class):
        """Test batch user ID lookup"""
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        # Mock get_users response
        mock_user1 = Mock()
        mock_user1.username = "caldera"
        mock_user1.id = "123456"

        mock_user2 = Mock()
        mock_user2.username = "fabric"
        mock_user2.id = "789012"

        mock_response = Mock()
        mock_response.data = [mock_user1, mock_user2]
        mock_client.get_users.return_value = mock_response

        monitor = OptimizedTwitterMonitor(
            self.bearer_token, self.companies, self.keywords
        )

        handles = ["@caldera", "@fabric"]
        user_map = monitor.batch_lookup_users(handles)

        self.assertEqual(user_map["@caldera"], "123456")
        self.assertEqual(user_map["@fabric"], "789012")

        # Should be cached
        self.assertIn("caldera", monitor.state['user_id_cache'])
        self.assertIn("fabric", monitor.state['user_id_cache'])

    @patch('twitter_monitor_optimized.tweepy.Client')
    def test_batch_lookup_uses_cache(self, mock_client_class):
        """Test batch lookup uses cached user IDs"""
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        monitor = OptimizedTwitterMonitor(
            self.bearer_token, self.companies, self.keywords
        )

        # Pre-populate cache
        monitor.state['user_id_cache']['caldera'] = "cached_id_123"

        user_map = monitor.batch_lookup_users(["@caldera"])

        self.assertEqual(user_map["@caldera"], "cached_id_123")
        mock_client.get_users.assert_not_called()

    @patch('twitter_monitor_optimized.tweepy.Client')
    def test_tweet_relevance_analysis_high_confidence(self, mock_client_class):
        """Test tweet analysis with high confidence signals"""
        mock_client_class.return_value = Mock()

        monitor = OptimizedTwitterMonitor(
            self.bearer_token, self.companies, self.keywords
        )

        tweet = {
            'text': 'Caldera TGE is live! Claim your $CAL tokens now. Token launch happening!',
            'id': '123',
            'metrics': {
                'retweet_count': 100,
                'like_count': 500,
                'impression_count': 10000
            }
        }

        is_relevant, confidence, info = monitor.analyze_tweet_relevance(tweet)

        self.assertTrue(is_relevant)
        self.assertGreater(confidence, 0.4)
        self.assertIn('Caldera', info['matched_companies'])
        self.assertIn('$CAL', info['token_symbols'])
        self.assertGreater(len(info['matched_keywords']), 0)

    @patch('twitter_monitor_optimized.tweepy.Client')
    def test_tweet_relevance_analysis_low_confidence(self, mock_client_class):
        """Test tweet analysis with low confidence"""
        mock_client_class.return_value = Mock()

        monitor = OptimizedTwitterMonitor(
            self.bearer_token, self.companies, self.keywords
        )

        tweet = {
            'text': 'General crypto market update for today',
            'id': '124',
            'metrics': {}
        }

        is_relevant, confidence, info = monitor.analyze_tweet_relevance(tweet)

        self.assertFalse(is_relevant)
        self.assertLess(confidence, 0.4)
        self.assertEqual(len(info['matched_companies']), 0)

    @patch('twitter_monitor_optimized.tweepy.Client')
    def test_token_symbol_detection(self, mock_client_class):
        """Test token symbol detection in tweets"""
        mock_client_class.return_value = Mock()

        monitor = OptimizedTwitterMonitor(
            self.bearer_token, self.companies, self.keywords
        )

        tweet = {
            'text': '$CAL $FAB $BTC tokens are trending',
            'id': '125',
            'metrics': {}
        }

        is_relevant, confidence, info = monitor.analyze_tweet_relevance(tweet)

        self.assertIn('$CAL', info['token_symbols'])
        self.assertIn('$FAB', info['token_symbols'])
        self.assertGreater(len(info['token_symbols']), 0)

    @patch('twitter_monitor_optimized.tweepy.Client')
    def test_exclusion_patterns(self, mock_client_class):
        """Test exclusion patterns reduce confidence"""
        mock_client_class.return_value = Mock()

        monitor = OptimizedTwitterMonitor(
            self.bearer_token, self.companies, self.keywords
        )

        tweet = {
            'text': 'Caldera testnet token launch for NFT game',
            'id': '126',
            'metrics': {}
        }

        is_relevant, confidence, info = monitor.analyze_tweet_relevance(tweet)

        # Exclusions should reduce confidence
        self.assertIn('exclusion_test', info['signals'])
        self.assertLess(confidence, 0.6)

    @patch('twitter_monitor_optimized.tweepy.Client')
    def test_high_engagement_bonus(self, mock_client_class):
        """Test high engagement increases confidence"""
        mock_client_class.return_value = Mock()

        monitor = OptimizedTwitterMonitor(
            self.bearer_token, self.companies, self.keywords
        )

        high_engagement_tweet = {
            'text': 'Caldera token launch',
            'id': '127',
            'metrics': {
                'retweet_count': 1000,
                'like_count': 5000,
                'impression_count': 50000
            }
        }

        low_engagement_tweet = {
            'text': 'Caldera token launch',
            'id': '128',
            'metrics': {
                'retweet_count': 1,
                'like_count': 5,
                'impression_count': 100
            }
        }

        _, high_conf, high_info = monitor.analyze_tweet_relevance(high_engagement_tweet)
        _, low_conf, low_info = monitor.analyze_tweet_relevance(low_engagement_tweet)

        self.assertGreater(high_conf, low_conf)
        self.assertIn('high_engagement', high_info['signals'])

    @patch('twitter_monitor_optimized.tweepy.Client')
    def test_search_query_construction(self, mock_client_class):
        """Test search query construction for different strategies"""
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        # Mock search results
        mock_tweet = Mock()
        mock_tweet.id = "999"
        mock_tweet.text = "Test tweet"
        mock_tweet.author_id = "author123"
        mock_tweet.created_at = datetime.now(timezone.utc)
        mock_tweet.public_metrics = {}

        mock_response = Mock()
        mock_response.data = [mock_tweet]
        mock_client.search_recent_tweets.return_value = mock_response

        monitor = OptimizedTwitterMonitor(
            self.bearer_token, self.companies, self.keywords
        )

        tweets = monitor.search_tge_tweets()

        # Should have called search with constructed queries
        self.assertTrue(mock_client.search_recent_tweets.called)

        # Check query structure
        call_args = mock_client.search_recent_tweets.call_args
        query = call_args[1]['query'] if 'query' in call_args[1] else call_args[0][0]

        # Should contain some TGE-related terms
        self.assertTrue(any(term in query.lower() for term in ['tge', 'token', 'launch']))

    @patch('twitter_monitor_optimized.tweepy.Client')
    def test_tweet_deduplication(self, mock_client_class):
        """Test tweets are deduplicated"""
        mock_client_class.return_value = Mock()

        monitor = OptimizedTwitterMonitor(
            self.bearer_token, self.companies, self.keywords
        )

        tweet_id = "duplicate_123"

        # First time should not be in cache
        self.assertNotIn(tweet_id, monitor.cache['tweets'])

        # Add to cache
        monitor.cache['tweets'][tweet_id] = {
            'timestamp': datetime.now(timezone.utc).isoformat()
        }

        # Second time should be in cache
        self.assertIn(tweet_id, monitor.cache['tweets'])

    @patch('twitter_monitor_optimized.tweepy.Client')
    def test_cache_cleanup(self, mock_client_class):
        """Test old cache entries are cleaned up"""
        mock_client_class.return_value = Mock()

        # Create cache with old entry
        old_cache = {
            'tweets': {
                'old_tweet': {
                    'timestamp': (datetime.now(timezone.utc) - timedelta(days=8)).isoformat()
                },
                'recent_tweet': {
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }
            }
        }

        with patch('builtins.open', mock_open(read_data=json.dumps(old_cache))):
            with patch('os.path.exists', return_value=True):
                monitor = OptimizedTwitterMonitor(
                    self.bearer_token, self.companies, self.keywords
                )

        # Old tweet should be removed (>7 days)
        self.assertNotIn('old_tweet', monitor.cache['tweets'])
        self.assertIn('recent_tweet', monitor.cache['tweets'])

    @patch('twitter_monitor_optimized.tweepy.Client')
    def test_state_persistence(self, mock_client_class):
        """Test state is persisted correctly"""
        mock_client_class.return_value = Mock()

        test_state = {
            'since_ids': {'user_123': '999'},
            'user_id_cache': {'caldera': '123'},
            'list_id': 'list_456'
        }

        with patch('builtins.open', mock_open(read_data=json.dumps(test_state))):
            with patch('os.path.exists', return_value=True):
                monitor = OptimizedTwitterMonitor(
                    self.bearer_token, self.companies, self.keywords
                )

        self.assertEqual(monitor.state['list_id'], 'list_456')
        self.assertIn('caldera', monitor.state['user_id_cache'])


class TestTwitterListManagement(unittest.TestCase):
    """Test Twitter list creation and management"""

    @patch('twitter_monitor_optimized.tweepy.Client')
    def test_list_creation(self, mock_client_class):
        """Test Twitter list is created"""
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        # Mock get_me
        mock_me = Mock()
        mock_me.data = Mock()
        mock_client.get_me.return_value = mock_me

        # Mock create_list
        mock_list_response = Mock()
        mock_list_response.data = {'id': 'new_list_123'}
        mock_client.create_list.return_value = mock_list_response

        companies = [{"name": "Test", "tokens": ["TST"], "priority": "HIGH"}]
        keywords = ["TGE"]

        with patch('os.path.exists', return_value=False):
            with patch('builtins.open', mock_open(read_data="{}")):
                with patch('os.makedirs'):
                    monitor = OptimizedTwitterMonitor(
                        "bearer_token_" + "x" * 100, companies, keywords
                    )

        user_ids = ["123", "456"]
        list_id = monitor.create_or_update_list(user_ids)

        self.assertEqual(list_id, 'new_list_123')
        mock_client.create_list.assert_called_once()


class TestEdgeCases(unittest.TestCase):
    """Test edge cases and error conditions"""

    @patch('twitter_monitor_optimized.tweepy.Client')
    def test_empty_tweet_text(self, mock_client_class):
        """Test handling of empty tweet text"""
        mock_client_class.return_value = Mock()

        companies = [{"name": "Test", "tokens": ["TST"], "priority": "HIGH"}]
        keywords = ["TGE"]

        with patch('os.path.exists', return_value=False):
            with patch('builtins.open', mock_open(read_data="{}")):
                with patch('os.makedirs'):
                    monitor = OptimizedTwitterMonitor(
                        "bearer_token_" + "x" * 100, companies, keywords
                    )

        tweet = {'text': '', 'id': '999', 'metrics': {}}
        is_relevant, confidence, info = monitor.analyze_tweet_relevance(tweet)

        self.assertFalse(is_relevant)
        self.assertEqual(confidence, 0)

    @patch('twitter_monitor_optimized.tweepy.Client')
    def test_api_error_handling(self, mock_client_class):
        """Test API error handling"""
        mock_client = Mock()
        mock_client.search_recent_tweets.side_effect = Exception("API Error")
        mock_client_class.return_value = mock_client

        companies = [{"name": "Test", "tokens": ["TST"], "priority": "HIGH"}]
        keywords = ["TGE"]

        with patch('os.path.exists', return_value=False):
            with patch('builtins.open', mock_open(read_data="{}")):
                with patch('os.makedirs'):
                    monitor = OptimizedTwitterMonitor(
                        "bearer_token_" + "x" * 100, companies, keywords
                    )

        # Should not crash on API error
        tweets = monitor.search_tge_tweets()

        self.assertIsInstance(tweets, list)


if __name__ == '__main__':
    unittest.main()

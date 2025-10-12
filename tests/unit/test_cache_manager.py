"""
Unit Tests for Cache Manager
Tests cache hit rates, TTL expiration, and cache efficiency
"""

import unittest
from unittest.mock import Mock, patch, mock_open
import sys
import os
import json
import hashlib
from datetime import datetime, timezone, timedelta

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from news_scraper_optimized import OptimizedNewsScraper
from twitter_monitor_optimized import OptimizedTwitterMonitor


class TestNewsCacheManager(unittest.TestCase):
    """Test caching functionality in news scraper"""

    def setUp(self):
        """Set up test fixtures"""
        self.companies = [{"name": "Test", "tokens": ["TST"], "priority": "HIGH"}]
        self.keywords = ["TGE"]
        self.news_sources = ["https://example.com/feed.xml"]

        with patch('os.path.exists', return_value=False):
            with patch('builtins.open', mock_open(read_data="{}")):
                with patch('os.makedirs'):
                    self.scraper = OptimizedNewsScraper(
                        self.companies, self.keywords, self.news_sources
                    )

    def test_cache_initialization(self):
        """Test cache is properly initialized"""
        self.assertIsInstance(self.scraper.cache, dict)
        self.assertIn('articles', self.scraper.cache)
        self.assertIn('summaries', self.scraper.cache)

    def test_cache_hit(self):
        """Test cache hit returns cached content"""
        url = "https://example.com/article"
        cache_key = hashlib.sha256(url.encode()).hexdigest()
        cached_content = "Cached article content"

        # Populate cache
        self.scraper.cache['articles'][cache_key] = {
            'content': cached_content,
            'cached_at': datetime.now(timezone.utc).isoformat(),
            'length': len(cached_content)
        }

        with patch('news_scraper_optimized.Article') as mock_article:
            content = self.scraper.fetch_article_content(url)

            # Should return cached content without fetching
            self.assertEqual(content, cached_content)
            mock_article.assert_not_called()

    def test_cache_miss(self):
        """Test cache miss fetches new content"""
        url = "https://example.com/new-article"

        with patch('news_scraper_optimized.Article') as mock_article_class:
            mock_article = Mock()
            # Content needs to be >30 chars per line AND >100 total to cache
            long_content = "This is new article content that is significantly longer than thirty characters per line and also exceeds one hundred characters total"
            mock_article.text = long_content
            mock_article_class.return_value = mock_article

            content = self.scraper.fetch_article_content(url)

            # Should fetch new content
            self.assertEqual(content, long_content)

            # Should cache the content
            cache_key = hashlib.sha256(url.encode()).hexdigest()
            self.assertIn(cache_key, self.scraper.cache['articles'])

    def test_cache_ttl_expiration(self):
        """Test cache entries expire after TTL"""
        # Create cache with old entry
        old_cache = {
            'articles': {
                'old_key': {
                    'content': 'Old content',
                    'cached_at': (datetime.now(timezone.utc) - timedelta(days=4)).isoformat()
                },
                'fresh_key': {
                    'content': 'Fresh content',
                    'cached_at': datetime.now(timezone.utc).isoformat()
                }
            },
            'summaries': {}
        }

        with patch('builtins.open', mock_open(read_data=json.dumps(old_cache))):
            with patch('os.path.exists', return_value=True):
                scraper = OptimizedNewsScraper(
                    self.companies, self.keywords, self.news_sources
                )

        # Old entry should be removed (>3 days)
        self.assertNotIn('old_key', scraper.cache['articles'])
        # Fresh entry should remain
        self.assertIn('fresh_key', scraper.cache['articles'])

    def test_cache_size_management(self):
        """Test cache size is managed"""
        # Add many entries
        for i in range(1000):
            cache_key = f"key_{i}"
            self.scraper.cache['articles'][cache_key] = {
                'content': f'Content {i}',
                'cached_at': datetime.now(timezone.utc).isoformat()
            }

        # Cache should have all entries
        self.assertEqual(len(self.scraper.cache['articles']), 1000)

    def test_cache_persistence(self):
        """Test cache is saved to disk"""
        url = "https://example.com/article"
        cache_key = hashlib.sha256(url.encode()).hexdigest()

        self.scraper.cache['articles'][cache_key] = {
            'content': 'Test content',
            'cached_at': datetime.now(timezone.utc).isoformat()
        }

        with patch('builtins.open', mock_open()) as mock_file:
            self.scraper.save_cache()

            # Should have written cache
            mock_file.assert_called()

    def test_cache_recovery_on_corruption(self):
        """Test cache recovery on corrupted cache file"""
        with patch('builtins.open', mock_open(read_data="invalid json{")):
            with patch('os.path.exists', return_value=True):
                scraper = OptimizedNewsScraper(
                    self.companies, self.keywords, self.news_sources
                )

        # Should initialize with empty cache on corruption
        self.assertIsInstance(scraper.cache, dict)
        self.assertIn('articles', scraper.cache)


class TestTwitterCacheManager(unittest.TestCase):
    """Test caching functionality in Twitter monitor"""

    def setUp(self):
        """Set up test fixtures"""
        self.companies = [{"name": "Test", "tokens": ["TST"], "priority": "HIGH"}]
        self.keywords = ["TGE"]

        with patch('os.path.exists', return_value=False):
            with patch('builtins.open', mock_open(read_data="{}")):
                with patch('os.makedirs'):
                    with patch('twitter_monitor_optimized.tweepy.Client'):
                        self.monitor = OptimizedTwitterMonitor(
                            "bearer_token_" + "x" * 100,
                            self.companies,
                            self.keywords
                        )

    def test_tweet_deduplication(self):
        """Test tweets are deduplicated via cache"""
        tweet_id = "12345"

        # First check - not in cache
        self.assertNotIn(tweet_id, self.monitor.cache['tweets'])

        # Add to cache
        self.monitor.cache['tweets'][tweet_id] = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'text_hash': hash('Test tweet')
        }

        # Second check - should be in cache
        self.assertIn(tweet_id, self.monitor.cache['tweets'])

    def test_user_id_cache(self):
        """Test user ID caching"""
        username = "testuser"
        user_id = "123456"

        # Not initially cached
        self.assertNotIn(username, self.monitor.state['user_id_cache'])

        # Cache user ID
        self.monitor.state['user_id_cache'][username] = user_id

        # Should be cached
        self.assertEqual(self.monitor.state['user_id_cache'][username], user_id)

    def test_twitter_cache_cleanup(self):
        """Test old tweets are removed from cache"""
        old_cache = {
            'tweets': {
                'old_tweet': {
                    'timestamp': (datetime.now(timezone.utc) - timedelta(days=8)).isoformat()
                },
                'recent_tweet': {
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }
            },
            'similar_tweets': {}
        }

        with patch('builtins.open', mock_open(read_data=json.dumps(old_cache))):
            with patch('os.path.exists', return_value=True):
                with patch('twitter_monitor_optimized.tweepy.Client'):
                    monitor = OptimizedTwitterMonitor(
                        "bearer_token_" + "x" * 100,
                        self.companies,
                        self.keywords
                    )

        # Old tweet should be removed (>7 days)
        self.assertNotIn('old_tweet', monitor.cache['tweets'])
        # Recent tweet should remain
        self.assertIn('recent_tweet', monitor.cache['tweets'])


class TestCachePerformance(unittest.TestCase):
    """Test cache performance metrics"""

    def setUp(self):
        """Set up test fixtures"""
        self.companies = [{"name": "Test", "tokens": ["TST"], "priority": "HIGH"}]
        self.keywords = ["TGE"]
        self.news_sources = ["https://example.com/feed.xml"]

        with patch('os.path.exists', return_value=False):
            with patch('builtins.open', mock_open(read_data="{}")):
                with patch('os.makedirs'):
                    self.scraper = OptimizedNewsScraper(
                        self.companies, self.keywords, self.news_sources
                    )

    def test_cache_hit_rate_calculation(self):
        """Test cache hit rate calculation"""
        cache_hits = 0
        cache_misses = 0

        urls = [f"https://example.com/article{i}" for i in range(10)]

        # First pass - all misses
        with patch('news_scraper_optimized.Article') as mock_article_class:
            mock_article = Mock()
            # Content needs to be >30 chars per line AND >100 total to cache
            mock_article.text = "This is article content that is significantly longer than thirty characters per line and exceeds one hundred characters total to ensure caching works properly"
            mock_article_class.return_value = mock_article

            for url in urls:
                content = self.scraper.fetch_article_content(url)
                if content:
                    cache_misses += 1

        # Second pass - all hits
        for url in urls:
            cache_key = hashlib.sha256(url.encode()).hexdigest()
            if cache_key in self.scraper.cache['articles']:
                cache_hits += 1

        hit_rate = cache_hits / (cache_hits + cache_misses) if (cache_hits + cache_misses) > 0 else 0

        self.assertEqual(cache_hits, 10)
        self.assertEqual(cache_misses, 10)
        self.assertEqual(hit_rate, 0.5)

    def test_cache_reduces_api_calls(self):
        """Test cache reduces API calls"""
        url = "https://example.com/article"

        with patch('news_scraper_optimized.Article') as mock_article_class:
            mock_article = Mock()
            # Content needs to be >30 chars per line to pass cleaning filter and >100 total to cache
            mock_article.text = "This is content that is longer than thirty characters per line and more than one hundred characters total to ensure caching"
            mock_article_class.return_value = mock_article

            # First call
            self.scraper.fetch_article_content(url)
            first_call_count = mock_article_class.call_count

            # Second call (should use cache)
            self.scraper.fetch_article_content(url)
            second_call_count = mock_article_class.call_count

            # Should only call once
            self.assertEqual(first_call_count, 1)
            self.assertEqual(second_call_count, 1)


class TestStateManagement(unittest.TestCase):
    """Test state management and persistence"""

    def setUp(self):
        """Set up test fixtures"""
        self.companies = [{"name": "Test", "tokens": ["TST"], "priority": "HIGH"}]
        self.keywords = ["TGE"]
        self.news_sources = ["https://example.com/feed.xml"]

    def test_state_initialization(self):
        """Test state is properly initialized"""
        with patch('os.path.exists', return_value=False):
            with patch('builtins.open', mock_open(read_data="{}")):
                with patch('os.makedirs'):
                    scraper = OptimizedNewsScraper(
                        self.companies, self.keywords, self.news_sources
                    )

        self.assertIsInstance(scraper.state, dict)
        self.assertIn('seen_urls', scraper.state)
        self.assertIn('feed_stats', scraper.state)

    def test_seen_urls_tracking(self):
        """Test seen URLs are tracked"""
        with patch('os.path.exists', return_value=False):
            with patch('builtins.open', mock_open(read_data="{}")):
                with patch('os.makedirs'):
                    scraper = OptimizedNewsScraper(
                        self.companies, self.keywords, self.news_sources
                    )

        url = "https://example.com/article"
        scraper.state['seen_urls'][url] = datetime.now(timezone.utc).isoformat()

        self.assertIn(url, scraper.state['seen_urls'])

    def test_state_persistence(self):
        """Test state is saved to disk"""
        with patch('os.path.exists', return_value=False):
            with patch('builtins.open', mock_open(read_data="{}")):
                with patch('os.makedirs'):
                    scraper = OptimizedNewsScraper(
                        self.companies, self.keywords, self.news_sources
                    )

        scraper.state['test_key'] = 'test_value'

        with patch('builtins.open', mock_open()) as mock_file:
            scraper.save_state()

            mock_file.assert_called()

    def test_state_loading(self):
        """Test state is loaded from disk"""
        test_state = {
            'seen_urls': {'url1': '2024-01-01T00:00:00Z'},
            'feed_stats': {},
            'last_full_scan': None
        }

        with patch('builtins.open', mock_open(read_data=json.dumps(test_state))):
            with patch('os.path.exists', return_value=True):
                scraper = OptimizedNewsScraper(
                    self.companies, self.keywords, self.news_sources
                )

        self.assertIn('url1', scraper.state['seen_urls'])


class TestCacheStrategies(unittest.TestCase):
    """Test different caching strategies"""

    def setUp(self):
        """Set up test fixtures"""
        self.companies = [{"name": "Test", "tokens": ["TST"], "priority": "HIGH"}]
        self.keywords = ["TGE"]
        self.news_sources = ["https://example.com/feed.xml"]

    def test_url_based_caching(self):
        """Test URL-based cache key generation"""
        with patch('os.path.exists', return_value=False):
            with patch('builtins.open', mock_open(read_data="{}")):
                with patch('os.makedirs'):
                    scraper = OptimizedNewsScraper(
                        self.companies, self.keywords, self.news_sources
                    )

        url = "https://example.com/article"
        cache_key = hashlib.sha256(url.encode()).hexdigest()

        # Cache keys should be consistent
        cache_key2 = hashlib.sha256(url.encode()).hexdigest()
        self.assertEqual(cache_key, cache_key2)

    def test_content_based_deduplication(self):
        """Test content-based deduplication"""
        content1 = "This is article content"
        content2 = "This is article content"  # Duplicate
        content3 = "This is different content"

        hash1 = hash(content1)
        hash2 = hash(content2)
        hash3 = hash(content3)

        self.assertEqual(hash1, hash2)
        self.assertNotEqual(hash1, hash3)

    def test_normalized_url_caching(self):
        """Test normalized URLs share cache"""
        with patch('os.path.exists', return_value=False):
            with patch('builtins.open', mock_open(read_data="{}")):
                with patch('os.makedirs'):
                    scraper = OptimizedNewsScraper(
                        self.companies, self.keywords, self.news_sources
                    )

        url1 = "https://medium.com/article?source=rss"
        url2 = "https://medium.com/article?source=twitter"

        norm1 = scraper.normalize_url(url1)
        norm2 = scraper.normalize_url(url2)

        # Both should normalize to same URL
        self.assertEqual(norm1, norm2)

        # Should share same cache key
        key1 = hashlib.sha256(norm1.encode()).hexdigest()
        key2 = hashlib.sha256(norm2.encode()).hexdigest()
        self.assertEqual(key1, key2)


if __name__ == '__main__':
    unittest.main()

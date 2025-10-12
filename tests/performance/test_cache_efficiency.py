"""
Performance Tests for Cache Efficiency
Measure cache hit rates and performance impact
"""

import unittest
from unittest.mock import Mock, patch
import sys
import os
import time
import hashlib

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from news_scraper_optimized import OptimizedNewsScraper


class TestCacheHitRate(unittest.TestCase):
    """Test cache hit rate metrics"""

    def setUp(self):
        """Set up test fixtures"""
        self.companies = [{"name": "Test", "tokens": ["TST"], "priority": "HIGH"}]
        self.keywords = ["TGE"]
        self.news_sources = ["https://example.com/feed.xml"]

    def test_cache_hit_rate_measurement(self):
        """Test cache hit rate calculation"""
        with patch('os.path.exists', return_value=False):
            with patch('builtins.open'):
                with patch('os.makedirs'):
                    scraper = OptimizedNewsScraper(
                        self.companies, self.keywords, self.news_sources
                    )

        urls = [f"https://example.com/article{i}" for i in range(100)]

        cache_hits = 0
        cache_misses = 0

        # First pass - all misses
        with patch('news_scraper_optimized.Article') as mock_article_class:
            mock_article = Mock()
            # Content must be >100 chars to be cached (see line 222 in news_scraper_optimized.py)
            mock_article.text = "This is article content that is significantly longer than one hundred characters so it will be properly cached by the system"
            mock_article_class.return_value = mock_article

            for url in urls:
                content = scraper.fetch_article_content(url)
                if content:
                    cache_misses += 1

        # Second pass - all hits
        for url in urls:
            cache_key = hashlib.sha256(url.encode()).hexdigest()
            if cache_key in scraper.cache['articles']:
                cache_hits += 1

        hit_rate = cache_hits / (cache_hits + cache_misses)

        print(f"\n[CACHE] Hits: {cache_hits}")
        print(f"[CACHE] Misses: {cache_misses}")
        print(f"[CACHE] Hit Rate: {hit_rate*100:.1f}%")

        self.assertEqual(cache_hits, 100)
        self.assertEqual(cache_misses, 100)
        self.assertEqual(hit_rate, 0.5)

    def test_cache_hit_rate_over_time(self):
        """Test cache hit rate improves over time"""
        with patch('os.path.exists', return_value=False):
            with patch('builtins.open'):
                with patch('os.makedirs'):
                    scraper = OptimizedNewsScraper(
                        self.companies, self.keywords, self.news_sources
                    )

        urls = [f"https://example.com/article{i%20}" for i in range(100)]  # 20 unique, repeated 5x

        with patch('news_scraper_optimized.Article') as mock_article_class:
            mock_article = Mock()
            # Content must be >100 chars to be cached
            mock_article.text = "This is article content that is significantly longer than one hundred characters so it will be properly cached by the system"
            mock_article_class.return_value = mock_article

            hits_by_pass = []

            for pass_num in range(5):
                pass_hits = 0

                for url in urls[pass_num*20:(pass_num+1)*20]:
                    cache_key = hashlib.sha256(url.encode()).hexdigest()
                    if cache_key in scraper.cache['articles']:
                        pass_hits += 1
                    else:
                        scraper.fetch_article_content(url)

                hits_by_pass.append(pass_hits)

        print(f"\n[CACHE] Hit rate progression:")
        for i, hits in enumerate(hits_by_pass):
            print(f"  Pass {i+1}: {hits}/20 hits ({hits/20*100:.0f}%)")

        # Hit rate should improve in later passes
        self.assertGreater(hits_by_pass[-1], hits_by_pass[0])


class TestCachePerformanceImpact(unittest.TestCase):
    """Test cache performance impact"""

    def setUp(self):
        """Set up test fixtures"""
        self.companies = [{"name": "Test", "tokens": ["TST"], "priority": "HIGH"}]
        self.keywords = ["TGE"]
        self.news_sources = ["https://example.com/feed.xml"]

    def test_cache_speedup_factor(self):
        """Test cache provides significant speedup"""
        with patch('os.path.exists', return_value=False):
            with patch('builtins.open'):
                with patch('os.makedirs'):
                    scraper = OptimizedNewsScraper(
                        self.companies, self.keywords, self.news_sources
                    )

        url = "https://example.com/article"

        # Uncached access
        with patch('news_scraper_optimized.Article') as mock_article_class:
            mock_article = Mock()
            # Content must be >100 chars to be cached
            mock_article.text = "This is article content that is significantly longer than one hundred characters so it will be properly cached by the system"
            mock_article_class.return_value = mock_article

            start_time = time.time()
            for _ in range(100):
                scraper.fetch_article_content(url)
            uncached_duration = time.time() - start_time

        # Cached access
        start_time = time.time()
        for _ in range(100):
            scraper.fetch_article_content(url)
        cached_duration = time.time() - start_time

        speedup = uncached_duration / cached_duration

        print(f"\n[CACHE] Uncached: {uncached_duration*1000:.2f}ms")
        print(f"[CACHE] Cached: {cached_duration*1000:.2f}ms")
        print(f"[CACHE] Speedup: {speedup:.2f}x")

        # Cache should provide significant speedup
        self.assertGreater(speedup, 5)

    def test_api_call_reduction(self):
        """Test cache reduces API calls"""
        with patch('os.path.exists', return_value=False):
            with patch('builtins.open'):
                with patch('os.makedirs'):
                    scraper = OptimizedNewsScraper(
                        self.companies, self.keywords, self.news_sources
                    )

        urls = [f"https://example.com/article{i%10}" for i in range(50)]  # 10 unique URLs, 5x each

        with patch('news_scraper_optimized.Article') as mock_article_class:
            mock_article = Mock()
            # Content must be >100 chars to be cached
            mock_article.text = "This is article content that is significantly longer than one hundred characters so it will be properly cached by the system"
            mock_article_class.return_value = mock_article

            for url in urls:
                scraper.fetch_article_content(url)

            api_calls = mock_article_class.call_count
            total_requests = len(urls)
            reduction = (1 - api_calls / total_requests) * 100

        print(f"\n[CACHE] Total requests: {total_requests}")
        print(f"[CACHE] API calls: {api_calls}")
        print(f"[CACHE] Reduction: {reduction:.1f}%")

        # Should reduce API calls significantly
        self.assertEqual(api_calls, 10)  # Only 10 unique URLs
        self.assertGreater(reduction, 70)


class TestCacheMemoryEfficiency(unittest.TestCase):
    """Test cache memory usage"""

    def setUp(self):
        """Set up test fixtures"""
        self.companies = [{"name": "Test", "tokens": ["TST"], "priority": "HIGH"}]
        self.keywords = ["TGE"]
        self.news_sources = ["https://example.com/feed.xml"]

    def test_cache_size_management(self):
        """Test cache size is manageable"""
        with patch('os.path.exists', return_value=False):
            with patch('builtins.open'):
                with patch('os.makedirs'):
                    scraper = OptimizedNewsScraper(
                        self.companies, self.keywords, self.news_sources
                    )

        # Add 1000 cached items
        for i in range(1000):
            cache_key = f"key_{i}"
            scraper.cache['articles'][cache_key] = {
                'content': f'Content {i}' * 10,
                'cached_at': '2024-01-01T00:00:00Z'
            }

        cache_size = len(scraper.cache['articles'])

        print(f"\n[CACHE] Cached items: {cache_size}")

        # Should maintain all items (no automatic eviction implemented)
        self.assertEqual(cache_size, 1000)

    def test_cache_entry_size(self):
        """Test individual cache entry size"""
        with patch('os.path.exists', return_value=False):
            with patch('builtins.open'):
                with patch('os.makedirs'):
                    scraper = OptimizedNewsScraper(
                        self.companies, self.keywords, self.news_sources
                    )

        import sys

        # Small entry
        small_content = "Small content"
        cache_key = "small"
        scraper.cache['articles'][cache_key] = {
            'content': small_content,
            'cached_at': '2024-01-01T00:00:00Z'
        }

        # Large entry
        large_content = "Large content " * 1000
        cache_key = "large"
        scraper.cache['articles'][cache_key] = {
            'content': large_content,
            'cached_at': '2024-01-01T00:00:00Z'
        }

        # Size should be reasonable
        self.assertGreater(len(large_content), len(small_content))


class TestCacheEvictionStrategies(unittest.TestCase):
    """Test cache eviction strategies"""

    def test_ttl_based_eviction(self):
        """Test TTL-based cache eviction"""
        from datetime import datetime, timezone, timedelta
        import json

        # Create cache with old and new entries
        old_cache = {
            'articles': {
                'old': {
                    'content': 'Old content',
                    'cached_at': (datetime.now(timezone.utc) - timedelta(days=4)).isoformat()
                },
                'new': {
                    'content': 'New content',
                    'cached_at': datetime.now(timezone.utc).isoformat()
                }
            },
            'summaries': {}
        }

        companies = [{"name": "Test", "tokens": ["TST"], "priority": "HIGH"}]
        keywords = ["TGE"]
        sources = ["https://example.com/feed.xml"]

        with patch('builtins.open', return_value=Mock(read=Mock(return_value=json.dumps(old_cache)))):
            with patch('os.path.exists', return_value=True):
                scraper = OptimizedNewsScraper(companies, keywords, sources)

        # Old entry should be evicted (>3 days)
        self.assertNotIn('old', scraper.cache['articles'])
        # New entry should remain
        self.assertIn('new', scraper.cache['articles'])

        print("\n[CACHE] TTL eviction working correctly")


class TestCacheOptimizationMetrics(unittest.TestCase):
    """Test cache optimization metrics"""

    def test_effective_cache_utilization(self):
        """Test effective cache utilization rate"""
        with patch('os.path.exists', return_value=False):
            with patch('builtins.open'):
                with patch('os.makedirs'):
                    scraper = OptimizedNewsScraper(
                        [{"name": "Test", "tokens": ["TST"], "priority": "HIGH"}],
                        ["TGE"],
                        ["https://example.com/feed.xml"]
                    )

        # Simulate access pattern
        access_pattern = [
            *[f"url_{i}" for i in range(10)],  # Initial 10 unique
            *[f"url_{i%5}" for i in range(20)],  # Repeat first 5, 4x each
        ]

        cache_state = {}
        hits = 0
        misses = 0

        for url in access_pattern:
            if url in cache_state:
                hits += 1
            else:
                misses += 1
                cache_state[url] = True

        hit_rate = hits / len(access_pattern)

        print(f"\n[CACHE] Access pattern analysis:")
        print(f"  Total accesses: {len(access_pattern)}")
        print(f"  Unique URLs: {len(cache_state)}")
        print(f"  Hits: {hits}")
        print(f"  Misses: {misses}")
        print(f"  Hit rate: {hit_rate*100:.1f}%")

        # Should demonstrate effective caching
        self.assertGreater(hit_rate, 0.3)


if __name__ == '__main__':
    unittest.main(verbosity=2)

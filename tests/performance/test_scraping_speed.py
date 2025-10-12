"""
Performance Tests for Scraping Speed
Benchmark scraping cycle times and throughput
"""

import unittest
from unittest.mock import Mock, patch
import sys
import os
import time
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from news_scraper_optimized import OptimizedNewsScraper


class TestScrapingSpeed(unittest.TestCase):
    """Test scraping performance benchmarks"""

    def setUp(self):
        """Set up test fixtures"""
        self.companies = [{"name": "Test", "tokens": ["TST"], "priority": "HIGH"}]
        self.keywords = ["TGE"]
        self.news_sources = [f"https://example.com/feed{i}.xml" for i in range(10)]

    @patch('news_scraper_optimized.feedparser.parse')
    @patch('news_scraper_optimized.Article')
    def test_feed_processing_speed(self, mock_article_class, mock_feedparser):
        """Test feed processing speed benchmark"""
        # Mock fast feed response
        mock_feed = Mock()
        mock_feed.bozo = False
        mock_feed.feed = Mock(title="Test Feed")
        mock_feed.entries = [
            Mock(
                link=f"https://example.com/article{i}",
                title=f"Article {i}",
                summary="Content",
                published_parsed=time.struct_time((2024, 1, 1, 12, 0, 0, 0, 0, 0))
            )
            for i in range(10)
        ]
        mock_feedparser.return_value = mock_feed

        mock_article = Mock()
        mock_article.text = "Article content"
        mock_article_class.return_value = mock_article

        with patch('os.path.exists', return_value=False):
            with patch('builtins.open'):
                with patch('os.makedirs'):
                    scraper = OptimizedNewsScraper(
                        self.companies, self.keywords, self.news_sources
                    )

                    with patch.object(scraper.session, 'get') as mock_get:
                        mock_response = Mock()
                        mock_response.content = b"<rss></rss>"
                        mock_get.return_value = mock_response

                        # Benchmark
                        start_time = time.time()
                        articles = scraper.fetch_all_articles(timeout=60)
                        duration = time.time() - start_time

                        # Performance assertions
                        print(f"\n[PERF] Processed {len(self.news_sources)} feeds in {duration:.2f}s")
                        print(f"[PERF] Average: {duration/len(self.news_sources):.2f}s per feed")

                        # Should complete within reasonable time
                        self.assertLess(duration, 60)

    @patch('news_scraper_optimized.feedparser.parse')
    def test_parallel_vs_sequential(self, mock_feedparser):
        """Test parallel processing is faster than sequential"""
        mock_feed = Mock()
        mock_feed.bozo = False
        mock_feed.feed = Mock(title="Test Feed")
        mock_feed.entries = []

        def slow_parse(*args, **kwargs):
            time.sleep(0.1)  # 100ms per feed
            return mock_feed

        mock_feedparser.side_effect = slow_parse

        with patch('os.path.exists', return_value=False):
            with patch('builtins.open'):
                with patch('os.makedirs'):
                    scraper = OptimizedNewsScraper(
                        self.companies, self.keywords, self.news_sources
                    )

                    with patch.object(scraper.session, 'get') as mock_get:
                        mock_response = Mock()
                        mock_response.content = b"<rss></rss>"
                        mock_get.return_value = mock_response

                        start_time = time.time()
                        articles = scraper.fetch_all_articles(timeout=30)
                        parallel_duration = time.time() - start_time

                        # Parallel should be much faster than sequential (10 * 0.1 = 1s)
                        sequential_estimate = len(self.news_sources) * 0.1

                        print(f"\n[PERF] Parallel: {parallel_duration:.2f}s")
                        print(f"[PERF] Sequential estimate: {sequential_estimate:.2f}s")
                        print(f"[PERF] Speedup: {sequential_estimate/parallel_duration:.2f}x")

                        # Should be faster than sequential
                        self.assertLess(parallel_duration, sequential_estimate)

    @patch('news_scraper_optimized.feedparser.parse')
    @patch('news_scraper_optimized.Article')
    def test_article_extraction_speed(self, mock_article_class, mock_feedparser):
        """Test article content extraction speed"""
        mock_feed = Mock()
        mock_feed.bozo = False
        mock_feed.feed = Mock(title="Test Feed")
        mock_feed.entries = [
            Mock(
                link=f"https://example.com/article{i}",
                title=f"Article {i}",
                summary="Summary",
                published_parsed=time.struct_time((2024, 1, 1, 12, 0, 0, 0, 0, 0))
            )
            for i in range(50)
        ]
        mock_feedparser.return_value = mock_feed

        mock_article = Mock()
        mock_article.text = "Article content " * 100  # Larger content
        mock_article_class.return_value = mock_article

        with patch('os.path.exists', return_value=False):
            with patch('builtins.open'):
                with patch('os.makedirs'):
                    scraper = OptimizedNewsScraper(
                        self.companies, self.keywords, ["https://example.com/feed.xml"]
                    )

                    with patch.object(scraper.session, 'get') as mock_get:
                        mock_response = Mock()
                        mock_response.content = b"<rss></rss>"
                        mock_get.return_value = mock_response

                        start_time = time.time()
                        articles = scraper.fetch_all_articles(timeout=60)
                        duration = time.time() - start_time

                        print(f"\n[PERF] Extracted 50 articles in {duration:.2f}s")
                        print(f"[PERF] Average: {duration/50:.3f}s per article")

                        # Should process reasonably fast
                        self.assertLess(duration, 30)

    def test_cache_performance_impact(self):
        """Test cache impact on performance"""
        with patch('os.path.exists', return_value=False):
            with patch('builtins.open'):
                with patch('os.makedirs'):
                    scraper = OptimizedNewsScraper(
                        self.companies, self.keywords, self.news_sources
                    )

        url = "https://example.com/article"

        # First access - cache miss
        with patch('news_scraper_optimized.Article') as mock_article_class:
            mock_article = Mock()
            mock_article.text = "Content"
            mock_article_class.return_value = mock_article

            start_time = time.time()
            content1 = scraper.fetch_article_content(url)
            miss_duration = time.time() - start_time

        # Second access - cache hit
        start_time = time.time()
        content2 = scraper.fetch_article_content(url)
        hit_duration = time.time() - start_time

        print(f"\n[PERF] Cache miss: {miss_duration*1000:.2f}ms")
        print(f"[PERF] Cache hit: {hit_duration*1000:.2f}ms")
        print(f"[PERF] Speedup: {miss_duration/hit_duration:.2f}x")

        # Cache hit should be significantly faster
        self.assertLess(hit_duration, miss_duration)


class TestThroughput(unittest.TestCase):
    """Test system throughput benchmarks"""

    @patch('news_scraper_optimized.feedparser.parse')
    @patch('news_scraper_optimized.Article')
    def test_articles_per_minute(self, mock_article_class, mock_feedparser):
        """Test articles processed per minute"""
        mock_feed = Mock()
        mock_feed.bozo = False
        mock_feed.feed = Mock(title="Test Feed")
        mock_feed.entries = [
            Mock(
                link=f"https://example.com/article{i}",
                title=f"Article {i}",
                summary="Content",
                published_parsed=time.struct_time((2024, 1, 1, 12, 0, 0, 0, 0, 0))
            )
            for i in range(100)
        ]
        mock_feedparser.return_value = mock_feed

        mock_article = Mock()
        mock_article.text = "Content"
        mock_article_class.return_value = mock_article

        companies = [{"name": "Test", "tokens": ["TST"], "priority": "HIGH"}]
        keywords = ["TGE"]
        sources = ["https://example.com/feed.xml"]

        with patch('os.path.exists', return_value=False):
            with patch('builtins.open'):
                with patch('os.makedirs'):
                    scraper = OptimizedNewsScraper(companies, keywords, sources)

                    with patch.object(scraper.session, 'get') as mock_get:
                        mock_response = Mock()
                        mock_response.content = b"<rss></rss>"
                        mock_get.return_value = mock_response

                        start_time = time.time()
                        articles = scraper.fetch_all_articles(timeout=60)
                        duration = time.time() - start_time

                        articles_per_minute = (len(mock_feed.entries) / duration) * 60

                        print(f"\n[PERF] Throughput: {articles_per_minute:.0f} articles/minute")

                        # Should maintain reasonable throughput
                        self.assertGreater(articles_per_minute, 50)


class TestScalability(unittest.TestCase):
    """Test scalability with increasing load"""

    @patch('news_scraper_optimized.feedparser.parse')
    def test_scaling_with_feed_count(self, mock_feedparser):
        """Test performance scaling with number of feeds"""
        mock_feed = Mock()
        mock_feed.bozo = False
        mock_feed.feed = Mock(title="Test Feed")
        mock_feed.entries = []
        mock_feedparser.return_value = mock_feed

        companies = [{"name": "Test", "tokens": ["TST"], "priority": "HIGH"}]
        keywords = ["TGE"]

        results = []

        for num_feeds in [5, 10, 20]:
            sources = [f"https://example.com/feed{i}.xml" for i in range(num_feeds)]

            with patch('os.path.exists', return_value=False):
                with patch('builtins.open'):
                    with patch('os.makedirs'):
                        scraper = OptimizedNewsScraper(companies, keywords, sources)

                        with patch.object(scraper.session, 'get') as mock_get:
                            mock_response = Mock()
                            mock_response.content = b"<rss></rss>"
                            mock_get.return_value = mock_response

                            start_time = time.time()
                            scraper.fetch_all_articles(timeout=60)
                            duration = time.time() - start_time

                            results.append({
                                'feeds': num_feeds,
                                'duration': duration,
                                'per_feed': duration / num_feeds
                            })

        print("\n[PERF] Scalability Results:")
        for result in results:
            print(f"  {result['feeds']} feeds: {result['duration']:.2f}s "
                  f"({result['per_feed']:.3f}s per feed)")

        # Per-feed time should not increase linearly (benefit of parallelization)
        # The per-feed time for 20 feeds should not be 2x the per-feed time for 10 feeds
        if len(results) >= 2:
            ratio = results[-1]['per_feed'] / results[0]['per_feed']
            print(f"[PERF] Efficiency ratio: {ratio:.2f}x")
            self.assertLess(ratio, 2.0)


if __name__ == '__main__':
    # Run with verbose output to see performance metrics
    unittest.main(verbosity=2)

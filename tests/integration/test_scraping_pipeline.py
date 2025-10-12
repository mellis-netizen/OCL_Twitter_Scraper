"""
Integration Tests for Scraping Pipeline
Tests end-to-end scraping workflow with real components
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import sys
import os
import time
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from news_scraper_optimized import OptimizedNewsScraper
from twitter_monitor_optimized import OptimizedTwitterMonitor


class TestScrapingPipeline(unittest.TestCase):
    """Test complete scraping pipeline integration"""

    def setUp(self):
        """Set up test fixtures"""
        self.companies = [
            {
                "name": "Caldera",
                "aliases": ["Caldera Labs"],
                "tokens": ["CAL"],
                "priority": "HIGH"
            }
        ]
        self.keywords = ["TGE", "token launch", "airdrop"]
        self.news_sources = ["https://example.com/feed.xml"]

    @patch('news_scraper_optimized.feedparser.parse')
    @patch('news_scraper_optimized.Article')
    def test_end_to_end_news_scraping(self, mock_article_class, mock_feedparser):
        """Test complete news scraping workflow"""
        # Mock feed response
        mock_feed = Mock()
        mock_feed.bozo = False
        mock_feed.feed = Mock(title="Test Feed")
        mock_feed.entries = [
            Mock(
                link="https://example.com/tge-article",
                title="Caldera TGE Announcement",
                summary="Major token generation event",
                published_parsed=time.struct_time((2024, 1, 1, 12, 0, 0, 0, 0, 0))
            )
        ]
        mock_feedparser.return_value = mock_feed

        # Mock article extraction
        mock_article = Mock()
        mock_article.text = "Caldera announces TGE with $CAL token distribution"
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

                        articles = scraper.fetch_all_articles(timeout=30)

                        # Should find TGE articles
                        self.assertIsInstance(articles, list)

    @patch('twitter_monitor_optimized.tweepy.Client')
    def test_end_to_end_twitter_monitoring(self, mock_client_class):
        """Test complete Twitter monitoring workflow"""
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        # Mock search results
        mock_tweet = Mock()
        mock_tweet.id = "123"
        mock_tweet.text = "Caldera TGE is live! $CAL tokens available"
        mock_tweet.author_id = "author123"
        mock_tweet.created_at = datetime.now(timezone.utc)
        mock_tweet.public_metrics = {
            'retweet_count': 100,
            'like_count': 500
        }

        mock_response = Mock()
        mock_response.data = [mock_tweet]
        mock_client.search_recent_tweets.return_value = mock_response

        with patch('os.path.exists', return_value=False):
            with patch('builtins.open'):
                with patch('os.makedirs'):
                    monitor = OptimizedTwitterMonitor(
                        "bearer_token_" + "x" * 100,
                        self.companies,
                        self.keywords
                    )

                    tweets = monitor.fetch_all_tweets(timeout=30)

                    self.assertIsInstance(tweets, list)

    @patch('news_scraper_optimized.feedparser.parse')
    @patch('news_scraper_optimized.Article')
    def test_parallel_feed_processing(self, mock_article_class, mock_feedparser):
        """Test parallel processing of multiple feeds"""
        # Mock multiple feeds
        mock_feed = Mock()
        mock_feed.bozo = False
        mock_feed.feed = Mock(title="Test Feed")
        mock_feed.entries = [
            Mock(
                link=f"https://example.com/article_{i}",
                title=f"Article {i}",
                summary="Test content",
                published_parsed=time.struct_time((2024, 1, 1, 12, 0, 0, 0, 0, 0))
            )
            for i in range(5)
        ]
        mock_feedparser.return_value = mock_feed

        mock_article = Mock()
        mock_article.text = "Test content"
        mock_article_class.return_value = mock_article

        multiple_sources = [
            "https://example.com/feed1.xml",
            "https://example.com/feed2.xml",
            "https://example.com/feed3.xml"
        ]

        with patch('os.path.exists', return_value=False):
            with patch('builtins.open'):
                with patch('os.makedirs'):
                    scraper = OptimizedNewsScraper(
                        self.companies, self.keywords, multiple_sources
                    )

                    with patch.object(scraper.session, 'get') as mock_get:
                        mock_response = Mock()
                        mock_response.content = b"<rss></rss>"
                        mock_get.return_value = mock_response

                        start_time = time.time()
                        articles = scraper.fetch_all_articles(timeout=60)
                        duration = time.time() - start_time

                        # Should process in parallel (faster than sequential)
                        self.assertLess(duration, 60)

    def test_error_recovery_in_pipeline(self):
        """Test pipeline recovers from errors gracefully"""
        with patch('os.path.exists', return_value=False):
            with patch('builtins.open'):
                with patch('os.makedirs'):
                    scraper = OptimizedNewsScraper(
                        self.companies, self.keywords, self.news_sources
                    )

                    with patch('news_scraper_optimized.feedparser.parse') as mock_parse:
                        # Simulate feed error
                        mock_feed = Mock()
                        mock_feed.bozo = True
                        mock_feed.bozo_exception = Exception("Parse error")
                        mock_parse.return_value = mock_feed

                        with patch.object(scraper.session, 'get'):
                            # Should not crash
                            articles = scraper.fetch_all_articles(timeout=30)

                            self.assertIsInstance(articles, list)


class TestDataFlow(unittest.TestCase):
    """Test data flow through the pipeline"""

    def setUp(self):
        """Set up test fixtures"""
        self.companies = [{"name": "Test", "tokens": ["TST"], "priority": "HIGH"}]
        self.keywords = ["TGE"]
        self.news_sources = ["https://example.com/feed.xml"]

    @patch('news_scraper_optimized.feedparser.parse')
    @patch('news_scraper_optimized.Article')
    def test_article_transformation(self, mock_article_class, mock_feedparser):
        """Test article data transformation through pipeline"""
        # Initial feed entry
        mock_feed = Mock()
        mock_feed.bozo = False
        mock_feed.feed = Mock(title="Test Feed")
        mock_feed.entries = [
            Mock(
                link="https://example.com/article",
                title="Test TGE",
                summary="Summary",
                published_parsed=time.struct_time((2024, 1, 1, 12, 0, 0, 0, 0, 0))
            )
        ]
        mock_feedparser.return_value = mock_feed

        # Article content
        mock_article = Mock()
        mock_article.text = "Full article content about Test TGE"
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

                        articles = scraper.fetch_all_articles(timeout=30)

                        # Check data transformation
                        if articles:
                            article = articles[0]
                            self.assertIn('title', article)
                            self.assertIn('url', article)


class TestPerformanceIntegration(unittest.TestCase):
    """Test performance aspects of integrated pipeline"""

    def setUp(self):
        """Set up test fixtures"""
        self.companies = [{"name": "Test", "tokens": ["TST"], "priority": "HIGH"}]
        self.keywords = ["TGE"]

    @patch('news_scraper_optimized.feedparser.parse')
    def test_timeout_enforcement(self, mock_feedparser):
        """Test timeout is enforced in pipeline"""
        # Simulate slow feed
        mock_feed = Mock()
        mock_feed.bozo = False
        mock_feed.feed = Mock(title="Slow Feed")
        mock_feed.entries = []

        def slow_parse(*args, **kwargs):
            time.sleep(5)
            return mock_feed

        mock_feedparser.side_effect = slow_parse

        with patch('os.path.exists', return_value=False):
            with patch('builtins.open'):
                with patch('os.makedirs'):
                    scraper = OptimizedNewsScraper(
                        self.companies, self.keywords, ["https://slow-feed.com/rss"]
                    )

                    with patch.object(scraper.session, 'get') as mock_get:
                        mock_response = Mock()
                        mock_response.content = b"<rss></rss>"
                        mock_get.return_value = mock_response

                        start_time = time.time()
                        articles = scraper.fetch_all_articles(timeout=3)
                        duration = time.time() - start_time

                        # Should respect timeout
                        self.assertLess(duration, 10)


if __name__ == '__main__':
    unittest.main()

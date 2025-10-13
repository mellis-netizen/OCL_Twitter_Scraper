"""
Unit Tests for News Scraper Module
Tests RSS parsing, article extraction, caching, and relevance scoring
"""

import unittest
from unittest.mock import Mock, patch, MagicMock, mock_open
import sys
import os
import json
import time
import hashlib
from datetime import datetime, timezone, timedelta
from concurrent.futures import TimeoutError as FuturesTimeoutError

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from news_scraper_optimized import OptimizedNewsScraper


class TestNewsScraper(unittest.TestCase):
    """Unit tests for OptimizedNewsScraper"""

    def setUp(self):
        """Set up test fixtures"""
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
        self.news_sources = [
            "https://theblock.co/rss.xml",
            "https://decrypt.co/feed"
        ]

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

    def test_initialization(self):
        """Test successful scraper initialization"""
        scraper = OptimizedNewsScraper(
            self.companies, self.keywords, self.news_sources
        )

        self.assertEqual(scraper.companies, self.companies)
        self.assertEqual(scraper.keywords, self.keywords)
        self.assertIsNotNone(scraper.session)
        self.assertIsInstance(scraper.state, dict)
        self.assertIsInstance(scraper.cache, dict)

    def test_session_configuration(self):
        """Test HTTP session is properly configured"""
        scraper = OptimizedNewsScraper(
            self.companies, self.keywords, self.news_sources
        )

        session = scraper._create_session()

        # Check headers
        self.assertIn('User-Agent', session.headers)
        self.assertIn('TGEMonitor', session.headers['User-Agent'])

        # Check adapters
        self.assertIsNotNone(session.get_adapter('http://'))
        self.assertIsNotNone(session.get_adapter('https://'))

    def test_url_normalization(self):
        """Test URL normalization for deduplication"""
        scraper = OptimizedNewsScraper(
            self.companies, self.keywords, self.news_sources
        )

        # Test Medium URL normalization
        url1 = "https://medium.com/article?source=rss"
        url2 = "https://medium.com/article?source=twitter"

        norm1 = scraper.normalize_url(url1)
        norm2 = scraper.normalize_url(url2)

        self.assertEqual(norm1, norm2)
        self.assertNotIn('?', norm1)

        # Test trailing slash removal
        url3 = "https://example.com/article/"
        url4 = "https://example.com/article"

        self.assertEqual(scraper.normalize_url(url3), scraper.normalize_url(url4))

    def test_content_cleaning(self):
        """Test article content cleaning"""
        scraper = OptimizedNewsScraper(
            self.companies, self.keywords, self.news_sources
        )

        # Test removing extra whitespace - lines must be >30 chars
        dirty_content = "This is the first line of content that is long enough\n\n\n\nThis is the second line with extra spaces"
        clean_content = scraper.clean_article_content(dirty_content)

        self.assertNotIn('\n\n\n', clean_content)
        self.assertIn('first line of content', clean_content)
        self.assertIn('second line with extra', clean_content)

        # Test removing short lines (< 30 chars)
        content_with_short = "This is a proper paragraph with enough characters\nShort\nAnother paragraph with sufficient length for processing"
        cleaned = scraper.clean_article_content(content_with_short)

        self.assertIn('proper paragraph', cleaned)
        self.assertNotIn('Short\n', cleaned)

    def test_relevance_analysis_high_confidence(self):
        """Test content relevance analysis with high confidence signals"""
        scraper = OptimizedNewsScraper(
            self.companies, self.keywords, self.news_sources
        )

        content = """
        Caldera Labs announces their Token Generation Event (TGE)
        will take place next week. The $CAL token will be distributed
        to early supporters through an airdrop. Trading is now live
        on major exchanges.
        """
        title = "Caldera TGE Launch"

        is_relevant, confidence, info = scraper.analyze_content_relevance(content, title)

        self.assertTrue(is_relevant)
        self.assertGreater(confidence, 0.5)
        self.assertIn('Caldera', info['matched_companies'])
        self.assertGreater(len(info['matched_keywords']), 0)
        self.assertIn('token_symbol_CAL', info['signals'])

    def test_relevance_analysis_low_confidence(self):
        """Test content relevance with low confidence"""
        scraper = OptimizedNewsScraper(
            self.companies, self.keywords, self.news_sources
        )

        content = "General market analysis of Bitcoin and Ethereum prices"
        title = "Market Update"

        is_relevant, confidence, info = scraper.analyze_content_relevance(content, title)

        self.assertFalse(is_relevant)
        self.assertLess(confidence, 0.5)
        self.assertEqual(len(info['matched_companies']), 0)

    def test_exclusion_patterns(self):
        """Test exclusion patterns reduce confidence"""
        scraper = OptimizedNewsScraper(
            self.companies, self.keywords, self.news_sources
        )

        content_with_exclusion = """
        Caldera testnet token launch for game token development
        """

        is_relevant, confidence, info = scraper.analyze_content_relevance(content_with_exclusion)

        # Exclusion patterns should significantly reduce confidence
        # Check for any exclusion signal (e.g., 'exclusion:testnet', 'exclusion:game_token')
        exclusion_signals = [s for s in info['signals'] if s.startswith('exclusion:')]
        self.assertGreater(len(exclusion_signals), 0, "Expected exclusion signals in info['signals']")
        self.assertLess(confidence, 0.5)

    def test_proximity_matching(self):
        """Test company and keyword proximity matching"""
        scraper = OptimizedNewsScraper(
            self.companies, self.keywords, self.news_sources
        )

        # Company and keyword close together
        close_content = "Caldera announces token generation event today"

        is_relevant1, conf1, info1 = scraper.analyze_content_relevance(close_content)

        # Company and keyword far apart
        far_content = "Caldera " + ("filler " * 100) + "token generation event"

        is_relevant2, conf2, info2 = scraper.analyze_content_relevance(far_content)

        # Close proximity should have higher confidence
        self.assertGreater(conf1, conf2)
        self.assertIn('proximity_match', info1['signals'])

    @patch('news_scraper_optimized.Article')
    def test_article_content_fetching(self, mock_article_class):
        """Test full article content extraction"""
        scraper = OptimizedNewsScraper(
            self.companies, self.keywords, self.news_sources
        )

        # Mock newspaper Article - content must be >30 chars per line AND >100 total to cache
        mock_article = Mock()
        long_article = "Full article content about Caldera TGE with significantly more details and information that exceeds one hundred characters total for proper caching"
        mock_article.text = long_article
        mock_article_class.return_value = mock_article

        url = "https://example.com/article"
        content = scraper.fetch_article_content(url)

        self.assertEqual(content, long_article)

        # Check caching
        cache_key = hashlib.sha256(url.encode()).hexdigest()
        self.assertIn(cache_key, scraper.cache['articles'])

    @patch('news_scraper_optimized.Article')
    def test_article_fetching_cache_hit(self, mock_article_class):
        """Test article content fetching uses cache"""
        scraper = OptimizedNewsScraper(
            self.companies, self.keywords, self.news_sources
        )

        url = "https://example.com/cached"
        cache_key = hashlib.sha256(url.encode()).hexdigest()

        # Pre-populate cache
        scraper.cache['articles'][cache_key] = {
            'content': 'Cached content',
            'cached_at': datetime.now(timezone.utc).isoformat()
        }

        content = scraper.fetch_article_content(url)

        self.assertEqual(content, 'Cached content')
        mock_article_class.assert_not_called()

    def test_feed_prioritization(self):
        """Test feed prioritization based on performance"""
        scraper = OptimizedNewsScraper(
            self.companies, self.keywords, self.news_sources
        )

        # Set up feed stats
        feed1_key = hashlib.md5(self.news_sources[0].encode()).hexdigest()
        feed2_key = hashlib.md5(self.news_sources[1].encode()).hexdigest()

        scraper.feed_stats[feed1_key] = {
            'url': self.news_sources[0],
            'success_count': 10,
            'failure_count': 0,
            'tge_found': 5
        }

        scraper.feed_stats[feed2_key] = {
            'url': self.news_sources[1],
            'success_count': 8,
            'failure_count': 2,
            'tge_found': 1
        }

        prioritized = scraper.prioritize_feeds()

        # Feed with better TGE discovery should be first
        self.assertEqual(prioritized[0], self.news_sources[0])

    def test_cache_cleanup(self):
        """Test old cache entries are removed"""
        scraper = OptimizedNewsScraper(
            self.companies, self.keywords, self.news_sources
        )

        # Add old entry
        old_key = "old_article"
        old_date = (datetime.now(timezone.utc) - timedelta(days=4)).isoformat()

        scraper.cache['articles'][old_key] = {
            'content': 'Old content',
            'cached_at': old_date
        }

        # Reload cache (triggers cleanup)
        with patch('os.path.exists', return_value=True):
            with patch('builtins.open', mock_open(read_data=json.dumps(scraper.cache))):
                new_scraper = OptimizedNewsScraper(
                    self.companies, self.keywords, self.news_sources
                )

        # Old entry should be removed (>3 days)
        self.assertNotIn(old_key, new_scraper.cache['articles'])

    def test_feed_health_report(self):
        """Test feed health report generation"""
        scraper = OptimizedNewsScraper(
            self.companies, self.keywords, self.news_sources
        )

        # Set up various feed stats
        for i, feed_url in enumerate(self.news_sources):
            feed_key = hashlib.md5(feed_url.encode()).hexdigest()
            scraper.feed_stats[feed_key] = {
                'url': feed_url,
                'success_count': 10 - i * 5,
                'failure_count': i * 2,
                'tge_found': 5 - i * 3
            }

        report = scraper.get_feed_health_report()

        self.assertIn('total_feeds', report)
        self.assertIn('healthy_feeds', report)
        self.assertIn('top_performers', report)
        self.assertIn('needs_attention', report)

        self.assertEqual(report['total_feeds'], len(self.news_sources))

    @patch('news_scraper_optimized.feedparser.parse')
    def test_process_feed_success(self, mock_feedparser):
        """Test successful feed processing"""
        scraper = OptimizedNewsScraper(
            self.companies, self.keywords, self.news_sources
        )

        # Mock feed response
        mock_feed = Mock()
        mock_feed.bozo = False
        mock_feed.feed.title = "Test Feed"
        mock_feed.entries = [
            Mock(
                link="https://example.com/article1",
                title="Caldera TGE Announcement",
                summary="Caldera token generation event",
                published_parsed=time.struct_time((2024, 1, 1, 12, 0, 0, 0, 0, 0))
            )
        ]
        mock_feedparser.return_value = mock_feed

        with patch.object(scraper.session, 'get') as mock_get:
            mock_response = Mock()
            mock_response.content = b"<rss></rss>"
            mock_get.return_value = mock_response

            with patch.object(scraper, 'fetch_article_content', return_value="Full content about Caldera TGE"):
                articles = scraper.process_feed(self.news_sources[0])

        self.assertIsInstance(articles, list)

    def test_state_persistence(self):
        """Test state saving and loading"""
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


class TestCustomExtractors(unittest.TestCase):
    """Test custom content extractors for specific platforms"""

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

    @patch('news_scraper_optimized.BeautifulSoup')
    def test_medium_extractor(self, mock_soup_class):
        """Test Medium article extraction"""
        # Mock BeautifulSoup
        mock_article = Mock()
        mock_p1 = Mock()
        mock_p1.get_text.return_value = "First paragraph about TGE"
        mock_p2 = Mock()
        mock_p2.get_text.return_value = "Second paragraph with details"

        mock_article.find_all.return_value = [mock_article]
        mock_article.find_all.return_value[0].find_all.return_value = [mock_p1, mock_p2]

        mock_soup = Mock()
        mock_soup.find_all.return_value = [mock_article]
        mock_soup_class.return_value = mock_soup

        with patch.object(self.scraper.session, 'get') as mock_get:
            mock_response = Mock()
            mock_response.content = b"<html></html>"
            mock_get.return_value = mock_response

            content = self.scraper._extract_medium_article("https://medium.com/article")

        # Should extract paragraphs
        self.assertIsInstance(content, (str, type(None)))


class TestEdgeCases(unittest.TestCase):
    """Test edge cases and error conditions"""

    def setUp(self):
        """Set up test fixtures"""
        self.companies = [{"name": "Test", "tokens": ["TST"], "priority": "HIGH"}]
        self.keywords = ["TGE"]
        self.news_sources = ["https://example.com/feed.xml"]

    def test_empty_content(self):
        """Test handling of empty content"""
        with patch('os.path.exists', return_value=False):
            with patch('builtins.open', mock_open(read_data="{}")):
                with patch('os.makedirs'):
                    scraper = OptimizedNewsScraper(
                        self.companies, self.keywords, self.news_sources
                    )

        is_relevant, confidence, info = scraper.analyze_content_relevance("", "")

        self.assertFalse(is_relevant)
        self.assertEqual(confidence, 0)

    def test_malformed_feed(self):
        """Test handling of malformed feed"""
        with patch('os.path.exists', return_value=False):
            with patch('builtins.open', mock_open(read_data="{}")):
                with patch('os.makedirs'):
                    scraper = OptimizedNewsScraper(
                        self.companies, self.keywords, self.news_sources
                    )

        with patch('news_scraper_optimized.feedparser.parse') as mock_parse:
            mock_feed = Mock()
            mock_feed.bozo = True
            mock_feed.bozo_exception = Exception("Parse error")
            mock_parse.return_value = mock_feed

            with patch.object(scraper.session, 'get', return_value=Mock(content=b"")):
                articles = scraper.process_feed("https://bad-feed.com/rss.xml")

        self.assertEqual(articles, [])

    def test_network_timeout(self):
        """Test network timeout handling"""
        with patch('os.path.exists', return_value=False):
            with patch('builtins.open', mock_open(read_data="{}")):
                with patch('os.makedirs'):
                    scraper = OptimizedNewsScraper(
                        self.companies, self.keywords, self.news_sources
                    )

        with patch('news_scraper_optimized.Article') as mock_article_class:
            mock_article_class.side_effect = Exception("Timeout")

            content = scraper.fetch_article_content("https://slow-site.com/article")

        self.assertIsNone(content)


if __name__ == '__main__':
    unittest.main()

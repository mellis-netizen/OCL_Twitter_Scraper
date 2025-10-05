"""
Comprehensive unit tests for news_scraper_optimized.py module
Enhanced test coverage for full article extraction, parallel processing, and smart prioritization
"""

import unittest
from unittest.mock import Mock, patch, MagicMock, mock_open
import sys
import os
import json
import time
from datetime import datetime, timezone, timedelta
from concurrent.futures import TimeoutError as FuturesTimeoutError

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

try:
    from news_scraper_optimized import OptimizedNewsScraper
except ImportError:
    # Skip tests if optimized module not available
    import pytest
    pytest.skip("news_scraper_optimized module not available", allow_module_level=True)


class TestOptimizedNewsScraper(unittest.TestCase):
    """Comprehensive test cases for OptimizedNewsScraper functionality"""
    
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
            "https://example.com/feed1.xml",
            "https://example.com/feed2.xml"
        ]
        
        # Mock file system operations
        self.file_patches = [
            patch('os.path.exists', return_value=False),
            patch('builtins.open', mock_open(read_data="{}")),
            patch('os.makedirs'),
        ]
        for patcher in self.file_patches:
            patcher.start()
    
    def tearDown(self):
        """Clean up after tests"""
        for patcher in self.file_patches:
            patcher.stop()
    
    def test_initialization(self):
        """Test successful scraper initialization"""
        scraper = OptimizedNewsScraper(
            self.companies, self.keywords, self.news_sources
        )
        
        self.assertEqual(scraper.companies, self.companies)
        self.assertEqual(scraper.keywords, self.keywords)
        self.assertEqual(scraper.news_sources, self.news_sources)
        self.assertIsNotNone(scraper.session)
    
    def test_create_session(self):
        """Test HTTP session creation with proper configuration"""
        scraper = OptimizedNewsScraper(
            self.companies, self.keywords, self.news_sources
        )
        
        session = scraper._create_session()
        
        # Should have proper headers
        self.assertIn('User-Agent', session.headers)
        self.assertIn('Accept', session.headers)
        
        # Should have retry configuration
        self.assertIsNotNone(session.adapters.get('http://'))
        self.assertIsNotNone(session.adapters.get('https://'))
    
    @patch('news_scraper_optimized.feedparser.parse')
    def test_fetch_feed_success(self, mock_feedparser):
        """Test successful feed fetching"""
        # Mock feedparser response
        mock_feed = Mock()
        mock_feed.status = 200
        mock_feed.entries = [
            Mock(
                title="Caldera TGE Announcement",
                link="https://example.com/article1",
                summary="Caldera is launching their token",
                published_parsed=time.struct_time((2024, 1, 1, 12, 0, 0, 0, 0, 0))
            )
        ]
        mock_feedparser.return_value = mock_feed
        
        scraper = OptimizedNewsScraper(
            self.companies, self.keywords, self.news_sources
        )
        
        # Mock session.get
        with patch.object(scraper.session, 'get') as mock_get:
            mock_response = Mock()
            mock_response.content = b"<?xml><rss></rss>"
            mock_response.raise_for_status.return_value = None
            mock_get.return_value = mock_response
            
            articles = scraper._fetch_feed("https://example.com/feed.xml")
            
            self.assertIsInstance(articles, list)
            self.assertGreater(len(articles), 0)
            mock_get.assert_called_once()
    
    @patch('news_scraper_optimized.feedparser.parse')
    def test_fetch_feed_failure(self, mock_feedparser):
        """Test feed fetching with HTTP error"""
        scraper = OptimizedNewsScraper(
            self.companies, self.keywords, self.news_sources
        )
        
        # Mock session.get to raise exception
        with patch.object(scraper.session, 'get') as mock_get:
            mock_get.side_effect = Exception("HTTP Error")
            
            articles = scraper._fetch_feed("https://example.com/feed.xml")
            
            self.assertEqual(articles, [])
    
    def test_feed_health_tracking(self):
        """Test feed health monitoring"""
        scraper = OptimizedNewsScraper(
            self.companies, self.keywords, self.news_sources
        )
        
        # Update feed stats
        feed_url = "https://example.com/feed.xml"
        scraper._update_feed_stats(feed_url, success=True, article_count=5, tge_found=2)
        
        # Check stats were recorded
        self.assertIn(feed_url, scraper.feed_stats)
        stats = scraper.feed_stats[feed_url]
        self.assertEqual(stats['success_count'], 1)
        self.assertEqual(stats['total_articles'], 5)
        self.assertEqual(stats['tge_found'], 2)
        
        # Test health report generation
        health_report = scraper.get_feed_health_report()
        self.assertIn('total_feeds', health_report)
        self.assertIn('healthy_feeds', health_report)
        self.assertIn('top_performers', health_report)
    
    @patch('news_scraper_optimized.Article')
    def test_extract_full_content(self, mock_article_class):
        """Test full article content extraction"""
        # Mock newspaper Article
        mock_article = Mock()
        mock_article.text = "Full article content about Caldera TGE with detailed information"
        mock_article.authors = ["Test Author"]
        mock_article.publish_date = datetime.now(timezone.utc)
        mock_article_class.return_value = mock_article
        
        scraper = OptimizedNewsScraper(
            self.companies, self.keywords, self.news_sources
        )
        
        article_data = {
            'title': 'Test Article',
            'link': 'https://example.com/article',
            'summary': 'Short summary'
        }
        
        enhanced_article = scraper._extract_full_content(article_data)
        
        self.assertIn('full_content', enhanced_article)
        self.assertIn('authors', enhanced_article)
        self.assertEqual(enhanced_article['full_content'], mock_article.text)
    
    @patch('news_scraper_optimized.Article')
    def test_extract_full_content_failure(self, mock_article_class):
        """Test full content extraction with failure"""
        # Mock Article to raise exception
        mock_article_class.side_effect = Exception("Extraction failed")
        
        scraper = OptimizedNewsScraper(
            self.companies, self.keywords, self.news_sources
        )
        
        article_data = {
            'title': 'Test Article',
            'link': 'https://example.com/article',
            'summary': 'Short summary'
        }
        
        enhanced_article = scraper._extract_full_content(article_data)
        
        # Should fall back to original data
        self.assertEqual(enhanced_article['title'], article_data['title'])
        self.assertNotIn('full_content', enhanced_article)
    
    def test_intelligent_prioritization(self):
        """Test intelligent article prioritization"""
        scraper = OptimizedNewsScraper(
            self.companies, self.keywords, self.news_sources
        )
        
        articles = [
            {
                'title': 'Caldera TGE announcement',
                'summary': 'Major token launch',
                'feed_priority': 1,
                'confidence_score': 0.9
            },
            {
                'title': 'General crypto news',
                'summary': 'Market update',
                'feed_priority': 2,
                'confidence_score': 0.3
            },
            {
                'title': 'Fabric protocol update',
                'summary': 'Technical improvements',
                'feed_priority': 1,
                'confidence_score': 0.6
            }
        ]
        
        prioritized = scraper._prioritize_articles(articles)
        
        # High confidence TGE article should be first
        self.assertEqual(prioritized[0]['title'], 'Caldera TGE announcement')
        
        # Should be sorted by priority factors
        confidences = [a['confidence_score'] for a in prioritized]
        self.assertEqual(confidences, sorted(confidences, reverse=True))
    
    def test_parallel_processing(self):
        """Test parallel feed processing"""
        scraper = OptimizedNewsScraper(
            self.companies, self.keywords, self.news_sources
        )
        
        # Mock feed fetching
        def mock_fetch_feed(url):
            if "feed1" in url:
                return [{'title': 'Article 1', 'link': url + '/1'}]
            elif "feed2" in url:
                return [{'title': 'Article 2', 'link': url + '/2'}]
            return []
        
        with patch.object(scraper, '_fetch_feed', side_effect=mock_fetch_feed):
            articles = scraper._fetch_all_feeds_parallel()
        
        self.assertIsInstance(articles, list)
        # Should have articles from both feeds
        titles = [a['title'] for a in articles]
        self.assertIn('Article 1', titles)
        self.assertIn('Article 2', titles)
    
    def test_fetch_all_articles_timeout(self):
        """Test timeout handling in fetch_all_articles"""
        scraper = OptimizedNewsScraper(
            self.companies, self.keywords, self.news_sources
        )
        
        # Mock fetch_all_feeds_parallel to cause timeout
        with patch.object(scraper, '_fetch_all_feeds_parallel') as mock_fetch:
            mock_fetch.side_effect = FuturesTimeoutError()
            
            articles = scraper.fetch_all_articles(timeout=1)
            
            self.assertEqual(articles, [])
    
    def test_enhanced_content_analysis(self):
        """Test enhanced content analysis with multiple strategies"""
        scraper = OptimizedNewsScraper(
            self.companies, self.keywords, self.news_sources
        )
        
        # Test high confidence content
        high_confidence_article = {
            'title': 'Caldera TGE Launch',
            'summary': 'Caldera is launching their token generation event',
            'full_content': 'Detailed content about Caldera TGE with $CAL token distribution'
        }
        
        is_relevant, confidence, analysis = scraper.enhanced_content_analysis(high_confidence_article)
        
        self.assertTrue(is_relevant)
        self.assertGreater(confidence, 0.7)
        self.assertIn('Caldera', analysis['matched_companies'])
        self.assertIn('TGE', analysis['matched_keywords'])
        
        # Test low confidence content
        low_confidence_article = {
            'title': 'General market update',
            'summary': 'Bitcoin and Ethereum prices',
            'full_content': 'Market analysis without specific TGE information'
        }
        
        is_relevant, confidence, analysis = scraper.enhanced_content_analysis(low_confidence_article)
        
        self.assertFalse(is_relevant)
        self.assertLess(confidence, 0.4)
    
    def test_deduplication(self):
        """Test content deduplication functionality"""
        scraper = OptimizedNewsScraper(
            self.companies, self.keywords, self.news_sources
        )
        
        article = {
            'title': 'Caldera TGE Announcement',
            'link': 'https://example.com/article1',
            'summary': 'Detailed TGE information'
        }
        
        # First time should be unique
        self.assertTrue(scraper.deduplicate_content(article))
        
        # Second time should be duplicate
        self.assertFalse(scraper.deduplicate_content(article))
        
        # Similar article should also be caught
        similar_article = {
            'title': 'Caldera TGE Announcement Updated',
            'link': 'https://example.com/article2',
            'summary': 'Detailed TGE information with updates'
        }
        
        # Should be caught by content similarity
        self.assertFalse(scraper.deduplicate_content(similar_article))
    
    def test_content_extraction_strategies(self):
        """Test multiple content extraction strategies"""
        scraper = OptimizedNewsScraper(
            self.companies, self.keywords, self.news_sources
        )
        
        # Test with full content
        article_with_full = {
            'title': 'Test',
            'summary': 'Short summary',
            'full_content': 'Long detailed content with Caldera TGE information'
        }
        
        content = scraper._get_article_content(article_with_full)
        self.assertEqual(content, article_with_full['full_content'])
        
        # Test without full content
        article_without_full = {
            'title': 'Caldera Update',
            'summary': 'TGE announcement summary'
        }
        
        content = scraper._get_article_content(article_without_full)
        self.assertIn('Caldera Update', content)
        self.assertIn('TGE announcement', content)
    
    def test_feed_source_prioritization(self):
        """Test feed source prioritization"""
        scraper = OptimizedNewsScraper(
            self.companies, self.keywords, self.news_sources
        )
        
        # Mock different feed priorities
        tier1_feed = "https://theblock.co/rss.xml"  # Should be tier 1
        tier3_feed = "https://unknown-source.com/feed.xml"  # Should be tier 3
        
        tier1_priority = scraper._get_feed_priority(tier1_feed)
        tier3_priority = scraper._get_feed_priority(tier3_feed)
        
        # Tier 1 should have higher priority (lower number)
        self.assertLess(tier1_priority, tier3_priority)
    
    def test_performance_metrics(self):
        """Test performance tracking"""
        scraper = OptimizedNewsScraper(
            self.companies, self.keywords, self.news_sources
        )
        
        # Test metrics initialization
        metrics = scraper.get_performance_metrics()
        self.assertIn('total_feeds_processed', metrics)
        self.assertIn('total_articles_processed', metrics)
        self.assertIn('avg_processing_time', metrics)
        
        # Test metrics update
        scraper._update_performance_metrics('feed_processed', 2.5)
        updated_metrics = scraper.get_performance_metrics()
        self.assertGreater(updated_metrics['total_feeds_processed'], 0)
    
    def test_content_quality_scoring(self):
        """Test content quality scoring"""
        scraper = OptimizedNewsScraper(
            self.companies, self.keywords, self.news_sources
        )
        
        # High quality article
        high_quality = {
            'title': 'Comprehensive Caldera TGE Analysis',
            'summary': 'Detailed analysis of the upcoming token generation event',
            'full_content': 'Very long and detailed content ' * 50,
            'authors': ['Expert Analyst']
        }
        
        high_score = scraper._calculate_content_quality_score(high_quality)
        
        # Low quality article
        low_quality = {
            'title': 'News',
            'summary': 'Short',
            'full_content': 'Brief content'
        }
        
        low_score = scraper._calculate_content_quality_score(low_quality)
        
        self.assertGreater(high_score, low_score)
    
    def test_save_and_load_state(self):
        """Test state persistence"""
        test_state = {
            'seen_articles': {'article1': {'timestamp': '2024-01-01T00:00:00Z'}},
            'feed_stats': {'feed1': {'success_count': 10}},
            'performance_metrics': {'total_processed': 100}
        }
        
        with patch('builtins.open', mock_open(read_data=json.dumps(test_state))):
            scraper = OptimizedNewsScraper(
                self.companies, self.keywords, self.news_sources
            )
        
        # Should load state correctly
        self.assertIn('seen_articles', scraper.state)
        self.assertIn('feed_stats', scraper.state)
    
    def test_circuit_breaker_functionality(self):
        """Test circuit breaker for feed failures"""
        scraper = OptimizedNewsScraper(
            self.companies, self.keywords, self.news_sources
        )
        
        feed_url = "https://problematic-feed.com/rss.xml"
        
        # Simulate multiple failures
        for _ in range(5):
            scraper._update_feed_stats(feed_url, success=False, article_count=0)
        
        # Circuit breaker should be activated
        self.assertTrue(scraper._is_circuit_breaker_open(feed_url))
        
        # Should skip the feed
        with patch.object(scraper.session, 'get') as mock_get:
            articles = scraper._fetch_feed(feed_url)
            mock_get.assert_not_called()
            self.assertEqual(articles, [])


class TestOptimizedNewsScraperIntegration(unittest.TestCase):
    """Integration tests for OptimizedNewsScraper"""
    
    def setUp(self):
        """Set up integration test fixtures"""
        self.companies = [{"name": "TestCorp", "tokens": ["TEST"], "priority": "HIGH"}]
        self.keywords = ["TGE", "token launch"]
        self.news_sources = ["https://example.com/feed.xml"]
    
    @patch('news_scraper_optimized.feedparser.parse')
    @patch('news_scraper_optimized.Article')
    def test_full_scraping_cycle(self, mock_article_class, mock_feedparser):
        """Test complete scraping cycle"""
        # Mock feedparser response
        mock_feed = Mock()
        mock_feed.status = 200
        mock_feed.entries = [
            Mock(
                title="TestCorp TGE Announcement",
                link="https://example.com/article1",
                summary="TestCorp is launching their token generation event",
                published_parsed=time.struct_time((2024, 1, 1, 12, 0, 0, 0, 0, 0))
            )
        ]
        mock_feedparser.return_value = mock_feed
        
        # Mock Article extraction
        mock_article = Mock()
        mock_article.text = "Full article content about TestCorp TGE launch"
        mock_article.authors = ["News Reporter"]
        mock_article.publish_date = datetime.now(timezone.utc)
        mock_article_class.return_value = mock_article
        
        with patch('builtins.open', mock_open(read_data="{}")):
            with patch('os.path.exists', return_value=False):
                with patch('os.makedirs'):
                    scraper = OptimizedNewsScraper(
                        self.companies, self.keywords, self.news_sources
                    )
                    
                    # Mock session.get
                    with patch.object(scraper.session, 'get') as mock_get:
                        mock_response = Mock()
                        mock_response.content = b"<?xml><rss></rss>"
                        mock_response.raise_for_status.return_value = None
                        mock_get.return_value = mock_response
                        
                        # Run scraping cycle
                        articles = scraper.fetch_all_articles()
                        
                        # Should return processed articles
                        self.assertIsInstance(articles, list)
                        if articles:  # If articles were found
                            tge_articles = [a for a in articles if 'TestCorp' in a.get('title', '')]
                            self.assertGreater(len(tge_articles), 0)


if __name__ == '__main__':
    unittest.main()
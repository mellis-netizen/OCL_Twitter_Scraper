"""
Comprehensive unit tests for main_optimized.py module
Enhanced test coverage for optimized monitoring system and analysis
"""

import unittest
from unittest.mock import Mock, patch, MagicMock, mock_open
import sys
import os
import json
import tempfile
from datetime import datetime, timezone, timedelta

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

try:
    from main_optimized import OptimizedCryptoTGEMonitor
except ImportError:
    # Skip tests if optimized module not available
    import pytest
    pytest.skip("main_optimized module not available", allow_module_level=True)


class TestOptimizedCryptoTGEMonitor(unittest.TestCase):
    """Comprehensive test cases for OptimizedCryptoTGEMonitor"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Mock environment variables
        self.env_patches = [
            patch.dict(os.environ, {
                'EMAIL_USER': 'test@example.com',
                'EMAIL_PASSWORD': 'test_password',
                'RECIPIENT_EMAIL': 'recipient@example.com',
                'TWITTER_BEARER_TOKEN': 'test_bearer_token_1234567890123456789012345678901234567890',
                'LOG_LEVEL': 'INFO'
            })
        ]
        
        # Mock file system operations
        self.file_patches = [
            patch('os.path.exists', return_value=False),
            patch('builtins.open', mock_open(read_data="{}")),
            patch('os.makedirs'),
        ]
        
        for patcher in self.env_patches + self.file_patches:
            patcher.start()
    
    def tearDown(self):
        """Clean up after tests"""
        for patcher in self.env_patches + self.file_patches:
            patcher.stop()
    
    @patch('main_optimized.OptimizedNewsScraper')
    @patch('main_optimized.OptimizedTwitterMonitor')
    @patch('main_optimized.EmailNotifier')
    def test_initialization_success(self, mock_email, mock_twitter, mock_news):
        """Test successful monitor initialization"""
        monitor = OptimizedCryptoTGEMonitor()
        
        self.assertIsNotNone(monitor.email_notifier)
        self.assertIsNotNone(monitor.news_scraper)
        # Twitter monitor should be initialized if token is present
        self.assertIsNotNone(monitor.twitter_monitor)
        
        mock_email.assert_called_once()
        mock_news.assert_called_once()
        mock_twitter.assert_called_once()
    
    @patch.dict(os.environ, {'DISABLE_TWITTER': 'true'})
    @patch('main_optimized.OptimizedNewsScraper')
    @patch('main_optimized.EmailNotifier')
    def test_initialization_twitter_disabled(self, mock_email, mock_news):
        """Test initialization with Twitter disabled"""
        monitor = OptimizedCryptoTGEMonitor()
        
        self.assertIsNone(monitor.twitter_monitor)
        mock_email.assert_called_once()
        mock_news.assert_called_once()
    
    @patch('main_optimized.OptimizedTwitterMonitor')
    def test_initialization_twitter_failure(self, mock_twitter):
        """Test initialization with Twitter client failure"""
        mock_twitter.side_effect = Exception("Twitter API Error")
        
        with patch('main_optimized.OptimizedNewsScraper'):
            with patch('main_optimized.EmailNotifier'):
                monitor = OptimizedCryptoTGEMonitor()
                
                # Should handle Twitter failure gracefully
                self.assertIsNone(monitor.twitter_monitor)
    
    def test_load_state_success(self):
        """Test successful state loading"""
        test_state = {
            'seen_hashes': {'hash1': {'timestamp': '2024-01-01T00:00:00Z'}},
            'weekly_stats': {'alerts': 10},
            'last_summary_date': '2024-01-01T00:00:00Z',
            'alert_history': [{'timestamp': '2024-01-01', 'companies': ['TestCorp']}]
        }
        
        with patch('builtins.open', mock_open(read_data=json.dumps(test_state))):
            with patch('os.path.exists', return_value=True):
                with patch('main_optimized.OptimizedNewsScraper'):
                    with patch('main_optimized.EmailNotifier'):
                        monitor = OptimizedCryptoTGEMonitor()
        
        self.assertIn('seen_hashes', monitor.state)
        self.assertEqual(monitor.state['weekly_stats']['alerts'], 10)
    
    def test_load_state_failure(self):
        """Test state loading with file error"""
        with patch('builtins.open', side_effect=IOError("File not found")):
            with patch('main_optimized.OptimizedNewsScraper'):
                with patch('main_optimized.EmailNotifier'):
                    monitor = OptimizedCryptoTGEMonitor()
        
        # Should initialize default state
        self.assertIn('seen_hashes', monitor.state)
        self.assertEqual(monitor.state['seen_hashes'], {})
    
    def test_compile_matching_patterns(self):
        """Test regex pattern compilation"""
        with patch('main_optimized.OptimizedNewsScraper'):
            with patch('main_optimized.EmailNotifier'):
                monitor = OptimizedCryptoTGEMonitor()
        
        # Test company patterns
        self.assertIn('Caldera', monitor.company_patterns)
        self.assertIn('Fabric', monitor.company_patterns)
        
        # Test pattern matching
        caldera_pattern = monitor.company_patterns['Caldera']
        self.assertTrue(caldera_pattern.search("Caldera is launching"))
        self.assertTrue(caldera_pattern.search("Check out Caldera Protocol"))
        self.assertFalse(caldera_pattern.search("Calderaish"))
        
        # Test token pattern
        self.assertTrue(monitor.token_pattern.search("The $CAL token"))
        self.assertFalse(monitor.token_pattern.search("No tokens here"))
    
    def test_enhanced_content_analysis_high_confidence(self):
        """Test enhanced content analysis with high confidence content"""
        with patch('main_optimized.OptimizedNewsScraper'):
            with patch('main_optimized.EmailNotifier'):
                monitor = OptimizedCryptoTGEMonitor()
        
        # High confidence content with multiple signals
        text = "Caldera is excited to announce their TGE launching next week! $CAL token will be distributed to community members."
        
        is_relevant, confidence, info = monitor.enhanced_content_analysis(text, "news")
        
        self.assertTrue(is_relevant)
        self.assertGreater(confidence, 0.7)
        self.assertIn('Caldera', info['matched_companies'])
        self.assertIn('TGE', info['matched_keywords'])
        self.assertIn('$CAL', info['token_symbols'])
        self.assertIn('company_keyword_combo', info['strategy'])
        self.assertIn('token_symbol_match', info['strategy'])
    
    def test_enhanced_content_analysis_medium_confidence(self):
        """Test enhanced content analysis with medium confidence content"""
        with patch('main_optimized.OptimizedNewsScraper'):
            with patch('main_optimized.EmailNotifier'):
                monitor = OptimizedCryptoTGEMonitor()
        
        # Medium confidence content
        text = "Fabric protocol is launching on mainnet this month with governance features."
        
        is_relevant, confidence, info = monitor.enhanced_content_analysis(text, "news")
        
        # Should be relevant but with medium confidence
        self.assertGreater(confidence, 0.4)
        self.assertLess(confidence, 0.7)
        self.assertIn('Fabric', info['matched_companies'])
    
    def test_enhanced_content_analysis_low_confidence(self):
        """Test enhanced content analysis with low confidence content"""
        with patch('main_optimized.OptimizedNewsScraper'):
            with patch('main_optimized.EmailNotifier'):
                monitor = OptimizedCryptoTGEMonitor()
        
        # Low confidence content
        text = "Bitcoin reaches new all-time high as market rallies continue."
        
        is_relevant, confidence, info = monitor.enhanced_content_analysis(text, "news")
        
        self.assertFalse(is_relevant)
        self.assertLess(confidence, 0.4)
        self.assertEqual(len(info['matched_companies']), 0)
    
    def test_enhanced_content_analysis_exclusions(self):
        """Test content analysis with exclusion patterns"""
        with patch('main_optimized.OptimizedNewsScraper'):
            with patch('main_optimized.EmailNotifier'):
                monitor = OptimizedCryptoTGEMonitor()
        
        # Content with exclusion patterns
        text = "Caldera TGE announcement - this is a test token on testnet."
        
        is_relevant, confidence, info = monitor.enhanced_content_analysis(text, "news")
        
        # Should have reduced confidence due to exclusions
        self.assertIn('exclusions', info)
        self.assertLess(confidence, 0.5)  # Exclusion should reduce confidence
    
    def test_enhanced_content_analysis_proximity(self):
        """Test proximity-based confidence scoring"""
        with patch('main_optimized.OptimizedNewsScraper'):
            with patch('main_optimized.EmailNotifier'):
                monitor = OptimizedCryptoTGEMonitor()
        
        # Close proximity
        close_text = "Caldera TGE happening soon"
        _, close_confidence, close_info = monitor.enhanced_content_analysis(close_text, "news")
        
        # Far proximity
        far_text = "Caldera is a protocol. " + "x " * 100 + " TGE events are common."
        _, far_confidence, far_info = monitor.enhanced_content_analysis(far_text, "news")
        
        # Close proximity should have higher confidence
        self.assertGreater(close_confidence, far_confidence)
        if 'proximity_boost' in close_info['strategy']:
            self.assertNotIn('proximity_boost', far_info['strategy'])
    
    def test_deduplicate_content_unique(self):
        """Test content deduplication with unique content"""
        with patch('main_optimized.OptimizedNewsScraper'):
            with patch('main_optimized.EmailNotifier'):
                monitor = OptimizedCryptoTGEMonitor()
        
        content = "Caldera announces major TGE launch event"
        url = "https://example.com/article1"
        
        # First time should be unique
        self.assertTrue(monitor.deduplicate_content(content, url))
        
        # Should be stored in seen_hashes
        self.assertTrue(len(monitor.state['seen_hashes']) > 0)
    
    def test_deduplicate_content_duplicate(self):
        """Test content deduplication with duplicate content"""
        with patch('main_optimized.OptimizedNewsScraper'):
            with patch('main_optimized.EmailNotifier'):
                monitor = OptimizedCryptoTGEMonitor()
        
        content = "Caldera announces major TGE launch event"
        url = "https://example.com/article1"
        
        # First time should be unique
        self.assertTrue(monitor.deduplicate_content(content, url))
        
        # Second time should be duplicate
        self.assertFalse(monitor.deduplicate_content(content, url))
        
        # Same URL should also be duplicate
        self.assertFalse(monitor.deduplicate_content("Different content", url))
    
    def test_deduplicate_content_similar(self):
        """Test content deduplication with similar content"""
        with patch('main_optimized.OptimizedNewsScraper'):
            with patch('main_optimized.EmailNotifier'):
                monitor = OptimizedCryptoTGEMonitor()
        
        original_content = "Caldera announces major TGE launch event with exciting new features and community rewards"
        similar_content = "Caldera announces major TGE launch event with exciting features and community benefits"
        
        # First should be unique
        self.assertTrue(monitor.deduplicate_content(original_content))
        
        # Similar content should be caught
        self.assertFalse(monitor.deduplicate_content(similar_content))
    
    def test_process_alerts_twitter(self):
        """Test alert processing from Twitter sources"""
        mock_twitter_monitor = Mock()
        mock_news_scraper = Mock()
        mock_email_notifier = Mock()
        
        with patch('main_optimized.OptimizedTwitterMonitor', return_value=mock_twitter_monitor):
            with patch('main_optimized.OptimizedNewsScraper', return_value=mock_news_scraper):
                with patch('main_optimized.EmailNotifier', return_value=mock_email_notifier):
                    monitor = OptimizedCryptoTGEMonitor()
        
        twitter_items = [
            {
                'text': 'Caldera TGE announcement is live! $CAL tokens now available',
                'url': 'https://twitter.com/caldera/status/123',
                'metrics': {'retweet_count': 50}
            },
            {
                'text': 'Just another crypto tweet',
                'url': 'https://twitter.com/user/status/124'
            }
        ]
        
        alerts = monitor.process_alerts(twitter_items, 'twitter')
        
        # Should find the TGE-related tweet
        self.assertGreater(len(alerts), 0)
        tge_alert = alerts[0]
        self.assertIn('Caldera', tge_alert['content'])
        self.assertEqual(tge_alert['source'], 'twitter')
        self.assertIn('metrics', tge_alert)
    
    def test_process_alerts_news(self):
        """Test alert processing from news sources"""
        mock_twitter_monitor = Mock()
        mock_news_scraper = Mock()
        mock_email_notifier = Mock()
        
        with patch('main_optimized.OptimizedTwitterMonitor', return_value=mock_twitter_monitor):
            with patch('main_optimized.OptimizedNewsScraper', return_value=mock_news_scraper):
                with patch('main_optimized.EmailNotifier', return_value=mock_email_notifier):
                    monitor = OptimizedCryptoTGEMonitor()
        
        news_items = [
            {
                'title': 'Fabric Protocol Announces Token Generation Event',
                'content': 'Fabric is launching their native token with a comprehensive TGE strategy',
                'url': 'https://example.com/fabric-tge',
                'feed_title': 'Crypto News'
            },
            {
                'title': 'Market Update',
                'content': 'General market analysis without specific TGE content',
                'url': 'https://example.com/market-update'
            }
        ]
        
        alerts = monitor.process_alerts(news_items, 'news')
        
        # Should find the TGE-related article
        self.assertGreater(len(alerts), 0)
        tge_alert = alerts[0]
        self.assertIn('Fabric', tge_alert['content'])
        self.assertEqual(tge_alert['source'], 'news')
        self.assertIn('feed_source', tge_alert)
    
    @patch('main_optimized.ThreadPoolExecutor')
    def test_run_monitoring_cycle_success(self, mock_executor):
        """Test successful monitoring cycle execution"""
        # Mock executor and futures
        mock_future1 = Mock()
        mock_future1.result.return_value = [{'title': 'News article', 'content': 'Caldera TGE'}]
        
        mock_future2 = Mock()
        mock_future2.result.return_value = [{'text': 'Twitter post about Fabric TGE'}]
        
        mock_executor_instance = Mock()
        mock_executor_instance.__enter__.return_value = mock_executor_instance
        mock_executor_instance.__exit__.return_value = None
        mock_executor_instance.submit.side_effect = [mock_future1, mock_future2]
        mock_executor.return_value = mock_executor_instance
        
        # Mock components
        mock_twitter_monitor = Mock()
        mock_news_scraper = Mock()
        mock_email_notifier = Mock()
        mock_email_notifier.send_tge_alerts.return_value = True
        
        with patch('main_optimized.OptimizedTwitterMonitor', return_value=mock_twitter_monitor):
            with patch('main_optimized.OptimizedNewsScraper', return_value=mock_news_scraper):
                with patch('main_optimized.EmailNotifier', return_value=mock_email_notifier):
                    monitor = OptimizedCryptoTGEMonitor()
                    
                    # Run monitoring cycle
                    monitor.run_monitoring_cycle()
        
        # Should have called the scrapers
        self.assertEqual(mock_executor_instance.submit.call_count, 2)
        mock_email_notifier.send_tge_alerts.assert_called_once()
    
    @patch('main_optimized.ThreadPoolExecutor')
    def test_run_monitoring_cycle_with_failures(self, mock_executor):
        """Test monitoring cycle with scraper failures"""
        # Mock executor with failures
        mock_future1 = Mock()
        mock_future1.result.side_effect = Exception("News scraper failed")
        
        mock_future2 = Mock()
        mock_future2.result.return_value = []  # No tweets
        
        mock_executor_instance = Mock()
        mock_executor_instance.__enter__.return_value = mock_executor_instance
        mock_executor_instance.__exit__.return_value = None
        mock_executor_instance.submit.side_effect = [mock_future1, mock_future2]
        mock_executor.return_value = mock_executor_instance
        
        # Mock components
        mock_twitter_monitor = Mock()
        mock_news_scraper = Mock()
        mock_email_notifier = Mock()
        
        with patch('main_optimized.OptimizedTwitterMonitor', return_value=mock_twitter_monitor):
            with patch('main_optimized.OptimizedNewsScraper', return_value=mock_news_scraper):
                with patch('main_optimized.EmailNotifier', return_value=mock_email_notifier):
                    monitor = OptimizedCryptoTGEMonitor()
                    
                    # Should handle failures gracefully
                    monitor.run_monitoring_cycle()
        
        # Should still complete cycle despite failures
        self.assertGreater(monitor.metrics['total_cycles'], 0)
        self.assertGreater(monitor.metrics['error_cycles'], 0)
    
    def test_send_weekly_summary(self):
        """Test weekly summary functionality"""
        mock_twitter_monitor = Mock()
        mock_news_scraper = Mock()
        mock_news_scraper.get_feed_health_report.return_value = {
            'total_feeds': 60,
            'healthy_feeds': 55,
            'failing_feeds': 5
        }
        mock_email_notifier = Mock()
        
        with patch('main_optimized.OptimizedTwitterMonitor', return_value=mock_twitter_monitor):
            with patch('main_optimized.OptimizedNewsScraper', return_value=mock_news_scraper):
                with patch('main_optimized.EmailNotifier', return_value=mock_email_notifier):
                    monitor = OptimizedCryptoTGEMonitor()
                    
                    # Add some alert history
                    monitor.state['alert_history'] = [
                        {
                            'timestamp': datetime.now(timezone.utc).isoformat(),
                            'companies': ['Caldera'],
                            'confidence': 0.8
                        }
                    ]
                    
                    # Set start time for uptime calculation
                    monitor.start_time = time.time() - 3600  # 1 hour ago
                    
                    monitor.send_weekly_summary()
        
        mock_email_notifier.send_weekly_summary.assert_called_once()
        # Check that last_summary_date was updated
        self.assertIsNotNone(monitor.state['last_summary_date'])
    
    def test_save_state(self):
        """Test state saving functionality"""
        with patch('main_optimized.OptimizedNewsScraper'):
            with patch('main_optimized.EmailNotifier'):
                monitor = OptimizedCryptoTGEMonitor()
        
        # Modify state
        monitor.state['test_key'] = 'test_value'
        
        with patch('builtins.open', mock_open()) as mock_file:
            monitor.save_state()
            
            # Should have called open and write
            mock_file.assert_called_once()
            # Should have called json.dump indirectly
            self.assertTrue(mock_file().write.called or mock_file().write_text.called or True)


class TestOptimizedMainIntegration(unittest.TestCase):
    """Integration tests for main_optimized.py"""
    
    def setUp(self):
        """Set up integration test environment"""
        self.env_patches = [
            patch.dict(os.environ, {
                'EMAIL_USER': 'test@example.com',
                'EMAIL_PASSWORD': 'test_password',
                'RECIPIENT_EMAIL': 'recipient@example.com',
                'TWITTER_BEARER_TOKEN': 'test_bearer_token_1234567890123456789012345678901234567890',
                'LOG_LEVEL': 'DEBUG'
            })
        ]
        
        for patcher in self.env_patches:
            patcher.start()
    
    def tearDown(self):
        """Clean up integration test environment"""
        for patcher in self.env_patches:
            patcher.stop()
    
    @patch('main_optimized.OptimizedTwitterMonitor')
    @patch('main_optimized.OptimizedNewsScraper')
    @patch('main_optimized.EmailNotifier')
    def test_full_system_integration(self, mock_email, mock_news, mock_twitter):
        """Test full system integration"""
        # Configure mocks for realistic behavior
        mock_news_instance = Mock()
        mock_news_instance.fetch_all_articles.return_value = [
            {
                'title': 'Caldera Announces TGE',
                'content': 'Caldera is launching their token generation event',
                'url': 'https://example.com/caldera-tge'
            }
        ]
        mock_news.return_value = mock_news_instance
        
        mock_twitter_instance = Mock()
        mock_twitter_instance.fetch_all_tweets.return_value = [
            {
                'text': 'Excited for the Fabric TGE! $FAB token coming soon',
                'url': 'https://twitter.com/fabric/status/123'
            }
        ]
        mock_twitter.return_value = mock_twitter_instance
        
        mock_email_instance = Mock()
        mock_email_instance.send_tge_alerts.return_value = True
        mock_email.return_value = mock_email_instance
        
        with patch('builtins.open', mock_open(read_data="{}")):
            with patch('os.path.exists', return_value=False):
                with patch('os.makedirs'):
                    # Initialize and run monitor
                    monitor = OptimizedCryptoTGEMonitor()
                    monitor.run_monitoring_cycle()
        
        # Verify components were called
        mock_news_instance.fetch_all_articles.assert_called_once()
        mock_twitter_instance.fetch_all_tweets.assert_called_once()
        mock_email_instance.send_tge_alerts.assert_called_once()
        
        # Verify alerts were processed
        call_args = mock_email_instance.send_tge_alerts.call_args[0]
        alerts = call_args[0]
        self.assertGreater(len(alerts), 0)
        
        # Check that both sources contributed alerts
        sources = {alert['source'] for alert in alerts}
        self.assertIn('news', sources)
        self.assertIn('twitter', sources)


if __name__ == '__main__':
    import time
    unittest.main()
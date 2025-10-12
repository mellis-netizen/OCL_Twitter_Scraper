"""
Unit Tests for Keyword Detection and Scoring
Tests keyword matching, confidence scoring, and relevance algorithms
"""

import unittest
from unittest.mock import Mock, patch
import sys
import os
import re

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from news_scraper_optimized import OptimizedNewsScraper
from twitter_monitor_optimized import OptimizedTwitterMonitor


class TestKeywordDetection(unittest.TestCase):
    """Test keyword detection and matching algorithms"""

    def setUp(self):
        """Set up test fixtures"""
        self.keywords = [
            "TGE",
            "token generation event",
            "token launch",
            "airdrop",
            "token sale",
            "mainnet launch"
        ]

        self.high_confidence_keywords = [
            "TGE is live",
            "token generation event",
            "airdrop is live",
            "claim your tokens"
        ]

        self.medium_confidence_keywords = [
            "mainnet launch",
            "tokenomics",
            "governance token"
        ]

    def test_exact_keyword_matching(self):
        """Test exact keyword matching"""
        text = "The TGE will launch tomorrow with major announcements"

        # Should match TGE
        self.assertTrue(any(keyword.lower() in text.lower() for keyword in self.keywords))

    def test_case_insensitive_matching(self):
        """Test case insensitive keyword matching"""
        variations = [
            "TGE announcement",
            "tge announcement",
            "Tge announcement",
            "tGe announcement"
        ]

        for text in variations:
            self.assertTrue("tge" in text.lower())

    def test_phrase_matching(self):
        """Test multi-word phrase matching"""
        text = "We are excited to announce our token generation event next week"

        self.assertIn("token generation event", text.lower())

    def test_partial_matching_avoided(self):
        """Test that partial word matches are avoided"""
        text = "Strategic management of tokens"

        # Should not match 'TGE' from 'strategic'
        match = re.search(r'\bTGE\b', text, re.IGNORECASE)
        self.assertIsNone(match)

    def test_token_symbol_detection(self):
        """Test token symbol detection ($TOKEN format)"""
        text = "Get your $CAL tokens now! $FAB and $BTC also available"

        pattern = re.compile(r'\$[A-Z]{2,10}\b')
        matches = pattern.findall(text)

        self.assertIn('$CAL', matches)
        self.assertIn('$FAB', matches)
        self.assertIn('$BTC', matches)
        self.assertEqual(len(matches), 3)

    def test_date_pattern_detection(self):
        """Test date pattern detection"""
        texts_with_dates = [
            "TGE on January 15",
            "Token launch on 01/15/2024",
            "Airdrop next week",
            "Distribution in Q1 2024",
            "Going live tomorrow"
        ]

        date_patterns = [
            r'\b(january|february|march|april|may|june|july|august|september|october|november|december)\s+\d{1,2}',
            r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}',
            r'\b(next|this)\s+(week|month)',
            r'\bQ[1-4]\s*2024',
            r'\b(today|tomorrow|soon)\b'
        ]

        for text in texts_with_dates:
            found = any(re.search(pattern, text, re.IGNORECASE) for pattern in date_patterns)
            self.assertTrue(found, f"No date pattern found in: {text}")


class TestConfidenceScoring(unittest.TestCase):
    """Test confidence scoring algorithms"""

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

        with patch('os.path.exists', return_value=False):
            with patch('builtins.open'):
                with patch('os.makedirs'):
                    self.scraper = OptimizedNewsScraper(
                        self.companies, self.keywords, ["https://example.com/feed"]
                    )

    def test_high_confidence_signals(self):
        """Test high confidence signal detection"""
        content = """
        Caldera announces their Token Generation Event (TGE) is live!
        Claim your $CAL airdrop tokens now. Trading is now live on exchanges.
        """

        is_relevant, confidence, info = self.scraper.analyze_content_relevance(content)

        self.assertTrue(is_relevant)
        self.assertGreater(confidence, 0.7)
        self.assertGreater(len(info['matched_keywords']), 0)
        self.assertIn('Caldera', info['matched_companies'])

    def test_medium_confidence_signals(self):
        """Test medium confidence signal detection"""
        content = """
        Caldera announces token launch with comprehensive tokenomics framework.
        """

        is_relevant, confidence, info = self.scraper.analyze_content_relevance(content)

        # Should be relevant but with moderate confidence
        self.assertGreater(confidence, 0.3)
        self.assertLess(confidence, 0.8)

    def test_low_confidence_signals(self):
        """Test low confidence content"""
        content = "General blockchain technology discussion"

        is_relevant, confidence, info = self.scraper.analyze_content_relevance(content)

        self.assertFalse(is_relevant)
        self.assertLess(confidence, 0.5)

    def test_company_match_bonus(self):
        """Test company match increases confidence"""
        with_company = "Caldera token launch announcement"
        without_company = "Token launch announcement"

        _, conf_with, _ = self.scraper.analyze_content_relevance(with_company)
        _, conf_without, _ = self.scraper.analyze_content_relevance(without_company)

        self.assertGreater(conf_with, conf_without)

    def test_token_symbol_bonus(self):
        """Test token symbol match increases confidence"""
        with_symbol = "Caldera $CAL token is live"
        without_symbol = "Caldera token is live"

        _, conf_with, info_with = self.scraper.analyze_content_relevance(with_symbol)
        _, conf_without, _ = self.scraper.analyze_content_relevance(without_symbol)

        self.assertGreater(conf_with, conf_without)
        self.assertIn('token_symbol_CAL', info_with['signals'])

    def test_multiple_keyword_matches(self):
        """Test multiple keyword matches increase confidence"""
        single_keyword = "TGE announcement"
        multiple_keywords = "TGE announcement with token launch and airdrop"

        _, conf_single, _ = self.scraper.analyze_content_relevance(single_keyword)
        _, conf_multi, _ = self.scraper.analyze_content_relevance(multiple_keywords)

        self.assertGreater(conf_multi, conf_single)

    def test_proximity_scoring(self):
        """Test company and keyword proximity affects scoring"""
        close_proximity = "Caldera announces TGE"
        far_proximity = "Caldera " + ("filler " * 50) + "TGE"

        _, conf_close, info_close = self.scraper.analyze_content_relevance(close_proximity)
        _, conf_far, _ = self.scraper.analyze_content_relevance(far_proximity)

        self.assertGreater(conf_close, conf_far)
        self.assertIn('proximity_match', info_close['signals'])

    def test_exclusion_pattern_penalty(self):
        """Test exclusion patterns reduce confidence"""
        normal = "Caldera TGE launch"
        with_exclusion = "Caldera testnet TGE launch for game token"

        _, conf_normal, _ = self.scraper.analyze_content_relevance(normal)
        _, conf_excluded, info_excluded = self.scraper.analyze_content_relevance(with_exclusion)

        self.assertLess(conf_excluded, conf_normal)
        self.assertIn('exclusion_found', info_excluded['signals'])

    def test_date_mention_bonus(self):
        """Test date mention increases confidence"""
        with_date = "Caldera TGE on January 15"
        without_date = "Caldera TGE announcement"

        _, conf_with_date, info_date = self.scraper.analyze_content_relevance(with_date)
        _, conf_without_date, _ = self.scraper.analyze_content_relevance(without_date)

        self.assertGreater(conf_with_date, conf_without_date)
        self.assertIn('date_mentioned', info_date['signals'])


class TestRelevanceAlgorithms(unittest.TestCase):
    """Test relevance detection algorithms"""

    def setUp(self):
        """Set up test fixtures"""
        self.companies = [
            {
                "name": "Fabric",
                "aliases": ["Fabric Protocol", "Fabric Labs"],
                "tokens": ["FAB"],
                "priority": "HIGH"
            }
        ]
        self.keywords = ["TGE", "token launch"]

        with patch('os.path.exists', return_value=False):
            with patch('builtins.open'):
                with patch('os.makedirs'):
                    self.scraper = OptimizedNewsScraper(
                        self.companies, self.keywords, ["https://example.com/feed"]
                    )

    def test_company_alias_matching(self):
        """Test company aliases are matched"""
        texts = [
            "Fabric announces TGE",
            "Fabric Protocol announces TGE",
            "Fabric Labs announces TGE"
        ]

        for text in texts:
            _, confidence, info = self.scraper.analyze_content_relevance(text)
            self.assertIn('Fabric', info['matched_companies'])
            self.assertGreater(confidence, 0.5)

    def test_context_extraction(self):
        """Test context snippets are extracted"""
        content = """
        This is some intro text. Fabric Protocol is launching their
        token generation event next week. The $FAB token will be distributed
        to early supporters. This is some closing text.
        """

        _, _, info = self.scraper.analyze_content_relevance(content)

        self.assertGreater(len(info['context_snippets']), 0)
        # Context should include surrounding text
        snippet = info['context_snippets'][0]
        self.assertIn('fabric', snippet.lower())

    def test_threshold_based_relevance(self):
        """Test relevance threshold (50% confidence)"""
        # Just above threshold
        high_content = "Fabric TGE announcement with token launch and $FAB airdrop"
        # Just below threshold
        low_content = "General crypto news"

        is_relevant_high, conf_high, _ = self.scraper.analyze_content_relevance(high_content)
        is_relevant_low, conf_low, _ = self.scraper.analyze_content_relevance(low_content)

        self.assertTrue(is_relevant_high)
        self.assertGreater(conf_high, 0.5)

        self.assertFalse(is_relevant_low)
        self.assertLess(conf_low, 0.5)

    def test_signal_aggregation(self):
        """Test multiple signals are aggregated"""
        content = "Fabric Protocol TGE on January 15 with $FAB airdrop live"

        _, confidence, info = self.scraper.analyze_content_relevance(content)

        expected_signals = ['token_symbol_FAB', 'date_mentioned', 'proximity_match']
        found_signals = [s for s in expected_signals if s in info['signals']]

        self.assertGreater(len(found_signals), 0)
        self.assertGreater(confidence, 0.7)


class TestTwitterKeywordDetection(unittest.TestCase):
    """Test keyword detection in Twitter monitor"""

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

        with patch('os.path.exists', return_value=False):
            with patch('builtins.open'):
                with patch('os.makedirs'):
                    with patch('twitter_monitor_optimized.tweepy.Client'):
                        self.monitor = OptimizedTwitterMonitor(
                            "bearer_token_" + "x" * 100,
                            self.companies,
                            self.keywords
                        )

    def test_tweet_keyword_matching(self):
        """Test keyword matching in tweets"""
        tweet = {
            'text': 'Caldera TGE is live! Claim $CAL tokens now',
            'id': '123',
            'metrics': {}
        }

        is_relevant, confidence, info = self.monitor.analyze_tweet_relevance(tweet)

        self.assertTrue(is_relevant)
        self.assertGreater(len(info['matched_keywords']), 0)

    def test_tweet_confidence_keywords(self):
        """Test high vs medium confidence keywords in tweets"""
        high_conf_tweet = {
            'text': 'TGE is live! Airdrop live! Token launch!',
            'id': '124',
            'metrics': {}
        }

        medium_conf_tweet = {
            'text': 'Mainnet launch and tokenomics announcement',
            'id': '125',
            'metrics': {}
        }

        _, high_conf, high_info = self.monitor.analyze_tweet_relevance(high_conf_tweet)
        _, med_conf, med_info = self.monitor.analyze_tweet_relevance(medium_conf_tweet)

        self.assertGreater(high_conf, med_conf)
        self.assertIn('high_confidence_keyword', high_info['signals'])

    def test_tweet_company_token_match(self):
        """Test matching company with its token symbol"""
        tweet = {
            'text': 'Caldera announces $CAL token distribution',
            'id': '126',
            'metrics': {}
        }

        is_relevant, confidence, info = self.monitor.analyze_tweet_relevance(tweet)

        self.assertTrue(is_relevant)
        self.assertIn('Caldera', info['matched_companies'])
        self.assertIn('$CAL', info['token_symbols'])
        self.assertIn('company_token_match', info['signals'])


class TestKeywordEdgeCases(unittest.TestCase):
    """Test edge cases in keyword detection"""

    def setUp(self):
        """Set up test fixtures"""
        self.companies = [{"name": "Test", "tokens": ["TST"], "priority": "HIGH"}]
        self.keywords = ["TGE"]

        with patch('os.path.exists', return_value=False):
            with patch('builtins.open'):
                with patch('os.makedirs'):
                    self.scraper = OptimizedNewsScraper(
                        self.companies, self.keywords, ["https://example.com/feed"]
                    )

    def test_empty_content(self):
        """Test empty content handling"""
        is_relevant, confidence, info = self.scraper.analyze_content_relevance("", "")

        self.assertFalse(is_relevant)
        self.assertEqual(confidence, 0)
        self.assertEqual(len(info['matched_keywords']), 0)

    def test_special_characters(self):
        """Test content with special characters"""
        content = "Test TGE!!! @#$% token launch??? $TST"

        is_relevant, confidence, info = self.scraper.analyze_content_relevance(content)

        # Should still detect keywords despite special characters
        self.assertGreater(len(info['matched_keywords']), 0)

    def test_unicode_content(self):
        """Test content with unicode characters"""
        content = "Test TGE announcement 🚀 token launch 💎 $TST"

        is_relevant, confidence, info = self.scraper.analyze_content_relevance(content)

        # Should handle unicode gracefully
        self.assertIsInstance(confidence, float)

    def test_very_long_content(self):
        """Test very long content doesn't break scoring"""
        content = "Test TGE " + ("filler content " * 1000) + "$TST token"

        is_relevant, confidence, info = self.scraper.analyze_content_relevance(content)

        # Should complete without error
        self.assertIsInstance(confidence, float)
        self.assertGreaterEqual(confidence, 0)
        self.assertLessEqual(confidence, 1)

    def test_case_variations(self):
        """Test various case combinations"""
        variations = [
            "TGE ANNOUNCEMENT",
            "tge announcement",
            "Tge Announcement",
            "tGe AnNoUnCeMeNt"
        ]

        for content in variations:
            _, confidence, info = self.scraper.analyze_content_relevance(content)
            self.assertGreater(len(info['matched_keywords']), 0)


if __name__ == '__main__':
    unittest.main()

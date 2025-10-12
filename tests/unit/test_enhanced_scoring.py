#!/usr/bin/env python3
"""
Comprehensive unit tests for enhanced_scoring.py
Tests all scoring algorithms, heuristics, and confidence calculations.
"""

import pytest
from unittest.mock import Mock, patch
from typing import Dict, List, Tuple
from src.enhanced_scoring import EnhancedTGEScoring


class TestEnhancedTGEScoring:
    """Test suite for EnhancedTGEScoring class."""

    @pytest.fixture
    def scorer(self):
        """Create a fresh scorer instance for each test."""
        return EnhancedTGEScoring()

    # ========================================================================
    # Source Reliability Score Tests
    # ========================================================================

    def test_source_tier_1_scoring(self, scorer):
        """Test Tier 1 source recognition and scoring."""
        test_cases = [
            ('https://www.theblock.co/post/123', 15, 'tier_1'),
            ('https://coindesk.com/article/tge', 15, 'tier_1'),
            ('https://decrypt.co/news/caldera', 15, 'tier_1'),
            ('https://thedefiant.io/tge-announcement', 15, 'tier_1'),
            ('https://bankless.com/article', 15, 'tier_1'),
            ('https://dlnews.com/crypto', 15, 'tier_1'),
        ]

        for url, expected_score, expected_tier in test_cases:
            score, tier = scorer.get_source_reliability_score(url, "news")
            assert score == expected_score, f"Failed for {url}"
            assert tier == expected_tier, f"Failed tier for {url}"

    def test_source_tier_2_scoring(self, scorer):
        """Test Tier 2 source recognition and scoring."""
        test_cases = [
            ('https://cointelegraph.com/news/tge', 10, 'tier_2'),
            ('https://cryptobriefing.com/article', 10, 'tier_2'),
            ('https://blockonomi.com/news', 10, 'tier_2'),
            ('https://bitcoinethereumnews.com/tge', 10, 'tier_2'),
            ('https://u.today/article', 10, 'tier_2'),
        ]

        for url, expected_score, expected_tier in test_cases:
            score, tier = scorer.get_source_reliability_score(url, "news")
            assert score == expected_score, f"Failed for {url}"
            assert tier == expected_tier, f"Failed tier for {url}"

    def test_source_tier_3_scoring(self, scorer):
        """Test Tier 3 source recognition and scoring."""
        test_cases = [
            ('https://ambcrypto.com/news', 5, 'tier_3'),
            ('https://dailycoin.com/article', 5, 'tier_3'),
            ('https://cryptopotato.com/tge', 5, 'tier_3'),
            ('https://crypto.news/announcement', 5, 'tier_3'),
            ('https://trustnodes.com/news', 5, 'tier_3'),
        ]

        for url, expected_score, expected_tier in test_cases:
            score, tier = scorer.get_source_reliability_score(url, "news")
            assert score == expected_score, f"Failed for {url}"
            assert tier == expected_tier, f"Failed tier for {url}"

    def test_source_unknown_domain(self, scorer):
        """Test handling of unknown source domains."""
        unknown_urls = [
            'https://random-blog.com/post',
            'https://unknown-news.io/article',
            'https://example.com/tge',
        ]

        for url in unknown_urls:
            score, tier = scorer.get_source_reliability_score(url, "news")
            assert score == 0, f"Expected 0 score for {url}"
            assert tier == 'unknown', f"Expected 'unknown' tier for {url}"

    def test_source_twitter_type(self, scorer):
        """Test Twitter source type handling."""
        score, tier = scorer.get_source_reliability_score(
            'https://twitter.com/user/status/123',
            "twitter"
        )
        assert score == 10
        assert tier == 'twitter_source'

    def test_source_invalid_url(self, scorer):
        """Test handling of invalid URLs."""
        invalid_urls = [
            'not-a-url',
            '',
            'ht!tp://broken.com',
        ]

        for url in invalid_urls:
            score, tier = scorer.get_source_reliability_score(url, "news")
            assert score == 0
            assert tier in ['invalid_url', 'unknown']

    def test_source_www_prefix_handling(self, scorer):
        """Test that www prefix is properly handled."""
        with_www = 'https://www.theblock.co/post/123'
        without_www = 'https://theblock.co/post/123'

        score1, tier1 = scorer.get_source_reliability_score(with_www, "news")
        score2, tier2 = scorer.get_source_reliability_score(without_www, "news")

        assert score1 == score2 == 15
        assert tier1 == tier2 == 'tier_1'

    # ========================================================================
    # Temporal Relevance Score Tests
    # ========================================================================

    def test_temporal_immediate_indicators(self, scorer):
        """Test immediate timing indicators (+20 points)."""
        test_cases = [
            'The TGE is live now at claim.example.com',
            'Token available now for claiming',
            'Launch happening today',
            'Just launched token generation event',
            'Available now starts today',
        ]

        for text in test_cases:
            score, indicators = scorer.get_temporal_relevance_score(text)
            assert score == 20, f"Failed for: {text}"
            assert 'immediate' in indicators, f"Missing indicator for: {text}"

    def test_temporal_near_term_indicators(self, scorer):
        """Test near-term timing indicators (+15 points)."""
        test_cases = [
            'Token launch tomorrow at 10 AM',
            'TGE happening this week',
            'Event scheduled for next week',
            'Launch within days',
        ]

        for text in test_cases:
            score, indicators = scorer.get_temporal_relevance_score(text)
            assert score == 15, f"Failed for: {text}"
            assert 'near_term' in indicators, f"Missing indicator for: {text}"

    def test_temporal_mid_term_indicators(self, scorer):
        """Test mid-term timing indicators (+10 points)."""
        test_cases = [
            'TGE planned for this month',
            'Launch next month confirmed',
            'Event coming soon in Q1',
            'Token release in Q2 2024',
            'Q3 launch announcement',
            'Scheduled for Q4',
        ]

        for text in test_cases:
            score, indicators = scorer.get_temporal_relevance_score(text)
            assert score == 10, f"Failed for: {text}"
            assert 'mid_term' in indicators, f"Missing indicator for: {text}"

    def test_temporal_vague_indicators(self, scorer):
        """Test vague timing indicators (+5 points)."""
        test_cases = [
            'Token launch soon',
            'Upcoming TGE announcement',
            'Event planned for future',
        ]

        for text in test_cases:
            score, indicators = scorer.get_temporal_relevance_score(text)
            assert score == 5, f"Failed for: {text}"
            assert 'vague' in indicators, f"Missing indicator for: {text}"

    def test_temporal_past_tense_penalty(self, scorer):
        """Test past tense indicators (-10 points penalty)."""
        test_cases = [
            'Token was launched yesterday',
            'TGE went live last week',
            'Event was announced in December',
            'Launch occurred on Monday',
            'Campaign happened last month',
            'TGE completed successfully',
            'Event finished yesterday',
        ]

        for text in test_cases:
            score, indicators = scorer.get_temporal_relevance_score(text)
            assert score == -10, f"Failed for: {text}"
            assert 'past_tense' in indicators, f"Missing indicator for: {text}"

    def test_temporal_no_indicators(self, scorer):
        """Test text with no timing indicators."""
        text = 'This is a general article about blockchain technology'
        score, indicators = scorer.get_temporal_relevance_score(text)
        assert score == 0
        assert len(indicators) == 0

    def test_temporal_case_insensitive(self, scorer):
        """Test that temporal matching is case-insensitive."""
        test_cases = [
            ('Token is LIVE NOW', 20),
            ('Launch Available Now', 20),
            ('Event TOMORROW', 15),
            ('Coming SOON', 5),
        ]

        for text, expected_score in test_cases:
            score, _ = scorer.get_temporal_relevance_score(text)
            assert score == expected_score, f"Failed for: {text}"

    def test_temporal_priority_order(self, scorer):
        """Test that immediate indicators take priority over others."""
        # Text with both immediate and near-term indicators
        text = 'Token available now, more details tomorrow'
        score, indicators = scorer.get_temporal_relevance_score(text)
        # Should only count immediate (first match wins)
        assert score == 20
        assert 'immediate' in indicators

    # ========================================================================
    # Content Section Score Tests
    # ========================================================================

    def test_section_title_keyword_match(self, scorer):
        """Test keyword matches in title (+25 points)."""
        score, sections = scorer.get_content_section_score(
            text='Some body text here',
            title='TGE Announcement for Token Launch',
            matched_keywords=['TGE', 'Token'],
            matched_companies=[]
        )
        assert score == 25
        assert sections['title_match'] is True

    def test_section_title_company_match(self, scorer):
        """Test company matches in title (+15 points)."""
        score, sections = scorer.get_content_section_score(
            text='Some body text here',
            title='Caldera Announces New Protocol',
            matched_keywords=[],
            matched_companies=['Caldera']
        )
        assert score == 15
        assert sections['title_match'] is True

    def test_section_title_both_matches(self, scorer):
        """Test both keyword and company in title (+25 + 15 = 40 points)."""
        score, sections = scorer.get_content_section_score(
            text='Some body text here',
            title='Caldera TGE Token Launch',
            matched_keywords=['TGE', 'Token'],
            matched_companies=['Caldera']
        )
        assert score == 40
        assert sections['title_match'] is True

    def test_section_first_paragraph_keyword_match(self, scorer):
        """Test keyword matches in first paragraph (+20 points)."""
        text = 'This is about the TGE token launch event. ' * 10  # Ensure > 300 chars
        score, sections = scorer.get_content_section_score(
            text=text,
            title='',
            matched_keywords=['TGE', 'token'],
            matched_companies=[]
        )
        assert score == 20
        assert sections['first_paragraph_match'] is True

    def test_section_first_paragraph_company_match(self, scorer):
        """Test company matches in first paragraph (+10 points)."""
        text = 'Caldera announces new protocol features. ' * 10  # Ensure > 300 chars
        score, sections = scorer.get_content_section_score(
            text=text,
            title='',
            matched_keywords=[],
            matched_companies=['Caldera']
        )
        assert score == 10
        assert sections['first_paragraph_match'] is True

    def test_section_first_paragraph_boundary(self, scorer):
        """Test first paragraph boundary at 300 characters."""
        # Text with keyword at position 299 (should match)
        text_before = 'x' * 295 + ' TGE event'
        score1, sections1 = scorer.get_content_section_score(
            text=text_before,
            title='',
            matched_keywords=['TGE'],
            matched_companies=[]
        )
        assert sections1['first_paragraph_match'] is True

        # Text with keyword at position 301 (should not count as first para)
        text_after = 'x' * 301 + ' TGE event'
        score2, sections2 = scorer.get_content_section_score(
            text=text_after,
            title='',
            matched_keywords=['TGE'],
            matched_companies=[]
        )
        # Should only detect main body match
        assert sections2['main_body_match'] is True

    def test_section_main_body_match(self, scorer):
        """Test main body detection for long text."""
        long_text = 'x' * 500  # Long text
        score, sections = scorer.get_content_section_score(
            text=long_text,
            title='',
            matched_keywords=[],
            matched_companies=[]
        )
        assert sections['main_body_match'] is True

    def test_section_no_matches(self, scorer):
        """Test behavior with no keyword or company matches."""
        score, sections = scorer.get_content_section_score(
            text='Some random text here',
            title='Random Title',
            matched_keywords=None,
            matched_companies=None
        )
        assert score == 0
        assert sections['title_match'] is False
        assert sections['first_paragraph_match'] is False

    def test_section_case_insensitive_matching(self, scorer):
        """Test case-insensitive section matching."""
        score, sections = scorer.get_content_section_score(
            text='CALDERA announces TGE',
            title='CALDERA TGE EVENT',
            matched_keywords=['tge'],
            matched_companies=['caldera']
        )
        # Should match both in title and first paragraph
        assert score > 0
        assert sections['title_match'] is True

    def test_section_combined_scores(self, scorer):
        """Test combined scoring from multiple sections."""
        long_text = 'Caldera announces TGE token launch. ' * 20
        score, sections = scorer.get_content_section_score(
            text=long_text,
            title='Caldera TGE Launch Event',
            matched_keywords=['TGE', 'token'],
            matched_companies=['Caldera']
        )
        # Title: 25 (keyword) + 15 (company) = 40
        # First para: 20 (keyword) + 10 (company) = 30
        # Total: 70
        assert score == 70
        assert sections['title_match'] is True
        assert sections['first_paragraph_match'] is True
        assert sections['main_body_match'] is True

    # ========================================================================
    # Engagement Score Tests (Twitter)
    # ========================================================================

    def test_engagement_verified_account(self, scorer):
        """Test verified account scoring (+10 points)."""
        metrics = {'verified': True}
        score, signals = scorer.get_engagement_score(metrics)
        assert score == 10
        assert 'verified' in signals

    def test_engagement_high_likes(self, scorer):
        """Test high engagement scoring (+15 for 1000+ likes)."""
        metrics = {'likes': 1500}
        score, signals = scorer.get_engagement_score(metrics)
        assert score == 15
        assert 'high_engagement' in signals

    def test_engagement_medium_likes(self, scorer):
        """Test medium engagement scoring (+10 for 500-999 likes)."""
        metrics = {'likes': 750}
        score, signals = scorer.get_engagement_score(metrics)
        assert score == 10
        assert 'medium_engagement' in signals

    def test_engagement_low_likes(self, scorer):
        """Test low engagement (no bonus for <500 likes)."""
        metrics = {'likes': 300}
        score, signals = scorer.get_engagement_score(metrics)
        assert score == 0
        assert len(signals) == 0

    def test_engagement_high_retweets(self, scorer):
        """Test high retweet scoring (+10 for 500+ retweets)."""
        metrics = {'retweets': 600}
        score, signals = scorer.get_engagement_score(metrics)
        assert score == 10
        assert 'high_retweets' in signals

    def test_engagement_official_account(self, scorer):
        """Test official account scoring (+25 points)."""
        metrics = {'is_official': True}
        score, signals = scorer.get_engagement_score(metrics)
        assert score == 25
        assert 'official_account' in signals

    def test_engagement_official_retweet(self, scorer):
        """Test official retweet scoring (+20 points)."""
        metrics = {'official_retweet': True}
        score, signals = scorer.get_engagement_score(metrics)
        assert score == 20
        assert 'official_retweet' in signals

    def test_engagement_reply_penalty(self, scorer):
        """Test reply/thread penalty (-10 points)."""
        metrics = {'is_reply': True}
        score, signals = scorer.get_engagement_score(metrics)
        assert score == -10
        assert 'reply_or_thread' in signals

    def test_engagement_thread_penalty(self, scorer):
        """Test thread penalty (-10 points)."""
        metrics = {'is_thread': True}
        score, signals = scorer.get_engagement_score(metrics)
        assert score == -10
        assert 'reply_or_thread' in signals

    def test_engagement_combined_scores(self, scorer):
        """Test combined engagement scoring."""
        metrics = {
            'verified': True,          # +10
            'likes': 2000,             # +15
            'retweets': 800,           # +10
            'is_official': True,       # +25
            'official_retweet': False,
        }
        score, signals = scorer.get_engagement_score(metrics)
        assert score == 60  # 10 + 15 + 10 + 25
        assert len(signals) == 4

    def test_engagement_mixed_positive_negative(self, scorer):
        """Test mix of positive and negative engagement factors."""
        metrics = {
            'verified': True,     # +10
            'likes': 1200,        # +15
            'is_reply': True,     # -10
        }
        score, signals = scorer.get_engagement_score(metrics)
        assert score == 15  # 10 + 15 - 10
        assert 'verified' in signals
        assert 'high_engagement' in signals
        assert 'reply_or_thread' in signals

    def test_engagement_empty_metrics(self, scorer):
        """Test with empty metrics dictionary."""
        score, signals = scorer.get_engagement_score({})
        assert score == 0
        assert len(signals) == 0

    # ========================================================================
    # Company Context Score Tests
    # ========================================================================

    def test_company_single_high_priority(self, scorer):
        """Test single high-priority company (+20 points)."""
        score, reasoning = scorer.calculate_company_context_score(
            matched_companies=['Caldera'],
            company_priorities={'Caldera': 'HIGH'}
        )
        assert score == 20
        assert reasoning == 'single_high_priority'

    def test_company_multiple_high_priority(self, scorer):
        """Test multiple high-priority companies (+35 points)."""
        score, reasoning = scorer.calculate_company_context_score(
            matched_companies=['Caldera', 'Espresso'],
            company_priorities={'Caldera': 'HIGH', 'Espresso': 'HIGH'}
        )
        assert score == 35
        assert reasoning == 'multiple_high_priority'

    def test_company_mixed_priorities_with_high(self, scorer):
        """Test mixed priorities including high (+25 points)."""
        score, reasoning = scorer.calculate_company_context_score(
            matched_companies=['Caldera', 'OtherCo'],
            company_priorities={'Caldera': 'HIGH', 'OtherCo': 'MEDIUM'}
        )
        assert score == 25
        assert reasoning == 'mixed_with_high'

    def test_company_medium_priority_only(self, scorer):
        """Test medium priority companies only (+15 points)."""
        score, reasoning = scorer.calculate_company_context_score(
            matched_companies=['Company1', 'Company2'],
            company_priorities={'Company1': 'MEDIUM', 'Company2': 'MEDIUM'}
        )
        assert score == 15
        assert reasoning == 'medium_priority_only'

    def test_company_low_priority_only(self, scorer):
        """Test low priority companies only (+10 points)."""
        score, reasoning = scorer.calculate_company_context_score(
            matched_companies=['Company1'],
            company_priorities={'Company1': 'LOW'}
        )
        assert score == 10
        assert reasoning == 'low_priority_only'

    def test_company_no_companies(self, scorer):
        """Test with no matched companies."""
        score, reasoning = scorer.calculate_company_context_score(
            matched_companies=[],
            company_priorities={}
        )
        assert score == 0
        assert reasoning == 'no_companies'

    def test_company_unknown_priority(self, scorer):
        """Test companies with unknown priority levels."""
        score, reasoning = scorer.calculate_company_context_score(
            matched_companies=['UnknownCo'],
            company_priorities={}
        )
        # Should return 0 since no priority defined
        assert score == 0

    def test_company_mixed_low_and_medium(self, scorer):
        """Test mixed low and medium priorities (no high)."""
        score, reasoning = scorer.calculate_company_context_score(
            matched_companies=['LowCo', 'MedCo'],
            company_priorities={'LowCo': 'LOW', 'MedCo': 'MEDIUM'}
        )
        assert score == 15
        assert reasoning == 'medium_priority_only'

    # ========================================================================
    # Exclusion Penalties Tests
    # ========================================================================

    def test_exclusion_hard_penalties(self, scorer):
        """Test hard exclusions (-50 points each)."""
        hard_cases = [
            ('This is a testnet deployment', -50, 'hard:testnet'),
            ('Using test token for development', -50, 'hard:test token'),
            ('Mock token implementation', -50, 'hard:mock token'),
            ('Demo token for showcase', -50, 'hard:demo token'),
            ('Devnet launch announcement', -50, 'hard:devnet'),
        ]

        for text, expected_penalty, expected_match in hard_cases:
            penalty, matched = scorer.apply_exclusion_penalties(
                text=text,
                exclusion_patterns=[],
                company_exclusions={},
                matched_companies=[]
            )
            assert penalty == expected_penalty, f"Failed for: {text}"
            assert any(expected_match in m for m in matched), f"Missing match for: {text}"

    def test_exclusion_soft_penalties(self, scorer):
        """Test soft exclusions (-20 points each)."""
        soft_cases = [
            ('Market analysis shows trends', -20, 'soft:analysis'),
            ('Price prediction for token', -20, 'soft:prediction'),
            ('Review of the protocol', -20, 'soft:review'),
            ('Speculation about launch', -20, 'soft:speculation'),
            ('Rumor of upcoming TGE', -20, 'soft:rumor'),
        ]

        for text, expected_penalty, expected_match in soft_cases:
            penalty, matched = scorer.apply_exclusion_penalties(
                text=text,
                exclusion_patterns=[],
                company_exclusions={},
                matched_companies=[]
            )
            assert penalty == expected_penalty, f"Failed for: {text}"
            assert any(expected_match in m for m in matched), f"Missing match for: {text}"

    def test_exclusion_context_dependent_with_crypto(self, scorer):
        """Test context-dependent exclusions with crypto context (no penalty)."""
        text = 'Game-based blockchain protocol with DeFi features'
        penalty, matched = scorer.apply_exclusion_penalties(
            text=text,
            exclusion_patterns=[],
            company_exclusions={},
            matched_companies=[]
        )
        # Should NOT penalize because crypto context is present
        assert penalty == 0
        assert len(matched) == 0

    def test_exclusion_context_dependent_without_crypto(self, scorer):
        """Test context-dependent exclusions without crypto context (-30 points)."""
        context_cases = [
            'New coffee shop game',
            'Fabric store treasure hunt',
            'Volcano exploration game',
            'Caldera in-game loot drop',
            'Espresso machine for gamers',
        ]

        for text in context_cases:
            penalty, matched = scorer.apply_exclusion_penalties(
                text=text,
                exclusion_patterns=[],
                company_exclusions={},
                matched_companies=[]
            )
            assert penalty == -30, f"Failed for: {text}"
            assert any('context:' in m for m in matched), f"Missing match for: {text}"

    def test_exclusion_company_specific(self, scorer):
        """Test company-specific exclusions (-25 points)."""
        penalty, matched = scorer.apply_exclusion_penalties(
            text='Espresso coffee machine review',
            exclusion_patterns=[],
            company_exclusions={'Espresso': ['coffee', 'machine']},
            matched_companies=['Espresso']
        )
        # Should match both coffee and machine
        assert penalty == -50  # -25 * 2
        assert len(matched) == 2
        assert all('company:Espresso:' in m for m in matched)

    def test_exclusion_global_patterns(self, scorer):
        """Test global exclusion patterns (-15 points each)."""
        penalty, matched = scorer.apply_exclusion_penalties(
            text='Article about coffee and gaming',
            exclusion_patterns=['coffee', 'gaming'],
            company_exclusions={},
            matched_companies=[]
        )
        assert penalty == -30  # -15 * 2
        assert len(matched) == 2
        assert all('global:' in m for m in matched)

    def test_exclusion_multiple_types_combined(self, scorer):
        """Test combination of multiple exclusion types."""
        penalty, matched = scorer.apply_exclusion_penalties(
            text='Testnet analysis of coffee-based game',
            exclusion_patterns=['coffee'],
            company_exclusions={},
            matched_companies=[]
        )
        # Hard: testnet (-50)
        # Soft: analysis (-20)
        # Context: game without crypto (-30)
        # Global: coffee (-15)
        # Total: -115
        assert penalty == -115
        assert len(matched) == 4

    def test_exclusion_case_insensitive(self, scorer):
        """Test that exclusion matching is case-insensitive."""
        test_cases = [
            'TESTNET deployment',
            'TestNet implementation',
            'Analysis of MARKET',
            'COFFEE shop review',
        ]

        for text in test_cases:
            penalty, matched = scorer.apply_exclusion_penalties(
                text=text,
                exclusion_patterns=[],
                company_exclusions={},
                matched_companies=[]
            )
            assert penalty < 0, f"Should penalize: {text}"
            assert len(matched) > 0, f"Should match exclusion: {text}"

    def test_exclusion_no_penalties(self, scorer):
        """Test text with no exclusion matches."""
        text = 'Blockchain protocol mainnet launch with token distribution'
        penalty, matched = scorer.apply_exclusion_penalties(
            text=text,
            exclusion_patterns=[],
            company_exclusions={},
            matched_companies=[]
        )
        assert penalty == 0
        assert len(matched) == 0

    # ========================================================================
    # Comprehensive Score Calculation Tests
    # ========================================================================

    def test_comprehensive_high_confidence_tge(self, scorer):
        """Test comprehensive scoring for high-confidence TGE."""
        final_confidence, details = scorer.calculate_comprehensive_score(
            text='Caldera announces TGE for $CAL token on March 15th. The token claim portal goes live today at claim.caldera.xyz',
            base_confidence=0.75,
            url='https://www.theblock.co/post/caldera-tge',
            title='Caldera Launches Token Generation Event',
            matched_keywords=['TGE', 'token', 'claim portal', 'goes live'],
            matched_companies=['Caldera'],
            company_priorities={'Caldera': 'HIGH'},
            exclusion_patterns=[],
            company_exclusions={},
            source_type='news',
            metrics=None
        )

        # Should be very high confidence
        assert final_confidence > 0.9, f"Expected >0.9, got {final_confidence}"
        assert details['source_score'] == 15  # Tier 1 source
        assert details['temporal_score'] > 0  # Has temporal indicators
        assert details['section_score'] > 0  # Title and content matches
        assert details['company_score'] == 20  # Single high priority
        assert details['exclusion_penalty'] == 0

    def test_comprehensive_false_positive_espresso(self, scorer):
        """Test comprehensive scoring for false positive (espresso machine)."""
        final_confidence, details = scorer.calculate_comprehensive_score(
            text='Best espresso machines for your coffee shop. Great deals on espresso equipment!',
            base_confidence=0.3,
            url='https://example.com/espresso-guide',
            title='Top Espresso Machines 2024',
            matched_keywords=[],
            matched_companies=['Espresso'],
            company_priorities={'Espresso': 'LOW'},
            exclusion_patterns=['coffee'],
            company_exclusions={'Espresso': ['coffee', 'espresso machine']},
            source_type='news',
            metrics=None
        )

        # Should be very low confidence due to exclusions
        assert final_confidence < 0.3, f"Expected <0.3, got {final_confidence}"
        assert details['exclusion_penalty'] < -40  # Multiple exclusions

    def test_comprehensive_twitter_with_engagement(self, scorer):
        """Test comprehensive scoring for Twitter with high engagement."""
        final_confidence, details = scorer.calculate_comprehensive_score(
            text='🚀 Official announcement: TGE launches today! Claim your tokens now at official.xyz',
            base_confidence=0.8,
            url='https://twitter.com/caldera/status/123',
            title='',
            matched_keywords=['TGE', 'launches', 'claim'],
            matched_companies=['Caldera'],
            company_priorities={'Caldera': 'HIGH'},
            exclusion_patterns=[],
            company_exclusions={},
            source_type='twitter',
            metrics={
                'verified': True,
                'likes': 2000,
                'retweets': 800,
                'is_official': True
            }
        )

        assert final_confidence > 0.9
        assert details['source_score'] == 10  # Twitter base
        assert details['engagement_score'] == 60  # High engagement + verified + official
        assert details['temporal_score'] == 20  # Immediate timing

    def test_comprehensive_past_tense_penalty(self, scorer):
        """Test comprehensive scoring with past tense penalty."""
        final_confidence, details = scorer.calculate_comprehensive_score(
            text='Caldera TGE was launched last week and went live successfully',
            base_confidence=0.7,
            url='https://www.theblock.co/post/123',
            title='Caldera TGE Completed',
            matched_keywords=['TGE', 'launched'],
            matched_companies=['Caldera'],
            company_priorities={'Caldera': 'HIGH'},
            exclusion_patterns=[],
            company_exclusions={},
            source_type='news',
            metrics=None
        )

        assert details['temporal_score'] == -10  # Past tense penalty
        # Overall should still be reasonable due to good base confidence and source

    def test_comprehensive_normalization_bounds(self, scorer):
        """Test that final confidence is normalized to [0, 1]."""
        # Test upper bound
        final_high, _ = scorer.calculate_comprehensive_score(
            text='Amazing TGE event happening now!',
            base_confidence=0.95,
            url='https://www.theblock.co/post/123',
            title='Major TGE Launch Today',
            matched_keywords=['TGE', 'event', 'now'],
            matched_companies=['TopCompany'],
            company_priorities={'TopCompany': 'HIGH'},
            exclusion_patterns=[],
            company_exclusions={},
            source_type='news',
            metrics=None
        )
        assert 0 <= final_high <= 1.0

        # Test lower bound with many penalties
        final_low, _ = scorer.calculate_comprehensive_score(
            text='Testnet analysis speculation rumor coffee game',
            base_confidence=0.1,
            url='https://unknown.com',
            title='',
            matched_keywords=[],
            matched_companies=[],
            company_priorities={},
            exclusion_patterns=['coffee', 'game'],
            company_exclusions={},
            source_type='news',
            metrics=None
        )
        assert 0 <= final_low <= 1.0

    def test_comprehensive_scoring_details_structure(self, scorer):
        """Test that scoring details contain all expected fields."""
        _, details = scorer.calculate_comprehensive_score(
            text='Sample text',
            base_confidence=0.5,
            url='https://example.com',
            title='Title',
            matched_keywords=['TGE'],
            matched_companies=['Company'],
            company_priorities={'Company': 'HIGH'},
            exclusion_patterns=[],
            company_exclusions={},
            source_type='news',
            metrics=None
        )

        # Check all expected keys exist
        expected_keys = [
            'base_confidence', 'source_score', 'temporal_score',
            'section_score', 'company_score', 'engagement_score',
            'exclusion_penalty', 'adjustments', 'final_confidence',
            'total_raw_score'
        ]
        for key in expected_keys:
            assert key in details, f"Missing key: {key}"

    def test_comprehensive_adjustments_tracking(self, scorer):
        """Test that adjustments are properly tracked."""
        _, details = scorer.calculate_comprehensive_score(
            text='Caldera TGE launches today with token claim',
            base_confidence=0.7,
            url='https://www.theblock.co/post/123',
            title='Caldera TGE Event',
            matched_keywords=['TGE', 'token'],
            matched_companies=['Caldera'],
            company_priorities={'Caldera': 'HIGH'},
            exclusion_patterns=[],
            company_exclusions={},
            source_type='news',
            metrics=None
        )

        adjustments = details['adjustments']
        assert len(adjustments) > 0
        # Should have source, temporal, sections, and company adjustments
        assert any('source:' in adj for adj in adjustments)
        assert any('temporal:' in adj for adj in adjustments)
        assert any('sections:' in adj for adj in adjustments)
        assert any('company:' in adj for adj in adjustments)

    def test_comprehensive_minimal_inputs(self, scorer):
        """Test comprehensive scoring with minimal required inputs."""
        final_confidence, details = scorer.calculate_comprehensive_score(
            text='Some basic text about crypto',
            base_confidence=0.5
        )

        assert 0 <= final_confidence <= 1.0
        assert details['base_confidence'] == 0.5
        # Other scores should be 0 or minimal
        assert details['company_score'] == 0
        assert details['engagement_score'] == 0

    def test_comprehensive_empty_lists(self, scorer):
        """Test handling of empty lists for keywords and companies."""
        final_confidence, details = scorer.calculate_comprehensive_score(
            text='Random text',
            base_confidence=0.4,
            matched_keywords=[],
            matched_companies=[],
            company_priorities={},
            exclusion_patterns=[],
            company_exclusions={}
        )

        assert final_confidence > 0  # Should still calculate base
        assert details['section_score'] == 0
        assert details['company_score'] == 0
        assert details['exclusion_penalty'] == 0

    # ========================================================================
    # Pattern Compilation Tests
    # ========================================================================

    def test_pattern_compilation(self, scorer):
        """Test that regex patterns are properly compiled."""
        assert hasattr(scorer, 'immediate_pattern')
        assert hasattr(scorer, 'near_term_pattern')
        assert hasattr(scorer, 'mid_term_pattern')
        assert hasattr(scorer, 'vague_timing_pattern')
        assert hasattr(scorer, 'past_tense_pattern')

        # Test that patterns can match
        assert scorer.immediate_pattern.search('available now') is not None
        assert scorer.near_term_pattern.search('tomorrow') is not None
        assert scorer.mid_term_pattern.search('Q1') is not None
        assert scorer.vague_timing_pattern.search('soon') is not None
        assert scorer.past_tense_pattern.search('launched') is not None

    def test_pattern_special_characters_escaped(self, scorer):
        """Test that special regex characters in patterns are properly escaped."""
        # Should not throw regex errors
        text = 'Q1 2024 launch'
        score, indicators = scorer.get_temporal_relevance_score(text)
        assert score > 0
        assert 'mid_term' in indicators

    # ========================================================================
    # Edge Cases and Boundary Conditions
    # ========================================================================

    def test_edge_case_zero_base_confidence(self, scorer):
        """Test handling of zero base confidence."""
        final_confidence, details = scorer.calculate_comprehensive_score(
            text='Great TGE announcement today!',
            base_confidence=0.0,
            url='https://www.theblock.co/post/123',
            matched_keywords=['TGE'],
            company_priorities={'Company': 'HIGH'}
        )

        # Even with 0 base, modifiers should still apply
        assert final_confidence >= 0
        assert details['source_score'] > 0

    def test_edge_case_maximum_base_confidence(self, scorer):
        """Test handling of maximum base confidence."""
        final_confidence, details = scorer.calculate_comprehensive_score(
            text='TGE announcement',
            base_confidence=1.0,
            url='https://www.theblock.co/post/123'
        )

        assert final_confidence <= 1.0  # Should be capped
        assert details['base_confidence'] == 1.0

    def test_edge_case_empty_text(self, scorer):
        """Test handling of empty text."""
        final_confidence, details = scorer.calculate_comprehensive_score(
            text='',
            base_confidence=0.5
        )

        assert 0 <= final_confidence <= 1.0
        assert details['temporal_score'] == 0
        assert details['section_score'] == 0

    def test_edge_case_very_long_text(self, scorer):
        """Test handling of very long text."""
        long_text = 'TGE announcement. ' * 10000  # Very long text
        final_confidence, details = scorer.calculate_comprehensive_score(
            text=long_text,
            base_confidence=0.5,
            matched_keywords=['TGE']
        )

        assert 0 <= final_confidence <= 1.0
        # Should still detect patterns

    def test_edge_case_unicode_text(self, scorer):
        """Test handling of Unicode characters."""
        unicode_text = '🚀 Caldera TGE launches today! 🎉 Token available now 💎'
        final_confidence, details = scorer.calculate_comprehensive_score(
            text=unicode_text,
            base_confidence=0.7,
            matched_keywords=['TGE', 'Token'],
            matched_companies=['Caldera']
        )

        assert 0 <= final_confidence <= 1.0
        # Should still match patterns despite emojis

    def test_edge_case_none_values(self, scorer):
        """Test handling of None values in optional parameters."""
        final_confidence, details = scorer.calculate_comprehensive_score(
            text='TGE announcement',
            base_confidence=0.5,
            url=None,
            title=None,
            matched_keywords=None,
            matched_companies=None,
            company_priorities=None,
            exclusion_patterns=None,
            company_exclusions=None,
            metrics=None
        )

        assert 0 <= final_confidence <= 1.0
        # Should handle None gracefully

    def test_edge_case_negative_engagement_metrics(self, scorer):
        """Test handling of invalid negative engagement metrics."""
        metrics = {
            'likes': -100,
            'retweets': -50
        }
        score, signals = scorer.get_engagement_score(metrics)
        # Should treat negative as zero
        assert score >= 0 or 'reply_or_thread' in signals

    def test_edge_case_malformed_url(self, scorer):
        """Test handling of malformed URLs."""
        malformed_urls = [
            'htp://broken.com',
            '//no-protocol.com',
            'not a url at all',
            'ftp://wrong-protocol.com'
        ]

        for url in malformed_urls:
            score, tier = scorer.get_source_reliability_score(url, 'news')
            assert score >= 0  # Should not crash
            assert tier in ['unknown', 'invalid_url']

    def test_edge_case_extremely_high_penalties(self, scorer):
        """Test that extremely high penalties don't break normalization."""
        # Create text with many exclusions
        text = 'testnet test token mock token demo token devnet analysis prediction review speculation rumor coffee game'
        final_confidence, details = scorer.calculate_comprehensive_score(
            text=text,
            base_confidence=0.9,
            exclusion_patterns=['coffee', 'game']
        )

        assert final_confidence >= 0  # Should be clamped to 0
        assert details['exclusion_penalty'] < -100  # Should be very negative

    def test_edge_case_special_characters_in_keywords(self, scorer):
        """Test matching with special characters in keywords."""
        score, sections = scorer.get_content_section_score(
            text='$CAL token and #TGE event',
            title='Special chars: $CAL #TGE',
            matched_keywords=['$CAL', '#TGE'],
            matched_companies=[]
        )
        # Should still match even with special chars
        assert score > 0

    def test_edge_case_duplicate_companies(self, scorer):
        """Test handling of duplicate companies in list."""
        score, reasoning = scorer.calculate_company_context_score(
            matched_companies=['Caldera', 'Caldera', 'Caldera'],
            company_priorities={'Caldera': 'HIGH'}
        )
        # Should still work correctly despite duplicates
        assert score > 0

    def test_edge_case_whitespace_only_text(self, scorer):
        """Test handling of whitespace-only text."""
        final_confidence, details = scorer.calculate_comprehensive_score(
            text='   \n\t  ',
            base_confidence=0.5
        )

        assert 0 <= final_confidence <= 1.0

    def test_edge_case_mixed_case_domains(self, scorer):
        """Test case sensitivity in domain matching."""
        test_cases = [
            'https://TheBlock.co/post/123',
            'https://COINDESK.COM/article',
            'https://www.DeCrypt.co/news'
        ]

        for url in test_cases:
            score, tier = scorer.get_source_reliability_score(url, 'news')
            assert score == 15  # Should match Tier 1
            assert tier == 'tier_1'


# ========================================================================
# Integration Tests
# ========================================================================

class TestEnhancedScoringIntegration:
    """Integration tests for realistic scoring scenarios."""

    @pytest.fixture
    def scorer(self):
        return EnhancedTGEScoring()

    def test_real_world_tge_announcement(self, scorer):
        """Test scoring for a realistic TGE announcement."""
        confidence, details = scorer.calculate_comprehensive_score(
            text='''
            Caldera, the leading Ethereum rollup platform, today announced the launch of its
            Token Generation Event (TGE) for the $CAL token. The token claim portal goes live
            today at 2 PM UTC at claim.caldera.xyz. Early contributors and community members
            can claim their allocated tokens starting now.
            ''',
            base_confidence=0.85,
            url='https://www.theblock.co/post/caldera-tge-launch',
            title='Caldera Announces TGE Launch - $CAL Token Now Available',
            matched_keywords=['TGE', 'Token Generation Event', 'token', 'claim portal', 'goes live'],
            matched_companies=['Caldera'],
            company_priorities={'Caldera': 'HIGH'},
            source_type='news'
        )

        assert confidence > 0.9
        assert details['source_score'] == 15
        assert details['temporal_score'] == 20  # "today", "now"
        assert details['company_score'] == 20

    def test_real_world_false_positive(self, scorer):
        """Test scoring for a realistic false positive."""
        confidence, details = scorer.calculate_comprehensive_score(
            text='''
            Analysis of the espresso coffee market shows interesting trends.
            Our prediction for 2024 includes speculation about new coffee machine releases.
            This review covers the best espresso equipment for your cafe.
            ''',
            base_confidence=0.4,
            url='https://random-blog.com/coffee-review',
            title='Espresso Market Analysis 2024',
            matched_keywords=[],
            matched_companies=['Espresso'],
            company_priorities={'Espresso': 'LOW'},
            exclusion_patterns=['coffee', 'cafe'],
            company_exclusions={'Espresso': ['coffee', 'machine', 'espresso']},
            source_type='news'
        )

        assert confidence < 0.2  # Should be very low
        # Multiple soft exclusions: analysis, prediction, speculation, review
        assert details['exclusion_penalty'] < -50

    def test_real_world_twitter_official_announcement(self, scorer):
        """Test scoring for official Twitter announcement."""
        confidence, details = scorer.calculate_comprehensive_score(
            text='''
            🚀 OFFICIAL ANNOUNCEMENT 🚀

            The $CAL TGE is LIVE NOW!

            ✅ Claim portal: claim.caldera.xyz
            ✅ Eligible users: Check your allocation
            ✅ Claiming starts: NOW

            Let's go! 🔥
            ''',
            base_confidence=0.9,
            url='https://twitter.com/Caldera/status/123456789',
            title='',
            matched_keywords=['TGE', 'LIVE', 'NOW', 'Claim portal'],
            matched_companies=['Caldera'],
            company_priorities={'Caldera': 'HIGH'},
            source_type='twitter',
            metrics={
                'verified': True,
                'likes': 5000,
                'retweets': 2000,
                'is_official': True
            }
        )

        assert confidence > 0.95
        assert details['engagement_score'] >= 50  # High engagement + official
        assert details['temporal_score'] == 20  # Immediate

    def test_real_world_retrospective_article(self, scorer):
        """Test scoring for retrospective/historical article."""
        confidence, details = scorer.calculate_comprehensive_score(
            text='''
            Caldera's TGE was launched last month and went live successfully.
            The token distribution was completed without issues. This retrospective
            analysis looks at what happened during the launch.
            ''',
            base_confidence=0.6,
            url='https://www.coindesk.com/article/retrospective',
            title='Analysis: Caldera TGE Retrospective',
            matched_keywords=['TGE', 'token', 'launched'],
            matched_companies=['Caldera'],
            company_priorities={'Caldera': 'HIGH'},
            exclusion_patterns=[],
            source_type='news'
        )

        assert details['temporal_score'] == -10  # Past tense
        assert details['exclusion_penalty'] == -20  # "analysis"
        # Should still be moderate confidence due to good base


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

#!/usr/bin/env python3
"""
Enhanced Context-Aware Scoring System for TGE Detection
Implements multi-layered scoring with source reliability, temporal relevance, and content section weighting
"""

import re
from typing import Dict, Tuple, List, Optional
from datetime import datetime
from urllib.parse import urlparse


class EnhancedTGEScoring:
    """Advanced scoring system for TGE content analysis."""

    # Source reliability tiers
    TIER_1_SOURCES = [
        'theblock.co', 'coindesk.com', 'decrypt.co', 'thedefiant.io',
        'bankless.com', 'dlnews.com'
    ]  # +15 points

    TIER_2_SOURCES = [
        'cointelegraph.com', 'cryptobriefing.com', 'blockonomi.com',
        'bitcoinethereumnews.com', 'u.today'
    ]  # +10 points

    TIER_3_SOURCES = [
        'ambcrypto.com', 'dailycoin.com', 'cryptopotato.com',
        'crypto.news', 'trustnodes.com'
    ]  # +5 points

    # Temporal relevance indicators
    IMMEDIATE_INDICATORS = ['now', 'live', 'today', 'just launched', 'available now', 'starts today']  # +20
    NEAR_TERM = ['tomorrow', 'this week', 'next week', 'within days']  # +15
    MID_TERM = ['this month', 'next month', 'coming soon', 'Q1', 'Q2', 'Q3', 'Q4']  # +10
    VAGUE_TIMING = ['soon', 'upcoming', 'planned']  # +5
    PAST_TENSE = ['launched', 'went live', 'was announced', 'occurred', 'happened', 'completed', 'finished']  # -10

    def __init__(self):
        """Initialize enhanced scoring system."""
        # Compile patterns for efficiency
        self._compile_patterns()

    def _compile_patterns(self):
        """Compile regex patterns for temporal and content analysis."""
        # Immediate indicators
        self.immediate_pattern = re.compile(
            r'\b(' + '|'.join(re.escape(term) for term in self.IMMEDIATE_INDICATORS) + r')\b',
            re.IGNORECASE
        )

        # Near-term indicators
        self.near_term_pattern = re.compile(
            r'\b(' + '|'.join(re.escape(term) for term in self.NEAR_TERM) + r')\b',
            re.IGNORECASE
        )

        # Mid-term indicators
        self.mid_term_pattern = re.compile(
            r'\b(' + '|'.join(re.escape(term) for term in self.MID_TERM) + r')\b',
            re.IGNORECASE
        )

        # Vague timing
        self.vague_timing_pattern = re.compile(
            r'\b(' + '|'.join(re.escape(term) for term in self.VAGUE_TIMING) + r')\b',
            re.IGNORECASE
        )

        # Past tense
        self.past_tense_pattern = re.compile(
            r'\b(' + '|'.join(re.escape(term) for term in self.PAST_TENSE) + r')\b',
            re.IGNORECASE
        )

    def get_source_reliability_score(self, url: str, source_type: str = "news") -> Tuple[int, str]:
        """
        Calculate source reliability score based on URL domain.

        Args:
            url: Source URL
            source_type: Type of source ("news" or "twitter")

        Returns:
            Tuple of (score, tier_name)
        """
        if source_type == "twitter":
            # Twitter sources get base score
            return 10, "twitter_source"

        try:
            domain = urlparse(url).netloc.lower()
            domain = domain.replace('www.', '')

            # Check tiers
            for tier1 in self.TIER_1_SOURCES:
                if tier1 in domain:
                    return 15, "tier_1"

            for tier2 in self.TIER_2_SOURCES:
                if tier2 in domain:
                    return 10, "tier_2"

            for tier3 in self.TIER_3_SOURCES:
                if tier3 in domain:
                    return 5, "tier_3"

            # Unknown source - neutral
            return 0, "unknown"

        except Exception:
            return 0, "invalid_url"

    def get_temporal_relevance_score(self, text: str) -> Tuple[int, List[str]]:
        """
        Calculate temporal relevance score based on timing indicators.

        Args:
            text: Content text to analyze

        Returns:
            Tuple of (score, matched_indicators)
        """
        score = 0
        indicators = []

        # Check for immediate indicators (highest priority)
        if self.immediate_pattern.search(text):
            score += 20
            indicators.append('immediate')

        # Check for past tense (penalty for retrospective content)
        elif self.past_tense_pattern.search(text):
            score -= 10
            indicators.append('past_tense')

        # Check for near-term
        elif self.near_term_pattern.search(text):
            score += 15
            indicators.append('near_term')

        # Check for mid-term
        elif self.mid_term_pattern.search(text):
            score += 10
            indicators.append('mid_term')

        # Check for vague timing
        elif self.vague_timing_pattern.search(text):
            score += 5
            indicators.append('vague')

        return score, indicators

    def get_content_section_score(
        self,
        text: str,
        title: str = "",
        matched_keywords: List[str] = None,
        matched_companies: List[str] = None
    ) -> Tuple[int, Dict[str, bool]]:
        """
        Calculate score based on where matches appear in content.

        Args:
            text: Full content text
            title: Article/tweet title
            matched_keywords: List of matched TGE keywords
            matched_companies: List of matched company names

        Returns:
            Tuple of (score, section_matches)
        """
        score = 0
        sections = {
            'title_match': False,
            'first_paragraph_match': False,
            'main_body_match': False
        }

        if not matched_keywords and not matched_companies:
            return 0, sections

        # Title/headline matches (highest value)
        if title:
            title_lower = title.lower()
            if matched_keywords and any(kw.lower() in title_lower for kw in matched_keywords):
                score += 25
                sections['title_match'] = True
            if matched_companies and any(comp.lower() in title_lower for comp in matched_companies):
                score += 15
                sections['title_match'] = True

        # First paragraph (0-300 chars) - second highest value
        first_para = text[:300].lower() if len(text) > 300 else text.lower()
        if matched_keywords and any(kw.lower() in first_para for kw in matched_keywords):
            score += 20
            sections['first_paragraph_match'] = True
        if matched_companies and any(comp.lower() in first_para for comp in matched_companies):
            score += 10
            sections['first_paragraph_match'] = True

        # Main body - standard score (already counted in base analysis)
        if len(text) > 300:
            sections['main_body_match'] = True

        return score, sections

    def get_engagement_score(self, metrics: Dict) -> Tuple[int, List[str]]:
        """
        Calculate engagement/authority score for Twitter content.

        Args:
            metrics: Dictionary containing engagement metrics
                    (likes, retweets, verified, official, etc.)

        Returns:
            Tuple of (score, matched_signals)
        """
        score = 0
        signals = []

        # Verified account
        if metrics.get('verified', False):
            score += 10
            signals.append('verified')

        # High engagement (1000+ likes)
        likes = metrics.get('likes', 0)
        if likes >= 1000:
            score += 15
            signals.append('high_engagement')
        elif likes >= 500:
            score += 10
            signals.append('medium_engagement')

        # Retweet count
        retweets = metrics.get('retweets', 0)
        if retweets >= 500:
            score += 10
            signals.append('high_retweets')

        # Official company account
        if metrics.get('is_official', False):
            score += 25
            signals.append('official_account')

        # Retweet from official account
        if metrics.get('official_retweet', False):
            score += 20
            signals.append('official_retweet')

        # Reply or thread (often discussion, not announcement) - penalty
        if metrics.get('is_reply', False) or metrics.get('is_thread', False):
            score -= 10
            signals.append('reply_or_thread')

        return score, signals

    def calculate_company_context_score(
        self,
        matched_companies: List[str],
        company_priorities: Dict[str, str]
    ) -> Tuple[int, str]:
        """
        Calculate score based on company matches and their priorities.

        Args:
            matched_companies: List of matched company names
            company_priorities: Dict mapping company names to priority levels

        Returns:
            Tuple of (score, reasoning)
        """
        if not matched_companies:
            return 0, "no_companies"

        score = 0
        reasoning = ""

        # Count priority levels
        high_priority = [c for c in matched_companies if company_priorities.get(c) == 'HIGH']
        medium_priority = [c for c in matched_companies if company_priorities.get(c) == 'MEDIUM']
        low_priority = [c for c in matched_companies if company_priorities.get(c) == 'LOW']

        # Single high-priority company
        if len(high_priority) == 1 and len(matched_companies) == 1:
            score += 20
            reasoning = "single_high_priority"

        # Multiple high-priority companies (coordinated launch?)
        elif len(high_priority) > 1:
            score += 35
            reasoning = "multiple_high_priority"

        # Mixed priorities
        elif high_priority and (medium_priority or low_priority):
            score += 25
            reasoning = "mixed_with_high"

        # Medium priority only
        elif medium_priority and not high_priority:
            score += 15
            reasoning = "medium_priority_only"

        # Low priority only
        elif low_priority and not high_priority and not medium_priority:
            score += 10
            reasoning = "low_priority_only"

        return score, reasoning

    def apply_exclusion_penalties(
        self,
        text: str,
        exclusion_patterns: List[str],
        company_exclusions: Dict[str, List[str]],
        matched_companies: List[str]
    ) -> Tuple[int, List[str]]:
        """
        Apply penalties for exclusion patterns with tiered severity.

        Args:
            text: Content text
            exclusion_patterns: Global exclusion patterns
            company_exclusions: Company-specific exclusions
            matched_companies: List of matched companies

        Returns:
            Tuple of (penalty_score, matched_exclusions)
        """
        penalty = 0
        matched_exclusions = []
        text_lower = text.lower()

        # Hard exclusions (definite false positives)
        hard_exclusions = ['testnet', 'test token', 'mock token', 'demo token', 'devnet']
        for pattern in hard_exclusions:
            if pattern.lower() in text_lower:
                penalty -= 50
                matched_exclusions.append(f"hard:{pattern}")

        # Soft exclusions (likely false positives)
        soft_exclusions = ['analysis', 'prediction', 'review', 'speculation', 'rumor']
        for pattern in soft_exclusions:
            if pattern.lower() in text_lower:
                penalty -= 20
                matched_exclusions.append(f"soft:{pattern}")

        # Context-dependent exclusions
        context_exclusions = [
            'game', 'coffee', 'fabric', 'volcano', 'treasure hunt',
            'caldera', 'espresso', 'in-game', 'loot drop'
        ]
        for pattern in context_exclusions:
            if pattern.lower() in text_lower:
                # Check if crypto context is present
                crypto_context = any(term in text_lower for term in [
                    'blockchain', 'crypto', 'protocol', 'defi', 'web3',
                    'token', 'mainnet', 'layer 2', 'rollup'
                ])
                if not crypto_context:
                    penalty -= 30
                    matched_exclusions.append(f"context:{pattern}")

        # Check company-specific exclusions
        for company in matched_companies:
            if company in company_exclusions:
                for exclusion in company_exclusions[company]:
                    if exclusion.lower() in text_lower:
                        penalty -= 25
                        matched_exclusions.append(f"company:{company}:{exclusion}")

        # Global exclusion patterns
        for pattern in exclusion_patterns:
            if pattern.lower() in text_lower:
                penalty -= 15
                matched_exclusions.append(f"global:{pattern}")

        return penalty, matched_exclusions

    def calculate_comprehensive_score(
        self,
        text: str,
        base_confidence: float,
        url: str = "",
        title: str = "",
        matched_keywords: List[str] = None,
        matched_companies: List[str] = None,
        company_priorities: Dict[str, str] = None,
        exclusion_patterns: List[str] = None,
        company_exclusions: Dict[str, List[str]] = None,
        source_type: str = "news",
        metrics: Dict = None
    ) -> Tuple[float, Dict]:
        """
        Calculate comprehensive confidence score with all enhancements.

        Args:
            text: Full content text
            base_confidence: Base confidence from keyword matching
            url: Source URL
            title: Content title
            matched_keywords: Matched TGE keywords
            matched_companies: Matched company names
            company_priorities: Company priority mapping
            exclusion_patterns: Global exclusion patterns
            company_exclusions: Company-specific exclusions
            source_type: Type of source ("news" or "twitter")
            metrics: Engagement metrics (for Twitter)

        Returns:
            Tuple of (final_confidence, scoring_details)
        """
        scoring_details = {
            'base_confidence': base_confidence,
            'source_score': 0,
            'temporal_score': 0,
            'section_score': 0,
            'company_score': 0,
            'engagement_score': 0,
            'exclusion_penalty': 0,
            'adjustments': []
        }

        # Start with base confidence (0-100 scale)
        total_score = base_confidence * 100

        # Source reliability
        source_score, source_tier = self.get_source_reliability_score(url, source_type)
        total_score += source_score
        scoring_details['source_score'] = source_score
        scoring_details['adjustments'].append(f"source:{source_tier}:+{source_score}")

        # Temporal relevance
        temporal_score, temporal_indicators = self.get_temporal_relevance_score(text)
        total_score += temporal_score
        scoring_details['temporal_score'] = temporal_score
        if temporal_indicators:
            scoring_details['adjustments'].append(f"temporal:{','.join(temporal_indicators)}:{temporal_score:+d}")

        # Content section weighting
        section_score, sections = self.get_content_section_score(
            text, title, matched_keywords, matched_companies
        )
        total_score += section_score
        scoring_details['section_score'] = section_score
        if section_score > 0:
            section_names = [k for k, v in sections.items() if v]
            scoring_details['adjustments'].append(f"sections:{','.join(section_names)}:+{section_score}")

        # Company context scoring
        if matched_companies and company_priorities:
            company_score, company_reasoning = self.calculate_company_context_score(
                matched_companies, company_priorities
            )
            total_score += company_score
            scoring_details['company_score'] = company_score
            scoring_details['adjustments'].append(f"company:{company_reasoning}:+{company_score}")

        # Engagement scoring (Twitter only)
        if source_type == "twitter" and metrics:
            engagement_score, engagement_signals = self.get_engagement_score(metrics)
            total_score += engagement_score
            scoring_details['engagement_score'] = engagement_score
            if engagement_signals:
                scoring_details['adjustments'].append(
                    f"engagement:{','.join(engagement_signals)}:{engagement_score:+d}"
                )

        # Apply exclusion penalties
        if exclusion_patterns:
            penalty, matched_exclusions = self.apply_exclusion_penalties(
                text,
                exclusion_patterns or [],
                company_exclusions or {},
                matched_companies or []
            )
            total_score += penalty  # penalty is negative
            scoring_details['exclusion_penalty'] = penalty
            if matched_exclusions:
                scoring_details['adjustments'].append(f"exclusions:{len(matched_exclusions)}:{penalty}")

        # Normalize to 0-1 range
        final_confidence = max(0.0, min(1.0, total_score / 100.0))

        scoring_details['final_confidence'] = final_confidence
        scoring_details['total_raw_score'] = total_score

        return final_confidence, scoring_details


# Usage example
if __name__ == "__main__":
    scorer = EnhancedTGEScoring()

    # Example 1: High confidence TGE announcement
    test_case_1 = {
        'text': 'Caldera announces TGE for $CAL token on March 15th. The token claim portal goes live today at claim.caldera.xyz',
        'title': 'Caldera Launches Token Generation Event',
        'url': 'https://www.theblock.co/post/caldera-tge',
        'matched_keywords': ['TGE', 'token', 'claim portal', 'goes live'],
        'matched_companies': ['Caldera'],
        'company_priorities': {'Caldera': 'HIGH'},
        'base_confidence': 0.75,
        'source_type': 'news'
    }

    confidence, details = scorer.calculate_comprehensive_score(**test_case_1)
    print(f"Test Case 1 - High Confidence TGE:")
    print(f"  Final Confidence: {confidence:.2%}")
    print(f"  Details: {details}")
    print()

    # Example 2: False positive (espresso machine)
    test_case_2 = {
        'text': 'Best espresso machines for your coffee shop. Great deals on espresso equipment!',
        'title': 'Top Espresso Machines 2024',
        'url': 'https://example.com/espresso-guide',
        'matched_keywords': [],
        'matched_companies': ['Espresso'],
        'company_priorities': {'Espresso': 'LOW'},
        'company_exclusions': {'Espresso': ['coffee', 'espresso machine']},
        'base_confidence': 0.3,
        'source_type': 'news',
        'exclusion_patterns': ['coffee']
    }

    confidence2, details2 = scorer.calculate_comprehensive_score(**test_case_2)
    print(f"Test Case 2 - False Positive:")
    print(f"  Final Confidence: {confidence2:.2%}")
    print(f"  Details: {details2}")

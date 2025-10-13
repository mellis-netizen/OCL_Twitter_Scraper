#!/usr/bin/env python3
"""
Enhanced Context-Aware Scoring System for TGE Detection
Implements multi-layered scoring with source reliability, temporal relevance, and content section weighting
Optimized for maximum accuracy with fuzzy matching, temporal analysis, and false positive rejection
"""

import re
from typing import Dict, Tuple, List, Optional
from datetime import datetime, timedelta
from urllib.parse import urlparse
from difflib import SequenceMatcher
from dateutil import parser as date_parser
import calendar


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

    # Temporal relevance indicators (significantly expanded)
    IMMEDIATE_INDICATORS = [
        'now', 'live', 'today', 'just launched', 'available now', 'starts today',
        'is live', 'has launched', 'now live', 'live now', 'goes live today',
        'starting now', 'currently live', 'active now', 'open now'
    ]  # +20
    NEAR_TERM = [
        'tomorrow', 'this week', 'next week', 'within days', 'in the coming days',
        'later this week', 'early next week', 'by end of week', 'within 48 hours',
        'in 24 hours', 'in two days', 'in three days'
    ]  # +15
    MID_TERM = [
        'this month', 'next month', 'coming soon', 'Q1', 'Q2', 'Q3', 'Q4',
        'january', 'february', 'march', 'april', 'may', 'june', 'july',
        'august', 'september', 'october', 'november', 'december',
        'end of month', 'mid-month', 'early next month', 'late this month'
    ]  # +10
    VAGUE_TIMING = ['soon', 'upcoming', 'planned', 'to be announced', 'tba']  # +5
    PAST_TENSE = [
        'launched', 'went live', 'was announced', 'occurred', 'happened',
        'completed', 'finished', 'concluded', 'ended', 'has ended',
        'was live', 'had launched', 'already launched', 'previously launched'
    ]  # -10

    # False positive indicators (patterns that should NOT be in crypto TGE context)
    FALSE_POSITIVE_PATTERNS = {
        'gaming': ['in-game', 'game token', 'gaming token', 'play-to-earn', 'p2e', 'loot drop', 'nft game'],
        'coffee': ['espresso machine', 'coffee shop', 'barista', 'cafe', 'brewing', 'coffee bean'],
        'physical_goods': ['fabric', 'clothing', 'merchandise', 'physical product', 'shipping'],
        'speculation': ['price prediction', 'technical analysis', 'chart analysis', 'trading signal'],
        'testing': ['test token', 'mock token', 'demo token', 'sandbox test'],
        'non_crypto': ['volcano', 'mountain', 'geographic', 'espresso beans']
    }

    # Patterns that need explicit checking (not just presence)
    CONDITIONAL_FALSE_POSITIVES = {
        'testnet': r'\btestnet\b(?!\s+(to|→|->)\s+mainnet)',  # Only if NOT "testnet to mainnet"
        'devnet': r'\bdevnet\b(?!\s+(to|→|->)\s+mainnet)',
    }

    # Crypto context indicators (must be present for ambiguous terms)
    CRYPTO_CONTEXT = [
        'blockchain', 'crypto', 'cryptocurrency', 'protocol', 'defi', 'web3',
        'mainnet', 'layer 2', 'l2', 'rollup', 'smart contract', 'dapp',
        'token economics', 'tokenomics', 'airdrop', 'claim', 'staking',
        'liquidity', 'trading', 'exchange', 'cex', 'dex', 'wallet'
    ]

    def __init__(self, fuzzy_match_threshold: float = 0.85, confidence_threshold: float = 0.65):
        """
        Initialize enhanced scoring system.

        Args:
            fuzzy_match_threshold: Minimum similarity score for fuzzy company matching (0-1)
            confidence_threshold: Minimum confidence for TGE detection (0-1)
        """
        self.fuzzy_match_threshold = fuzzy_match_threshold
        self.confidence_threshold = confidence_threshold

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

        # Crypto context pattern
        self.crypto_context_pattern = re.compile(
            r'\b(' + '|'.join(re.escape(term) for term in self.CRYPTO_CONTEXT) + r')\b',
            re.IGNORECASE
        )

        # Date patterns for extraction
        self.date_patterns = [
            # Full dates: Jan 15, 2024 or January 15, 2024
            re.compile(r'\b(january|february|march|april|may|june|july|august|september|october|november|december)\s+\d{1,2},?\s*\d{4}\b', re.IGNORECASE),
            # Short dates: 01/15/2024 or 01-15-2024
            re.compile(r'\b\d{1,2}[/-]\d{1,2}[/-]\d{4}\b'),
            # Relative dates with specific times
            re.compile(r'\b(tomorrow|today)\s+at\s+\d{1,2}(:\d{2})?\s*(am|pm|utc|est|pst)?\b', re.IGNORECASE),
            # Quarter mentions: Q1 2024
            re.compile(r'\bQ[1-4]\s+\d{4}\b', re.IGNORECASE),
        ]

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

    def fuzzy_match_company(self, text: str, company_name: str, aliases: List[str] = None) -> Tuple[bool, float, str]:
        """
        Fuzzy match company name with threshold.

        Args:
            text: Text to search in
            company_name: Primary company name
            aliases: List of company aliases

        Returns:
            Tuple of (is_match, similarity_score, matched_term)
        """
        text_lower = text.lower()
        all_names = [company_name] + (aliases or [])

        best_match = None
        best_score = 0.0
        best_term = ""

        for name in all_names:
            name_lower = name.lower()

            # Exact match gets 1.0
            if name_lower in text_lower:
                return True, 1.0, name

            # Check fuzzy match for each word in text
            words = text_lower.split()
            for word in words:
                # Skip very short words
                if len(word) < 3:
                    continue

                similarity = SequenceMatcher(None, name_lower, word).ratio()
                if similarity > best_score:
                    best_score = similarity
                    best_term = name

                # Also check if company name is substring or word is substring
                if name_lower in word or word in name_lower:
                    overlap = min(len(name_lower), len(word)) / max(len(name_lower), len(word))
                    if overlap > best_score:
                        best_score = overlap
                        best_term = name

        is_match = best_score >= self.fuzzy_match_threshold
        return is_match, best_score, best_term if is_match else ""

    def extract_and_analyze_dates(self, text: str) -> Tuple[int, List[Dict]]:
        """
        Extract dates from text and determine if they're future or past.

        Args:
            text: Text to analyze

        Returns:
            Tuple of (score_adjustment, date_info_list)
        """
        score = 0
        dates_found = []
        today = datetime.now()

        for pattern in self.date_patterns:
            matches = pattern.finditer(text)
            for match in matches:
                date_str = match.group(0)
                try:
                    # Try to parse the date
                    parsed_date = date_parser.parse(date_str, fuzzy=True)

                    # Calculate days from now
                    days_diff = (parsed_date - today).days

                    date_info = {
                        'date_str': date_str,
                        'parsed_date': parsed_date.isoformat(),
                        'days_from_now': days_diff
                    }

                    # Score based on how far in the future
                    if -7 <= days_diff <= 0:  # Past week (might be announcement of today's event)
                        score += 5
                        date_info['category'] = 'recent_past'
                    elif 0 < days_diff <= 7:  # Next week
                        score += 25
                        date_info['category'] = 'immediate_future'
                    elif 7 < days_diff <= 30:  # Next month
                        score += 15
                        date_info['category'] = 'near_future'
                    elif 30 < days_diff <= 90:  # Next quarter
                        score += 10
                        date_info['category'] = 'mid_future'
                    elif days_diff > 90:  # Far future
                        score += 5
                        date_info['category'] = 'far_future'
                    else:  # More than a week in the past
                        score -= 15
                        date_info['category'] = 'past'

                    dates_found.append(date_info)

                except (ValueError, OverflowError):
                    # Could not parse date
                    continue

        return score, dates_found

    def detect_false_positives(self, text: str) -> Tuple[int, List[str]]:
        """
        Detect false positive patterns and apply penalties.

        Args:
            text: Text to analyze

        Returns:
            Tuple of (penalty_score, matched_patterns)
        """
        penalty = 0
        matched_patterns = []
        text_lower = text.lower()

        # Check if crypto context is present
        has_crypto_context = bool(self.crypto_context_pattern.search(text))

        # Check conditional patterns first (testnet, devnet)
        for term, pattern in self.CONDITIONAL_FALSE_POSITIVES.items():
            if re.search(pattern, text_lower, re.IGNORECASE):
                matched_patterns.append(f"testing:{term}")
                penalty -= 50  # Hard penalty for standalone testnet/devnet

        # Check standard false positive patterns
        for category, patterns in self.FALSE_POSITIVE_PATTERNS.items():
            for pattern in patterns:
                if pattern.lower() in text_lower:
                    matched_patterns.append(f"{category}:{pattern}")

                    # Apply different penalties based on category and context
                    if category == 'testing':
                        penalty -= 50  # Hard penalty for test tokens
                    elif category == 'speculation':
                        penalty -= 30  # High penalty for speculation
                    elif category in ['gaming', 'coffee', 'physical_goods', 'non_crypto']:
                        if has_crypto_context:
                            penalty -= 10  # Light penalty if crypto context exists
                        else:
                            penalty -= 40  # Heavy penalty without crypto context

        # Additional checks for ambiguous terms (only if no strong crypto context)
        if not has_crypto_context or len(self.crypto_context_pattern.findall(text)) < 2:
            ambiguous_terms = ['token', 'cal', 'espresso']
            for term in ambiguous_terms:
                if term in text_lower:
                    # Check density of crypto terms
                    crypto_matches = len(self.crypto_context_pattern.findall(text))
                    word_count = len(text_lower.split())
                    crypto_density = crypto_matches / max(word_count, 1)

                    if crypto_density < 0.02:  # Less than 2% crypto terms
                        penalty -= 25
                        matched_patterns.append(f"ambiguous:{term}:low_crypto_context")

        return penalty, matched_patterns

    def calculate_keyword_relevance_score(self, matched_keywords: List[str], text: str) -> Tuple[int, Dict]:
        """
        Calculate weighted keyword relevance score based on keyword importance.

        Args:
            matched_keywords: List of matched keywords
            text: Full text for context

        Returns:
            Tuple of (score, keyword_details)
        """
        score = 0
        keyword_details = {
            'high_value': [],
            'medium_value': [],
            'low_value': [],
            'weighted_score': 0
        }

        # Keyword importance tiers based on real TGE announcements
        HIGH_VALUE_KEYWORDS = {
            'tge': 40,
            'token generation event': 45,
            'token generation': 40,
            'airdrop live': 40,
            'claim now': 40,
            'claim portal': 35,
            'token launch': 35,
            'now live': 35,
            'trading live': 35,
            'listing announcement': 35
        }

        MEDIUM_VALUE_KEYWORDS = {
            'airdrop': 25,
            'token claim': 25,
            'token distribution': 25,
            'genesis event': 25,
            'mainnet launch': 30,
            'token sale': 20,
            'public sale': 20,
            'ido': 20,
            'initial dex offering': 20
        }

        LOW_VALUE_KEYWORDS = {
            'token': 10,
            'launch': 10,
            'announcement': 10,
            'coming soon': 5,
            'roadmap': 5
        }

        text_lower = text.lower()

        # Check high-value keywords
        for keyword, points in HIGH_VALUE_KEYWORDS.items():
            if keyword in text_lower:
                score += points
                keyword_details['high_value'].append(keyword)

        # Check medium-value keywords
        for keyword, points in MEDIUM_VALUE_KEYWORDS.items():
            if keyword in text_lower:
                score += points
                keyword_details['medium_value'].append(keyword)

        # Check low-value keywords
        for keyword, points in LOW_VALUE_KEYWORDS.items():
            if keyword in text_lower:
                # Only count if not already counted in higher tiers
                if keyword not in keyword_details['high_value'] and keyword not in keyword_details['medium_value']:
                    score += points
                    keyword_details['low_value'].append(keyword)

        keyword_details['weighted_score'] = score
        return score, keyword_details

    def calibrate_confidence(self, raw_confidence: float, scoring_details: Dict) -> Tuple[float, str]:
        """
        Calibrate confidence score based on signal strength and consistency.

        Args:
            raw_confidence: Raw confidence score (0-1)
            scoring_details: Dictionary with all scoring components

        Returns:
            Tuple of (calibrated_confidence, calibration_reasoning)
        """
        calibrated = raw_confidence
        reasoning = []

        # Strong positive signals boost confidence
        if scoring_details.get('temporal_score', 0) >= 15:
            calibrated += 0.05
            reasoning.append('strong_temporal_signal')

        if scoring_details.get('section_score', 0) >= 20:
            calibrated += 0.05
            reasoning.append('title_or_headline_match')

        if scoring_details.get('source_score', 0) >= 15:
            calibrated += 0.03
            reasoning.append('tier_1_source')

        # Multiple high-value keywords
        keyword_score = scoring_details.get('keyword_weighted_score', 0)
        if keyword_score >= 50:
            calibrated += 0.08
            reasoning.append('multiple_high_value_keywords')

        # Consistency checks - penalize if missing expected components
        has_company = len(scoring_details.get('matched_companies', [])) > 0
        has_keywords = len(scoring_details.get('matched_keywords', [])) > 0
        has_temporal = scoring_details.get('temporal_score', 0) > 0

        # Strong TGEs should have all three
        if calibrated > 0.7:
            if not (has_company and has_keywords and has_temporal):
                calibrated -= 0.15
                reasoning.append('missing_expected_components')

        # Heavy penalty for false positive indicators
        if scoring_details.get('false_positive_penalty', 0) < -30:
            calibrated *= 0.6  # Reduce by 40%
            reasoning.append('strong_false_positive_signals')

        # Ensure confidence is in valid range
        calibrated = max(0.0, min(1.0, calibrated))

        return calibrated, ' | '.join(reasoning) if reasoning else 'no_adjustments'

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
            'keyword_weighted_score': 0,
            'date_analysis_score': 0,
            'false_positive_penalty': 0,
            'matched_companies': matched_companies or [],
            'matched_keywords': matched_keywords or [],
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

        # NEW: Enhanced keyword weighting
        if matched_keywords:
            keyword_score, keyword_details = self.calculate_keyword_relevance_score(matched_keywords, text)
            total_score += keyword_score
            scoring_details['keyword_weighted_score'] = keyword_score
            scoring_details['keyword_details'] = keyword_details
            if keyword_score > 0:
                scoring_details['adjustments'].append(
                    f"keywords:weighted:{keyword_score:+d}|high:{len(keyword_details['high_value'])}|med:{len(keyword_details['medium_value'])}"
                )

        # NEW: Date extraction and analysis
        date_score, dates_found = self.extract_and_analyze_dates(text)
        total_score += date_score
        scoring_details['date_analysis_score'] = date_score
        scoring_details['dates_found'] = dates_found
        if dates_found:
            scoring_details['adjustments'].append(
                f"dates:{len(dates_found)}:{date_score:+d}"
            )

        # NEW: False positive detection
        fp_penalty, fp_patterns = self.detect_false_positives(text)
        total_score += fp_penalty
        scoring_details['false_positive_penalty'] = fp_penalty
        scoring_details['false_positive_patterns'] = fp_patterns
        if fp_patterns:
            scoring_details['adjustments'].append(
                f"false_positives:{len(fp_patterns)}:{fp_penalty}"
            )

        # Apply exclusion penalties (kept for backward compatibility)
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
        raw_confidence = max(0.0, min(1.0, total_score / 100.0))
        scoring_details['raw_confidence'] = raw_confidence
        scoring_details['total_raw_score'] = total_score

        # NEW: Confidence calibration
        final_confidence, calibration_reason = self.calibrate_confidence(raw_confidence, scoring_details)
        scoring_details['final_confidence'] = final_confidence
        scoring_details['calibration_reason'] = calibration_reason
        if calibration_reason != 'no_adjustments':
            scoring_details['adjustments'].append(f"calibration:{calibration_reason}")

        # Apply confidence threshold
        scoring_details['meets_threshold'] = final_confidence >= self.confidence_threshold

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

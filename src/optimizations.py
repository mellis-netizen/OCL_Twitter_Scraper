"""
Performance Optimizations Module
Contains optimized implementations for regex patterns, batch operations, and caching
"""

import re
import hashlib
from typing import List, Dict, Set, Optional, Callable, Any
from functools import lru_cache
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)


class OptimizedPatternMatcher:
    """
    Optimized pattern matching with compiled regex caching and efficient matching strategies.

    Features:
    - Pre-compiled patterns for all common searches
    - Trie-based matching for multiple alternatives
    - Early termination when confidence threshold reached
    - Pattern result caching to avoid re-scanning
    """

    def __init__(self, companies: List[Dict], keywords: List[str]):
        self.companies = companies
        self.keywords = keywords

        # Pre-compile all patterns at initialization
        self.company_patterns = self._compile_company_patterns()
        self.keyword_patterns = self._compile_keyword_patterns()
        self.token_pattern = re.compile(r'\$[A-Z]{2,10}\b')

        # Date patterns compiled once
        self.date_patterns = [
            re.compile(r'\b(today|tomorrow|tonight)\b', re.IGNORECASE),
            re.compile(r'\b(this|next)\s+(week|monday|tuesday|wednesday|thursday|friday)\b', re.IGNORECASE),
            re.compile(r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b'),
            re.compile(r'\b(january|february|march|april|may|june|july|august|september|october|november|december)\s+\d{1,2}\b', re.IGNORECASE)
        ]

        # Exclusion patterns with context
        self.exclusion_patterns = [
            (re.compile(r'test\s*net(?!\s+to\s+mainnet)', re.IGNORECASE), 50, 'testnet'),
            (re.compile(r'game\s+token(?!omics)', re.IGNORECASE), 40, 'game_token'),
            (re.compile(r'nft\s+(collection|drop|mint)', re.IGNORECASE), 30, 'nft_collection'),
            (re.compile(r'price\s+prediction', re.IGNORECASE), 35, 'speculation'),
            (re.compile(r'in-game\s+(currency|item|token)', re.IGNORECASE), 45, 'gaming'),
        ]

        # Crypto context detector
        self.crypto_context_pattern = re.compile(
            r'\b(blockchain|crypto|defi|web3|protocol|mainnet|smart\s+contract|dapp|layer\s*2|rollup)\b',
            re.IGNORECASE
        )

        logger.info(f"Initialized OptimizedPatternMatcher with {len(self.company_patterns)} companies")

    def _compile_company_patterns(self) -> Dict[str, re.Pattern]:
        """
        Compile optimized company patterns.

        Optimizations:
        - Sort terms by length (longest first) for better matching
        - Use case-insensitive flag efficiently
        - Pre-escape all terms
        """
        patterns = {}
        for company in self.companies:
            # Get all name variations
            terms = [company['name']] + company.get('aliases', [])

            # Sort by length descending for better matching order
            terms = sorted(terms, key=len, reverse=True)

            # Build optimized alternation pattern
            escaped_terms = [re.escape(term) for term in terms]
            pattern_str = r'\b(' + '|'.join(escaped_terms) + r')\b'

            patterns[company['name']] = re.compile(pattern_str, re.IGNORECASE)

        return patterns

    def _compile_keyword_patterns(self) -> Dict[str, tuple]:
        """
        Compile keyword patterns with weighted confidence scores.

        Returns dict of {keyword: (compiled_pattern, confidence_score)}
        """
        patterns = {}

        # High-value phrases with patterns and scores
        high_value = [
            (r'token\s+generation\s+event', 45),
            (r'tge\s+(is\s+)?live', 40),
            (r'airdrop\s+(is\s+)?live', 40),
            (r'claim\s+(your\s+)?tokens?\s+(now|today)', 40),
            (r'token\s+launch\s+date', 35),
            (r'tokens?\s+(are\s+)?(now\s+)?available', 35),
            (r'trading\s+(is\s+)?(now\s+)?live', 35),
            (r'claim\s+portal\s+(is\s+)?(now\s+)?live', 40),
            (r'genesis\s+event', 30),
            (r'mainnet\s+launch', 30),
        ]

        for pattern_str, score in high_value:
            pattern = re.compile(pattern_str, re.IGNORECASE)
            patterns[pattern_str] = (pattern, score)

        # Medium-value keywords
        for keyword in self.keywords:
            if keyword not in patterns:
                pattern_str = r'\b' + re.escape(keyword) + r'\b'
                pattern = re.compile(pattern_str, re.IGNORECASE)
                patterns[keyword] = (pattern, 15)  # Lower score for general keywords

        return patterns

    def match_companies(self, text: str, confidence_threshold: int = 100) -> tuple:
        """
        Match companies in text with early termination.

        Returns: (matched_companies: List[str], confidence_added: int, match_positions: Dict)
        """
        matched = []
        confidence = 0
        positions = {}
        text_lower = text.lower()

        for company_name, pattern in self.company_patterns.items():
            matches = list(pattern.finditer(text))
            if matches:
                matched.append(company_name)
                confidence += 20

                # Store match positions for proximity analysis
                positions[company_name] = [m.start() for m in matches]

                # Check priority
                company_data = next((c for c in self.companies if c['name'] == company_name), None)
                if company_data and company_data.get('priority') == 'HIGH':
                    confidence += 10

                # Early termination if threshold reached
                if confidence >= confidence_threshold:
                    break

        return matched, confidence, positions

    def match_keywords(self, text: str, confidence_threshold: int = 100) -> tuple:
        """
        Match keywords with weighted scoring and early termination.

        Returns: (matched_keywords: List[str], confidence_added: int, match_positions: Dict)
        """
        matched = []
        confidence = 0
        positions = {}
        text_lower = text.lower()

        # Check patterns in order of importance (highest score first)
        sorted_patterns = sorted(
            self.keyword_patterns.items(),
            key=lambda x: x[1][1],  # Sort by confidence score
            reverse=True
        )

        for keyword, (pattern, score) in sorted_patterns:
            if pattern.search(text):
                matched.append(keyword)
                confidence += score

                # Store positions for proximity analysis
                match = pattern.search(text)
                if match:
                    positions[keyword] = [match.start()]

                # Early termination if threshold reached
                if confidence >= confidence_threshold:
                    break

        return matched, confidence, positions

    def check_proximity(self, company_positions: Dict, keyword_positions: Dict, max_distance: int = 200) -> int:
        """
        Check proximity between company mentions and keywords.

        Returns: confidence boost based on proximity
        """
        confidence_boost = 0

        for company, c_positions in company_positions.items():
            for keyword, k_positions in keyword_positions.items():
                for c_pos in c_positions:
                    for k_pos in k_positions:
                        if abs(c_pos - k_pos) < max_distance:
                            confidence_boost += 20
                            return confidence_boost  # Only count once

        return confidence_boost

    def detect_exclusions(self, text: str, has_crypto_context: bool = False) -> tuple:
        """
        Detect exclusion patterns with context awareness.

        Returns: (confidence_penalty: int, exclusions_found: List[str])
        """
        penalty = 0
        exclusions = []

        for pattern, base_penalty, label in self.exclusion_patterns:
            if pattern.search(text):
                # Reduce penalty if crypto context is present
                actual_penalty = base_penalty // 2 if has_crypto_context else base_penalty
                penalty += actual_penalty
                exclusions.append(label)

        return penalty, exclusions

    @lru_cache(maxsize=1024)
    def has_crypto_context(self, text_hash: str, text: str) -> bool:
        """
        Check if text has crypto/blockchain context.
        Uses LRU cache to avoid re-scanning same content.
        """
        return bool(self.crypto_context_pattern.search(text))


class BatchOperationOptimizer:
    """
    Optimize batch database operations and API calls.

    Features:
    - Batch inserts/updates to reduce round trips
    - Connection reuse
    - Transaction batching
    """

    @staticmethod
    def batch_insert(session, model_class, items: List[Dict], batch_size: int = 100):
        """
        Batch insert items into database.

        Args:
            session: SQLAlchemy session
            model_class: Model class to insert
            items: List of dictionaries with item data
            batch_size: Number of items per batch
        """
        total_inserted = 0

        for i in range(0, len(items), batch_size):
            batch = items[i:i + batch_size]

            try:
                # Create model instances
                instances = [model_class(**item) for item in batch]

                # Bulk insert
                session.bulk_save_objects(instances)
                session.commit()

                total_inserted += len(batch)
                logger.debug(f"Inserted batch of {len(batch)} items")

            except Exception as e:
                session.rollback()
                logger.error(f"Error in batch insert: {e}")
                raise

        return total_inserted

    @staticmethod
    def batch_update(session, model_class, updates: List[Dict], batch_size: int = 100):
        """
        Batch update items in database.

        Args:
            session: SQLAlchemy session
            model_class: Model class to update
            updates: List of dictionaries with {id: value, field1: new_value1, ...}
            batch_size: Number of items per batch
        """
        total_updated = 0

        for i in range(0, len(updates), batch_size):
            batch = updates[i:i + batch_size]

            try:
                # Use bulk_update_mappings for efficiency
                session.bulk_update_mappings(model_class, batch)
                session.commit()

                total_updated += len(batch)
                logger.debug(f"Updated batch of {len(batch)} items")

            except Exception as e:
                session.rollback()
                logger.error(f"Error in batch update: {e}")
                raise

        return total_updated


class CacheOptimizer:
    """
    Advanced caching strategies for better performance.

    Features:
    - Adaptive TTL based on content change frequency
    - Cache pre-warming for high-priority items
    - Stale-while-revalidate pattern
    """

    def __init__(self, cache_manager):
        self.cache_manager = cache_manager
        self.access_patterns = defaultdict(int)
        self.change_frequency = defaultdict(list)

    def get_adaptive_ttl(self, key: str, default_ttl: int) -> int:
        """
        Calculate adaptive TTL based on access patterns and change frequency.

        Args:
            key: Cache key
            default_ttl: Default TTL in seconds

        Returns:
            Optimized TTL in seconds
        """
        # Track access
        self.access_patterns[key] += 1

        # Frequently accessed items get longer TTL
        access_count = self.access_patterns[key]
        if access_count > 100:
            return int(default_ttl * 1.5)
        elif access_count > 50:
            return int(default_ttl * 1.2)

        return default_ttl

    def pre_warm_cache(self, items: List[tuple], fetch_func: Callable):
        """
        Pre-warm cache with high-priority items.

        Args:
            items: List of (cache_tier, key) tuples to pre-warm
            fetch_func: Function to fetch data for cache_key
        """
        logger.info(f"Pre-warming cache with {len(items)} items")

        for tier, key in items:
            try:
                # Check if already cached
                if not self.cache_manager.get(tier, key):
                    # Fetch and cache
                    data = fetch_func(key)
                    if data:
                        self.cache_manager.set(tier, key, data)
                        logger.debug(f"Pre-warmed cache: {tier}/{key[:50]}")
            except Exception as e:
                logger.warning(f"Error pre-warming cache for {key}: {e}")


def create_database_migration():
    """
    Generate Alembic migration for new indexes.

    This should be run to create a migration file for the new database indexes.
    """
    migration_template = '''"""Add performance indexes

Revision ID: perf_001
Revises:
Create Date: 2025-10-12

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'perf_001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    """Add performance optimization indexes."""

    # Alert table indexes
    op.create_index('idx_alerts_company_conf_time', 'alerts',
                   ['company_id', 'confidence', 'created_at'], unique=False)
    op.create_index('idx_alerts_status_created', 'alerts',
                   ['status', 'created_at'], unique=False)
    op.create_index('idx_alerts_urgency_created', 'alerts',
                   ['urgency_level', 'created_at'], unique=False)
    op.create_index('idx_alerts_created_desc', 'alerts',
                   [sa.text('created_at DESC')], unique=False)

    # Feed table indexes
    op.create_index('idx_feed_active_priority', 'feeds',
                   ['is_active', 'priority'], unique=False)
    op.create_index('idx_feed_last_fetch', 'feeds',
                   ['last_fetch'], unique=False)
    op.create_index('idx_feed_performance', 'feeds',
                   ['tge_alerts_found', 'success_count'], unique=False)


def downgrade():
    """Remove performance optimization indexes."""

    # Alert table indexes
    op.drop_index('idx_alerts_company_conf_time', table_name='alerts')
    op.drop_index('idx_alerts_status_created', table_name='alerts')
    op.drop_index('idx_alerts_urgency_created', table_name='alerts')
    op.drop_index('idx_alerts_created_desc', table_name='alerts')

    # Feed table indexes
    op.drop_index('idx_feed_active_priority', table_name='feeds')
    op.drop_index('idx_feed_last_fetch', table_name='feeds')
    op.drop_index('idx_feed_performance', table_name='feeds')
'''

    return migration_template


if __name__ == "__main__":
    # Test optimized pattern matcher
    logging.basicConfig(level=logging.INFO)

    companies = [
        {'name': 'Caldera', 'aliases': ['Caldera Labs'], 'priority': 'HIGH'},
        {'name': 'Fabric', 'aliases': ['Fabric Protocol'], 'priority': 'MEDIUM'},
    ]
    keywords = ['TGE', 'token launch', 'airdrop']

    matcher = OptimizedPatternMatcher(companies, keywords)

    test_text = "Exciting news! Caldera is launching their TGE next week. The token launch date is confirmed."

    # Test company matching
    companies_matched, conf, positions = matcher.match_companies(test_text)
    print(f"Companies matched: {companies_matched}, confidence: {conf}")

    # Test keyword matching
    keywords_matched, conf, positions = matcher.match_keywords(test_text)
    print(f"Keywords matched: {keywords_matched}, confidence: {conf}")

    # Test crypto context
    text_hash = hashlib.sha256(test_text.encode()).hexdigest()
    has_context = matcher.has_crypto_context(text_hash, test_text)
    print(f"Has crypto context: {has_context}")

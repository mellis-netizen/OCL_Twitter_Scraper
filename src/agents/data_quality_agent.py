"""
Data Quality Agent
Handles deduplication, validation, and data quality enforcement
"""

import hashlib
import re
from typing import Dict, Any, List, Set, Tuple
from datetime import datetime, timedelta
from difflib import SequenceMatcher

from src.agents.base_agent import BaseAgent


class DataQualityAgent(BaseAgent):
    """
    Agent specialized in data quality, deduplication, and validation
    """

    def __init__(self, agent_id: str, config: Dict[str, Any]):
        super().__init__(agent_id, "data_quality", config)

        # Deduplication parameters
        self.similarity_threshold = config.get('similarity_threshold', 0.85)
        self.url_cache: Set[str] = set()
        self.content_hashes: Set[str] = set()
        self.fuzzy_matches: Dict[str, List[str]] = {}

        # Quality thresholds
        self.min_content_length = config.get('min_content_length', 100)
        self.min_confidence = config.get('min_confidence', 0.3)
        self.max_age_days = config.get('max_age_days', 7)

    async def _do_initialize(self):
        """Initialize data quality agent"""
        self.logger.info("Data quality agent initialized")

        # Try to restore cache from memory
        cache_data = await self.retrieve_memory('dedup_cache', 'cache')
        if cache_data:
            self.url_cache = set(cache_data.get('urls', []))
            self.content_hashes = set(cache_data.get('hashes', []))
            self.logger.info(f"Restored {len(self.url_cache)} URLs and {len(self.content_hashes)} hashes from cache")

        await self.store_memory('initialized', {
            'timestamp': datetime.now().isoformat(),
            'similarity_threshold': self.similarity_threshold,
            'min_content_length': self.min_content_length
        }, 'initialization')

    async def _execute_task_impl(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Execute data quality task"""
        task_type = task.get('type', 'deduplicate')

        if task_type == 'deduplicate':
            return await self._deduplicate_items(task)
        elif task_type == 'validate':
            return await self._validate_items(task)
        elif task_type == 'merge':
            return await self._merge_duplicate_items(task)
        elif task_type == 'clean_cache':
            return await self._clean_cache(task)
        else:
            raise ValueError(f"Unknown task type: {task_type}")

    async def _deduplicate_items(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Deduplicate a list of items"""
        items = task.get('items', [])
        dedup_strategy = task.get('strategy', 'url_and_content')

        unique_items = []
        duplicates = []
        duplicate_reasons = []

        for item in items:
            is_duplicate, reason = await self._check_duplicate(item, dedup_strategy)

            if is_duplicate:
                duplicates.append(item)
                duplicate_reasons.append(reason)
            else:
                unique_items.append(item)
                await self._add_to_cache(item)

        # Store deduplication results
        await self.store_memory(f'dedup_{int(datetime.now().timestamp())}', {
            'original_count': len(items),
            'unique_count': len(unique_items),
            'duplicate_count': len(duplicates),
            'timestamp': datetime.now().isoformat()
        }, 'dedup_results')

        # Update metrics
        await self.update_metrics({
            'total_processed': self.state['metrics'].get('total_processed', 0) + len(items),
            'duplicates_found': self.state['metrics'].get('duplicates_found', 0) + len(duplicates),
            'dedup_rate': len(duplicates) / len(items) if items else 0
        })

        # Save cache periodically
        await self._save_cache()

        return {
            'unique_items': unique_items,
            'duplicates': duplicates,
            'duplicate_reasons': duplicate_reasons,
            'stats': {
                'original_count': len(items),
                'unique_count': len(unique_items),
                'duplicate_count': len(duplicates),
                'dedup_rate': len(duplicates) / len(items) if items else 0
            }
        }

    async def _validate_items(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Validate items against quality criteria"""
        items = task.get('items', [])

        valid_items = []
        invalid_items = []
        validation_issues = []

        for item in items:
            is_valid, issues = self._validate_item(item)

            if is_valid:
                valid_items.append(item)
            else:
                invalid_items.append(item)
                validation_issues.append(issues)

        # Store validation results
        await self.store_memory(f'validation_{int(datetime.now().timestamp())}', {
            'total_items': len(items),
            'valid_count': len(valid_items),
            'invalid_count': len(invalid_items),
            'timestamp': datetime.now().isoformat()
        }, 'validation_results')

        # Update metrics
        await self.update_metrics({
            'items_validated': self.state['metrics'].get('items_validated', 0) + len(items),
            'validation_failures': self.state['metrics'].get('validation_failures', 0) + len(invalid_items)
        })

        return {
            'valid_items': valid_items,
            'invalid_items': invalid_items,
            'validation_issues': validation_issues,
            'stats': {
                'total_items': len(items),
                'valid_count': len(valid_items),
                'invalid_count': len(invalid_items),
                'pass_rate': len(valid_items) / len(items) if items else 0
            }
        }

    async def _merge_duplicate_items(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Merge duplicate items, keeping the best version"""
        items = task.get('items', [])

        # Group similar items
        groups = self._group_similar_items(items)

        merged_items = []
        for group in groups:
            if len(group) == 1:
                merged_items.append(group[0])
            else:
                # Merge multiple items, keeping best fields
                merged = self._merge_group(group)
                merged_items.append(merged)

        return {
            'merged_items': merged_items,
            'original_count': len(items),
            'merged_count': len(merged_items),
            'reduction': len(items) - len(merged_items)
        }

    async def _clean_cache(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Clean up old cache entries"""
        max_age_days = task.get('max_age_days', self.max_age_days)

        original_url_count = len(self.url_cache)
        original_hash_count = len(self.content_hashes)

        # For simplicity, clear fuzzy matches older than threshold
        # In production, you'd want to track timestamps for each entry
        old_fuzzy_count = len(self.fuzzy_matches)
        self.fuzzy_matches = {}

        await self._save_cache()

        return {
            'urls_before': original_url_count,
            'hashes_before': original_hash_count,
            'fuzzy_matches_cleared': old_fuzzy_count,
            'timestamp': datetime.now().isoformat()
        }

    async def _check_duplicate(self, item: Dict[str, Any], strategy: str) -> Tuple[bool, str]:
        """Check if item is a duplicate"""

        # URL-based deduplication
        if strategy in ['url', 'url_and_content']:
            url = item.get('url', '')
            if url and url in self.url_cache:
                return True, 'duplicate_url'

        # Content hash deduplication
        if strategy in ['content', 'url_and_content']:
            content = item.get('content', '') + item.get('title', '')
            content_hash = hashlib.sha256(content.encode()).hexdigest()

            if content_hash in self.content_hashes:
                return True, 'duplicate_content_hash'

        # Fuzzy content matching
        if strategy in ['fuzzy', 'url_and_content']:
            content = item.get('content', '') + item.get('title', '')
            if content:
                for existing_hash, existing_content in self.fuzzy_matches.items():
                    similarity = self._calculate_similarity(content, existing_content[0])
                    if similarity >= self.similarity_threshold:
                        return True, f'fuzzy_match_{similarity:.2f}'

        return False, 'unique'

    async def _add_to_cache(self, item: Dict[str, Any]):
        """Add item to deduplication cache"""
        url = item.get('url', '')
        if url:
            self.url_cache.add(url)

        content = item.get('content', '') + item.get('title', '')
        if content:
            content_hash = hashlib.sha256(content.encode()).hexdigest()
            self.content_hashes.add(content_hash)
            self.fuzzy_matches[content_hash] = [content, datetime.now().isoformat()]

    async def _save_cache(self):
        """Save deduplication cache to memory"""
        cache_data = {
            'urls': list(self.url_cache),
            'hashes': list(self.content_hashes),
            'timestamp': datetime.now().isoformat()
        }

        await self.store_memory('dedup_cache', cache_data, 'cache')

    def _validate_item(self, item: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate item against quality criteria"""
        issues = []

        # Check required fields
        if not item.get('title'):
            issues.append('missing_title')

        if not item.get('content'):
            issues.append('missing_content')

        # Check content length
        content = item.get('content', '')
        if len(content) < self.min_content_length:
            issues.append(f'content_too_short_{len(content)}_chars')

        # Check confidence if present
        confidence = item.get('confidence', 1.0)
        if confidence < self.min_confidence:
            issues.append(f'low_confidence_{confidence:.2f}')

        # Check age if timestamp present
        published = item.get('published')
        if published:
            try:
                pub_date = datetime.fromisoformat(str(published))
                age_days = (datetime.now() - pub_date).days
                if age_days > self.max_age_days:
                    issues.append(f'too_old_{age_days}_days')
            except:
                issues.append('invalid_timestamp')

        # Check for spam patterns
        if self._is_spam(item):
            issues.append('spam_detected')

        return len(issues) == 0, issues

    def _is_spam(self, item: Dict[str, Any]) -> bool:
        """Detect spam patterns"""
        content = (item.get('content', '') + item.get('title', '')).lower()

        spam_patterns = [
            r'click here',
            r'buy now',
            r'limited time offer',
            r'guaranteed profit',
            r'100x gains',
            r'secret method'
        ]

        for pattern in spam_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                return True

        return False

    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """Calculate similarity between two texts"""
        return SequenceMatcher(None, text1.lower(), text2.lower()).ratio()

    def _group_similar_items(self, items: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
        """Group similar items together"""
        groups = []
        used_indices = set()

        for i, item1 in enumerate(items):
            if i in used_indices:
                continue

            group = [item1]
            used_indices.add(i)

            content1 = item1.get('content', '') + item1.get('title', '')

            for j, item2 in enumerate(items[i + 1:], start=i + 1):
                if j in used_indices:
                    continue

                content2 = item2.get('content', '') + item2.get('title', '')
                similarity = self._calculate_similarity(content1, content2)

                if similarity >= self.similarity_threshold:
                    group.append(item2)
                    used_indices.add(j)

            groups.append(group)

        return groups

    def _merge_group(self, group: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Merge a group of similar items, keeping best fields"""
        # Start with first item
        merged = group[0].copy()

        # Get longest content
        longest_content = max(group, key=lambda x: len(x.get('content', '')))
        merged['content'] = longest_content.get('content', '')

        # Get highest confidence
        if any('confidence' in item for item in group):
            highest_conf = max((item.get('confidence', 0) for item in group))
            merged['confidence'] = highest_conf

        # Collect all sources
        sources = []
        for item in group:
            source = item.get('source', '')
            if source and source not in sources:
                sources.append(source)
        merged['sources'] = sources

        # Add merge metadata
        merged['merged_from_count'] = len(group)
        merged['merged_at'] = datetime.now().isoformat()

        return merged

    async def _do_shutdown(self):
        """Clean up data quality agent"""
        self.logger.info("Shutting down data quality agent")

        # Save final cache state
        await self._save_cache()

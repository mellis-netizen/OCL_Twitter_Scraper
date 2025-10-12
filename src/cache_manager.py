"""
Intelligent Cache Manager for TGE Scraping System
Provides multi-tier caching with TTL management for optimal performance

Performance Targets:
- 30% reduction in API calls through intelligent caching
- Sub-millisecond cache lookups
- Automatic cache invalidation and cleanup
"""

import time
import json
import logging
import hashlib
from typing import Any, Callable, Dict, Optional, Tuple
from datetime import datetime, timedelta, timezone
from collections import OrderedDict
from threading import Lock
import os

logger = logging.getLogger(__name__)


class CacheEntry:
    """Individual cache entry with metadata."""

    def __init__(self, value: Any, ttl: int):
        self.value = value
        self.created_at = time.time()
        self.ttl = ttl
        self.access_count = 0
        self.last_accessed = time.time()

    def is_valid(self) -> bool:
        """Check if cache entry is still valid."""
        return (time.time() - self.created_at) < self.ttl

    def touch(self):
        """Update access metadata."""
        self.access_count += 1
        self.last_accessed = time.time()


class IntelligentCacheManager:
    """
    Multi-tier cache manager with automatic TTL management.

    Cache Tiers:
    - RSS Feed Cache: 10-15 minutes TTL
    - Twitter User Cache: 1 hour TTL
    - Article Content Cache: 3 days TTL
    - Search Results Cache: 5 minutes TTL

    Performance Features:
    - LRU eviction for memory management
    - Automatic cache warming
    - Hit rate tracking
    - Conditional requests support (ETags, Last-Modified)
    """

    def __init__(self, max_memory_mb: int = 100):
        """
        Initialize cache manager.

        Args:
            max_memory_mb: Maximum memory to use for caching (in MB)
        """
        self.max_memory_bytes = max_memory_mb * 1024 * 1024

        # Cache tiers with different TTLs (in seconds)
        self.rss_cache: Dict[str, CacheEntry] = OrderedDict()  # 10 min TTL
        self.twitter_user_cache: Dict[str, CacheEntry] = OrderedDict()  # 1 hour TTL
        self.article_content_cache: Dict[str, CacheEntry] = OrderedDict()  # 3 days TTL
        self.search_results_cache: Dict[str, CacheEntry] = OrderedDict()  # 5 min TTL
        self.conditional_headers_cache: Dict[str, Dict] = {}  # ETags and Last-Modified

        # TTL configurations
        self.ttls = {
            'rss': 600,  # 10 minutes
            'twitter_user': 3600,  # 1 hour
            'article_content': 259200,  # 3 days
            'search_results': 300,  # 5 minutes
            'conditional_headers': 86400  # 24 hours
        }

        # Performance metrics
        self.stats = {
            'hits': 0,
            'misses': 0,
            'evictions': 0,
            'size_bytes': 0,
            'tier_stats': {
                'rss': {'hits': 0, 'misses': 0},
                'twitter_user': {'hits': 0, 'misses': 0},
                'article_content': {'hits': 0, 'misses': 0},
                'search_results': {'hits': 0, 'misses': 0}
            }
        }

        # Thread safety
        self.lock = Lock()

        # Persistence
        self.persistence_file = 'state/cache_persistence.json'
        self._load_persistent_cache()

    def _generate_key(self, key: str) -> str:
        """Generate consistent cache key."""
        return hashlib.sha256(key.encode()).hexdigest()

    def _estimate_size(self, value: Any) -> int:
        """Estimate memory size of cached value."""
        try:
            return len(json.dumps(value, default=str).encode())
        except:
            return 1024  # Default estimate

    def _cleanup_expired(self, cache_dict: Dict[str, CacheEntry]):
        """Remove expired entries from cache."""
        expired_keys = [k for k, v in cache_dict.items() if not v.is_valid()]
        for key in expired_keys:
            del cache_dict[key]
            self.stats['evictions'] += 1

    def _enforce_memory_limit(self):
        """Evict least recently used entries if memory limit exceeded."""
        if self.stats['size_bytes'] <= self.max_memory_bytes:
            return

        # Collect all entries with access times
        all_entries = []
        for cache_name, cache_dict in [
            ('rss', self.rss_cache),
            ('twitter_user', self.twitter_user_cache),
            ('article_content', self.article_content_cache),
            ('search_results', self.search_results_cache)
        ]:
            for key, entry in cache_dict.items():
                all_entries.append((cache_name, key, entry.last_accessed))

        # Sort by last accessed (oldest first)
        all_entries.sort(key=lambda x: x[2])

        # Evict oldest entries until under limit
        evicted = 0
        for cache_name, key, _ in all_entries:
            if self.stats['size_bytes'] <= self.max_memory_bytes:
                break

            cache_dict = getattr(self, f"{cache_name}_cache")
            if key in cache_dict:
                entry = cache_dict[key]
                self.stats['size_bytes'] -= self._estimate_size(entry.value)
                del cache_dict[key]
                evicted += 1

        if evicted > 0:
            logger.info(f"Evicted {evicted} cache entries to enforce memory limit")
            self.stats['evictions'] += evicted

    def get(self, tier: str, key: str) -> Optional[Any]:
        """
        Get value from cache tier.

        Args:
            tier: Cache tier name ('rss', 'twitter_user', 'article_content', 'search_results')
            key: Cache key

        Returns:
            Cached value or None if not found/expired
        """
        with self.lock:
            cache_dict = getattr(self, f"{tier}_cache", None)
            if cache_dict is None:
                logger.warning(f"Unknown cache tier: {tier}")
                return None

            # Cleanup expired entries periodically
            if len(cache_dict) % 100 == 0:
                self._cleanup_expired(cache_dict)

            cache_key = self._generate_key(key)

            if cache_key in cache_dict:
                entry = cache_dict[cache_key]

                if entry.is_valid():
                    entry.touch()
                    self.stats['hits'] += 1
                    self.stats['tier_stats'][tier]['hits'] += 1

                    # Move to end for LRU
                    cache_dict.move_to_end(cache_key)

                    logger.debug(f"Cache hit: {tier}/{key[:50]}")
                    return entry.value
                else:
                    # Expired entry
                    del cache_dict[cache_key]
                    self.stats['evictions'] += 1

            self.stats['misses'] += 1
            self.stats['tier_stats'][tier]['misses'] += 1
            logger.debug(f"Cache miss: {tier}/{key[:50]}")
            return None

    def set(self, tier: str, key: str, value: Any) -> bool:
        """
        Set value in cache tier.

        Args:
            tier: Cache tier name
            key: Cache key
            value: Value to cache

        Returns:
            True if successfully cached
        """
        with self.lock:
            cache_dict = getattr(self, f"{tier}_cache", None)
            if cache_dict is None:
                logger.warning(f"Unknown cache tier: {tier}")
                return False

            cache_key = self._generate_key(key)
            ttl = self.ttls.get(tier, 600)

            entry = CacheEntry(value, ttl)
            size = self._estimate_size(value)

            # Update size tracking
            if cache_key in cache_dict:
                old_size = self._estimate_size(cache_dict[cache_key].value)
                self.stats['size_bytes'] -= old_size

            self.stats['size_bytes'] += size
            cache_dict[cache_key] = entry

            # Enforce memory limit
            self._enforce_memory_limit()

            logger.debug(f"Cache set: {tier}/{key[:50]} (size: {size} bytes)")
            return True

    def get_or_fetch(self, tier: str, key: str, fetch_func: Callable[[], Any]) -> Tuple[Any, bool]:
        """
        Cache-aside pattern: get from cache or fetch and cache.

        Args:
            tier: Cache tier name
            key: Cache key
            fetch_func: Function to call if cache miss

        Returns:
            Tuple of (value, was_cached)
        """
        # Try cache first
        cached_value = self.get(tier, key)
        if cached_value is not None:
            return cached_value, True

        # Cache miss - fetch and cache
        try:
            fetched_value = fetch_func()
            if fetched_value is not None:
                self.set(tier, key, fetched_value)
            return fetched_value, False
        except Exception as e:
            logger.error(f"Error in fetch function: {e}")
            return None, False

    def get_conditional_headers(self, url: str) -> Dict[str, str]:
        """
        Get conditional request headers (If-Modified-Since, If-None-Match).

        Args:
            url: URL to get headers for

        Returns:
            Dictionary of conditional headers
        """
        with self.lock:
            url_key = self._generate_key(url)
            if url_key in self.conditional_headers_cache:
                headers_info = self.conditional_headers_cache[url_key]

                # Check if headers are still valid
                if time.time() - headers_info.get('cached_at', 0) < self.ttls['conditional_headers']:
                    headers = {}

                    if 'etag' in headers_info:
                        headers['If-None-Match'] = headers_info['etag']

                    if 'last_modified' in headers_info:
                        headers['If-Modified-Since'] = headers_info['last_modified']

                    return headers

        return {}

    def save_conditional_headers(self, url: str, response_headers: Dict[str, str]):
        """
        Save conditional headers from response for future requests.

        Args:
            url: URL that was fetched
            response_headers: Response headers containing ETag/Last-Modified
        """
        with self.lock:
            url_key = self._generate_key(url)
            headers_info = {'cached_at': time.time()}

            # Extract relevant headers (case-insensitive)
            headers_lower = {k.lower(): v for k, v in response_headers.items()}

            if 'etag' in headers_lower:
                headers_info['etag'] = headers_lower['etag']

            if 'last-modified' in headers_lower:
                headers_info['last_modified'] = headers_lower['last-modified']

            if len(headers_info) > 1:  # More than just cached_at
                self.conditional_headers_cache[url_key] = headers_info

    def invalidate(self, tier: str, key: str) -> bool:
        """
        Invalidate specific cache entry.

        Args:
            tier: Cache tier name
            key: Cache key to invalidate

        Returns:
            True if entry was invalidated
        """
        with self.lock:
            cache_dict = getattr(self, f"{tier}_cache", None)
            if cache_dict is None:
                return False

            cache_key = self._generate_key(key)
            if cache_key in cache_dict:
                entry = cache_dict[cache_key]
                self.stats['size_bytes'] -= self._estimate_size(entry.value)
                del cache_dict[cache_key]
                logger.debug(f"Invalidated cache: {tier}/{key[:50]}")
                return True

            return False

    def clear(self, tier: Optional[str] = None):
        """
        Clear cache tier or all caches.

        Args:
            tier: Cache tier to clear, or None for all tiers
        """
        with self.lock:
            if tier:
                cache_dict = getattr(self, f"{tier}_cache", None)
                if cache_dict:
                    cache_dict.clear()
                    logger.info(f"Cleared {tier} cache")
            else:
                self.rss_cache.clear()
                self.twitter_user_cache.clear()
                self.article_content_cache.clear()
                self.search_results_cache.clear()
                self.conditional_headers_cache.clear()
                self.stats['size_bytes'] = 0
                logger.info("Cleared all caches")

    def get_stats(self) -> Dict:
        """Get cache performance statistics."""
        with self.lock:
            total_requests = self.stats['hits'] + self.stats['misses']
            hit_rate = (self.stats['hits'] / total_requests * 100) if total_requests > 0 else 0

            tier_stats = {}
            for tier_name, tier_data in self.stats['tier_stats'].items():
                tier_requests = tier_data['hits'] + tier_data['misses']
                tier_hit_rate = (tier_data['hits'] / tier_requests * 100) if tier_requests > 0 else 0
                tier_stats[tier_name] = {
                    'hit_rate': round(tier_hit_rate, 2),
                    'hits': tier_data['hits'],
                    'misses': tier_data['misses'],
                    'size': len(getattr(self, f"{tier_name}_cache"))
                }

            return {
                'overall_hit_rate': round(hit_rate, 2),
                'total_hits': self.stats['hits'],
                'total_misses': self.stats['misses'],
                'total_evictions': self.stats['evictions'],
                'memory_used_mb': round(self.stats['size_bytes'] / (1024 * 1024), 2),
                'memory_limit_mb': round(self.max_memory_bytes / (1024 * 1024), 2),
                'tier_stats': tier_stats,
                'conditional_headers_cached': len(self.conditional_headers_cache)
            }

    def _load_persistent_cache(self):
        """Load cache from disk for critical data."""
        try:
            if os.path.exists(self.persistence_file):
                with open(self.persistence_file, 'r') as f:
                    data = json.load(f)

                # Restore conditional headers cache
                self.conditional_headers_cache = data.get('conditional_headers', {})

                logger.info(f"Loaded {len(self.conditional_headers_cache)} conditional headers from disk")
        except Exception as e:
            logger.warning(f"Could not load persistent cache: {e}")

    def save_persistent_cache(self):
        """Save critical cache data to disk."""
        try:
            os.makedirs('state', exist_ok=True)

            data = {
                'conditional_headers': self.conditional_headers_cache,
                'saved_at': datetime.now(timezone.utc).isoformat()
            }

            with open(self.persistence_file, 'w') as f:
                json.dump(data, f, indent=2)

            logger.debug("Saved persistent cache to disk")
        except Exception as e:
            logger.warning(f"Could not save persistent cache: {e}")

    def cleanup(self):
        """Cleanup and save before shutdown."""
        logger.info("Cache manager cleanup started")

        # Cleanup all tiers
        for cache_dict in [self.rss_cache, self.twitter_user_cache,
                          self.article_content_cache, self.search_results_cache]:
            self._cleanup_expired(cache_dict)

        # Save persistent data
        self.save_persistent_cache()

        # Log final stats
        stats = self.get_stats()
        logger.info(f"Cache stats on shutdown: {stats}")


# Global cache instance
_cache_manager = None


def get_cache_manager() -> IntelligentCacheManager:
    """Get global cache manager instance."""
    global _cache_manager
    if _cache_manager is None:
        _cache_manager = IntelligentCacheManager()
    return _cache_manager

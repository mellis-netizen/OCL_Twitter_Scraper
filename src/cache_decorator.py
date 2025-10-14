"""
Performance caching decorator for API endpoints
Implements Redis-based caching with configurable TTL
"""

import json
import hashlib
import logging
from functools import wraps
from typing import Optional, Callable, Any
from datetime import datetime, timezone

from .database import CacheManager

logger = logging.getLogger(__name__)


class APICache:
    """API response caching with Redis backend"""

    def __init__(self):
        self.cache = CacheManager()
        self.hit_count = 0
        self.miss_count = 0

    def _generate_cache_key(self, prefix: str, *args, **kwargs) -> str:
        """Generate unique cache key from function arguments"""
        # Create a stable representation of args and kwargs
        key_data = {
            'args': [str(arg) for arg in args],
            'kwargs': {k: str(v) for k, v in sorted(kwargs.items())}
        }

        key_string = json.dumps(key_data, sort_keys=True)
        key_hash = hashlib.md5(key_string.encode()).hexdigest()

        return f"{prefix}:{key_hash}"

    def cache_response(
        self,
        ttl: int = 300,
        key_prefix: Optional[str] = None,
        skip_cache: Optional[Callable[[Any], bool]] = None
    ):
        """
        Decorator to cache API responses

        Args:
            ttl: Time to live in seconds (default: 300 = 5 minutes)
            key_prefix: Optional prefix for cache key (default: function name)
            skip_cache: Optional function to determine if caching should be skipped

        Example:
            @api_cache.cache_response(ttl=60)
            async def get_alerts(filter: AlertFilter):
                return query_alerts(filter)
        """
        def decorator(func):
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                # Determine cache key prefix
                prefix = key_prefix or f"api:{func.__name__}"
                cache_key = self._generate_cache_key(prefix, *args, **kwargs)

                # Check if we should skip cache
                if skip_cache and skip_cache(*args, **kwargs):
                    logger.debug(f"Skipping cache for {cache_key}")
                    return await func(*args, **kwargs)

                # Try to get from cache
                cached_value = self.cache.get(cache_key)

                if cached_value:
                    self.hit_count += 1
                    logger.debug(f"Cache HIT: {cache_key}")
                    try:
                        return json.loads(cached_value)
                    except json.JSONDecodeError:
                        logger.warning(f"Failed to decode cached value for {cache_key}")

                # Cache miss - execute function
                self.miss_count += 1
                logger.debug(f"Cache MISS: {cache_key}")

                result = await func(*args, **kwargs)

                # Store in cache
                try:
                    cache_value = json.dumps(result, default=str)
                    self.cache.set(cache_key, cache_value, ttl)
                    logger.debug(f"Cached result for {cache_key} (TTL: {ttl}s)")
                except (TypeError, json.JSONEncodeError) as e:
                    logger.warning(f"Failed to cache result for {cache_key}: {e}")

                return result

            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                # Determine cache key prefix
                prefix = key_prefix or f"api:{func.__name__}"
                cache_key = self._generate_cache_key(prefix, *args, **kwargs)

                # Check if we should skip cache
                if skip_cache and skip_cache(*args, **kwargs):
                    logger.debug(f"Skipping cache for {cache_key}")
                    return func(*args, **kwargs)

                # Try to get from cache
                cached_value = self.cache.get(cache_key)

                if cached_value:
                    self.hit_count += 1
                    logger.debug(f"Cache HIT: {cache_key}")
                    try:
                        return json.loads(cached_value)
                    except json.JSONDecodeError:
                        logger.warning(f"Failed to decode cached value for {cache_key}")

                # Cache miss - execute function
                self.miss_count += 1
                logger.debug(f"Cache MISS: {cache_key}")

                result = func(*args, **kwargs)

                # Store in cache
                try:
                    cache_value = json.dumps(result, default=str)
                    self.cache.set(cache_key, cache_value, ttl)
                    logger.debug(f"Cached result for {cache_key} (TTL: {ttl}s)")
                except (TypeError, json.JSONEncodeError) as e:
                    logger.warning(f"Failed to cache result for {cache_key}: {e}")

                return result

            # Return appropriate wrapper based on function type
            import asyncio
            if asyncio.iscoroutinefunction(func):
                return async_wrapper
            else:
                return sync_wrapper

        return decorator

    def invalidate_pattern(self, pattern: str) -> int:
        """
        Invalidate all cache keys matching pattern

        Args:
            pattern: Redis pattern (e.g., "api:alerts:*")

        Returns:
            Number of keys invalidated
        """
        try:
            keys = self.cache.get_keys(pattern)
            count = 0
            for key in keys:
                self.cache.delete(key)
                count += 1

            logger.info(f"Invalidated {count} cache keys matching {pattern}")
            return count

        except Exception as e:
            logger.error(f"Error invalidating cache pattern {pattern}: {e}")
            return 0

    def get_stats(self) -> dict:
        """Get cache performance statistics"""
        total_requests = self.hit_count + self.miss_count
        hit_rate = (self.hit_count / total_requests * 100) if total_requests > 0 else 0

        return {
            'hit_count': self.hit_count,
            'miss_count': self.miss_count,
            'total_requests': total_requests,
            'hit_rate_percent': round(hit_rate, 2)
        }

    def reset_stats(self):
        """Reset cache statistics"""
        self.hit_count = 0
        self.miss_count = 0


# Global cache instance
api_cache = APICache()


# Convenience decorator
def cache_response(ttl: int = 300, key_prefix: Optional[str] = None):
    """
    Convenience decorator for caching API responses

    Example:
        @cache_response(ttl=60)
        async def get_data():
            return expensive_query()
    """
    return api_cache.cache_response(ttl=ttl, key_prefix=key_prefix)


# Cache invalidation helpers
def invalidate_alerts_cache():
    """Invalidate all alert-related caches"""
    return api_cache.invalidate_pattern("api:*alerts*")


def invalidate_statistics_cache():
    """Invalidate all statistics caches"""
    return api_cache.invalidate_pattern("api:*statistics*")


def invalidate_all_cache():
    """Invalidate all API caches"""
    return api_cache.invalidate_pattern("api:*")


if __name__ == "__main__":
    # Test cache decorator
    import time

    @cache_response(ttl=5)
    def expensive_operation(x: int) -> int:
        """Simulate expensive operation"""
        time.sleep(1)
        return x * 2

    print("Testing cache decorator...")

    # First call - should be slow (cache miss)
    start = time.time()
    result1 = expensive_operation(5)
    time1 = time.time() - start
    print(f"First call: {result1} (took {time1:.2f}s)")

    # Second call - should be fast (cache hit)
    start = time.time()
    result2 = expensive_operation(5)
    time2 = time.time() - start
    print(f"Second call: {result2} (took {time2:.2f}s)")

    # Different argument - should be slow (cache miss)
    start = time.time()
    result3 = expensive_operation(10)
    time3 = time.time() - start
    print(f"Third call (different arg): {result3} (took {time3:.2f}s)")

    # Print statistics
    stats = api_cache.get_stats()
    print(f"\nCache statistics: {stats}")

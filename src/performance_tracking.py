"""
Performance Tracking and Monitoring Module
Provides query timing, cache metrics, and API call tracking
"""

import time
import logging
from typing import Dict, List, Optional, Any
from contextlib import contextmanager
from collections import defaultdict, deque
from datetime import datetime, timezone
from functools import wraps
import threading

logger = logging.getLogger(__name__)


class PerformanceTracker:
    """
    Comprehensive performance tracking for database queries, API calls, and cache operations.

    Features:
    - Query timing and slow query logging
    - Cache hit rate tracking
    - API call rate and error tracking
    - Resource utilization monitoring
    - Performance percentiles (p50, p95, p99)
    """

    def __init__(self, slow_query_threshold_ms: float = 100):
        self.slow_query_threshold = slow_query_threshold_ms / 1000  # Convert to seconds

        # Metrics storage
        self.query_times: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self.cache_stats: Dict[str, Dict[str, int]] = defaultdict(lambda: {'hits': 0, 'misses': 0})
        self.api_call_stats: Dict[str, Dict[str, Any]] = defaultdict(
            lambda: {
                'total_calls': 0,
                'errors': 0,
                'rate_limits': 0,
                'total_time': 0,
                'last_call': None
            }
        )
        self.slow_queries: List[Dict] = []

        # Thread safety
        self.lock = threading.Lock()

        # Session tracking
        self.session_start = time.time()

    @contextmanager
    def track_query(self, query_name: str, query_text: Optional[str] = None):
        """
        Context manager for tracking database query performance.

        Usage:
            with tracker.track_query("get_recent_alerts"):
                results = db.query(Alert).filter(...).all()
        """
        start_time = time.time()
        error = None

        try:
            yield
        except Exception as e:
            error = e
            raise
        finally:
            elapsed = time.time() - start_time

            with self.lock:
                # Record query time
                self.query_times[query_name].append(elapsed)

                # Log slow queries
                if elapsed > self.slow_query_threshold:
                    slow_query_info = {
                        'name': query_name,
                        'duration_ms': elapsed * 1000,
                        'timestamp': datetime.now(timezone.utc).isoformat(),
                        'query_text': query_text[:500] if query_text else None,
                        'error': str(error) if error else None
                    }
                    self.slow_queries.append(slow_query_info)

                    # Keep only last 100 slow queries
                    if len(self.slow_queries) > 100:
                        self.slow_queries.pop(0)

                    logger.warning(
                        f"Slow query detected: {query_name} took {elapsed*1000:.2f}ms"
                    )

    @contextmanager
    def track_api_call(self, api_name: str, endpoint: str = ""):
        """
        Context manager for tracking API call performance and errors.

        Usage:
            with tracker.track_api_call("twitter_api", "/search/tweets"):
                response = client.search_tweets(...)
        """
        start_time = time.time()
        error = None
        is_rate_limit = False

        try:
            yield
        except Exception as e:
            error = e
            # Detect rate limit errors
            if 'rate limit' in str(e).lower() or 'too many requests' in str(e).lower():
                is_rate_limit = True
            raise
        finally:
            elapsed = time.time() - start_time

            with self.lock:
                stats = self.api_call_stats[api_name]
                stats['total_calls'] += 1
                stats['total_time'] += elapsed
                stats['last_call'] = datetime.now(timezone.utc).isoformat()

                if error:
                    stats['errors'] += 1
                if is_rate_limit:
                    stats['rate_limits'] += 1

    def record_cache_hit(self, cache_tier: str):
        """Record a cache hit for the specified tier."""
        with self.lock:
            self.cache_stats[cache_tier]['hits'] += 1

    def record_cache_miss(self, cache_tier: str):
        """Record a cache miss for the specified tier."""
        with self.lock:
            self.cache_stats[cache_tier]['misses'] += 1

    def get_query_stats(self, query_name: Optional[str] = None) -> Dict:
        """
        Get query performance statistics.

        Args:
            query_name: Specific query to get stats for, or None for all queries

        Returns:
            Dictionary with performance metrics including percentiles
        """
        with self.lock:
            if query_name:
                times = list(self.query_times.get(query_name, []))
                if not times:
                    return {'error': 'No data for query'}

                return self._calculate_percentiles(query_name, times)
            else:
                # Return stats for all queries
                stats = {}
                for name, times in self.query_times.items():
                    if times:
                        stats[name] = self._calculate_percentiles(name, list(times))
                return stats

    def _calculate_percentiles(self, name: str, times: List[float]) -> Dict:
        """Calculate performance percentiles for query times."""
        if not times:
            return {}

        sorted_times = sorted(times)
        n = len(sorted_times)

        return {
            'query_name': name,
            'count': n,
            'avg_ms': (sum(times) / n) * 1000,
            'min_ms': sorted_times[0] * 1000,
            'max_ms': sorted_times[-1] * 1000,
            'p50_ms': sorted_times[int(n * 0.50)] * 1000 if n > 0 else 0,
            'p95_ms': sorted_times[int(n * 0.95)] * 1000 if n > 1 else 0,
            'p99_ms': sorted_times[int(n * 0.99)] * 1000 if n > 2 else 0,
        }

    def get_cache_stats(self) -> Dict:
        """Get cache performance statistics."""
        with self.lock:
            stats = {}
            for tier, data in self.cache_stats.items():
                total = data['hits'] + data['misses']
                hit_rate = (data['hits'] / total * 100) if total > 0 else 0

                stats[tier] = {
                    'hits': data['hits'],
                    'misses': data['misses'],
                    'total_requests': total,
                    'hit_rate_percent': round(hit_rate, 2)
                }
            return stats

    def get_api_stats(self) -> Dict:
        """Get API call statistics."""
        with self.lock:
            stats = {}
            for api_name, data in self.api_call_stats.items():
                avg_time = 0
                if data['total_calls'] > 0:
                    avg_time = (data['total_time'] / data['total_calls']) * 1000

                error_rate = 0
                if data['total_calls'] > 0:
                    error_rate = (data['errors'] / data['total_calls']) * 100

                stats[api_name] = {
                    'total_calls': data['total_calls'],
                    'errors': data['errors'],
                    'rate_limits': data['rate_limits'],
                    'avg_response_time_ms': round(avg_time, 2),
                    'error_rate_percent': round(error_rate, 2),
                    'last_call': data['last_call']
                }
            return stats

    def get_slow_queries(self, limit: int = 10) -> List[Dict]:
        """Get recent slow queries."""
        with self.lock:
            return self.slow_queries[-limit:]

    def get_summary(self) -> Dict:
        """Get comprehensive performance summary."""
        uptime = time.time() - self.session_start

        return {
            'uptime_seconds': round(uptime, 2),
            'query_stats': self.get_query_stats(),
            'cache_stats': self.get_cache_stats(),
            'api_stats': self.get_api_stats(),
            'slow_queries_count': len(self.slow_queries),
            'timestamp': datetime.now(timezone.utc).isoformat()
        }

    def reset(self):
        """Reset all metrics."""
        with self.lock:
            self.query_times.clear()
            self.cache_stats.clear()
            self.api_call_stats.clear()
            self.slow_queries.clear()
            self.session_start = time.time()
            logger.info("Performance tracker metrics reset")


# Decorator for tracking function performance
def track_performance(tracker: PerformanceTracker, operation_name: str):
    """
    Decorator for tracking function performance.

    Usage:
        @track_performance(tracker, "process_articles")
        def process_articles(articles):
            ...
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            with tracker.track_query(operation_name):
                return func(*args, **kwargs)
        return wrapper
    return decorator


# Global performance tracker instance
_performance_tracker = None


def get_performance_tracker(slow_query_threshold_ms: float = 100) -> PerformanceTracker:
    """Get global performance tracker instance."""
    global _performance_tracker
    if _performance_tracker is None:
        _performance_tracker = PerformanceTracker(slow_query_threshold_ms)
    return _performance_tracker


def log_performance_summary():
    """Log performance summary to logger."""
    tracker = get_performance_tracker()
    summary = tracker.get_summary()

    logger.info("=" * 60)
    logger.info("Performance Summary")
    logger.info("=" * 60)
    logger.info(f"Uptime: {summary['uptime_seconds']:.2f}s")

    # Query performance
    logger.info("\nQuery Performance:")
    for query_name, stats in summary['query_stats'].items():
        logger.info(
            f"  {query_name}: "
            f"avg={stats['avg_ms']:.2f}ms, "
            f"p95={stats['p95_ms']:.2f}ms, "
            f"count={stats['count']}"
        )

    # Cache performance
    logger.info("\nCache Performance:")
    for tier, stats in summary['cache_stats'].items():
        logger.info(
            f"  {tier}: "
            f"hit_rate={stats['hit_rate_percent']:.1f}%, "
            f"hits={stats['hits']}, "
            f"misses={stats['misses']}"
        )

    # API performance
    logger.info("\nAPI Performance:")
    for api_name, stats in summary['api_stats'].items():
        logger.info(
            f"  {api_name}: "
            f"calls={stats['total_calls']}, "
            f"avg_time={stats['avg_response_time_ms']:.2f}ms, "
            f"error_rate={stats['error_rate_percent']:.1f}%"
        )

    # Slow queries
    slow_queries = tracker.get_slow_queries(5)
    if slow_queries:
        logger.info("\nRecent Slow Queries:")
        for sq in slow_queries:
            logger.info(
                f"  {sq['name']}: {sq['duration_ms']:.2f}ms at {sq['timestamp']}"
            )

    logger.info("=" * 60)


if __name__ == "__main__":
    # Test performance tracker
    logging.basicConfig(level=logging.INFO)

    tracker = PerformanceTracker(slow_query_threshold_ms=50)

    # Simulate some operations
    import time
    import random

    print("Testing performance tracker...")

    # Simulate queries
    for i in range(100):
        with tracker.track_query("get_alerts"):
            time.sleep(random.uniform(0.01, 0.15))

    # Simulate API calls
    for i in range(50):
        try:
            with tracker.track_api_call("twitter_api"):
                time.sleep(random.uniform(0.05, 0.2))
                if random.random() < 0.1:
                    raise Exception("Rate limit exceeded")
        except:
            pass

    # Simulate cache operations
    for i in range(200):
        if random.random() < 0.7:
            tracker.record_cache_hit("article_content")
        else:
            tracker.record_cache_miss("article_content")

    # Print summary
    log_performance_summary()

    # Test query stats
    print("\nDetailed query stats:")
    print(tracker.get_query_stats("get_alerts"))

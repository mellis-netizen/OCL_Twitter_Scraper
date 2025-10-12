"""
Performance Monitoring System for TGE Scraping
Tracks scraping performance, cache efficiency, and API usage

Performance Metrics:
- Scraping cycle times (<60s target)
- Cache hit rates (>70% target)
- API call counts (30% reduction target)
- Deduplication effectiveness
- Rate limit compliance (100% target)
"""

import time
import json
import logging
from typing import Dict, List, Optional
from datetime import datetime, timezone
from collections import defaultdict, deque
from threading import Lock
import os

logger = logging.getLogger(__name__)


class PerformanceTimer:
    """Context manager for timing operations."""

    def __init__(self, name: str, monitor: 'PerformanceMonitor'):
        self.name = name
        self.monitor = monitor
        self.start_time = None
        self.end_time = None

    def __enter__(self):
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end_time = time.time()
        duration = self.end_time - self.start_time
        self.monitor.record_operation(self.name, duration, exc_type is None)


class PerformanceMonitor:
    """
    Performance monitoring and metrics tracking system.

    Tracks:
    - Scraping cycle times
    - Cache hit rates
    - API call counts
    - Deduplication rates
    - Error rates
    - Component-level performance
    """

    def __init__(self, history_size: int = 100):
        """
        Initialize performance monitor.

        Args:
            history_size: Number of historical measurements to keep
        """
        self.history_size = history_size

        # Operation timing
        self.operation_times: Dict[str, deque] = defaultdict(lambda: deque(maxlen=history_size))
        self.operation_success: Dict[str, Dict[str, int]] = defaultdict(lambda: {'success': 0, 'failure': 0})

        # Component metrics
        self.component_metrics = {
            'news_scraper': {
                'cycles': 0,
                'total_time': 0.0,
                'articles_found': 0,
                'feeds_processed': 0,
                'cache_hits': 0,
                'cache_misses': 0,
                'api_calls': 0
            },
            'twitter_monitor': {
                'cycles': 0,
                'total_time': 0.0,
                'tweets_found': 0,
                'users_fetched': 0,
                'cache_hits': 0,
                'cache_misses': 0,
                'api_calls': 0,
                'rate_limit_hits': 0
            },
            'deduplication': {
                'total_items': 0,
                'duplicates_removed': 0,
                'unique_items': 0
            }
        }

        # Cycle tracking
        self.cycle_history = deque(maxlen=history_size)
        self.current_cycle = None

        # API tracking
        self.api_calls_history = deque(maxlen=history_size)
        self.current_api_count = 0

        # Baseline metrics (for comparison)
        self.baseline_metrics = {
            'avg_cycle_time': 90.0,  # 90 seconds baseline
            'avg_api_calls': 150,  # API calls per cycle
            'cache_hit_rate': 0.0  # No caching baseline
        }

        # Thread safety
        self.lock = Lock()

        # Persistence
        self.metrics_file = 'state/performance_metrics.json'
        self._load_baseline()

    def timer(self, operation_name: str) -> PerformanceTimer:
        """
        Create timer context manager for operation.

        Args:
            operation_name: Name of operation to time

        Returns:
            Timer context manager
        """
        return PerformanceTimer(operation_name, self)

    def record_operation(self, operation_name: str, duration: float, success: bool = True):
        """
        Record operation timing.

        Args:
            operation_name: Name of operation
            duration: Duration in seconds
            success: Whether operation succeeded
        """
        with self.lock:
            self.operation_times[operation_name].append(duration)

            if success:
                self.operation_success[operation_name]['success'] += 1
            else:
                self.operation_success[operation_name]['failure'] += 1

            logger.debug(f"Operation {operation_name}: {duration*1000:.2f}ms (success={success})")

    def start_cycle(self):
        """Start new scraping cycle."""
        with self.lock:
            self.current_cycle = {
                'start_time': time.time(),
                'news_scraper': {},
                'twitter_monitor': {},
                'api_calls_start': self.current_api_count
            }
            logger.info("Started new scraping cycle")

    def end_cycle(self):
        """End current scraping cycle and record metrics."""
        with self.lock:
            if self.current_cycle is None:
                logger.warning("end_cycle called without start_cycle")
                return

            duration = time.time() - self.current_cycle['start_time']
            api_calls = self.current_api_count - self.current_cycle['api_calls_start']

            cycle_metrics = {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'duration': duration,
                'api_calls': api_calls,
                **self.current_cycle
            }

            self.cycle_history.append(cycle_metrics)

            # Update baseline if we have enough history
            if len(self.cycle_history) >= 10:
                self._update_baseline()

            logger.info(f"Cycle completed in {duration:.2f}s with {api_calls} API calls")

            self.current_cycle = None

    def record_api_call(self, component: str = 'unknown'):
        """
        Record API call.

        Args:
            component: Component making the API call
        """
        with self.lock:
            self.current_api_count += 1
            if component in self.component_metrics:
                self.component_metrics[component]['api_calls'] += 1

    def record_cache_access(self, component: str, hit: bool):
        """
        Record cache access.

        Args:
            component: Component accessing cache
            hit: Whether it was a cache hit
        """
        with self.lock:
            if component in self.component_metrics:
                if hit:
                    self.component_metrics[component]['cache_hits'] += 1
                else:
                    self.component_metrics[component]['cache_misses'] += 1

    def record_deduplication(self, total: int, duplicates: int):
        """
        Record deduplication results.

        Args:
            total: Total items processed
            duplicates: Number of duplicates removed
        """
        with self.lock:
            metrics = self.component_metrics['deduplication']
            metrics['total_items'] += total
            metrics['duplicates_removed'] += duplicates
            metrics['unique_items'] += (total - duplicates)

    def record_scraper_cycle(self, articles_found: int, feeds_processed: int, duration: float):
        """
        Record news scraper cycle.

        Args:
            articles_found: Number of articles found
            feeds_processed: Number of feeds processed
            duration: Cycle duration in seconds
        """
        with self.lock:
            metrics = self.component_metrics['news_scraper']
            metrics['cycles'] += 1
            metrics['total_time'] += duration
            metrics['articles_found'] += articles_found
            metrics['feeds_processed'] += feeds_processed

    def record_twitter_cycle(self, tweets_found: int, users_fetched: int, duration: float, rate_limit_hit: bool = False):
        """
        Record Twitter monitor cycle.

        Args:
            tweets_found: Number of tweets found
            users_fetched: Number of users fetched
            duration: Cycle duration in seconds
            rate_limit_hit: Whether rate limit was hit
        """
        with self.lock:
            metrics = self.component_metrics['twitter_monitor']
            metrics['cycles'] += 1
            metrics['total_time'] += duration
            metrics['tweets_found'] += tweets_found
            metrics['users_fetched'] += users_fetched
            if rate_limit_hit:
                metrics['rate_limit_hits'] += 1

    def get_operation_stats(self, operation_name: str) -> Dict:
        """
        Get statistics for specific operation.

        Args:
            operation_name: Name of operation

        Returns:
            Operation statistics
        """
        with self.lock:
            times = list(self.operation_times.get(operation_name, []))
            success_count = self.operation_success.get(operation_name, {})

            if not times:
                return {
                    'count': 0,
                    'avg_duration_ms': 0,
                    'min_duration_ms': 0,
                    'max_duration_ms': 0,
                    'p95_duration_ms': 0,
                    'success_rate': 0
                }

            times_sorted = sorted(times)
            total = success_count['success'] + success_count['failure']
            success_rate = (success_count['success'] / total * 100) if total > 0 else 0

            p95_index = int(len(times_sorted) * 0.95)

            return {
                'count': len(times),
                'avg_duration_ms': round(sum(times) / len(times) * 1000, 2),
                'min_duration_ms': round(min(times) * 1000, 2),
                'max_duration_ms': round(max(times) * 1000, 2),
                'p95_duration_ms': round(times_sorted[p95_index] * 1000, 2) if p95_index < len(times_sorted) else 0,
                'success_rate': round(success_rate, 2),
                'success_count': success_count['success'],
                'failure_count': success_count['failure']
            }

    def get_component_stats(self, component: str) -> Dict:
        """
        Get statistics for component.

        Args:
            component: Component name

        Returns:
            Component statistics
        """
        with self.lock:
            if component not in self.component_metrics:
                return {}

            metrics = self.component_metrics[component].copy()

            # Calculate derived metrics
            if component in ['news_scraper', 'twitter_monitor']:
                if metrics['cycles'] > 0:
                    metrics['avg_cycle_time'] = round(metrics['total_time'] / metrics['cycles'], 2)

                total_cache = metrics['cache_hits'] + metrics['cache_misses']
                metrics['cache_hit_rate'] = round((metrics['cache_hits'] / total_cache * 100) if total_cache > 0 else 0, 2)

                if component == 'news_scraper':
                    metrics['articles_per_cycle'] = round(metrics['articles_found'] / metrics['cycles'], 2) if metrics['cycles'] > 0 else 0
                elif component == 'twitter_monitor':
                    metrics['tweets_per_cycle'] = round(metrics['tweets_found'] / metrics['cycles'], 2) if metrics['cycles'] > 0 else 0

            elif component == 'deduplication':
                if metrics['total_items'] > 0:
                    metrics['deduplication_rate'] = round((metrics['duplicates_removed'] / metrics['total_items'] * 100), 2)
                    metrics['unique_rate'] = round((metrics['unique_items'] / metrics['total_items'] * 100), 2)

            return metrics

    def get_cycle_stats(self) -> Dict:
        """Get scraping cycle statistics."""
        with self.lock:
            if not self.cycle_history:
                return {
                    'total_cycles': 0,
                    'avg_duration': 0,
                    'min_duration': 0,
                    'max_duration': 0,
                    'avg_api_calls': 0,
                    'target_met': False
                }

            durations = [cycle['duration'] for cycle in self.cycle_history]
            api_calls = [cycle['api_calls'] for cycle in self.cycle_history]

            avg_duration = sum(durations) / len(durations)
            avg_api = sum(api_calls) / len(api_calls)

            # Check if targets are met
            target_duration_met = avg_duration < 60  # <60s target
            target_api_reduction = ((self.baseline_metrics['avg_api_calls'] - avg_api) /
                                   self.baseline_metrics['avg_api_calls'] * 100) if self.baseline_metrics['avg_api_calls'] > 0 else 0

            return {
                'total_cycles': len(self.cycle_history),
                'avg_duration': round(avg_duration, 2),
                'min_duration': round(min(durations), 2),
                'max_duration': round(max(durations), 2),
                'avg_api_calls': round(avg_api, 2),
                'baseline_duration': self.baseline_metrics['avg_cycle_time'],
                'baseline_api_calls': self.baseline_metrics['avg_api_calls'],
                'improvement_percent': round(((self.baseline_metrics['avg_cycle_time'] - avg_duration) /
                                             self.baseline_metrics['avg_cycle_time'] * 100), 2),
                'api_reduction_percent': round(target_api_reduction, 2),
                'target_duration_met': target_duration_met,
                'target_api_reduction_met': target_api_reduction >= 30
            }

    def get_performance_report(self) -> Dict:
        """Get comprehensive performance report."""
        with self.lock:
            return {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'cycle_stats': self.get_cycle_stats(),
                'news_scraper': self.get_component_stats('news_scraper'),
                'twitter_monitor': self.get_component_stats('twitter_monitor'),
                'deduplication': self.get_component_stats('deduplication'),
                'operation_stats': {
                    op: self.get_operation_stats(op)
                    for op in self.operation_times.keys()
                }
            }

    def _update_baseline(self):
        """Update baseline metrics from history."""
        if len(self.cycle_history) < 10:
            return

        recent_cycles = list(self.cycle_history)[-10:]
        durations = [cycle['duration'] for cycle in recent_cycles]
        api_calls = [cycle['api_calls'] for cycle in recent_cycles]

        self.baseline_metrics['avg_cycle_time'] = sum(durations) / len(durations)
        self.baseline_metrics['avg_api_calls'] = sum(api_calls) / len(api_calls)

        # Calculate cache hit rate
        news_metrics = self.component_metrics['news_scraper']
        twitter_metrics = self.component_metrics['twitter_monitor']

        total_hits = news_metrics['cache_hits'] + twitter_metrics['cache_hits']
        total_accesses = (news_metrics['cache_hits'] + news_metrics['cache_misses'] +
                         twitter_metrics['cache_hits'] + twitter_metrics['cache_misses'])

        if total_accesses > 0:
            self.baseline_metrics['cache_hit_rate'] = total_hits / total_accesses * 100

    def _load_baseline(self):
        """Load baseline metrics from file."""
        try:
            if os.path.exists(self.metrics_file):
                with open(self.metrics_file, 'r') as f:
                    data = json.load(f)
                    if 'baseline_metrics' in data:
                        self.baseline_metrics.update(data['baseline_metrics'])
                        logger.info(f"Loaded baseline metrics: {self.baseline_metrics}")
        except Exception as e:
            logger.warning(f"Could not load baseline metrics: {e}")

    def save_metrics(self):
        """Save performance metrics to file."""
        try:
            os.makedirs('state', exist_ok=True)

            report = self.get_performance_report()
            report['baseline_metrics'] = self.baseline_metrics

            with open(self.metrics_file, 'w') as f:
                json.dump(report, f, indent=2)

            logger.info("Performance metrics saved")
        except Exception as e:
            logger.warning(f"Could not save performance metrics: {e}")

    def print_summary(self):
        """Print performance summary to console."""
        report = self.get_performance_report()

        print("\n" + "="*60)
        print("PERFORMANCE SUMMARY")
        print("="*60)

        # Cycle stats
        cycle_stats = report['cycle_stats']
        print(f"\nScraping Cycles:")
        print(f"  Total Cycles: {cycle_stats['total_cycles']}")
        print(f"  Avg Duration: {cycle_stats['avg_duration']:.2f}s (target: <60s)")
        print(f"  Improvement: {cycle_stats['improvement_percent']:.1f}%")
        print(f"  Avg API Calls: {cycle_stats['avg_api_calls']:.0f}")
        print(f"  API Reduction: {cycle_stats['api_reduction_percent']:.1f}% (target: >30%)")

        # News scraper
        news_stats = report['news_scraper']
        if news_stats.get('cycles', 0) > 0:
            print(f"\nNews Scraper:")
            print(f"  Cache Hit Rate: {news_stats.get('cache_hit_rate', 0):.1f}%")
            print(f"  Articles/Cycle: {news_stats.get('articles_per_cycle', 0):.1f}")
            print(f"  API Calls: {news_stats.get('api_calls', 0)}")

        # Twitter monitor
        twitter_stats = report['twitter_monitor']
        if twitter_stats.get('cycles', 0) > 0:
            print(f"\nTwitter Monitor:")
            print(f"  Cache Hit Rate: {twitter_stats.get('cache_hit_rate', 0):.1f}%")
            print(f"  Tweets/Cycle: {twitter_stats.get('tweets_per_cycle', 0):.1f}")
            print(f"  API Calls: {twitter_stats.get('api_calls', 0)}")
            print(f"  Rate Limit Hits: {twitter_stats.get('rate_limit_hits', 0)}")

        # Deduplication
        dedup_stats = report['deduplication']
        if dedup_stats.get('total_items', 0) > 0:
            print(f"\nDeduplication:")
            print(f"  Dedup Rate: {dedup_stats.get('deduplication_rate', 0):.1f}%")
            print(f"  Unique Items: {dedup_stats.get('unique_items', 0)}")

        print("="*60 + "\n")


# Global performance monitor instance
_performance_monitor = None


def get_performance_monitor() -> PerformanceMonitor:
    """Get global performance monitor instance."""
    global _performance_monitor
    if _performance_monitor is None:
        _performance_monitor = PerformanceMonitor()
    return _performance_monitor

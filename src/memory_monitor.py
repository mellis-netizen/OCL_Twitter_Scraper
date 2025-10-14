"""
Memory usage monitoring and profiling for TGE Monitor
Tracks memory consumption, identifies leaks, and provides optimization insights
"""

import os
import sys
import time
import psutil
import logging
import tracemalloc
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timezone
from collections import defaultdict

logger = logging.getLogger(__name__)


class MemoryMonitor:
    """
    Monitor memory usage and identify potential memory leaks
    """

    def __init__(self, enable_tracemalloc: bool = False):
        """
        Initialize memory monitor

        Args:
            enable_tracemalloc: Enable detailed Python memory tracking (has performance overhead)
        """
        self.process = psutil.Process(os.getpid())
        self.enable_tracemalloc = enable_tracemalloc
        self.snapshots = []
        self.baseline_memory = None

        # Start tracemalloc if enabled
        if self.enable_tracemalloc:
            tracemalloc.start()
            logger.info("Memory tracing enabled (tracemalloc)")

        # Initial memory reading
        self.baseline_memory = self.get_memory_usage()
        logger.info(f"Baseline memory: {self.baseline_memory['rss_mb']:.1f} MB")

    def get_memory_usage(self) -> Dict[str, float]:
        """
        Get current memory usage metrics

        Returns:
            Dictionary with memory metrics in MB
        """
        try:
            memory_info = self.process.memory_info()

            return {
                'rss_mb': memory_info.rss / 1024 / 1024,  # Resident Set Size
                'vms_mb': memory_info.vms / 1024 / 1024,  # Virtual Memory Size
                'percent': self.process.memory_percent(),
                'timestamp': datetime.now(timezone.utc).isoformat()
            }

        except Exception as e:
            logger.error(f"Error getting memory usage: {e}")
            return {
                'rss_mb': 0.0,
                'vms_mb': 0.0,
                'percent': 0.0,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }

    def get_system_memory(self) -> Dict[str, float]:
        """Get system-wide memory statistics"""
        try:
            system_memory = psutil.virtual_memory()

            return {
                'total_gb': system_memory.total / 1024 / 1024 / 1024,
                'available_gb': system_memory.available / 1024 / 1024 / 1024,
                'used_gb': system_memory.used / 1024 / 1024 / 1024,
                'percent': system_memory.percent
            }

        except Exception as e:
            logger.error(f"Error getting system memory: {e}")
            return {}

    def take_snapshot(self, label: str = ""):
        """
        Take a memory snapshot for tracking

        Args:
            label: Optional label to identify this snapshot
        """
        snapshot = self.get_memory_usage()
        snapshot['label'] = label or f"snapshot_{len(self.snapshots)}"

        self.snapshots.append(snapshot)

        logger.info(
            f"Memory snapshot '{snapshot['label']}': "
            f"{snapshot['rss_mb']:.1f} MB RSS "
            f"({snapshot['percent']:.1f}% of system memory)"
        )

        return snapshot

    def get_memory_diff(self, start_label: Optional[str] = None) -> Dict[str, float]:
        """
        Calculate memory difference from a previous snapshot or baseline

        Args:
            start_label: Label of starting snapshot (None for baseline)

        Returns:
            Dictionary with memory difference metrics
        """
        current = self.get_memory_usage()

        # Find starting snapshot
        if start_label:
            start_snapshot = next(
                (s for s in self.snapshots if s['label'] == start_label),
                self.baseline_memory
            )
        else:
            start_snapshot = self.baseline_memory

        if not start_snapshot:
            return {'error': 'No baseline memory measurement'}

        return {
            'rss_diff_mb': current['rss_mb'] - start_snapshot['rss_mb'],
            'vms_diff_mb': current['vms_mb'] - start_snapshot['vms_mb'],
            'percent_diff': current['percent'] - start_snapshot['percent'],
            'start_memory': start_snapshot['rss_mb'],
            'current_memory': current['rss_mb']
        }

    def get_top_memory_consumers(self, limit: int = 10) -> List[Tuple[str, float]]:
        """
        Get top memory-consuming objects (requires tracemalloc)

        Args:
            limit: Number of top consumers to return

        Returns:
            List of (object_type, size_mb) tuples
        """
        if not self.enable_tracemalloc:
            logger.warning("tracemalloc not enabled, cannot get memory consumers")
            return []

        try:
            snapshot = tracemalloc.take_snapshot()
            top_stats = snapshot.statistics('lineno')

            consumers = []
            for stat in top_stats[:limit]:
                size_mb = stat.size / 1024 / 1024
                consumers.append((str(stat), size_mb))

            return consumers

        except Exception as e:
            logger.error(f"Error getting memory consumers: {e}")
            return []

    def detect_memory_leak(self, threshold_mb: float = 50.0) -> Dict[str, any]:
        """
        Detect potential memory leaks by comparing snapshots

        Args:
            threshold_mb: Memory growth threshold to flag as potential leak

        Returns:
            Dictionary with leak detection results
        """
        if len(self.snapshots) < 2:
            return {'leak_detected': False, 'reason': 'Insufficient snapshots'}

        # Compare first and last snapshots
        first_snapshot = self.snapshots[0]
        last_snapshot = self.snapshots[-1]

        memory_growth = last_snapshot['rss_mb'] - first_snapshot['rss_mb']
        growth_rate = memory_growth / len(self.snapshots)

        leak_detected = memory_growth > threshold_mb

        return {
            'leak_detected': leak_detected,
            'memory_growth_mb': memory_growth,
            'growth_rate_mb_per_snapshot': growth_rate,
            'snapshots_analyzed': len(self.snapshots),
            'first_memory_mb': first_snapshot['rss_mb'],
            'last_memory_mb': last_snapshot['rss_mb'],
            'threshold_mb': threshold_mb
        }

    def generate_report(self) -> str:
        """
        Generate comprehensive memory usage report

        Returns:
            Formatted report string
        """
        current = self.get_memory_usage()
        system = self.get_system_memory()
        diff = self.get_memory_diff()
        leak_detection = self.detect_memory_leak()

        report = []
        report.append("=" * 70)
        report.append("MEMORY USAGE REPORT")
        report.append("=" * 70)

        # Current memory
        report.append("\nCurrent Memory Usage:")
        report.append(f"  RSS (Resident Set Size): {current['rss_mb']:.1f} MB")
        report.append(f"  VMS (Virtual Memory Size): {current['vms_mb']:.1f} MB")
        report.append(f"  Process Memory %: {current['percent']:.1f}%")

        # System memory
        report.append("\nSystem Memory:")
        report.append(f"  Total: {system['total_gb']:.1f} GB")
        report.append(f"  Available: {system['available_gb']:.1f} GB")
        report.append(f"  Used: {system['used_gb']:.1f} GB ({system['percent']:.1f}%)")

        # Memory change from baseline
        report.append("\nMemory Change from Baseline:")
        report.append(f"  RSS Change: {diff['rss_diff_mb']:+.1f} MB")
        report.append(f"  VMS Change: {diff['vms_diff_mb']:+.1f} MB")
        report.append(f"  Baseline: {diff['start_memory']:.1f} MB")

        # Snapshots
        if self.snapshots:
            report.append(f"\nMemory Snapshots ({len(self.snapshots)}):")
            for snapshot in self.snapshots[-5:]:  # Last 5 snapshots
                report.append(
                    f"  {snapshot['label']}: {snapshot['rss_mb']:.1f} MB "
                    f"({snapshot['percent']:.1f}%)"
                )

        # Leak detection
        report.append("\nMemory Leak Detection:")
        report.append(f"  Leak Detected: {leak_detection['leak_detected']}")
        if leak_detection['leak_detected']:
            report.append(
                f"  Memory Growth: {leak_detection['memory_growth_mb']:.1f} MB "
                f"(threshold: {leak_detection['threshold_mb']} MB)"
            )

        # Top memory consumers (if available)
        if self.enable_tracemalloc:
            consumers = self.get_top_memory_consumers(5)
            if consumers:
                report.append("\nTop Memory Consumers:")
                for location, size_mb in consumers:
                    report.append(f"  {size_mb:.2f} MB - {location}")

        report.append("=" * 70)

        return "\n".join(report)

    def log_report(self):
        """Log memory usage report"""
        report = self.generate_report()
        logger.info(f"\n{report}")

    def cleanup(self):
        """Cleanup and stop memory tracking"""
        if self.enable_tracemalloc:
            tracemalloc.stop()
            logger.info("Memory tracing stopped")


# Global memory monitor instance
_memory_monitor = None


def get_memory_monitor(enable_tracemalloc: bool = False) -> MemoryMonitor:
    """
    Get or create global memory monitor instance

    Args:
        enable_tracemalloc: Enable detailed memory tracking

    Returns:
        MemoryMonitor instance
    """
    global _memory_monitor

    if _memory_monitor is None:
        _memory_monitor = MemoryMonitor(enable_tracemalloc=enable_tracemalloc)

    return _memory_monitor


# Decorator for monitoring memory usage of functions
def monitor_memory(func):
    """
    Decorator to monitor memory usage of a function

    Example:
        @monitor_memory
        def expensive_operation():
            # ... operation code
            pass
    """
    def wrapper(*args, **kwargs):
        monitor = get_memory_monitor()

        # Take snapshot before
        before = monitor.take_snapshot(f"before_{func.__name__}")

        # Execute function
        result = func(*args, **kwargs)

        # Take snapshot after
        after = monitor.take_snapshot(f"after_{func.__name__}")

        # Log memory diff
        memory_used = after['rss_mb'] - before['rss_mb']
        logger.info(
            f"Function '{func.__name__}' memory usage: "
            f"{memory_used:+.2f} MB"
        )

        return result

    return wrapper


if __name__ == "__main__":
    # Test memory monitor
    print("Testing Memory Monitor...")

    monitor = MemoryMonitor(enable_tracemalloc=True)

    # Take initial snapshot
    monitor.take_snapshot("start")

    # Simulate memory usage
    data = []
    for i in range(5):
        # Allocate some memory
        data.append([0] * 1000000)
        time.sleep(0.5)
        monitor.take_snapshot(f"iteration_{i+1}")

    # Generate report
    print(monitor.generate_report())

    # Detect leaks
    leak_detection = monitor.detect_memory_leak(threshold_mb=10.0)
    print(f"\nLeak Detection: {leak_detection}")

    # Cleanup
    monitor.cleanup()

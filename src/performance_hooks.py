"""
Performance Hooks Integration
Coordinates performance metrics with claude-flow hooks for swarm coordination

Integrates:
- Post-task performance reporting
- Session metrics export
- Cache statistics sharing
- Performance benchmarking results
"""

import json
import logging
import subprocess
from typing import Dict, Optional
from datetime import datetime, timezone

from cache_manager import get_cache_manager
from session_manager import get_session_manager
from performance_monitor import get_performance_monitor

logger = logging.getLogger(__name__)


class PerformanceHooks:
    """
    Performance hooks for claude-flow integration.

    Provides:
    - Pre-task setup and validation
    - Post-task performance reporting
    - Session-level metrics export
    - Memory storage of performance data
    """

    def __init__(self, task_description: str = "Performance optimization"):
        self.task_description = task_description
        self.task_id = None
        self.session_id = None

        self.cache_manager = get_cache_manager()
        self.session_manager = get_session_manager()
        self.perf_monitor = get_performance_monitor()

    def pre_task(self) -> bool:
        """
        Execute pre-task hook.

        Returns:
            True if successful
        """
        try:
            cmd = [
                'npx', 'claude-flow@alpha', 'hooks', 'pre-task',
                '--description', self.task_description
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0:
                # Parse task ID from output
                for line in result.stdout.split('\n'):
                    if 'Task ID:' in line:
                        self.task_id = line.split('Task ID:')[1].strip()
                        logger.info(f"Pre-task hook completed: {self.task_id}")
                        return True

                logger.info("Pre-task hook completed")
                return True
            else:
                logger.warning(f"Pre-task hook failed: {result.stderr}")
                return False

        except Exception as e:
            logger.warning(f"Could not execute pre-task hook: {e}")
            return False

    def post_task(self, success: bool = True) -> bool:
        """
        Execute post-task hook with performance metrics.

        Args:
            success: Whether task completed successfully

        Returns:
            True if successful
        """
        try:
            # Get performance report
            report = self.perf_monitor.get_performance_report()

            # Store metrics in memory
            memory_key = f"performance/optimization/{datetime.now(timezone.utc).isoformat()}"

            # Execute post-task hook
            cmd = [
                'npx', 'claude-flow@alpha', 'hooks', 'post-task'
            ]

            if self.task_id:
                cmd.extend(['--task-id', self.task_id])

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0:
                logger.info("Post-task hook completed")

                # Store performance metrics in memory
                self._store_performance_metrics(memory_key, report)

                return True
            else:
                logger.warning(f"Post-task hook failed: {result.stderr}")
                return False

        except Exception as e:
            logger.warning(f"Could not execute post-task hook: {e}")
            return False

    def notify(self, message: str, performance_data: Optional[Dict] = None) -> bool:
        """
        Send notification with performance data.

        Args:
            message: Notification message
            performance_data: Optional performance data to include

        Returns:
            True if successful
        """
        try:
            cmd = [
                'npx', 'claude-flow@alpha', 'hooks', 'notify',
                '--message', message
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0:
                logger.info(f"Notification sent: {message}")

                if performance_data:
                    # Store in memory
                    memory_key = f"notifications/{datetime.now(timezone.utc).isoformat()}"
                    self._store_performance_metrics(memory_key, performance_data)

                return True
            else:
                logger.warning(f"Notification failed: {result.stderr}")
                return False

        except Exception as e:
            logger.warning(f"Could not send notification: {e}")
            return False

    def session_end(self, export_metrics: bool = True) -> bool:
        """
        End session and export metrics.

        Args:
            export_metrics: Whether to export performance metrics

        Returns:
            True if successful
        """
        try:
            cmd = [
                'npx', 'claude-flow@alpha', 'hooks', 'session-end',
                '--export-metrics', 'true' if export_metrics else 'false'
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0:
                logger.info("Session end hook completed")

                if export_metrics:
                    # Get final metrics
                    final_report = self._get_final_metrics_report()

                    # Store final report
                    memory_key = f"performance/final_report/{datetime.now(timezone.utc).isoformat()}"
                    self._store_performance_metrics(memory_key, final_report)

                    # Print summary
                    self.perf_monitor.print_summary()

                return True
            else:
                logger.warning(f"Session end hook failed: {result.stderr}")
                return False

        except Exception as e:
            logger.warning(f"Could not execute session end hook: {e}")
            return False

    def _store_performance_metrics(self, memory_key: str, metrics: Dict) -> bool:
        """
        Store performance metrics in claude-flow memory.

        Args:
            memory_key: Memory key
            metrics: Metrics to store

        Returns:
            True if successful
        """
        try:
            metrics_json = json.dumps(metrics, default=str)

            cmd = [
                'npx', 'claude-flow@alpha', 'memory', 'store',
                memory_key,
                metrics_json,
                '--ttl', '86400'  # 24 hours
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0:
                logger.debug(f"Stored performance metrics: {memory_key}")
                return True
            else:
                logger.warning(f"Failed to store metrics: {result.stderr}")
                return False

        except Exception as e:
            logger.warning(f"Could not store performance metrics: {e}")
            return False

    def _get_final_metrics_report(self) -> Dict:
        """
        Get comprehensive final metrics report.

        Returns:
            Final metrics report
        """
        try:
            performance_report = self.perf_monitor.get_performance_report()
            cache_stats = self.cache_manager.get_stats()
            session_stats = self.session_manager.get_metrics()

            # Calculate target achievement
            cycle_stats = performance_report.get('cycle_stats', {})
            news_stats = performance_report.get('news_scraper', {})
            twitter_stats = performance_report.get('twitter_monitor', {})

            targets = {
                'cycle_time': {
                    'target': 60,
                    'actual': cycle_stats.get('avg_duration', 0),
                    'met': cycle_stats.get('target_duration_met', False),
                    'unit': 'seconds'
                },
                'api_reduction': {
                    'target': 30,
                    'actual': cycle_stats.get('api_reduction_percent', 0),
                    'met': cycle_stats.get('target_api_reduction_met', False),
                    'unit': 'percent'
                },
                'cache_hit_rate': {
                    'target': 70,
                    'actual': cache_stats.get('overall_hit_rate', 0),
                    'met': cache_stats.get('overall_hit_rate', 0) >= 70,
                    'unit': 'percent'
                },
                'connection_reuse': {
                    'target': 80,
                    'actual': session_stats.get('connection_reuse_rate', 0),
                    'met': session_stats.get('connection_reuse_rate', 0) >= 80,
                    'unit': 'percent'
                }
            }

            return {
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'summary': {
                    'total_cycles': cycle_stats.get('total_cycles', 0),
                    'avg_cycle_time': cycle_stats.get('avg_duration', 0),
                    'avg_api_calls': cycle_stats.get('avg_api_calls', 0),
                    'cache_hit_rate': cache_stats.get('overall_hit_rate', 0),
                    'connection_reuse_rate': session_stats.get('connection_reuse_rate', 0)
                },
                'targets': targets,
                'all_targets_met': all(t['met'] for t in targets.values()),
                'performance_report': performance_report,
                'cache_stats': cache_stats,
                'session_stats': session_stats
            }

        except Exception as e:
            logger.error(f"Error generating final metrics report: {e}")
            return {
                'error': str(e),
                'timestamp': datetime.now(timezone.utc).isoformat()
            }


def execute_performance_cycle_with_hooks(
    task_description: str,
    work_function: callable,
    *args,
    **kwargs
) -> Dict:
    """
    Execute performance-monitored work with hooks integration.

    Args:
        task_description: Description of task
        work_function: Function to execute
        *args: Arguments for work function
        **kwargs: Keyword arguments for work function

    Returns:
        Results including performance metrics
    """
    hooks = PerformanceHooks(task_description)

    # Pre-task hook
    hooks.pre_task()

    # Get performance monitor
    perf_monitor = get_performance_monitor()
    perf_monitor.start_cycle()

    success = False
    result = None
    error = None

    try:
        # Execute work
        result = work_function(*args, **kwargs)
        success = True

    except Exception as e:
        error = str(e)
        logger.error(f"Work function failed: {e}")

    finally:
        # End cycle
        perf_monitor.end_cycle()

        # Post-task hook
        hooks.post_task(success=success)

        # Get metrics
        metrics = perf_monitor.get_performance_report()

        # Notify
        if success:
            hooks.notify(
                f"Task completed: {task_description}",
                performance_data=metrics
            )
        else:
            hooks.notify(
                f"Task failed: {task_description} - {error}",
                performance_data=metrics
            )

    return {
        'success': success,
        'result': result,
        'error': error,
        'metrics': metrics
    }


# Convenience function for cleanup
def cleanup_with_hooks():
    """Cleanup all performance modules with hooks integration."""
    hooks = PerformanceHooks("Performance optimization cleanup")

    # Get managers
    cache_manager = get_cache_manager()
    session_manager = get_session_manager()
    perf_monitor = get_performance_monitor()

    # Cleanup
    cache_manager.cleanup()
    session_manager.close_all()
    perf_monitor.save_metrics()

    # Session end hook with metrics export
    hooks.session_end(export_metrics=True)

    logger.info("Cleanup with hooks completed")

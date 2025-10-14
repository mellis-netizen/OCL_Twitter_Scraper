"""
Performance monitoring middleware for FastAPI
Tracks response times, logs slow requests, and collects metrics
"""

import time
import logging
from typing import Callable
from datetime import datetime, timezone

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from .database import DatabaseManager
from .models import SystemMetrics

logger = logging.getLogger(__name__)


class PerformanceMonitoringMiddleware(BaseHTTPMiddleware):
    """
    Middleware to monitor API performance
    - Tracks response times
    - Logs slow requests
    - Records metrics to database
    - Adds performance headers
    """

    def __init__(
        self,
        app: ASGIApp,
        slow_threshold: float = 1.0,
        log_all_requests: bool = False,
        record_metrics: bool = True
    ):
        super().__init__(app)
        self.slow_threshold = slow_threshold  # Log requests slower than this (seconds)
        self.log_all_requests = log_all_requests
        self.record_metrics = record_metrics

        # Performance tracking
        self.request_count = 0
        self.total_response_time = 0.0
        self.slow_request_count = 0

        # Endpoint-specific tracking
        self.endpoint_stats = {}

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and track performance"""

        # Start timing
        start_time = time.time()

        # Get request info
        method = request.method
        path = request.url.path
        endpoint_key = f"{method} {path}"

        # Process request
        try:
            response = await call_next(request)
            status_code = response.status_code
            error = None

        except Exception as e:
            logger.error(f"Error processing request {endpoint_key}: {e}", exc_info=True)
            status_code = 500
            error = str(e)
            raise

        finally:
            # Calculate response time
            response_time = time.time() - start_time

            # Update statistics
            self.request_count += 1
            self.total_response_time += response_time

            # Track endpoint-specific stats
            if endpoint_key not in self.endpoint_stats:
                self.endpoint_stats[endpoint_key] = {
                    'count': 0,
                    'total_time': 0.0,
                    'min_time': float('inf'),
                    'max_time': 0.0,
                    'slow_count': 0
                }

            stats = self.endpoint_stats[endpoint_key]
            stats['count'] += 1
            stats['total_time'] += response_time
            stats['min_time'] = min(stats['min_time'], response_time)
            stats['max_time'] = max(stats['max_time'], response_time)

            # Check if slow
            if response_time > self.slow_threshold:
                self.slow_request_count += 1
                stats['slow_count'] += 1

                logger.warning(
                    f"SLOW REQUEST: {endpoint_key} "
                    f"took {response_time:.2f}s (threshold: {self.slow_threshold}s) "
                    f"[Status: {status_code}]"
                )

            # Log all requests if enabled
            elif self.log_all_requests:
                logger.info(
                    f"{method} {path} "
                    f"completed in {response_time:.3f}s "
                    f"[Status: {status_code}]"
                )

            # Add performance headers to response
            response.headers["X-Process-Time"] = f"{response_time:.3f}"
            response.headers["X-Request-ID"] = str(self.request_count)

            # Record metrics to database (async, don't block response)
            if self.record_metrics and response_time > 0.1:  # Only record significant requests
                try:
                    self._record_metric_async(
                        endpoint=endpoint_key,
                        response_time=response_time,
                        status_code=status_code
                    )
                except Exception as e:
                    logger.debug(f"Failed to record metric: {e}")

        return response

    def _record_metric_async(self, endpoint: str, response_time: float, status_code: int):
        """Record performance metric to database (non-blocking)"""
        try:
            with DatabaseManager.get_session() as db:
                metric = SystemMetrics(
                    metric_type='api_performance',
                    metric_name=endpoint,
                    value=response_time,
                    unit='seconds',
                    tags={
                        'status_code': status_code,
                        'timestamp': datetime.now(timezone.utc).isoformat()
                    }
                )
                db.add(metric)
                db.commit()

        except Exception as e:
            logger.debug(f"Error recording metric: {e}")

    def get_statistics(self) -> dict:
        """Get overall performance statistics"""
        avg_response_time = (
            self.total_response_time / self.request_count
            if self.request_count > 0
            else 0
        )

        slow_rate = (
            self.slow_request_count / self.request_count * 100
            if self.request_count > 0
            else 0
        )

        # Calculate endpoint averages
        endpoint_averages = {}
        for endpoint, stats in self.endpoint_stats.items():
            avg_time = stats['total_time'] / stats['count'] if stats['count'] > 0 else 0
            endpoint_averages[endpoint] = {
                'avg_time': round(avg_time, 3),
                'min_time': round(stats['min_time'], 3),
                'max_time': round(stats['max_time'], 3),
                'count': stats['count'],
                'slow_count': stats['slow_count'],
                'slow_rate': round(stats['slow_count'] / stats['count'] * 100, 2) if stats['count'] > 0 else 0
            }

        return {
            'total_requests': self.request_count,
            'total_response_time': round(self.total_response_time, 2),
            'avg_response_time': round(avg_response_time, 3),
            'slow_request_count': self.slow_request_count,
            'slow_request_rate': round(slow_rate, 2),
            'endpoint_stats': endpoint_averages
        }

    def get_slowest_endpoints(self, limit: int = 10) -> list:
        """Get slowest endpoints by average response time"""
        endpoint_list = []

        for endpoint, stats in self.endpoint_stats.items():
            avg_time = stats['total_time'] / stats['count'] if stats['count'] > 0 else 0
            endpoint_list.append({
                'endpoint': endpoint,
                'avg_time': round(avg_time, 3),
                'max_time': round(stats['max_time'], 3),
                'count': stats['count'],
                'slow_count': stats['slow_count']
            })

        # Sort by average time descending
        endpoint_list.sort(key=lambda x: x['avg_time'], reverse=True)

        return endpoint_list[:limit]

    def reset_statistics(self):
        """Reset all performance statistics"""
        self.request_count = 0
        self.total_response_time = 0.0
        self.slow_request_count = 0
        self.endpoint_stats.clear()

        logger.info("Performance statistics reset")


def setup_performance_monitoring(app, slow_threshold: float = 1.0):
    """
    Setup performance monitoring for FastAPI app

    Args:
        app: FastAPI application
        slow_threshold: Threshold in seconds for logging slow requests

    Returns:
        PerformanceMonitoringMiddleware instance
    """
    middleware = PerformanceMonitoringMiddleware(
        app=app,
        slow_threshold=slow_threshold,
        log_all_requests=False,  # Set to True for debugging
        record_metrics=True
    )

    app.add_middleware(PerformanceMonitoringMiddleware, slow_threshold=slow_threshold)

    # Add performance statistics endpoint
    @app.get("/performance/stats")
    async def get_performance_stats():
        """Get API performance statistics"""
        return middleware.get_statistics()

    @app.get("/performance/slowest")
    async def get_slowest_endpoints(limit: int = 10):
        """Get slowest endpoints"""
        return middleware.get_slowest_endpoints(limit)

    @app.post("/performance/reset")
    async def reset_performance_stats():
        """Reset performance statistics"""
        middleware.reset_statistics()
        return {"message": "Performance statistics reset"}

    logger.info(f"Performance monitoring enabled (slow threshold: {slow_threshold}s)")

    return middleware


if __name__ == "__main__":
    print("Performance monitoring middleware configured")
    print("Add to FastAPI app with: setup_performance_monitoring(app, slow_threshold=1.0)")

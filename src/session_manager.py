"""
Shared Session Manager with Connection Pooling
Optimizes HTTP requests with connection reuse and intelligent pooling

Performance Targets:
- >80% connection reuse rate
- 50 concurrent connections pool
- Sub-100ms connection establishment
- Automatic retry with exponential backoff
"""

import logging
import time
from typing import Dict, Optional
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from urllib3 import PoolManager
from threading import Lock

logger = logging.getLogger(__name__)


class ConnectionMetrics:
    """Track connection pool metrics."""

    def __init__(self):
        self.total_requests = 0
        self.connection_reuses = 0
        self.connection_creates = 0
        self.retry_count = 0
        self.timeout_count = 0
        self.error_count = 0
        self.total_request_time = 0.0
        self.lock = Lock()

    def record_request(self, duration: float, reused: bool = False):
        """Record request metrics."""
        with self.lock:
            self.total_requests += 1
            self.total_request_time += duration
            if reused:
                self.connection_reuses += 1
            else:
                self.connection_creates += 1

    def record_retry(self):
        """Record retry attempt."""
        with self.lock:
            self.retry_count += 1

    def record_timeout(self):
        """Record timeout."""
        with self.lock:
            self.timeout_count += 1

    def record_error(self):
        """Record error."""
        with self.lock:
            self.error_count += 1

    def get_stats(self) -> Dict:
        """Get connection metrics."""
        with self.lock:
            reuse_rate = (self.connection_reuses / self.total_requests * 100) if self.total_requests > 0 else 0
            avg_duration = (self.total_request_time / self.total_requests) if self.total_requests > 0 else 0

            return {
                'total_requests': self.total_requests,
                'connection_reuse_rate': round(reuse_rate, 2),
                'connection_reuses': self.connection_reuses,
                'connection_creates': self.connection_creates,
                'retry_count': self.retry_count,
                'timeout_count': self.timeout_count,
                'error_count': self.error_count,
                'avg_request_duration_ms': round(avg_duration * 1000, 2)
            }


class OptimizedHTTPAdapter(HTTPAdapter):
    """Custom HTTP adapter with connection tracking."""

    def __init__(self, metrics: ConnectionMetrics, *args, **kwargs):
        self.metrics = metrics
        super().__init__(*args, **kwargs)

    def send(self, request, **kwargs):
        """Send request and track metrics."""
        start_time = time.time()

        try:
            # Check if connection is being reused
            # This is a heuristic based on connection pool state
            pool_key = self.get_connection(request.url, None).pool.pool
            reused = pool_key.qsize() > 0

            response = super().send(request, **kwargs)
            duration = time.time() - start_time

            self.metrics.record_request(duration, reused)
            return response

        except requests.exceptions.Timeout:
            self.metrics.record_timeout()
            raise
        except Exception:
            self.metrics.record_error()
            raise


class SharedSessionManager:
    """
    Shared session manager with optimized connection pooling.

    Features:
    - Connection pool size: 50 connections
    - Connection reuse >80% target
    - Automatic retry with exponential backoff + jitter
    - Request timeout management
    - Connection metrics tracking
    - Keep-alive optimization
    """

    def __init__(
        self,
        pool_connections: int = 50,
        pool_maxsize: int = 50,
        max_retries: int = 3,
        backoff_factor: float = 0.5,
        timeout: int = 30
    ):
        """
        Initialize session manager.

        Args:
            pool_connections: Number of connection pools to cache
            pool_maxsize: Maximum number of connections in pool
            max_retries: Maximum retry attempts
            backoff_factor: Backoff multiplier between retries
            timeout: Default request timeout in seconds
        """
        self.pool_connections = pool_connections
        self.pool_maxsize = pool_maxsize
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self.default_timeout = timeout

        # Metrics
        self.metrics = ConnectionMetrics()

        # Create sessions for different use cases
        self.sessions = {
            'default': self._create_session(),
            'rss': self._create_session(timeout=15),
            'twitter': self._create_session(timeout=30),
            'article': self._create_session(timeout=20)
        }

        logger.info(f"Session manager initialized with pool size: {pool_maxsize}")

    def _create_session(self, timeout: Optional[int] = None) -> requests.Session:
        """
        Create optimized session with connection pooling.

        Args:
            timeout: Custom timeout for this session

        Returns:
            Configured requests session
        """
        session = requests.Session()

        # Retry strategy with exponential backoff
        retry_strategy = Retry(
            total=self.max_retries,
            backoff_factor=self.backoff_factor,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS", "POST"],
            raise_on_status=False
        )

        # Create optimized adapter
        adapter = OptimizedHTTPAdapter(
            metrics=self.metrics,
            pool_connections=self.pool_connections,
            pool_maxsize=self.pool_maxsize,
            max_retries=retry_strategy,
            pool_block=False
        )

        session.mount('http://', adapter)
        session.mount('https://', adapter)

        # Optimized headers
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Cache-Control': 'max-age=0'
        })

        # Set default timeout
        if timeout:
            session.timeout = timeout
        else:
            session.timeout = self.default_timeout

        return session

    def get_session(self, session_type: str = 'default') -> requests.Session:
        """
        Get session for specific use case.

        Args:
            session_type: Type of session ('default', 'rss', 'twitter', 'article')

        Returns:
            Configured session
        """
        return self.sessions.get(session_type, self.sessions['default'])

    def request(
        self,
        method: str,
        url: str,
        session_type: str = 'default',
        timeout: Optional[int] = None,
        **kwargs
    ) -> requests.Response:
        """
        Make HTTP request with connection pooling.

        Args:
            method: HTTP method
            url: URL to request
            session_type: Session type to use
            timeout: Custom timeout
            **kwargs: Additional request arguments

        Returns:
            Response object
        """
        session = self.get_session(session_type)

        # Use session timeout if not specified
        if timeout is None:
            timeout = getattr(session, 'timeout', self.default_timeout)

        try:
            response = session.request(method, url, timeout=timeout, **kwargs)
            return response
        except requests.exceptions.RetryError:
            self.metrics.record_retry()
            raise
        except requests.exceptions.Timeout:
            self.metrics.record_timeout()
            raise
        except Exception:
            self.metrics.record_error()
            raise

    def get(self, url: str, session_type: str = 'default', **kwargs) -> requests.Response:
        """Convenience method for GET requests."""
        return self.request('GET', url, session_type, **kwargs)

    def post(self, url: str, session_type: str = 'default', **kwargs) -> requests.Response:
        """Convenience method for POST requests."""
        return self.request('POST', url, session_type, **kwargs)

    def head(self, url: str, session_type: str = 'default', **kwargs) -> requests.Response:
        """Convenience method for HEAD requests."""
        return self.request('HEAD', url, session_type, **kwargs)

    def get_metrics(self) -> Dict:
        """Get connection pool metrics."""
        return self.metrics.get_stats()

    def close_all(self):
        """Close all sessions and cleanup."""
        for session_name, session in self.sessions.items():
            try:
                session.close()
                logger.debug(f"Closed {session_name} session")
            except Exception as e:
                logger.warning(f"Error closing {session_name} session: {e}")

        # Log final metrics
        final_metrics = self.get_metrics()
        logger.info(f"Session manager final metrics: {final_metrics}")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close_all()


# Global session manager instance
_session_manager = None


def get_session_manager() -> SharedSessionManager:
    """Get global session manager instance."""
    global _session_manager
    if _session_manager is None:
        _session_manager = SharedSessionManager()
    return _session_manager


def close_session_manager():
    """Close global session manager."""
    global _session_manager
    if _session_manager is not None:
        _session_manager.close_all()
        _session_manager = None

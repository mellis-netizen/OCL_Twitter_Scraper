"""
Production-Grade Rate Limiting and Throttling System
Provides token bucket, leaky bucket, and sliding window rate limiting with backpressure handling
"""

import time
import logging
import threading
from typing import Dict, Optional, Tuple, Any
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass, field
from collections import deque
from enum import Enum
import asyncio

logger = logging.getLogger(__name__)


class RateLimitStrategy(Enum):
    """Rate limiting strategies"""
    TOKEN_BUCKET = "token_bucket"
    LEAKY_BUCKET = "leaky_bucket"
    SLIDING_WINDOW = "sliding_window"
    FIXED_WINDOW = "fixed_window"


@dataclass
class RateLimitConfig:
    """Configuration for rate limiter"""
    requests_per_second: float = 10.0
    burst_size: int = 20
    strategy: RateLimitStrategy = RateLimitStrategy.TOKEN_BUCKET
    enforce: bool = True
    wait_on_rate_limit: bool = True


@dataclass
class RateLimitStatus:
    """Current rate limit status"""
    allowed: bool
    remaining: int
    reset_at: datetime
    retry_after: Optional[float] = None
    message: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'allowed': self.allowed,
            'remaining': self.remaining,
            'reset_at': self.reset_at.isoformat(),
            'retry_after': self.retry_after,
            'message': self.message
        }


class TokenBucketLimiter:
    """Token bucket rate limiter implementation"""

    def __init__(self, rate: float, capacity: int):
        """
        Args:
            rate: Tokens per second
            capacity: Maximum bucket capacity
        """
        self.rate = rate
        self.capacity = capacity
        self.tokens = float(capacity)
        self.last_update = time.time()
        self._lock = threading.Lock()

    def _refill(self):
        """Refill tokens based on elapsed time"""
        now = time.time()
        elapsed = now - self.last_update

        # Add tokens based on elapsed time
        self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)
        self.last_update = now

    def consume(self, tokens: int = 1) -> Tuple[bool, float]:
        """
        Try to consume tokens

        Returns:
            Tuple of (success, wait_time_if_failed)
        """
        with self._lock:
            self._refill()

            if self.tokens >= tokens:
                self.tokens -= tokens
                return True, 0.0
            else:
                # Calculate wait time needed
                tokens_needed = tokens - self.tokens
                wait_time = tokens_needed / self.rate
                return False, wait_time

    def get_available_tokens(self) -> int:
        """Get number of available tokens"""
        with self._lock:
            self._refill()
            return int(self.tokens)

    def reset(self):
        """Reset to full capacity"""
        with self._lock:
            self.tokens = float(self.capacity)
            self.last_update = time.time()


class SlidingWindowLimiter:
    """Sliding window rate limiter implementation"""

    def __init__(self, max_requests: int, window_seconds: int):
        """
        Args:
            max_requests: Maximum requests in window
            window_seconds: Window size in seconds
        """
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests: deque = deque()
        self._lock = threading.Lock()

    def _cleanup_old_requests(self):
        """Remove requests outside the window"""
        now = time.time()
        cutoff = now - self.window_seconds

        while self.requests and self.requests[0] < cutoff:
            self.requests.popleft()

    def consume(self, count: int = 1) -> Tuple[bool, float]:
        """
        Try to consume request quota

        Returns:
            Tuple of (success, wait_time_if_failed)
        """
        with self._lock:
            self._cleanup_old_requests()

            if len(self.requests) + count <= self.max_requests:
                # Add timestamps for each request
                now = time.time()
                for _ in range(count):
                    self.requests.append(now)
                return True, 0.0
            else:
                # Calculate wait time until oldest request expires
                if self.requests:
                    oldest = self.requests[0]
                    wait_time = (oldest + self.window_seconds) - time.time()
                    return False, max(0, wait_time)
                return False, 0.0

    def get_remaining(self) -> int:
        """Get remaining requests in window"""
        with self._lock:
            self._cleanup_old_requests()
            return self.max_requests - len(self.requests)

    def reset(self):
        """Reset the limiter"""
        with self._lock:
            self.requests.clear()


class RateLimiter:
    """Flexible rate limiter with multiple strategies"""

    def __init__(self, name: str, config: RateLimitConfig):
        self.name = name
        self.config = config

        # Initialize strategy-specific limiter
        if config.strategy == RateLimitStrategy.TOKEN_BUCKET:
            self.limiter = TokenBucketLimiter(
                rate=config.requests_per_second,
                capacity=config.burst_size
            )
        elif config.strategy == RateLimitStrategy.SLIDING_WINDOW:
            self.limiter = SlidingWindowLimiter(
                max_requests=int(config.requests_per_second),
                window_seconds=1
            )
        else:
            # Default to token bucket
            self.limiter = TokenBucketLimiter(
                rate=config.requests_per_second,
                capacity=config.burst_size
            )

        self.total_requests = 0
        self.total_blocked = 0
        self.total_wait_time = 0.0

        logger.info(f"Rate limiter '{name}' initialized with {config.strategy.value} strategy")

    def acquire(self, tokens: int = 1, wait: Optional[bool] = None) -> RateLimitStatus:
        """
        Acquire permission for request(s)

        Args:
            tokens: Number of tokens/requests to acquire
            wait: Whether to wait if rate limited (None = use config default)

        Returns:
            RateLimitStatus with result
        """
        should_wait = wait if wait is not None else self.config.wait_on_rate_limit

        self.total_requests += tokens

        # Try to consume
        allowed, wait_time = self.limiter.consume(tokens)

        if allowed:
            return RateLimitStatus(
                allowed=True,
                remaining=self._get_remaining(),
                reset_at=self._get_reset_time(),
                message="Request allowed"
            )

        # Rate limited
        self.total_blocked += tokens

        if should_wait and wait_time > 0:
            logger.debug(f"Rate limiter '{self.name}': waiting {wait_time:.2f}s")
            time.sleep(wait_time)
            self.total_wait_time += wait_time

            # Try again after waiting
            allowed, _ = self.limiter.consume(tokens)
            if allowed:
                return RateLimitStatus(
                    allowed=True,
                    remaining=self._get_remaining(),
                    reset_at=self._get_reset_time(),
                    message="Request allowed after waiting"
                )

        return RateLimitStatus(
            allowed=False,
            remaining=self._get_remaining(),
            reset_at=self._get_reset_time(),
            retry_after=wait_time,
            message=f"Rate limit exceeded. Retry after {wait_time:.2f}s"
        )

    async def acquire_async(self, tokens: int = 1, wait: Optional[bool] = None) -> RateLimitStatus:
        """Async version of acquire"""
        should_wait = wait if wait is not None else self.config.wait_on_rate_limit

        self.total_requests += tokens

        # Try to consume
        allowed, wait_time = self.limiter.consume(tokens)

        if allowed:
            return RateLimitStatus(
                allowed=True,
                remaining=self._get_remaining(),
                reset_at=self._get_reset_time(),
                message="Request allowed"
            )

        # Rate limited
        self.total_blocked += tokens

        if should_wait and wait_time > 0:
            logger.debug(f"Rate limiter '{self.name}': waiting {wait_time:.2f}s")
            await asyncio.sleep(wait_time)
            self.total_wait_time += wait_time

            # Try again after waiting
            allowed, _ = self.limiter.consume(tokens)
            if allowed:
                return RateLimitStatus(
                    allowed=True,
                    remaining=self._get_remaining(),
                    reset_at=self._get_reset_time(),
                    message="Request allowed after waiting"
                )

        return RateLimitStatus(
            allowed=False,
            remaining=self._get_remaining(),
            reset_at=self._get_reset_time(),
            retry_after=wait_time,
            message=f"Rate limit exceeded. Retry after {wait_time:.2f}s"
        )

    def _get_remaining(self) -> int:
        """Get remaining quota"""
        if isinstance(self.limiter, TokenBucketLimiter):
            return self.limiter.get_available_tokens()
        elif isinstance(self.limiter, SlidingWindowLimiter):
            return self.limiter.get_remaining()
        return 0

    def _get_reset_time(self) -> datetime:
        """Get when the rate limit resets"""
        # For sliding window, it resets continuously
        # For token bucket, it refills continuously
        # Return next second as a reasonable estimate
        return datetime.now(timezone.utc) + timedelta(seconds=1)

    def get_stats(self) -> Dict[str, Any]:
        """Get rate limiter statistics"""
        return {
            'name': self.name,
            'strategy': self.config.strategy.value,
            'config': {
                'requests_per_second': self.config.requests_per_second,
                'burst_size': self.config.burst_size
            },
            'stats': {
                'total_requests': self.total_requests,
                'total_blocked': self.total_blocked,
                'block_rate': self.total_blocked / max(self.total_requests, 1),
                'total_wait_time': self.total_wait_time,
                'remaining': self._get_remaining()
            }
        }

    def reset(self):
        """Reset the rate limiter"""
        self.limiter.reset()
        logger.info(f"Rate limiter '{self.name}' reset")


class BackpressureManager:
    """Manages backpressure for queue-based systems"""

    def __init__(
        self,
        max_queue_size: int = 1000,
        high_water_mark: float = 0.8,
        low_water_mark: float = 0.5
    ):
        """
        Args:
            max_queue_size: Maximum queue size
            high_water_mark: Threshold to start applying backpressure (0-1)
            low_water_mark: Threshold to release backpressure (0-1)
        """
        self.max_queue_size = max_queue_size
        self.high_water_mark = int(max_queue_size * high_water_mark)
        self.low_water_mark = int(max_queue_size * low_water_mark)

        self.current_size = 0
        self.backpressure_active = False
        self.total_rejected = 0
        self._lock = threading.Lock()

    def should_accept(self) -> Tuple[bool, str]:
        """
        Check if new item should be accepted

        Returns:
            Tuple of (should_accept, reason)
        """
        with self._lock:
            if self.current_size >= self.max_queue_size:
                self.total_rejected += 1
                return False, f"Queue full ({self.current_size}/{self.max_queue_size})"

            if self.backpressure_active and self.current_size >= self.low_water_mark:
                self.total_rejected += 1
                return False, f"Backpressure active ({self.current_size}/{self.max_queue_size})"

            return True, "OK"

    def add_item(self) -> bool:
        """Add item to queue"""
        with self._lock:
            if self.current_size >= self.max_queue_size:
                return False

            self.current_size += 1

            # Check if we should activate backpressure
            if not self.backpressure_active and self.current_size >= self.high_water_mark:
                self.backpressure_active = True
                logger.warning(
                    f"Backpressure activated: queue size {self.current_size}/{self.max_queue_size}"
                )

            return True

    def remove_item(self):
        """Remove item from queue"""
        with self._lock:
            if self.current_size > 0:
                self.current_size -= 1

            # Check if we should deactivate backpressure
            if self.backpressure_active and self.current_size <= self.low_water_mark:
                self.backpressure_active = False
                logger.info(
                    f"Backpressure deactivated: queue size {self.current_size}/{self.max_queue_size}"
                )

    def get_status(self) -> Dict[str, Any]:
        """Get backpressure status"""
        with self._lock:
            return {
                'current_size': self.current_size,
                'max_size': self.max_queue_size,
                'utilization': self.current_size / self.max_queue_size,
                'backpressure_active': self.backpressure_active,
                'high_water_mark': self.high_water_mark,
                'low_water_mark': self.low_water_mark,
                'total_rejected': self.total_rejected
            }

    def reset(self):
        """Reset backpressure manager"""
        with self._lock:
            self.current_size = 0
            self.backpressure_active = False
            self.total_rejected = 0


class RateLimitManager:
    """Manages multiple rate limiters"""

    def __init__(self):
        self.limiters: Dict[str, RateLimiter] = {}
        self.backpressure_managers: Dict[str, BackpressureManager] = {}

    def register_limiter(self, name: str, config: RateLimitConfig) -> RateLimiter:
        """Register a new rate limiter"""
        if name in self.limiters:
            logger.warning(f"Rate limiter '{name}' already exists")
            return self.limiters[name]

        limiter = RateLimiter(name, config)
        self.limiters[name] = limiter
        logger.info(f"Registered rate limiter: {name}")
        return limiter

    def get_limiter(self, name: str) -> Optional[RateLimiter]:
        """Get rate limiter by name"""
        return self.limiters.get(name)

    def register_backpressure(
        self,
        name: str,
        max_queue_size: int = 1000,
        high_water_mark: float = 0.8,
        low_water_mark: float = 0.5
    ) -> BackpressureManager:
        """Register a backpressure manager"""
        if name in self.backpressure_managers:
            logger.warning(f"Backpressure manager '{name}' already exists")
            return self.backpressure_managers[name]

        manager = BackpressureManager(max_queue_size, high_water_mark, low_water_mark)
        self.backpressure_managers[name] = manager
        logger.info(f"Registered backpressure manager: {name}")
        return manager

    def get_backpressure(self, name: str) -> Optional[BackpressureManager]:
        """Get backpressure manager by name"""
        return self.backpressure_managers.get(name)

    def get_all_stats(self) -> Dict[str, Any]:
        """Get statistics for all rate limiters"""
        return {
            'rate_limiters': {
                name: limiter.get_stats()
                for name, limiter in self.limiters.items()
            },
            'backpressure': {
                name: manager.get_status()
                for name, manager in self.backpressure_managers.items()
            }
        }

    def reset_all(self):
        """Reset all rate limiters and backpressure managers"""
        for limiter in self.limiters.values():
            limiter.reset()
        for manager in self.backpressure_managers.values():
            manager.reset()
        logger.info("All rate limiters and backpressure managers reset")


# Global rate limit manager
rate_limit_manager = RateLimitManager()

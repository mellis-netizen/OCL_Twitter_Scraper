"""
Production-Grade Error Handling and Recovery System
Provides comprehensive error handling with retry logic, circuit breakers, and graceful degradation
"""

import logging
import time
import functools
import asyncio
from typing import Optional, Callable, Any, Dict, List, Type, Union
from datetime import datetime, timedelta, timezone
from enum import Enum
from dataclasses import dataclass, field
from collections import defaultdict
import traceback

logger = logging.getLogger(__name__)


class ErrorSeverity(Enum):
    """Error severity levels for categorization"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class CircuitState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing if service recovered


@dataclass
class RetryConfig:
    """Configuration for retry behavior"""
    max_attempts: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    exponential_base: float = 2.0
    jitter: bool = True
    retryable_exceptions: tuple = (Exception,)
    non_retryable_exceptions: tuple = (ValueError, KeyError, TypeError)


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker"""
    failure_threshold: int = 5
    success_threshold: int = 2
    timeout: float = 60.0
    half_open_timeout: float = 30.0
    excluded_exceptions: tuple = (ValueError, KeyError)


@dataclass
class ErrorMetrics:
    """Track error metrics for monitoring"""
    total_errors: int = 0
    errors_by_type: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    errors_by_severity: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    last_error_time: Optional[datetime] = None
    error_rate: float = 0.0

    def record_error(self, error_type: str, severity: ErrorSeverity):
        """Record an error occurrence"""
        self.total_errors += 1
        self.errors_by_type[error_type] += 1
        self.errors_by_severity[severity.value] += 1
        self.last_error_time = datetime.now(timezone.utc)

    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary"""
        return {
            'total_errors': self.total_errors,
            'errors_by_type': dict(self.errors_by_type),
            'errors_by_severity': dict(self.errors_by_severity),
            'last_error_time': self.last_error_time.isoformat() if self.last_error_time else None,
            'error_rate': self.error_rate
        }


class CircuitBreaker:
    """Circuit breaker pattern implementation for external service calls"""

    def __init__(self, name: str, config: Optional[CircuitBreakerConfig] = None):
        self.name = name
        self.config = config or CircuitBreakerConfig()
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.last_state_change: datetime = datetime.now(timezone.utc)

        logger.info(f"Circuit breaker '{name}' initialized in CLOSED state")

    def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with circuit breaker protection"""
        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                logger.info(f"Circuit breaker '{self.name}' attempting reset (HALF_OPEN)")
                self.state = CircuitState.HALF_OPEN
                self.success_count = 0
            else:
                raise CircuitBreakerOpenError(
                    f"Circuit breaker '{self.name}' is OPEN. "
                    f"Service unavailable for {self.config.timeout}s"
                )

        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            if not isinstance(e, self.config.excluded_exceptions):
                self._on_failure()
            raise

    async def call_async(self, func: Callable, *args, **kwargs) -> Any:
        """Execute async function with circuit breaker protection"""
        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                logger.info(f"Circuit breaker '{self.name}' attempting reset (HALF_OPEN)")
                self.state = CircuitState.HALF_OPEN
                self.success_count = 0
            else:
                raise CircuitBreakerOpenError(
                    f"Circuit breaker '{self.name}' is OPEN. "
                    f"Service unavailable for {self.config.timeout}s"
                )

        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            if not isinstance(e, self.config.excluded_exceptions):
                self._on_failure()
            raise

    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset"""
        if not self.last_failure_time:
            return True

        time_since_failure = (datetime.now(timezone.utc) - self.last_failure_time).total_seconds()
        return time_since_failure >= self.config.timeout

    def _on_success(self):
        """Handle successful call"""
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.config.success_threshold:
                logger.info(f"Circuit breaker '{self.name}' closing (service recovered)")
                self.state = CircuitState.CLOSED
                self.failure_count = 0
                self.success_count = 0
                self.last_state_change = datetime.now(timezone.utc)
        elif self.state == CircuitState.CLOSED:
            self.failure_count = max(0, self.failure_count - 1)

    def _on_failure(self):
        """Handle failed call"""
        self.failure_count += 1
        self.last_failure_time = datetime.now(timezone.utc)

        if self.state == CircuitState.HALF_OPEN:
            logger.warning(f"Circuit breaker '{self.name}' re-opening (recovery failed)")
            self.state = CircuitState.OPEN
            self.success_count = 0
            self.last_state_change = datetime.now(timezone.utc)
        elif self.state == CircuitState.CLOSED:
            if self.failure_count >= self.config.failure_threshold:
                logger.error(f"Circuit breaker '{self.name}' opening (failure threshold reached)")
                self.state = CircuitState.OPEN
                self.last_state_change = datetime.now(timezone.utc)

    def get_state(self) -> Dict[str, Any]:
        """Get current circuit breaker state"""
        return {
            'name': self.name,
            'state': self.state.value,
            'failure_count': self.failure_count,
            'success_count': self.success_count,
            'last_failure_time': self.last_failure_time.isoformat() if self.last_failure_time else None,
            'last_state_change': self.last_state_change.isoformat()
        }

    def reset(self):
        """Manually reset circuit breaker"""
        logger.info(f"Circuit breaker '{self.name}' manually reset")
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
        self.last_state_change = datetime.now(timezone.utc)


class CircuitBreakerOpenError(Exception):
    """Raised when circuit breaker is open"""
    pass


class RetryExhaustedError(Exception):
    """Raised when all retry attempts are exhausted"""
    pass


def with_retry(config: Optional[RetryConfig] = None):
    """
    Decorator for automatic retry with exponential backoff

    Usage:
        @with_retry(RetryConfig(max_attempts=3, base_delay=1.0))
        def fetch_data():
            # Your code here
            pass
    """
    if config is None:
        config = RetryConfig()

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            last_exception = None

            for attempt in range(1, config.max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except config.non_retryable_exceptions as e:
                    logger.error(f"Non-retryable error in {func.__name__}: {str(e)}")
                    raise
                except config.retryable_exceptions as e:
                    last_exception = e

                    if attempt == config.max_attempts:
                        break

                    delay = min(
                        config.base_delay * (config.exponential_base ** (attempt - 1)),
                        config.max_delay
                    )

                    if config.jitter:
                        import random
                        delay *= (0.5 + random.random())

                    logger.warning(
                        f"Attempt {attempt}/{config.max_attempts} failed for {func.__name__}: {str(e)}. "
                        f"Retrying in {delay:.2f}s..."
                    )
                    time.sleep(delay)

            raise RetryExhaustedError(
                f"All {config.max_attempts} retry attempts exhausted for {func.__name__}"
            ) from last_exception

        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            last_exception = None

            for attempt in range(1, config.max_attempts + 1):
                try:
                    return await func(*args, **kwargs)
                except config.non_retryable_exceptions as e:
                    logger.error(f"Non-retryable error in {func.__name__}: {str(e)}")
                    raise
                except config.retryable_exceptions as e:
                    last_exception = e

                    if attempt == config.max_attempts:
                        break

                    delay = min(
                        config.base_delay * (config.exponential_base ** (attempt - 1)),
                        config.max_delay
                    )

                    if config.jitter:
                        import random
                        delay *= (0.5 + random.random())

                    logger.warning(
                        f"Attempt {attempt}/{config.max_attempts} failed for {func.__name__}: {str(e)}. "
                        f"Retrying in {delay:.2f}s..."
                    )
                    await asyncio.sleep(delay)

            raise RetryExhaustedError(
                f"All {config.max_attempts} retry attempts exhausted for {func.__name__}"
            ) from last_exception

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


class ErrorHandler:
    """Centralized error handling system"""

    def __init__(self):
        self.metrics = ErrorMetrics()
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self.error_callbacks: List[Callable] = []

    def register_circuit_breaker(self, name: str, config: Optional[CircuitBreakerConfig] = None) -> CircuitBreaker:
        """Register a new circuit breaker"""
        if name in self.circuit_breakers:
            return self.circuit_breakers[name]

        circuit_breaker = CircuitBreaker(name, config)
        self.circuit_breakers[name] = circuit_breaker
        logger.info(f"Registered circuit breaker: {name}")
        return circuit_breaker

    def get_circuit_breaker(self, name: str) -> Optional[CircuitBreaker]:
        """Get circuit breaker by name"""
        return self.circuit_breakers.get(name)

    def register_error_callback(self, callback: Callable):
        """Register callback to be called on errors"""
        self.error_callbacks.append(callback)

    def handle_error(
        self,
        error: Exception,
        context: str,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        additional_info: Optional[Dict[str, Any]] = None
    ):
        """Handle an error with proper logging and metrics"""
        error_type = type(error).__name__

        # Record metrics
        self.metrics.record_error(error_type, severity)

        # Log error with appropriate level
        log_message = f"Error in {context}: {str(error)}"
        if additional_info:
            log_message += f" | Additional info: {additional_info}"

        if severity == ErrorSeverity.CRITICAL:
            logger.critical(log_message, exc_info=True)
        elif severity == ErrorSeverity.HIGH:
            logger.error(log_message, exc_info=True)
        elif severity == ErrorSeverity.MEDIUM:
            logger.warning(log_message)
        else:
            logger.info(log_message)

        # Execute callbacks
        for callback in self.error_callbacks:
            try:
                callback(error, context, severity, additional_info)
            except Exception as e:
                logger.error(f"Error in error callback: {str(e)}")

    def get_metrics(self) -> Dict[str, Any]:
        """Get all error metrics"""
        return {
            'error_metrics': self.metrics.to_dict(),
            'circuit_breakers': {
                name: cb.get_state()
                for name, cb in self.circuit_breakers.items()
            }
        }

    def reset_circuit_breaker(self, name: str):
        """Manually reset a circuit breaker"""
        if name in self.circuit_breakers:
            self.circuit_breakers[name].reset()
        else:
            logger.warning(f"Circuit breaker '{name}' not found")

    def reset_all_circuit_breakers(self):
        """Reset all circuit breakers"""
        for cb in self.circuit_breakers.values():
            cb.reset()
        logger.info("All circuit breakers reset")


# Global error handler instance
error_handler = ErrorHandler()


def with_circuit_breaker(name: str, config: Optional[CircuitBreakerConfig] = None):
    """
    Decorator for circuit breaker protection

    Usage:
        @with_circuit_breaker("twitter_api")
        def fetch_tweets():
            # Your code here
            pass
    """
    circuit_breaker = error_handler.register_circuit_breaker(name, config)

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            return circuit_breaker.call(func, *args, **kwargs)

        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            return await circuit_breaker.call_async(func, *args, **kwargs)

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


class GracefulDegradation:
    """Provides fallback mechanisms for graceful degradation"""

    @staticmethod
    def with_fallback(primary_func: Callable, fallback_func: Callable, *fallback_args, **fallback_kwargs):
        """
        Execute primary function, fall back to fallback function on failure

        Usage:
            result = GracefulDegradation.with_fallback(
                fetch_from_api,
                fetch_from_cache,
                cache_key="data"
            )
        """
        try:
            return primary_func()
        except Exception as e:
            logger.warning(f"Primary function failed: {str(e)}, using fallback")
            try:
                return fallback_func(*fallback_args, **fallback_kwargs)
            except Exception as fallback_error:
                logger.error(f"Fallback also failed: {str(fallback_error)}")
                raise

    @staticmethod
    async def with_fallback_async(
        primary_func: Callable,
        fallback_func: Callable,
        *fallback_args,
        **fallback_kwargs
    ):
        """Async version of with_fallback"""
        try:
            return await primary_func()
        except Exception as e:
            logger.warning(f"Primary function failed: {str(e)}, using fallback")
            try:
                return await fallback_func(*fallback_args, **fallback_kwargs)
            except Exception as fallback_error:
                logger.error(f"Fallback also failed: {str(fallback_error)}")
                raise


class DeadLetterQueue:
    """Dead letter queue for failed operations"""

    def __init__(self, max_size: int = 1000):
        self.queue: List[Dict[str, Any]] = []
        self.max_size = max_size

    def add(self, operation: str, data: Any, error: Exception, context: Optional[Dict] = None):
        """Add failed operation to dead letter queue"""
        entry = {
            'operation': operation,
            'data': data,
            'error': str(error),
            'error_type': type(error).__name__,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'context': context or {},
            'traceback': traceback.format_exc()
        }

        self.queue.append(entry)

        # Maintain max size
        if len(self.queue) > self.max_size:
            self.queue.pop(0)

        logger.warning(f"Added to dead letter queue: {operation}")

    def get_all(self) -> List[Dict[str, Any]]:
        """Get all items in dead letter queue"""
        return self.queue.copy()

    def get_by_operation(self, operation: str) -> List[Dict[str, Any]]:
        """Get items by operation type"""
        return [item for item in self.queue if item['operation'] == operation]

    def clear(self):
        """Clear dead letter queue"""
        self.queue.clear()
        logger.info("Dead letter queue cleared")

    def size(self) -> int:
        """Get current queue size"""
        return len(self.queue)


# Global dead letter queue
dead_letter_queue = DeadLetterQueue()

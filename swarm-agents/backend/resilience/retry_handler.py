#!/usr/bin/env python3
"""
Advanced Retry Handler with Exponential Backoff and Jitter
Provides robust retry mechanisms for TGE Swarm services
"""

import asyncio
import random
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable, Union, Type
from dataclasses import dataclass
from enum import Enum
from functools import wraps
import math


class BackoffStrategy(Enum):
    """Backoff strategies for retries"""
    FIXED = "fixed"
    LINEAR = "linear"
    EXPONENTIAL = "exponential"
    EXPONENTIAL_JITTER = "exponential_jitter"
    DECORRELATED_JITTER = "decorrelated_jitter"


class RetryCondition(Enum):
    """Conditions for when to retry"""
    ON_EXCEPTION = "on_exception"
    ON_RESULT = "on_result"
    ON_TIMEOUT = "on_timeout"
    CUSTOM = "custom"


@dataclass
class RetryConfig:
    """Retry configuration"""
    max_attempts: int = 3
    base_delay: float = 1.0  # Base delay in seconds
    max_delay: float = 60.0  # Maximum delay in seconds
    backoff_strategy: BackoffStrategy = BackoffStrategy.EXPONENTIAL_JITTER
    jitter_max: float = 0.1  # Maximum jitter as fraction of delay
    
    # Exception handling
    retryable_exceptions: tuple = (Exception,)
    non_retryable_exceptions: tuple = ()
    
    # Timeout settings
    timeout: Optional[float] = None
    
    # Custom retry conditions
    retry_condition: Optional[Callable] = None
    
    # Multipliers for different strategies
    exponential_base: float = 2.0
    linear_increment: float = 1.0


@dataclass
class RetryAttempt:
    """Record of a retry attempt"""
    attempt_number: int
    timestamp: datetime
    delay: float
    success: bool
    error: Optional[str] = None
    duration: float = 0.0


class RetryHandler:
    """Advanced retry handler with multiple backoff strategies"""
    
    def __init__(self, name: str, config: RetryConfig = None):
        self.name = name
        self.config = config or RetryConfig()
        self.attempt_history: List[RetryAttempt] = []
        
        # Metrics
        self.total_calls = 0
        self.total_retries = 0
        self.total_successes = 0
        self.total_failures = 0
        
        self.logger = logging.getLogger(f"RetryHandler.{name}")
    
    async def execute(self, func: Callable, *args, **kwargs):
        """Execute function with retry logic"""
        self.total_calls += 1
        last_exception = None
        
        for attempt in range(1, self.config.max_attempts + 1):
            start_time = time.time()
            
            try:
                # Apply timeout if configured
                if self.config.timeout:
                    if asyncio.iscoroutinefunction(func):
                        result = await asyncio.wait_for(
                            func(*args, **kwargs),
                            timeout=self.config.timeout
                        )
                    else:
                        # For sync functions, we can't easily apply timeout
                        result = func(*args, **kwargs)
                else:
                    if asyncio.iscoroutinefunction(func):
                        result = await func(*args, **kwargs)
                    else:
                        result = func(*args, **kwargs)
                
                # Check custom retry condition
                if self.config.retry_condition and self.config.retry_condition(result):
                    if attempt < self.config.max_attempts:
                        duration = time.time() - start_time
                        self._record_attempt(attempt, False, "Custom retry condition", duration)
                        delay = self._calculate_delay(attempt)
                        await self._sleep_with_jitter(delay)
                        continue
                
                # Success
                duration = time.time() - start_time
                self._record_attempt(attempt, True, None, duration)
                self.total_successes += 1
                
                if attempt > 1:
                    self.total_retries += attempt - 1
                    self.logger.info(f"Succeeded on attempt {attempt} for {self.name}")
                
                return result
                
            except self.config.non_retryable_exceptions as e:
                # Non-retryable exception, fail immediately
                duration = time.time() - start_time
                self._record_attempt(attempt, False, str(e), duration)
                self.total_failures += 1
                self.logger.error(f"Non-retryable exception in {self.name}: {e}")
                raise
                
            except self.config.retryable_exceptions as e:
                duration = time.time() - start_time
                last_exception = e
                
                if attempt < self.config.max_attempts:
                    self._record_attempt(attempt, False, str(e), duration)
                    delay = self._calculate_delay(attempt)
                    
                    self.logger.warning(
                        f"Attempt {attempt} failed for {self.name}: {e}. "
                        f"Retrying in {delay:.2f}s"
                    )
                    
                    await self._sleep_with_jitter(delay)
                else:
                    # Final attempt failed
                    self._record_attempt(attempt, False, str(e), duration)
                    self.total_failures += 1
                    self.total_retries += attempt - 1
                    
                    self.logger.error(
                        f"All {attempt} attempts failed for {self.name}: {e}"
                    )
                    raise
            
            except asyncio.TimeoutError:
                duration = time.time() - start_time
                
                if attempt < self.config.max_attempts:
                    self._record_attempt(attempt, False, "timeout", duration)
                    delay = self._calculate_delay(attempt)
                    
                    self.logger.warning(
                        f"Attempt {attempt} timed out for {self.name}. "
                        f"Retrying in {delay:.2f}s"
                    )
                    
                    await self._sleep_with_jitter(delay)
                else:
                    self._record_attempt(attempt, False, "timeout", duration)
                    self.total_failures += 1
                    self.total_retries += attempt - 1
                    raise RetryTimeoutError(f"All attempts timed out for {self.name}")
        
        # Should not reach here, but just in case
        if last_exception:
            raise last_exception
        else:
            raise RetryExhaustionError(f"Retry attempts exhausted for {self.name}")
    
    def _calculate_delay(self, attempt: int) -> float:
        """Calculate delay based on backoff strategy"""
        if self.config.backoff_strategy == BackoffStrategy.FIXED:
            delay = self.config.base_delay
            
        elif self.config.backoff_strategy == BackoffStrategy.LINEAR:
            delay = self.config.base_delay + (attempt - 1) * self.config.linear_increment
            
        elif self.config.backoff_strategy == BackoffStrategy.EXPONENTIAL:
            delay = self.config.base_delay * (self.config.exponential_base ** (attempt - 1))
            
        elif self.config.backoff_strategy == BackoffStrategy.EXPONENTIAL_JITTER:
            base_delay = self.config.base_delay * (self.config.exponential_base ** (attempt - 1))
            jitter = random.uniform(0, self.config.jitter_max * base_delay)
            delay = base_delay + jitter
            
        elif self.config.backoff_strategy == BackoffStrategy.DECORRELATED_JITTER:
            # Decorrelated jitter as described in AWS Architecture Blog
            if attempt == 1:
                delay = self.config.base_delay
            else:
                prev_delay = getattr(self, '_last_delay', self.config.base_delay)
                delay = random.uniform(self.config.base_delay, prev_delay * 3)
            
            self._last_delay = delay
            
        else:
            delay = self.config.base_delay
        
        # Cap at maximum delay
        return min(delay, self.config.max_delay)
    
    async def _sleep_with_jitter(self, delay: float):
        """Sleep with optional jitter"""
        if self.config.backoff_strategy == BackoffStrategy.EXPONENTIAL_JITTER:
            # Jitter already applied in _calculate_delay
            await asyncio.sleep(delay)
        else:
            # Apply jitter here
            jitter = random.uniform(-self.config.jitter_max, self.config.jitter_max) * delay
            actual_delay = max(0, delay + jitter)
            await asyncio.sleep(actual_delay)
    
    def _record_attempt(self, attempt: int, success: bool, error: Optional[str], duration: float):
        """Record retry attempt"""
        self.attempt_history.append(RetryAttempt(
            attempt_number=attempt,
            timestamp=datetime.now(),
            delay=0,  # Delay is calculated before attempt, not recorded here
            success=success,
            error=error,
            duration=duration
        ))
        
        # Keep only recent history (last 100 attempts)
        if len(self.attempt_history) > 100:
            self.attempt_history = self.attempt_history[-100:]
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get retry handler metrics"""
        recent_attempts = self.attempt_history[-50:] if self.attempt_history else []
        
        if recent_attempts:
            success_rate = sum(1 for a in recent_attempts if a.success) / len(recent_attempts)
            avg_duration = sum(a.duration for a in recent_attempts) / len(recent_attempts)
            avg_attempts_per_call = len(recent_attempts) / max(1, len(set(a.timestamp.strftime('%Y%m%d%H%M%S%f') for a in recent_attempts)))
        else:
            success_rate = 0
            avg_duration = 0
            avg_attempts_per_call = 0
        
        return {
            'name': self.name,
            'total_calls': self.total_calls,
            'total_retries': self.total_retries,
            'total_successes': self.total_successes,
            'total_failures': self.total_failures,
            'success_rate': self.total_successes / max(self.total_calls, 1),
            'recent_success_rate': success_rate,
            'recent_avg_duration': avg_duration,
            'avg_attempts_per_call': avg_attempts_per_call,
            'config': {
                'max_attempts': self.config.max_attempts,
                'backoff_strategy': self.config.backoff_strategy.value,
                'base_delay': self.config.base_delay,
                'max_delay': self.config.max_delay
            }
        }
    
    def reset_metrics(self):
        """Reset retry metrics"""
        self.total_calls = 0
        self.total_retries = 0
        self.total_successes = 0
        self.total_failures = 0
        self.attempt_history.clear()


class RetryRegistry:
    """Registry for managing retry handlers"""
    
    def __init__(self):
        self.handlers: Dict[str, RetryHandler] = {}
        self.default_config = RetryConfig()
        self.logger = logging.getLogger("RetryRegistry")
    
    def get_handler(self, name: str, config: RetryConfig = None) -> RetryHandler:
        """Get or create retry handler"""
        if name not in self.handlers:
            handler_config = config or self.default_config
            self.handlers[name] = RetryHandler(name, handler_config)
            self.logger.info(f"Created retry handler: {name}")
        
        return self.handlers[name]
    
    def get_all_metrics(self) -> Dict[str, Dict[str, Any]]:
        """Get metrics for all retry handlers"""
        return {name: handler.get_metrics() for name, handler in self.handlers.items()}
    
    def reset_handler(self, name: str):
        """Reset specific retry handler"""
        if name in self.handlers:
            self.handlers[name].reset_metrics()
    
    def reset_all(self):
        """Reset all retry handlers"""
        for handler in self.handlers.values():
            handler.reset_metrics()


# Global registry instance
retry_registry = RetryRegistry()


# Decorator for easy retry application
def retry(name: str, config: RetryConfig = None):
    """Decorator to apply retry logic to a function"""
    def decorator(func):
        handler = retry_registry.get_handler(name, config)
        
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            return await handler.execute(func, *args, **kwargs)
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            return asyncio.run(handler.execute(func, *args, **kwargs))
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


# Retry with circuit breaker integration
def retry_with_circuit_breaker(retry_name: str, circuit_breaker_name: str, 
                              retry_config: RetryConfig = None):
    """Decorator combining retry and circuit breaker patterns"""
    from .circuit_breaker import circuit_breaker_registry
    
    def decorator(func):
        retry_handler = retry_registry.get_handler(retry_name, retry_config)
        circuit_breaker = circuit_breaker_registry.get_breaker(circuit_breaker_name)
        
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            async def circuit_breaker_wrapped():
                return await circuit_breaker.call(func, *args, **kwargs)
            
            return await retry_handler.execute(circuit_breaker_wrapped)
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            # For sync functions, create async wrapper
            async def async_func(*args, **kwargs):
                return func(*args, **kwargs)
            
            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                return asyncio.run(async_wrapper(*args, **kwargs))
            
            return sync_wrapper
    
    return decorator


# Custom exceptions
class RetryError(Exception):
    """Base exception for retry errors"""
    pass


class RetryExhaustionError(RetryError):
    """Raised when all retry attempts are exhausted"""
    pass


class RetryTimeoutError(RetryError):
    """Raised when retry attempts time out"""
    pass


# Utility functions for common retry patterns
def create_http_retry_config() -> RetryConfig:
    """Create retry config optimized for HTTP requests"""
    from aiohttp import ClientError, ServerTimeoutError
    
    return RetryConfig(
        max_attempts=3,
        base_delay=1.0,
        max_delay=30.0,
        backoff_strategy=BackoffStrategy.EXPONENTIAL_JITTER,
        retryable_exceptions=(ClientError, ServerTimeoutError, asyncio.TimeoutError),
        non_retryable_exceptions=(ValueError, TypeError),
        timeout=30.0
    )


def create_database_retry_config() -> RetryConfig:
    """Create retry config optimized for database operations"""
    return RetryConfig(
        max_attempts=5,
        base_delay=0.5,
        max_delay=10.0,
        backoff_strategy=BackoffStrategy.EXPONENTIAL_JITTER,
        retryable_exceptions=(ConnectionError, TimeoutError),
        timeout=60.0
    )


def create_message_queue_retry_config() -> RetryConfig:
    """Create retry config optimized for message queue operations"""
    return RetryConfig(
        max_attempts=3,
        base_delay=2.0,
        max_delay=60.0,
        backoff_strategy=BackoffStrategy.DECORRELATED_JITTER,
        retryable_exceptions=(ConnectionError, TimeoutError),
        timeout=30.0
    )


# Example usage and testing
if __name__ == "__main__":
    import random
    
    async def flaky_service(fail_probability: float = 0.5, delay: float = 0.1):
        """Simulate a flaky service"""
        await asyncio.sleep(delay)
        
        if random.random() < fail_probability:
            raise Exception("Service temporarily unavailable")
        
        return "success"
    
    async def test_retry_strategies():
        """Test different retry strategies"""
        strategies = [
            (BackoffStrategy.FIXED, "Fixed delay"),
            (BackoffStrategy.LINEAR, "Linear backoff"),
            (BackoffStrategy.EXPONENTIAL, "Exponential backoff"),
            (BackoffStrategy.EXPONENTIAL_JITTER, "Exponential with jitter"),
            (BackoffStrategy.DECORRELATED_JITTER, "Decorrelated jitter")
        ]
        
        for strategy, description in strategies:
            print(f"\nTesting {description}...")
            
            config = RetryConfig(
                max_attempts=4,
                base_delay=0.5,
                max_delay=5.0,
                backoff_strategy=strategy,
                retryable_exceptions=(Exception,)
            )
            
            handler = RetryHandler(f"test-{strategy.value}", config)
            
            try:
                start_time = time.time()
                result = await handler.execute(flaky_service, fail_probability=0.7)
                duration = time.time() - start_time
                print(f"  Success after {duration:.2f}s: {result}")
            except Exception as e:
                duration = time.time() - start_time
                print(f"  Failed after {duration:.2f}s: {e}")
            
            metrics = handler.get_metrics()
            print(f"  Attempts: {metrics['total_calls']}, Retries: {metrics['total_retries']}")
    
    # Test decorator
    @retry("decorated-service", RetryConfig(max_attempts=3, base_delay=0.1))
    async def decorated_flaky_service():
        if random.random() < 0.6:
            raise Exception("Random failure")
        return "decorated success"
    
    async def test_decorator():
        """Test retry decorator"""
        print("\nTesting retry decorator...")
        
        for i in range(3):
            try:
                result = await decorated_flaky_service()
                print(f"  Call {i+1}: {result}")
            except Exception as e:
                print(f"  Call {i+1} failed: {e}")
    
    async def test_custom_retry_condition():
        """Test custom retry condition"""
        print("\nTesting custom retry condition...")
        
        def should_retry(result):
            return result == "retry_me"
        
        async def service_with_custom_retry():
            if random.random() < 0.5:
                return "retry_me"
            return "success"
        
        config = RetryConfig(
            max_attempts=3,
            base_delay=0.1,
            retry_condition=should_retry
        )
        
        handler = RetryHandler("custom-retry", config)
        
        try:
            result = await handler.execute(service_with_custom_retry)
            print(f"  Final result: {result}")
        except Exception as e:
            print(f"  Failed: {e}")
    
    async def main():
        await test_retry_strategies()
        await test_decorator()
        await test_custom_retry_condition()
        
        # Show all metrics
        print("\nAll retry handler metrics:")
        all_metrics = retry_registry.get_all_metrics()
        for name, metrics in all_metrics.items():
            print(f"\n{name}:")
            for key, value in metrics.items():
                if isinstance(value, dict):
                    print(f"  {key}:")
                    for sub_key, sub_value in value.items():
                        print(f"    {sub_key}: {sub_value}")
                else:
                    print(f"  {key}: {value}")
    
    asyncio.run(main())
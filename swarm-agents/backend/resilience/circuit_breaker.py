#!/usr/bin/env python3
"""
Circuit Breaker Pattern Implementation for TGE Swarm
Provides resilience and fault tolerance for service communication
"""

import asyncio
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable, Union
from dataclasses import dataclass, field
from enum import Enum
import statistics
from functools import wraps


class CircuitState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"  # Normal operation
    OPEN = "open"      # Circuit is open, failing fast
    HALF_OPEN = "half_open"  # Testing if service is back


@dataclass
class CircuitBreakerConfig:
    """Circuit breaker configuration"""
    failure_threshold: int = 5  # Number of failures to trip circuit
    recovery_timeout: int = 60  # Seconds to wait before trying again
    expected_exception: type = Exception  # Exception type to count as failure
    success_threshold: int = 3  # Successful calls needed to close circuit in half-open state
    timeout: float = 30.0  # Request timeout in seconds
    
    # Sliding window configuration
    window_size: int = 60  # Size of sliding window in seconds
    minimum_requests: int = 10  # Minimum requests in window before evaluating
    
    # Advanced settings
    failure_rate_threshold: float = 0.5  # Failure rate threshold (0.0 to 1.0)
    slow_call_threshold: float = 5.0  # Threshold for slow calls in seconds
    slow_call_rate_threshold: float = 0.5  # Slow call rate threshold


@dataclass
class CallRecord:
    """Record of a service call"""
    timestamp: float
    success: bool
    duration: float
    error: Optional[str] = None


class CircuitBreaker:
    """Advanced circuit breaker with sliding window and rate-based detection"""
    
    def __init__(self, name: str, config: CircuitBreakerConfig = None):
        self.name = name
        self.config = config or CircuitBreakerConfig()
        
        # State management
        self.state = CircuitState.CLOSED
        self.last_failure_time = 0
        self.success_count = 0
        
        # Call tracking with sliding window
        self.call_history: List[CallRecord] = []
        self.consecutive_failures = 0
        
        # Metrics
        self.total_calls = 0
        self.total_failures = 0
        self.total_successes = 0
        self.total_timeouts = 0
        
        self.logger = logging.getLogger(f"CircuitBreaker.{name}")
    
    async def call(self, func: Callable, *args, **kwargs):
        """Execute function with circuit breaker protection"""
        current_time = time.time()
        
        # Check circuit state
        if self.state == CircuitState.OPEN:
            if current_time - self.last_failure_time >= self.config.recovery_timeout:
                self.state = CircuitState.HALF_OPEN
                self.success_count = 0
                self.logger.info(f"Circuit breaker {self.name} transitioning to HALF_OPEN")
            else:
                raise CircuitBreakerOpenError(f"Circuit breaker {self.name} is OPEN")
        
        # Execute call
        start_time = time.time()
        self.total_calls += 1
        
        try:
            # Apply timeout
            if asyncio.iscoroutinefunction(func):
                result = await asyncio.wait_for(
                    func(*args, **kwargs),
                    timeout=self.config.timeout
                )
            else:
                result = func(*args, **kwargs)
            
            # Record success
            duration = time.time() - start_time
            self._record_success(duration)
            
            return result
            
        except asyncio.TimeoutError:
            duration = time.time() - start_time
            self._record_failure(duration, "timeout")
            self.total_timeouts += 1
            raise CircuitBreakerTimeoutError(f"Call to {self.name} timed out after {self.config.timeout}s")
            
        except self.config.expected_exception as e:
            duration = time.time() - start_time
            self._record_failure(duration, str(e))
            raise
        
        except Exception as e:
            # Unexpected exception, don't count as circuit breaker failure
            duration = time.time() - start_time
            self.logger.warning(f"Unexpected exception in {self.name}: {e}")
            raise
    
    def _record_success(self, duration: float):
        """Record successful call"""
        current_time = time.time()
        
        # Add to call history
        self.call_history.append(CallRecord(
            timestamp=current_time,
            success=True,
            duration=duration
        ))
        
        self.total_successes += 1
        self.consecutive_failures = 0
        
        # State transitions
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.config.success_threshold:
                self.state = CircuitState.CLOSED
                self.logger.info(f"Circuit breaker {self.name} closed after {self.success_count} successful calls")
        
        # Clean old records
        self._clean_old_records()
        
        self.logger.debug(f"Successful call to {self.name} took {duration:.3f}s")
    
    def _record_failure(self, duration: float, error: str):
        """Record failed call"""
        current_time = time.time()
        
        # Add to call history
        self.call_history.append(CallRecord(
            timestamp=current_time,
            success=False,
            duration=duration,
            error=error
        ))
        
        self.total_failures += 1
        self.consecutive_failures += 1
        self.last_failure_time = current_time
        
        # Check if circuit should trip
        if self._should_trip_circuit():
            self.state = CircuitState.OPEN
            self.logger.warning(f"Circuit breaker {self.name} opened due to failures")
        
        # Clean old records
        self._clean_old_records()
        
        self.logger.warning(f"Failed call to {self.name} took {duration:.3f}s: {error}")
    
    def _should_trip_circuit(self) -> bool:
        """Determine if circuit should trip based on failure patterns"""
        # Check consecutive failures
        if self.consecutive_failures >= self.config.failure_threshold:
            return True
        
        # Check failure rate in sliding window
        window_calls = self._get_window_calls()
        
        if len(window_calls) < self.config.minimum_requests:
            return False
        
        # Calculate failure rate
        failures = sum(1 for call in window_calls if not call.success)
        failure_rate = failures / len(window_calls)
        
        if failure_rate >= self.config.failure_rate_threshold:
            return True
        
        # Check slow call rate
        slow_calls = sum(1 for call in window_calls if call.duration >= self.config.slow_call_threshold)
        slow_call_rate = slow_calls / len(window_calls)
        
        if slow_call_rate >= self.config.slow_call_rate_threshold:
            return True
        
        return False
    
    def _get_window_calls(self) -> List[CallRecord]:
        """Get calls within the sliding window"""
        current_time = time.time()
        window_start = current_time - self.config.window_size
        
        return [call for call in self.call_history if call.timestamp >= window_start]
    
    def _clean_old_records(self):
        """Remove old call records outside the window"""
        current_time = time.time()
        window_start = current_time - self.config.window_size
        
        self.call_history = [call for call in self.call_history if call.timestamp >= window_start]
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get circuit breaker metrics"""
        window_calls = self._get_window_calls()
        
        if window_calls:
            window_failures = sum(1 for call in window_calls if not call.success)
            window_failure_rate = window_failures / len(window_calls)
            
            durations = [call.duration for call in window_calls]
            avg_duration = statistics.mean(durations)
            p95_duration = statistics.quantiles(durations, n=20)[18] if len(durations) > 5 else 0
            
            slow_calls = sum(1 for call in window_calls if call.duration >= self.config.slow_call_threshold)
            slow_call_rate = slow_calls / len(window_calls)
        else:
            window_failure_rate = 0
            avg_duration = 0
            p95_duration = 0
            slow_call_rate = 0
        
        return {
            'name': self.name,
            'state': self.state.value,
            'total_calls': self.total_calls,
            'total_successes': self.total_successes,
            'total_failures': self.total_failures,
            'total_timeouts': self.total_timeouts,
            'consecutive_failures': self.consecutive_failures,
            'window_calls': len(window_calls),
            'window_failure_rate': window_failure_rate,
            'window_slow_call_rate': slow_call_rate,
            'avg_duration': avg_duration,
            'p95_duration': p95_duration,
            'last_failure_time': self.last_failure_time,
            'success_rate': self.total_successes / max(self.total_calls, 1)
        }
    
    def reset(self):
        """Reset circuit breaker to closed state"""
        self.state = CircuitState.CLOSED
        self.consecutive_failures = 0
        self.success_count = 0
        self.last_failure_time = 0
        self.call_history.clear()
        self.logger.info(f"Circuit breaker {self.name} manually reset")


class CircuitBreakerRegistry:
    """Registry for managing multiple circuit breakers"""
    
    def __init__(self):
        self.breakers: Dict[str, CircuitBreaker] = {}
        self.default_config = CircuitBreakerConfig()
        self.logger = logging.getLogger("CircuitBreakerRegistry")
    
    def get_breaker(self, name: str, config: CircuitBreakerConfig = None) -> CircuitBreaker:
        """Get or create circuit breaker"""
        if name not in self.breakers:
            breaker_config = config or self.default_config
            self.breakers[name] = CircuitBreaker(name, breaker_config)
            self.logger.info(f"Created circuit breaker: {name}")
        
        return self.breakers[name]
    
    def get_all_metrics(self) -> Dict[str, Dict[str, Any]]:
        """Get metrics for all circuit breakers"""
        return {name: breaker.get_metrics() for name, breaker in self.breakers.items()}
    
    def reset_breaker(self, name: str):
        """Reset specific circuit breaker"""
        if name in self.breakers:
            self.breakers[name].reset()
    
    def reset_all(self):
        """Reset all circuit breakers"""
        for breaker in self.breakers.values():
            breaker.reset()


# Global registry instance
circuit_breaker_registry = CircuitBreakerRegistry()


# Decorator for easy circuit breaker application
def circuit_breaker(name: str, config: CircuitBreakerConfig = None):
    """Decorator to apply circuit breaker to a function"""
    def decorator(func):
        breaker = circuit_breaker_registry.get_breaker(name, config)
        
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            return await breaker.call(func, *args, **kwargs)
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            return asyncio.run(breaker.call(func, *args, **kwargs))
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


# Custom exceptions
class CircuitBreakerError(Exception):
    """Base exception for circuit breaker errors"""
    pass


class CircuitBreakerOpenError(CircuitBreakerError):
    """Raised when circuit breaker is open"""
    pass


class CircuitBreakerTimeoutError(CircuitBreakerError):
    """Raised when call times out"""
    pass


# Example usage and testing
if __name__ == "__main__":
    import random
    
    async def unreliable_service(fail_rate: float = 0.3, delay: float = 0.1):
        """Simulate an unreliable service"""
        await asyncio.sleep(delay + random.random() * 0.1)
        
        if random.random() < fail_rate:
            raise Exception("Service failure")
        
        return "success"
    
    async def test_circuit_breaker():
        """Test circuit breaker functionality"""
        config = CircuitBreakerConfig(
            failure_threshold=3,
            recovery_timeout=5,
            timeout=1.0,
            window_size=10,
            minimum_requests=5
        )
        
        breaker = CircuitBreaker("test-service", config)
        
        print("Testing circuit breaker...")
        
        # Test normal operation
        for i in range(10):
            try:
                result = await breaker.call(unreliable_service, fail_rate=0.2)
                print(f"Call {i+1}: {result}")
            except Exception as e:
                print(f"Call {i+1} failed: {e}")
            
            await asyncio.sleep(0.1)
        
        print("\nMetrics after 10 calls:")
        metrics = breaker.get_metrics()
        for key, value in metrics.items():
            print(f"  {key}: {value}")
        
        # Test with high failure rate to trip circuit
        print("\nTesting with high failure rate...")
        for i in range(5):
            try:
                result = await breaker.call(unreliable_service, fail_rate=0.9)
                print(f"High-fail call {i+1}: {result}")
            except Exception as e:
                print(f"High-fail call {i+1} failed: {e}")
        
        print(f"\nCircuit state: {breaker.state}")
        
        # Test circuit breaker open behavior
        try:
            await breaker.call(unreliable_service)
        except CircuitBreakerOpenError as e:
            print(f"Circuit breaker blocked call: {e}")
        
        # Test recovery
        print("\nWaiting for recovery timeout...")
        await asyncio.sleep(6)
        
        try:
            result = await breaker.call(unreliable_service, fail_rate=0.0)
            print(f"Recovery call: {result}")
        except Exception as e:
            print(f"Recovery call failed: {e}")
        
        print(f"Final circuit state: {breaker.state}")
        
        final_metrics = breaker.get_metrics()
        print("\nFinal metrics:")
        for key, value in final_metrics.items():
            print(f"  {key}: {value}")
    
    # Test decorator
    @circuit_breaker("decorated-service")
    async def decorated_service():
        if random.random() < 0.5:
            raise Exception("Random failure")
        return "decorated success"
    
    async def test_decorator():
        """Test circuit breaker decorator"""
        print("\nTesting decorator...")
        
        for i in range(5):
            try:
                result = await decorated_service()
                print(f"Decorated call {i+1}: {result}")
            except Exception as e:
                print(f"Decorated call {i+1} failed: {e}")
    
    async def main():
        await test_circuit_breaker()
        await test_decorator()
        
        # Show all metrics
        print("\nAll circuit breaker metrics:")
        all_metrics = circuit_breaker_registry.get_all_metrics()
        for name, metrics in all_metrics.items():
            print(f"\n{name}:")
            for key, value in metrics.items():
                print(f"  {key}: {value}")
    
    asyncio.run(main())
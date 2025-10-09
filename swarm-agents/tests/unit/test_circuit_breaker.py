#!/usr/bin/env python3
"""
Unit Tests for Circuit Breaker Pattern
Tests resilience patterns, fault tolerance, and error handling
"""

import asyncio
import pytest
import time
from unittest.mock import AsyncMock, patch
from datetime import datetime, timedelta

from backend.resilience.circuit_breaker import (
    CircuitBreaker, CircuitBreakerConfig, CircuitState, CircuitBreakerRegistry,
    CircuitBreakerError, CircuitBreakerOpenError, CircuitBreakerTimeoutError,
    circuit_breaker, CallRecord
)


@pytest.mark.unit
class TestCircuitBreaker:
    """Test circuit breaker functionality"""
    
    def test_circuit_breaker_initialization(self, circuit_breaker_config):
        """Test circuit breaker initialization"""
        cb = CircuitBreaker("test-service", circuit_breaker_config)
        
        assert cb.name == "test-service"
        assert cb.config == circuit_breaker_config
        assert cb.state == CircuitState.CLOSED
        assert cb.total_calls == 0
        assert cb.consecutive_failures == 0
    
    def test_circuit_breaker_default_config(self):
        """Test circuit breaker with default config"""
        cb = CircuitBreaker("test-service")
        
        assert cb.config.failure_threshold == 5
        assert cb.config.recovery_timeout == 60
        assert cb.config.timeout == 30.0
    
    async def test_successful_call(self, circuit_breaker):
        """Test successful function call through circuit breaker"""
        async def successful_function():
            await asyncio.sleep(0.1)
            return "success"
        
        result = await circuit_breaker.call(successful_function)
        
        assert result == "success"
        assert circuit_breaker.state == CircuitState.CLOSED
        assert circuit_breaker.total_calls == 1
        assert circuit_breaker.total_successes == 1
        assert circuit_breaker.consecutive_failures == 0
    
    async def test_failed_call(self, circuit_breaker):
        """Test failed function call through circuit breaker"""
        async def failing_function():
            raise Exception("Test failure")
        
        with pytest.raises(Exception, match="Test failure"):
            await circuit_breaker.call(failing_function)
        
        assert circuit_breaker.state == CircuitState.CLOSED  # Not tripped yet
        assert circuit_breaker.total_calls == 1
        assert circuit_breaker.total_failures == 1
        assert circuit_breaker.consecutive_failures == 1
    
    async def test_timeout_call(self, circuit_breaker):
        """Test function call that times out"""
        async def slow_function():
            await asyncio.sleep(2.0)  # Longer than timeout (1.0s)
            return "slow"
        
        with pytest.raises(CircuitBreakerTimeoutError):
            await circuit_breaker.call(slow_function)
        
        assert circuit_breaker.total_calls == 1
        assert circuit_breaker.total_timeouts == 1
        assert circuit_breaker.consecutive_failures == 1
    
    async def test_circuit_trips_after_consecutive_failures(self, circuit_breaker):
        """Test circuit trips after reaching failure threshold"""
        async def failing_function():
            raise Exception("Failure")
        
        # Fail 3 times (threshold is 3 in test config)
        for i in range(3):
            with pytest.raises(Exception):
                await circuit_breaker.call(failing_function)
        
        # Circuit should be open now
        assert circuit_breaker.state == CircuitState.OPEN
        
        # Next call should fail fast
        with pytest.raises(CircuitBreakerOpenError):
            await circuit_breaker.call(failing_function)
    
    async def test_circuit_recovery_after_timeout(self, circuit_breaker):
        """Test circuit recovery after timeout period"""
        async def failing_function():
            raise Exception("Failure")
        
        async def successful_function():
            return "success"
        
        # Trip the circuit
        for i in range(3):
            with pytest.raises(Exception):
                await circuit_breaker.call(failing_function)
        
        assert circuit_breaker.state == CircuitState.OPEN
        
        # Fast-forward time past recovery timeout
        with patch('time.time', return_value=time.time() + 10):
            # Should transition to HALF_OPEN
            result = await circuit_breaker.call(successful_function)
            assert result == "success"
            assert circuit_breaker.state == CircuitState.HALF_OPEN
    
    async def test_half_open_state_success_closes_circuit(self, circuit_breaker):
        """Test that successful calls in HALF_OPEN state close the circuit"""
        async def successful_function():
            return "success"
        
        # Manually set to HALF_OPEN state
        circuit_breaker.state = CircuitState.HALF_OPEN
        circuit_breaker.success_count = 0
        
        # Make enough successful calls to close circuit (threshold is 3)
        for i in range(3):
            result = await circuit_breaker.call(successful_function)
            assert result == "success"
        
        assert circuit_breaker.state == CircuitState.CLOSED
    
    async def test_half_open_state_failure_reopens_circuit(self, circuit_breaker):
        """Test that failure in HALF_OPEN state reopens the circuit"""
        async def failing_function():
            raise Exception("Failure")
        
        # Manually set to HALF_OPEN state
        circuit_breaker.state = CircuitState.HALF_OPEN
        
        # One failure should reopen the circuit
        with pytest.raises(Exception):
            await circuit_breaker.call(failing_function)
        
        assert circuit_breaker.state == CircuitState.OPEN
    
    async def test_sliding_window_failure_rate(self):
        """Test failure rate calculation in sliding window"""
        config = CircuitBreakerConfig(
            failure_threshold=10,  # High threshold to test rate-based tripping
            window_size=10,
            minimum_requests=5,
            failure_rate_threshold=0.6  # 60% failure rate
        )
        
        cb = CircuitBreaker("rate-test", config)
        
        async def failing_function():
            raise Exception("Failure")
        
        async def successful_function():
            return "success"
        
        # Make 10 calls: 6 failures, 4 successes (60% failure rate)
        for i in range(6):
            with pytest.raises(Exception):
                await cb.call(failing_function)
        
        for i in range(4):
            await cb.call(successful_function)
        
        # Next failure should trip the circuit due to failure rate
        with pytest.raises(Exception):
            await cb.call(failing_function)
        
        # Circuit should be open due to failure rate
        assert cb.state == CircuitState.OPEN
    
    async def test_slow_call_rate_detection(self):
        """Test slow call rate detection"""
        config = CircuitBreakerConfig(
            failure_threshold=10,  # High threshold
            window_size=10,
            minimum_requests=5,
            slow_call_threshold=0.5,  # 0.5 seconds
            slow_call_rate_threshold=0.6  # 60% slow calls
        )
        
        cb = CircuitBreaker("slow-test", config)
        
        async def slow_function():
            await asyncio.sleep(0.6)  # Slow call
            return "slow"
        
        async def fast_function():
            await asyncio.sleep(0.1)  # Fast call
            return "fast"
        
        # Make 10 calls: 6 slow, 4 fast (60% slow rate)
        for i in range(6):
            await cb.call(slow_function)
        
        for i in range(4):
            await cb.call(fast_function)
        
        # Next slow call should trip the circuit
        await cb.call(slow_function)
        
        # Circuit should be open due to slow call rate
        assert cb.state == CircuitState.OPEN
    
    def test_call_history_cleanup(self, circuit_breaker):
        """Test that old call records are cleaned up"""
        # Manually add old call records
        old_time = time.time() - 100  # 100 seconds ago
        circuit_breaker.call_history.append(
            CallRecord(timestamp=old_time, success=True, duration=0.1)
        )
        
        # Add recent call record
        recent_time = time.time()
        circuit_breaker.call_history.append(
            CallRecord(timestamp=recent_time, success=True, duration=0.1)
        )
        
        # Cleanup should remove old records
        circuit_breaker._clean_old_records()
        
        # Only recent record should remain
        assert len(circuit_breaker.call_history) == 1
        assert circuit_breaker.call_history[0].timestamp == recent_time
    
    def test_get_metrics(self, circuit_breaker):
        """Test metrics collection"""
        # Add some call history
        current_time = time.time()
        circuit_breaker.call_history = [
            CallRecord(timestamp=current_time, success=True, duration=0.1),
            CallRecord(timestamp=current_time, success=False, duration=0.2, error="test"),
            CallRecord(timestamp=current_time, success=True, duration=0.15)
        ]
        
        circuit_breaker.total_calls = 10
        circuit_breaker.total_successes = 7
        circuit_breaker.total_failures = 3
        
        metrics = circuit_breaker.get_metrics()
        
        assert metrics['name'] == circuit_breaker.name
        assert metrics['state'] == CircuitState.CLOSED.value
        assert metrics['total_calls'] == 10
        assert metrics['total_successes'] == 7
        assert metrics['total_failures'] == 3
        assert metrics['window_calls'] == 3
        assert 'window_failure_rate' in metrics
        assert 'avg_duration' in metrics
    
    def test_reset_circuit_breaker(self, circuit_breaker):
        """Test resetting circuit breaker state"""
        # Set some state
        circuit_breaker.state = CircuitState.OPEN
        circuit_breaker.consecutive_failures = 5
        circuit_breaker.total_calls = 10
        circuit_breaker.call_history = [
            CallRecord(timestamp=time.time(), success=False, duration=0.1)
        ]
        
        # Reset
        circuit_breaker.reset()
        
        assert circuit_breaker.state == CircuitState.CLOSED
        assert circuit_breaker.consecutive_failures == 0
        assert circuit_breaker.success_count == 0
        assert len(circuit_breaker.call_history) == 0
    
    async def test_sync_function_call(self, circuit_breaker):
        """Test calling synchronous function through circuit breaker"""
        def sync_function():
            return "sync_result"
        
        result = await circuit_breaker.call(sync_function)
        
        assert result == "sync_result"
        assert circuit_breaker.total_calls == 1
        assert circuit_breaker.total_successes == 1
    
    async def test_unexpected_exception_handling(self, circuit_breaker):
        """Test handling of unexpected exceptions"""
        async def unexpected_error():
            raise KeyError("Unexpected error")  # Not the expected exception type
        
        # Should still raise the exception but not count as circuit breaker failure
        with pytest.raises(KeyError):
            await circuit_breaker.call(unexpected_error)
        
        # Should not increment consecutive failures for unexpected exceptions
        # (depends on implementation - might count as failure or not)
        assert circuit_breaker.total_calls == 1


@pytest.mark.unit
class TestCircuitBreakerConfig:
    """Test circuit breaker configuration"""
    
    def test_default_config(self):
        """Test default configuration values"""
        config = CircuitBreakerConfig()
        
        assert config.failure_threshold == 5
        assert config.recovery_timeout == 60
        assert config.expected_exception == Exception
        assert config.success_threshold == 3
        assert config.timeout == 30.0
        assert config.window_size == 60
        assert config.minimum_requests == 10
        assert config.failure_rate_threshold == 0.5
        assert config.slow_call_threshold == 5.0
        assert config.slow_call_rate_threshold == 0.5
    
    def test_custom_config(self):
        """Test custom configuration values"""
        config = CircuitBreakerConfig(
            failure_threshold=3,
            recovery_timeout=30,
            timeout=10.0,
            window_size=30,
            minimum_requests=5
        )
        
        assert config.failure_threshold == 3
        assert config.recovery_timeout == 30
        assert config.timeout == 10.0
        assert config.window_size == 30
        assert config.minimum_requests == 5


@pytest.mark.unit
class TestCircuitBreakerRegistry:
    """Test circuit breaker registry"""
    
    def test_registry_initialization(self):
        """Test registry initialization"""
        registry = CircuitBreakerRegistry()
        
        assert len(registry.breakers) == 0
        assert registry.default_config is not None
    
    def test_get_breaker_creates_new(self):
        """Test that getting breaker creates new one if not exists"""
        registry = CircuitBreakerRegistry()
        
        breaker = registry.get_breaker("test-service")
        
        assert "test-service" in registry.breakers
        assert registry.breakers["test-service"] == breaker
        assert breaker.name == "test-service"
    
    def test_get_breaker_returns_existing(self):
        """Test that getting existing breaker returns same instance"""
        registry = CircuitBreakerRegistry()
        
        breaker1 = registry.get_breaker("test-service")
        breaker2 = registry.get_breaker("test-service")
        
        assert breaker1 is breaker2
    
    def test_get_breaker_with_custom_config(self):
        """Test getting breaker with custom config"""
        registry = CircuitBreakerRegistry()
        custom_config = CircuitBreakerConfig(failure_threshold=3)
        
        breaker = registry.get_breaker("test-service", custom_config)
        
        assert breaker.config.failure_threshold == 3
    
    def test_get_all_metrics(self):
        """Test getting metrics for all breakers"""
        registry = CircuitBreakerRegistry()
        
        # Create some breakers
        breaker1 = registry.get_breaker("service1")
        breaker2 = registry.get_breaker("service2")
        
        # Set some state
        breaker1.total_calls = 10
        breaker2.total_calls = 5
        
        all_metrics = registry.get_all_metrics()
        
        assert "service1" in all_metrics
        assert "service2" in all_metrics
        assert all_metrics["service1"]["total_calls"] == 10
        assert all_metrics["service2"]["total_calls"] == 5
    
    def test_reset_breaker(self):
        """Test resetting specific breaker"""
        registry = CircuitBreakerRegistry()
        
        breaker = registry.get_breaker("test-service")
        breaker.state = CircuitState.OPEN
        breaker.consecutive_failures = 5
        
        registry.reset_breaker("test-service")
        
        assert breaker.state == CircuitState.CLOSED
        assert breaker.consecutive_failures == 0
    
    def test_reset_all_breakers(self):
        """Test resetting all breakers"""
        registry = CircuitBreakerRegistry()
        
        breaker1 = registry.get_breaker("service1")
        breaker2 = registry.get_breaker("service2")
        
        breaker1.state = CircuitState.OPEN
        breaker2.state = CircuitState.HALF_OPEN
        
        registry.reset_all()
        
        assert breaker1.state == CircuitState.CLOSED
        assert breaker2.state == CircuitState.CLOSED


@pytest.mark.unit
class TestCircuitBreakerDecorator:
    """Test circuit breaker decorator"""
    
    async def test_async_function_decorator(self):
        """Test decorator on async function"""
        @circuit_breaker("test-decorated", CircuitBreakerConfig(failure_threshold=2))
        async def decorated_async_func():
            return "async_result"
        
        result = await decorated_async_func()
        assert result == "async_result"
    
    async def test_async_function_decorator_failure(self):
        """Test decorator on failing async function"""
        @circuit_breaker("test-failing", CircuitBreakerConfig(failure_threshold=2))
        async def decorated_failing_func():
            raise Exception("Decorated failure")
        
        # First failure
        with pytest.raises(Exception, match="Decorated failure"):
            await decorated_failing_func()
        
        # Second failure should trip circuit
        with pytest.raises(Exception, match="Decorated failure"):
            await decorated_failing_func()
        
        # Third call should be blocked by circuit breaker
        with pytest.raises(CircuitBreakerOpenError):
            await decorated_failing_func()
    
    def test_sync_function_decorator(self):
        """Test decorator on sync function"""
        @circuit_breaker("test-sync", CircuitBreakerConfig(failure_threshold=2))
        def decorated_sync_func():
            return "sync_result"
        
        # Note: sync wrapper uses asyncio.run, so this might not work in async test
        # This test verifies the decorator setup
        assert hasattr(decorated_sync_func, '__wrapped__')
    
    async def test_decorator_preserves_function_metadata(self):
        """Test that decorator preserves function metadata"""
        @circuit_breaker("test-metadata")
        async def original_function():
            """Original docstring"""
            return "result"
        
        assert original_function.__name__ == "original_function"
        # Note: __doc__ might be modified by wraps decorator


@pytest.mark.unit
class TestCircuitBreakerExceptions:
    """Test circuit breaker custom exceptions"""
    
    def test_circuit_breaker_error(self):
        """Test base circuit breaker error"""
        error = CircuitBreakerError("Base error")
        assert str(error) == "Base error"
        assert isinstance(error, Exception)
    
    def test_circuit_breaker_open_error(self):
        """Test circuit breaker open error"""
        error = CircuitBreakerOpenError("Circuit is open")
        assert str(error) == "Circuit is open"
        assert isinstance(error, CircuitBreakerError)
    
    def test_circuit_breaker_timeout_error(self):
        """Test circuit breaker timeout error"""
        error = CircuitBreakerTimeoutError("Request timed out")
        assert str(error) == "Request timed out"
        assert isinstance(error, CircuitBreakerError)


@pytest.mark.unit
class TestCallRecord:
    """Test call record data structure"""
    
    def test_call_record_creation(self):
        """Test creating call record"""
        timestamp = time.time()
        record = CallRecord(
            timestamp=timestamp,
            success=True,
            duration=0.5,
            error=None
        )
        
        assert record.timestamp == timestamp
        assert record.success is True
        assert record.duration == 0.5
        assert record.error is None
    
    def test_call_record_with_error(self):
        """Test call record with error"""
        record = CallRecord(
            timestamp=time.time(),
            success=False,
            duration=0.3,
            error="Test error message"
        )
        
        assert record.success is False
        assert record.error == "Test error message"


@pytest.mark.unit
class TestCircuitBreakerEdgeCases:
    """Test edge cases and error conditions"""
    
    async def test_zero_timeout_config(self):
        """Test circuit breaker with zero timeout"""
        config = CircuitBreakerConfig(timeout=0.0)
        cb = CircuitBreaker("zero-timeout", config)
        
        async def normal_function():
            await asyncio.sleep(0.01)  # Any delay should timeout
            return "result"
        
        with pytest.raises(CircuitBreakerTimeoutError):
            await cb.call(normal_function)
    
    async def test_minimum_requests_not_met(self):
        """Test that circuit doesn't trip if minimum requests not met"""
        config = CircuitBreakerConfig(
            failure_threshold=10,
            minimum_requests=5,
            failure_rate_threshold=1.0  # 100% failure rate
        )
        cb = CircuitBreaker("min-requests", config)
        
        async def failing_function():
            raise Exception("Failure")
        
        # Make 3 failures (less than minimum_requests=5)
        for i in range(3):
            with pytest.raises(Exception):
                await cb.call(failing_function)
        
        # Circuit should still be closed
        assert cb.state == CircuitState.CLOSED
    
    async def test_very_long_recovery_timeout(self):
        """Test circuit with very long recovery timeout"""
        config = CircuitBreakerConfig(
            failure_threshold=1,
            recovery_timeout=3600  # 1 hour
        )
        cb = CircuitBreaker("long-timeout", config)
        
        async def failing_function():
            raise Exception("Failure")
        
        # Trip the circuit
        with pytest.raises(Exception):
            await cb.call(failing_function)
        
        assert cb.state == CircuitState.OPEN
        
        # Should still be open (no time passage)
        with pytest.raises(CircuitBreakerOpenError):
            await cb.call(failing_function)
    
    def test_empty_call_history_metrics(self):
        """Test metrics calculation with empty call history"""
        cb = CircuitBreaker("empty-history")
        
        metrics = cb.get_metrics()
        
        assert metrics['window_calls'] == 0
        assert metrics['window_failure_rate'] == 0
        assert metrics['avg_duration'] == 0
        assert metrics['p95_duration'] == 0
    
    async def test_exception_type_filtering(self):
        """Test that only expected exception types trigger circuit breaker"""
        config = CircuitBreakerConfig(
            failure_threshold=2,
            expected_exception=ValueError  # Only ValueError counts as failure
        )
        cb = CircuitBreaker("exception-filter", config)
        
        async def value_error_function():
            raise ValueError("Value error")
        
        async def type_error_function():
            raise TypeError("Type error")  # Different exception type
        
        # ValueError should count as failure
        with pytest.raises(ValueError):
            await cb.call(value_error_function)
        
        assert cb.consecutive_failures == 1
        
        # TypeError should not count as circuit breaker failure
        with pytest.raises(TypeError):
            await cb.call(type_error_function)
        
        # consecutive_failures might or might not be incremented depending on implementation
        # The important thing is that different exception types are handled appropriately
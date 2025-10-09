"""
Resilience patterns for TGE Swarm Backend
Provides circuit breakers, retry handlers, and fault tolerance mechanisms
"""

from .circuit_breaker import (
    CircuitBreaker, CircuitBreakerConfig, CircuitBreakerRegistry,
    circuit_breaker, circuit_breaker_registry,
    CircuitBreakerError, CircuitBreakerOpenError, CircuitBreakerTimeoutError
)

from .retry_handler import (
    RetryHandler, RetryConfig, RetryRegistry, BackoffStrategy,
    retry, retry_with_circuit_breaker, retry_registry,
    RetryError, RetryExhaustionError, RetryTimeoutError,
    create_http_retry_config, create_database_retry_config, create_message_queue_retry_config
)

__all__ = [
    # Circuit Breaker
    'CircuitBreaker', 'CircuitBreakerConfig', 'CircuitBreakerRegistry',
    'circuit_breaker', 'circuit_breaker_registry',
    'CircuitBreakerError', 'CircuitBreakerOpenError', 'CircuitBreakerTimeoutError',
    
    # Retry Handler
    'RetryHandler', 'RetryConfig', 'RetryRegistry', 'BackoffStrategy',
    'retry', 'retry_with_circuit_breaker', 'retry_registry',
    'RetryError', 'RetryExhaustionError', 'RetryTimeoutError',
    'create_http_retry_config', 'create_database_retry_config', 'create_message_queue_retry_config'
]
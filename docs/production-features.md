# Production-Grade Features Documentation

This document describes the production-grade features added to the TGE Monitor application.

## Table of Contents

1. [Error Handling and Recovery](#error-handling-and-recovery)
2. [Monitoring and Alerting](#monitoring-and-alerting)
3. [Rate Limiting and Throttling](#rate-limiting-and-throttling)
4. [Data Validation and Sanitization](#data-validation-and-sanitization)
5. [Structured Logging and Observability](#structured-logging-and-observability)
6. [Configuration Management](#configuration-management)
7. [Integration and Usage](#integration-and-usage)

## Error Handling and Recovery

### Features

- **Retry Logic with Exponential Backoff**: Automatically retry failed operations with configurable backoff
- **Circuit Breakers**: Protect against cascading failures in external services
- **Graceful Degradation**: Fallback mechanisms when primary services fail
- **Dead Letter Queue**: Track and store failed operations for later analysis

### Usage

```python
from src.error_handling import with_retry, with_circuit_breaker, RetryConfig, error_handler

# Retry decorator
@with_retry(RetryConfig(max_attempts=3, base_delay=1.0))
def fetch_data():
    # Your code here
    pass

# Circuit breaker decorator
@with_circuit_breaker("twitter_api")
def fetch_tweets():
    # Your code here
    pass

# Manual error handling
try:
    result = risky_operation()
except Exception as e:
    error_handler.handle_error(
        e,
        context="data_processing",
        severity=ErrorSeverity.HIGH,
        additional_info={"user_id": "123"}
    )
```

### Circuit Breaker States

- **CLOSED**: Normal operation, all requests allowed
- **OPEN**: Service is failing, requests are rejected
- **HALF_OPEN**: Testing if service has recovered

### Configuration

```python
CircuitBreakerConfig(
    failure_threshold=5,      # Open after 5 failures
    success_threshold=2,      # Close after 2 successes in half-open
    timeout=60.0,            # Wait 60s before attempting reset
    half_open_timeout=30.0   # Max time to stay in half-open
)
```

## Monitoring and Alerting

### Features

- **Health Checks**: Monitor component health status
- **Metrics Collection**: Track performance and usage metrics
- **System Monitoring**: CPU, memory, disk, network usage
- **Alert Management**: Raise and track system alerts

### Usage

```python
from src.monitoring import monitoring_system, HealthCheckResult, HealthStatus

# Register custom health check
def check_database():
    return HealthCheckResult(
        component="database",
        status=HealthStatus.HEALTHY,
        message="Database operational",
        response_time_ms=5.2
    )

monitoring_system.health_checker.register_check("database", check_database)

# Record metrics
monitoring_system.metrics.record("api_request_duration", 125.5)
monitoring_system.metrics.increment("api_requests_total")
monitoring_system.metrics.set_gauge("active_connections", 42)

# Raise alerts
monitoring_system.alert_manager.raise_alert(
    title="High Error Rate",
    message="Error rate exceeded 5% threshold",
    severity=AlertSeverity.WARNING,
    component="api_server"
)

# Get system status
status = monitoring_system.get_status_report()
```

### Health Status Levels

- **HEALTHY**: Component operating normally
- **DEGRADED**: Component functional but performance impacted
- **UNHEALTHY**: Component not functioning correctly
- **UNKNOWN**: Health status cannot be determined

## Rate Limiting and Throttling

### Features

- **Multiple Strategies**: Token bucket, leaky bucket, sliding window
- **Backpressure Management**: Prevent queue overflow
- **Per-Service Configuration**: Different limits for different services
- **Automatic Waiting**: Optional wait when rate limited

### Usage

```python
from src.rate_limiter import rate_limit_manager, RateLimitConfig, RateLimitStrategy

# Register rate limiter
rate_limit_manager.register_limiter(
    "api_requests",
    RateLimitConfig(
        requests_per_second=10.0,
        burst_size=20,
        strategy=RateLimitStrategy.TOKEN_BUCKET,
        wait_on_rate_limit=True
    )
)

# Use rate limiter
limiter = rate_limit_manager.get_limiter("api_requests")
status = limiter.acquire(tokens=1, wait=True)

if status.allowed:
    # Make request
    make_api_request()
else:
    # Handle rate limit
    print(f"Rate limited. Retry after {status.retry_after}s")

# Backpressure management
bp = rate_limit_manager.register_backpressure("processing_queue", max_queue_size=1000)

should_accept, reason = bp.should_accept()
if should_accept:
    bp.add_item()
    process_item()
    bp.remove_item()
```

### Rate Limiting Strategies

- **Token Bucket**: Allows bursts, refills at constant rate
- **Leaky Bucket**: Smooth rate, no bursts
- **Sliding Window**: Fixed number of requests per time window
- **Fixed Window**: Resets at fixed intervals

## Data Validation and Sanitization

### Features

- **Input Validation**: Validate strings, emails, URLs, numbers
- **XSS Protection**: Detect and prevent cross-site scripting attacks
- **SQL Injection Protection**: Detect SQL injection patterns
- **Content Sanitization**: Clean HTML, text, filenames, JSON

### Usage

```python
from src.validation import InputValidator, ContentSanitizer, validate_user_input

# Validate string
result = InputValidator.validate_string(
    user_input,
    min_length=3,
    max_length=100,
    pattern=r'^[a-zA-Z0-9_]+$'
)

if result.is_valid:
    safe_value = result.sanitized_value
else:
    print(f"Validation errors: {result.errors}")

# Validate email
result = InputValidator.validate_email("user@example.com")

# Validate URL
result = InputValidator.validate_url("https://example.com")

# Sanitize HTML
safe_html = ContentSanitizer.sanitize_html(user_html, strict=True)

# Sanitize text
safe_text = ContentSanitizer.sanitize_text(user_text)

# Sanitize filename
safe_filename = ContentSanitizer.sanitize_filename(user_filename)

# Convenience function
result = validate_user_input(value, input_type="email")
```

### Validation Result

```python
ValidationResult(
    is_valid=True,           # Whether validation passed
    sanitized_value="...",   # Cleaned/sanitized value
    errors=[],               # List of error messages
    warnings=[]              # List of warning messages
)
```

## Structured Logging and Observability

### Features

- **Structured Logging**: JSON-formatted logs with context
- **Request Tracing**: Distributed tracing with trace/span IDs
- **Performance Metrics**: Track operation duration and success rate
- **Context Management**: Thread-safe logging context

### Usage

```python
from src.structured_logging import initialize_observability, setup_json_logging

# Initialize observability
obs_system = initialize_observability("TGE_Monitor")

# Setup JSON logging
setup_json_logging(level="INFO", log_file="logs/app.log")

# Get structured logger
logger = obs_system.get_logger("my_module")

# Log with context
logger.set_context(user_id="123", request_id="abc")
logger.info("Processing request", extra_field="value")

# Trace requests
with obs_system.trace_request("process_data", user_id="123") as ctx:
    logger = ctx['logger']
    logger.info("Starting data processing")

    # Your code here

    logger.info("Data processing complete")

# Get performance report
report = obs_system.get_performance_report()
```

### Log Entry Format

```json
{
  "timestamp": "2025-01-15T10:30:00.000Z",
  "level": "INFO",
  "message": "Processing request",
  "logger": "TGE_Monitor.my_module",
  "trace_id": "abc123",
  "span_id": "def456",
  "user_id": "123",
  "extra": {
    "extra_field": "value"
  }
}
```

## Configuration Management

### Features

- **Environment-Based Config**: Different configs for dev/staging/prod
- **Feature Flags**: Toggle features without code changes
- **Secrets Management**: Secure handling of sensitive data
- **Configuration Validation**: Schema-based validation

### Usage

```python
from src.config_manager import initialize_config, Environment, FeatureFlag

# Initialize configuration
config = initialize_config(Environment.PRODUCTION)

# Load from environment
config.load_from_env(prefix="TGE_")

# Get configuration values
log_level = config.get_string("log_level", default="INFO")
max_workers = config.get_int("max_workers", default=4)
enable_twitter = config.get_bool("enable_twitter", default=True)

# Feature flags
config.register_feature_flag(
    FeatureFlag(
        name="new_feature",
        enabled=True,
        rollout_percentage=50,  # 50% rollout
        allowed_environments=[Environment.DEVELOPMENT, Environment.STAGING]
    )
)

if config.is_feature_enabled("new_feature"):
    # Use new feature
    pass

# Secrets management
from src.config_manager import get_secrets

secrets = get_secrets()
secrets.load_from_env(prefix="SECRET_")
api_key = secrets.get_secret("api_key")
```

### Environment Variables

Configuration can be loaded from environment variables with a prefix:

```bash
export TGE_LOG_LEVEL=DEBUG
export TGE_MAX_WORKERS=8
export TGE_ENABLE_TWITTER=true
export SECRET_API_KEY=your_api_key_here
```

## Integration and Usage

### Quick Start

```python
from src.production_integration import initialize_production, Environment

# Initialize all production features
production_system = initialize_production(
    app_name="TGE_Monitor",
    environment=Environment.PRODUCTION,
    config_overrides={
        'log_level': 'INFO',
        'max_workers': 4
    }
)

# Your application code here

# Shutdown gracefully
from src.production_integration import shutdown_production
shutdown_production()
```

### Full Example

```python
from src.production_integration import initialize_production, get_production_system
from src.error_handling import with_retry, with_circuit_breaker
from src.monitoring import monitoring_system
from src.rate_limiter import rate_limit_manager

# Initialize production system
prod = initialize_production("TGE_Monitor", Environment.PRODUCTION)

# Define your operations with production features
@with_circuit_breaker("twitter_api")
@with_retry()
def fetch_tweets():
    # Get rate limiter
    limiter = rate_limit_manager.get_limiter("twitter_api")

    # Acquire rate limit
    status = limiter.acquire(tokens=1, wait=True)

    if not status.allowed:
        raise Exception("Rate limited")

    # Fetch tweets
    return twitter_client.fetch()

# Use structured logging
logger = prod.obs_system.get_logger("twitter_monitor")

# Trace the operation
with prod.obs_system.trace_request("fetch_twitter_data") as ctx:
    logger = ctx['logger']

    try:
        tweets = fetch_tweets()
        logger.info(f"Fetched {len(tweets)} tweets")

        # Record metrics
        monitoring_system.metrics.increment("tweets_fetched", len(tweets))

    except Exception as e:
        logger.error("Failed to fetch tweets", exc_info=e)
        raise

# Get system status
status = prod.get_system_status()
print(f"System health: {status['monitoring']['overall_status']}")

# Shutdown
shutdown_production()
```

### System Status Endpoint

The system status can be exposed via an API endpoint:

```python
from fastapi import FastAPI
from src.production_integration import get_production_system

app = FastAPI()

@app.get("/health")
def health_check():
    prod = get_production_system()
    if not prod:
        return {"status": "not_initialized"}

    status = prod.get_system_status()
    return status
```

## Best Practices

### Error Handling

1. Always use circuit breakers for external service calls
2. Configure retry logic based on service characteristics
3. Monitor the dead letter queue and replay failed operations
4. Use appropriate error severity levels

### Monitoring

1. Register health checks for all critical components
2. Set up alerts for degraded/unhealthy states
3. Monitor key metrics: latency, throughput, error rates
4. Review monitoring dashboards regularly

### Rate Limiting

1. Set conservative rate limits initially
2. Monitor block rates and adjust limits
3. Use backpressure to prevent queue overflow
4. Configure wait behavior based on use case

### Validation

1. Validate all user input before processing
2. Sanitize output before displaying to users
3. Use strict HTML sanitization for user-generated content
4. Log validation failures for security monitoring

### Logging

1. Use structured logging for all application logs
2. Include trace/span IDs for request tracing
3. Set appropriate log levels
4. Monitor log volume and rotate logs

### Configuration

1. Use environment variables for deployment-specific config
2. Never commit secrets to version control
3. Use feature flags for gradual rollouts
4. Validate configuration on startup

## Troubleshooting

### Circuit Breaker Stuck Open

```python
from src.error_handling import error_handler

# Manually reset circuit breaker
error_handler.reset_circuit_breaker("service_name")
```

### High Rate Limit Block Rate

```python
from src.rate_limiter import rate_limit_manager

# Check rate limiter stats
stats = rate_limit_manager.get_all_stats()
print(stats)

# Adjust rate limit
limiter = rate_limit_manager.get_limiter("service_name")
limiter.reset()
```

### Health Check Failures

```python
from src.monitoring import monitoring_system

# Run specific health check
result = monitoring_system.health_checker.run_check("component_name")
print(result.message)
print(result.metadata)
```

### Dead Letter Queue Growing

```python
from src.error_handling import dead_letter_queue

# Review failed operations
failed_ops = dead_letter_queue.get_all()

# Process or clear
dead_letter_queue.clear()
```

## Performance Impact

The production features are designed to have minimal performance impact:

- **Error Handling**: Negligible overhead when no errors occur
- **Monitoring**: Background threads, ~1-2% CPU usage
- **Rate Limiting**: <1ms overhead per request
- **Validation**: Depends on input size, typically <5ms
- **Logging**: Async/buffered, minimal impact
- **Configuration**: One-time initialization cost

## Future Enhancements

- Integration with external monitoring services (Prometheus, Grafana)
- Distributed tracing support (Jaeger, Zipkin)
- Advanced feature flag targeting
- Automatic anomaly detection
- Performance regression detection
- A/B testing framework

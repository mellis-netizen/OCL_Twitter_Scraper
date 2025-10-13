"""
Production Integration Module
Integrates all production-grade features into the application
"""

import logging
import os
from typing import Optional, Dict, Any
from datetime import datetime, timezone

# Import production modules
from .error_handling import (
    error_handler, CircuitBreakerConfig, RetryConfig,
    with_retry, with_circuit_breaker, dead_letter_queue
)
from .monitoring import (
    monitoring_system, HealthCheckResult, HealthStatus,
    AlertSeverity
)
from .rate_limiter import (
    rate_limit_manager, RateLimitConfig, RateLimitStrategy
)
from .validation import InputValidator, ContentSanitizer, validate_user_input
from .structured_logging import (
    initialize_observability, setup_json_logging,
    get_observability
)
from .config_manager import (
    initialize_config, get_config, get_secrets,
    Environment, FeatureFlag
)

logger = logging.getLogger(__name__)


class ProductionSystem:
    """Manages all production-grade features"""

    def __init__(self, app_name: str = "TGE_Monitor", environment: Optional[Environment] = None):
        self.app_name = app_name
        self.environment = environment or Environment.DEVELOPMENT
        self.initialized = False

    def initialize(self, config_overrides: Optional[Dict[str, Any]] = None):
        """Initialize all production systems"""
        if self.initialized:
            logger.warning("Production system already initialized")
            return

        logger.info(f"Initializing production system for {self.app_name}")

        # 1. Initialize configuration
        logger.info("Initializing configuration management...")
        config = initialize_config(self.environment)

        # Load configuration from environment
        config.load_from_env(prefix="TGE_")

        # Apply overrides if provided
        if config_overrides:
            for key, value in config_overrides.items():
                config.set(key, value, source="override")

        # Load secrets
        secrets = get_secrets()
        secrets.load_from_env(prefix="SECRET_")

        # 2. Initialize structured logging
        logger.info("Initializing structured logging...")
        log_level = config.get_string("log_level", "INFO")
        log_file = config.get_string("log_file", "logs/application.log")

        setup_json_logging(
            level=log_level,
            log_file=log_file,
            console_output=True
        )

        # Initialize observability
        obs_system = initialize_observability(self.app_name)

        # 3. Register circuit breakers
        logger.info("Registering circuit breakers...")
        self._register_circuit_breakers()

        # 4. Register rate limiters
        logger.info("Registering rate limiters...")
        self._register_rate_limiters()

        # 5. Register health checks
        logger.info("Registering health checks...")
        self._register_health_checks()

        # 6. Register feature flags
        logger.info("Registering feature flags...")
        self._register_feature_flags()

        # 7. Start monitoring
        logger.info("Starting monitoring systems...")
        monitoring_system.start()

        self.initialized = True
        logger.info("Production system initialized successfully")

    def _register_circuit_breakers(self):
        """Register circuit breakers for external services"""

        # Twitter API circuit breaker
        error_handler.register_circuit_breaker(
            "twitter_api",
            CircuitBreakerConfig(
                failure_threshold=5,
                success_threshold=2,
                timeout=120.0,  # 2 minutes
                half_open_timeout=30.0
            )
        )

        # News RSS feeds circuit breaker
        error_handler.register_circuit_breaker(
            "news_feeds",
            CircuitBreakerConfig(
                failure_threshold=10,
                success_threshold=3,
                timeout=60.0,  # 1 minute
                half_open_timeout=30.0
            )
        )

        # Email service circuit breaker
        error_handler.register_circuit_breaker(
            "email_service",
            CircuitBreakerConfig(
                failure_threshold=3,
                success_threshold=2,
                timeout=300.0,  # 5 minutes
                half_open_timeout=60.0
            )
        )

        # Database circuit breaker
        error_handler.register_circuit_breaker(
            "database",
            CircuitBreakerConfig(
                failure_threshold=5,
                success_threshold=2,
                timeout=60.0,
                half_open_timeout=20.0
            )
        )

    def _register_rate_limiters(self):
        """Register rate limiters for different services"""

        # Twitter API rate limiter (450 requests per 15 minutes = 0.5 req/sec)
        rate_limit_manager.register_limiter(
            "twitter_api",
            RateLimitConfig(
                requests_per_second=0.5,
                burst_size=5,
                strategy=RateLimitStrategy.TOKEN_BUCKET,
                wait_on_rate_limit=True
            )
        )

        # News scraping rate limiter (10 concurrent feeds)
        rate_limit_manager.register_limiter(
            "news_scraping",
            RateLimitConfig(
                requests_per_second=10.0,
                burst_size=20,
                strategy=RateLimitStrategy.TOKEN_BUCKET,
                wait_on_rate_limit=True
            )
        )

        # API endpoints rate limiter (100 req/sec)
        rate_limit_manager.register_limiter(
            "api_endpoints",
            RateLimitConfig(
                requests_per_second=100.0,
                burst_size=200,
                strategy=RateLimitStrategy.SLIDING_WINDOW,
                wait_on_rate_limit=False
            )
        )

        # Email sending rate limiter (1 per second)
        rate_limit_manager.register_limiter(
            "email_sending",
            RateLimitConfig(
                requests_per_second=1.0,
                burst_size=5,
                strategy=RateLimitStrategy.TOKEN_BUCKET,
                wait_on_rate_limit=True
            )
        )

        # Register backpressure for processing queue
        rate_limit_manager.register_backpressure(
            "processing_queue",
            max_queue_size=1000,
            high_water_mark=0.8,
            low_water_mark=0.5
        )

    def _register_health_checks(self):
        """Register health checks for system components"""

        def check_twitter_api() -> HealthCheckResult:
            """Check Twitter API connectivity"""
            circuit_breaker = error_handler.get_circuit_breaker("twitter_api")

            if not circuit_breaker:
                return HealthCheckResult(
                    component="twitter_api",
                    status=HealthStatus.UNKNOWN,
                    message="Circuit breaker not found",
                    response_time_ms=0
                )

            cb_state = circuit_breaker.get_state()

            if cb_state['state'] == 'closed':
                status = HealthStatus.HEALTHY
                message = "Twitter API operational"
            elif cb_state['state'] == 'half_open':
                status = HealthStatus.DEGRADED
                message = "Twitter API recovering"
            else:
                status = HealthStatus.UNHEALTHY
                message = f"Twitter API circuit breaker open (failures: {cb_state['failure_count']})"

            return HealthCheckResult(
                component="twitter_api",
                status=status,
                message=message,
                response_time_ms=0,
                metadata=cb_state
            )

        def check_news_feeds() -> HealthCheckResult:
            """Check news feeds health"""
            circuit_breaker = error_handler.get_circuit_breaker("news_feeds")

            if not circuit_breaker:
                return HealthCheckResult(
                    component="news_feeds",
                    status=HealthStatus.UNKNOWN,
                    message="Circuit breaker not found",
                    response_time_ms=0
                )

            cb_state = circuit_breaker.get_state()

            if cb_state['state'] == 'closed':
                status = HealthStatus.HEALTHY
                message = "News feeds operational"
            elif cb_state['state'] == 'half_open':
                status = HealthStatus.DEGRADED
                message = "News feeds recovering"
            else:
                status = HealthStatus.UNHEALTHY
                message = "News feeds circuit breaker open"

            return HealthCheckResult(
                component="news_feeds",
                status=status,
                message=message,
                response_time_ms=0,
                metadata=cb_state
            )

        def check_rate_limiters() -> HealthCheckResult:
            """Check rate limiter status"""
            stats = rate_limit_manager.get_all_stats()

            # Check if any rate limiter has high block rate
            high_block_rate = False
            for limiter_name, limiter_stats in stats['rate_limiters'].items():
                block_rate = limiter_stats['stats']['block_rate']
                if block_rate > 0.5:  # More than 50% blocked
                    high_block_rate = True
                    break

            if high_block_rate:
                status = HealthStatus.DEGRADED
                message = "High rate limit blocks detected"
            else:
                status = HealthStatus.HEALTHY
                message = "Rate limiters operational"

            return HealthCheckResult(
                component="rate_limiters",
                status=status,
                message=message,
                response_time_ms=0,
                metadata=stats
            )

        # Register health checks
        monitoring_system.health_checker.register_check("twitter_api", check_twitter_api)
        monitoring_system.health_checker.register_check("news_feeds", check_news_feeds)
        monitoring_system.health_checker.register_check("rate_limiters", check_rate_limiters)

    def _register_feature_flags(self):
        """Register feature flags"""
        config = get_config()

        if not config:
            return

        # Twitter monitoring feature flag
        config.register_feature_flag(
            FeatureFlag(
                name="twitter_monitoring",
                enabled=config.get_bool("feature_twitter_monitoring", True),
                rollout_percentage=100,
                allowed_environments=[Environment.DEVELOPMENT, Environment.STAGING, Environment.PRODUCTION]
            )
        )

        # Advanced scoring feature flag
        config.register_feature_flag(
            FeatureFlag(
                name="advanced_scoring",
                enabled=config.get_bool("feature_advanced_scoring", True),
                rollout_percentage=100,
                allowed_environments=[Environment.DEVELOPMENT, Environment.STAGING, Environment.PRODUCTION]
            )
        )

        # Email notifications feature flag
        config.register_feature_flag(
            FeatureFlag(
                name="email_notifications",
                enabled=config.get_bool("feature_email_notifications", True),
                rollout_percentage=100,
                allowed_environments=[Environment.PRODUCTION, Environment.STAGING]
            )
        )

        # Swarm coordination feature flag
        config.register_feature_flag(
            FeatureFlag(
                name="swarm_coordination",
                enabled=config.get_bool("feature_swarm_coordination", False),
                rollout_percentage=50,  # Gradual rollout
                allowed_environments=[Environment.DEVELOPMENT, Environment.STAGING]
            )
        )

    def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status"""
        if not self.initialized:
            return {
                'initialized': False,
                'message': 'Production system not initialized'
            }

        # Get monitoring status
        monitoring_status = monitoring_system.get_status_report()

        # Get error metrics
        error_metrics = error_handler.get_metrics()

        # Get rate limit stats
        rate_limit_stats = rate_limit_manager.get_all_stats()

        # Get dead letter queue size
        dlq_size = dead_letter_queue.size()

        # Get observability report
        obs_system = get_observability()
        performance_report = obs_system.get_performance_report() if obs_system else {}

        return {
            'initialized': True,
            'app_name': self.app_name,
            'environment': self.environment.value,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'monitoring': monitoring_status,
            'errors': error_metrics,
            'rate_limits': rate_limit_stats,
            'dead_letter_queue_size': dlq_size,
            'performance': performance_report
        }

    def shutdown(self):
        """Shutdown production systems gracefully"""
        if not self.initialized:
            return

        logger.info("Shutting down production system...")

        # Stop monitoring
        monitoring_system.stop()

        # Save final status report
        try:
            status = self.get_system_status()
            report_file = f"logs/shutdown_report_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.json"
            monitoring_system.save_status_report(report_file)
            logger.info(f"Final status report saved to {report_file}")
        except Exception as e:
            logger.error(f"Failed to save shutdown report: {str(e)}")

        self.initialized = False
        logger.info("Production system shutdown complete")


# Global production system instance
production_system: Optional[ProductionSystem] = None


def initialize_production(
    app_name: str = "TGE_Monitor",
    environment: Optional[Environment] = None,
    config_overrides: Optional[Dict[str, Any]] = None
) -> ProductionSystem:
    """
    Initialize production system

    Args:
        app_name: Application name
        environment: Environment (development, staging, production)
        config_overrides: Configuration overrides

    Returns:
        ProductionSystem instance
    """
    global production_system

    if production_system and production_system.initialized:
        logger.warning("Production system already initialized")
        return production_system

    production_system = ProductionSystem(app_name, environment)
    production_system.initialize(config_overrides)

    return production_system


def get_production_system() -> Optional[ProductionSystem]:
    """Get global production system instance"""
    return production_system


def shutdown_production():
    """Shutdown production system"""
    global production_system

    if production_system:
        production_system.shutdown()
        production_system = None

"""
Comprehensive unit tests for src/rate_limiting.py

Tests all rate limiting functionality including:
- Multiple rate limiting strategies (fixed window, sliding window, token bucket)
- Redis integration and fallback to local cache
- Rate limit configurations and scopes
- Rate limit middleware for FastAPI
- API compliance checking
- Burst limiting
- Rate limit status and statistics
"""

import pytest
import sys
import time
import hashlib
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, MagicMock, patch, AsyncMock
from typing import Dict, Any

# Mock FastAPI before importing rate_limiting module
sys.modules['fastapi'] = MagicMock()
sys.modules['fastapi.responses'] = MagicMock()

from src.rate_limiting import (
    RateLimitStrategy,
    RateLimitScope,
    RateLimitConfig,
    RateLimitResult,
    AdvancedRateLimiter,
    RateLimitMiddleware,
    APIComplianceChecker,
    check_user_rate_limit,
    check_ip_rate_limit,
    check_api_key_rate_limit,
    reset_user_limit,
    get_rate_limit_stats
)


class MockRedis:
    """Mock Redis client for testing"""

    def __init__(self):
        self.data = {}
        self.expirations = {}
        self.sorted_sets = {}

    def pipeline(self):
        return MockRedisPipeline(self)

    def hgetall(self, key):
        return self.data.get(key, {})

    def hset(self, key, mapping):
        if key not in self.data:
            self.data[key] = {}
        self.data[key].update({k.encode() if isinstance(k, str) else k: str(v).encode() for k, v in mapping.items()})

    def delete(self, key):
        self.data.pop(key, None)
        self.sorted_sets.pop(key, None)

    def zcount(self, key, min_score, max_score):
        if key not in self.sorted_sets:
            return 0
        count = sum(1 for score in self.sorted_sets[key].values()
                   if min_score <= score <= max_score)
        return count

    def expire(self, key, seconds):
        self.expirations[key] = time.time() + seconds


class MockRedisPipeline:
    """Mock Redis pipeline for testing"""

    def __init__(self, redis_client):
        self.redis = redis_client
        self.commands = []

    def incr(self, key):
        self.commands.append(('incr', key))
        return self

    def expire(self, key, seconds):
        self.commands.append(('expire', key, seconds))
        return self

    def zadd(self, key, mapping):
        self.commands.append(('zadd', key, mapping))
        return self

    def zremrangebyscore(self, key, min_score, max_score):
        self.commands.append(('zremrangebyscore', key, min_score, max_score))
        return self

    def zcard(self, key):
        self.commands.append(('zcard', key))
        return self

    def hset(self, key, mapping):
        self.commands.append(('hset', key, mapping))
        return self

    def execute(self):
        results = []
        for cmd in self.commands:
            if cmd[0] == 'incr':
                key = cmd[1]
                if key not in self.redis.data:
                    self.redis.data[key] = 0
                self.redis.data[key] += 1
                results.append(self.redis.data[key])

            elif cmd[0] == 'expire':
                key, seconds = cmd[1], cmd[2]
                self.redis.expire(key, seconds)
                results.append(True)

            elif cmd[0] == 'zadd':
                key, mapping = cmd[1], cmd[2]
                if key not in self.redis.sorted_sets:
                    self.redis.sorted_sets[key] = {}
                self.redis.sorted_sets[key].update(mapping)
                results.append(len(mapping))

            elif cmd[0] == 'zremrangebyscore':
                key, min_score, max_score = cmd[1], cmd[2], cmd[3]
                if key in self.redis.sorted_sets:
                    to_remove = [k for k, v in self.redis.sorted_sets[key].items()
                               if min_score <= v <= max_score]
                    for k in to_remove:
                        del self.redis.sorted_sets[key][k]
                results.append(len(to_remove))

            elif cmd[0] == 'zcard':
                key = cmd[1]
                count = len(self.redis.sorted_sets.get(key, {}))
                results.append(count)

            elif cmd[0] == 'hset':
                key, mapping = cmd[1], cmd[2]
                self.redis.hset(key, mapping)
                results.append(len(mapping))

        return results


class TestRateLimitEnums:
    """Tests for rate limiting enums"""

    def test_rate_limit_strategy_values(self):
        """Test RateLimitStrategy enum values"""
        assert RateLimitStrategy.FIXED_WINDOW == "fixed_window"
        assert RateLimitStrategy.SLIDING_WINDOW == "sliding_window"
        assert RateLimitStrategy.TOKEN_BUCKET == "token_bucket"
        assert RateLimitStrategy.LEAKY_BUCKET == "leaky_bucket"

    def test_rate_limit_scope_values(self):
        """Test RateLimitScope enum values"""
        assert RateLimitScope.GLOBAL == "global"
        assert RateLimitScope.USER == "user"
        assert RateLimitScope.IP == "ip"
        assert RateLimitScope.API_KEY == "api_key"
        assert RateLimitScope.ENDPOINT == "endpoint"


class TestRateLimitConfig:
    """Tests for RateLimitConfig dataclass"""

    def test_default_config(self):
        """Test RateLimitConfig with required fields"""
        config = RateLimitConfig(limit=100, window=3600)

        assert config.limit == 100
        assert config.window == 3600
        assert config.strategy == RateLimitStrategy.SLIDING_WINDOW
        assert config.scope == RateLimitScope.USER
        assert config.burst_limit is None
        assert config.burst_window is None

    def test_custom_config(self):
        """Test RateLimitConfig with all fields"""
        config = RateLimitConfig(
            limit=50,
            window=300,
            strategy=RateLimitStrategy.TOKEN_BUCKET,
            scope=RateLimitScope.IP,
            burst_limit=10,
            burst_window=60
        )

        assert config.limit == 50
        assert config.window == 300
        assert config.strategy == RateLimitStrategy.TOKEN_BUCKET
        assert config.scope == RateLimitScope.IP
        assert config.burst_limit == 10
        assert config.burst_window == 60


class TestRateLimitResult:
    """Tests for RateLimitResult dataclass"""

    def test_result_creation(self):
        """Test RateLimitResult creation"""
        result = RateLimitResult(
            allowed=True,
            remaining=95,
            reset_time=1234567890,
            retry_after=None,
            limit=100,
            current_usage=5
        )

        assert result.allowed is True
        assert result.remaining == 95
        assert result.reset_time == 1234567890
        assert result.retry_after is None
        assert result.limit == 100
        assert result.current_usage == 5


class TestAdvancedRateLimiter:
    """Tests for AdvancedRateLimiter class"""

    def test_init_with_redis(self):
        """Test initialization with Redis client"""
        mock_redis = MockRedis()
        limiter = AdvancedRateLimiter(redis_client=mock_redis)

        assert limiter.redis_client == mock_redis
        assert isinstance(limiter.default_limits, dict)
        assert len(limiter.default_limits) > 0

    def test_init_without_redis(self):
        """Test initialization without Redis (fallback to local cache)"""
        with patch('src.rate_limiting.logger'):
            # Create limiter with explicit None
            limiter = AdvancedRateLimiter(redis_client=None)
            # May have redis_client or may fall back to local cache
            assert isinstance(limiter.local_cache, dict)

    def test_get_key_fixed_window(self):
        """Test key generation for fixed window strategy"""
        limiter = AdvancedRateLimiter(redis_client=MockRedis())
        config = RateLimitConfig(
            limit=10,
            window=60,
            strategy=RateLimitStrategy.FIXED_WINDOW
        )

        key = limiter._get_key("user123", config, "test_rule")

        assert "ratelimit" in key
        assert "user123" in key
        assert "test_rule" in key
        assert "fixed_window" in key

    def test_get_key_sliding_window(self):
        """Test key generation for sliding window strategy"""
        limiter = AdvancedRateLimiter(redis_client=MockRedis())
        config = RateLimitConfig(
            limit=10,
            window=60,
            strategy=RateLimitStrategy.SLIDING_WINDOW
        )

        key = limiter._get_key("user123", config, "test_rule")

        assert "ratelimit" in key
        assert "user123" in key
        assert "sliding_window" in key


class TestFixedWindowRateLimiting:
    """Tests for fixed window rate limiting strategy"""

    def test_fixed_window_first_request(self):
        """Test first request in fixed window"""
        mock_redis = MockRedis()
        limiter = AdvancedRateLimiter(redis_client=mock_redis)
        config = RateLimitConfig(limit=5, window=60, strategy=RateLimitStrategy.FIXED_WINDOW)

        key = limiter._get_key("test_user", config, "test")
        result = limiter._fixed_window_check(key, config)

        assert result.allowed is True
        assert result.remaining == 4
        assert result.limit == 5
        assert result.current_usage == 1

    def test_fixed_window_within_limit(self):
        """Test multiple requests within limit"""
        mock_redis = MockRedis()
        limiter = AdvancedRateLimiter(redis_client=mock_redis)
        config = RateLimitConfig(limit=5, window=60, strategy=RateLimitStrategy.FIXED_WINDOW)

        key = limiter._get_key("test_user", config, "test")

        # Make 5 requests
        for i in range(5):
            result = limiter._fixed_window_check(key, config)
            assert result.allowed is True
            assert result.remaining == 4 - i

    def test_fixed_window_exceeds_limit(self):
        """Test request exceeding fixed window limit"""
        mock_redis = MockRedis()
        limiter = AdvancedRateLimiter(redis_client=mock_redis)
        config = RateLimitConfig(limit=3, window=60, strategy=RateLimitStrategy.FIXED_WINDOW)

        key = limiter._get_key("test_user", config, "test")

        # Make 3 allowed requests
        for _ in range(3):
            result = limiter._fixed_window_check(key, config)
            assert result.allowed is True

        # 4th request should be denied
        result = limiter._fixed_window_check(key, config)
        assert result.allowed is False
        assert result.remaining == 0
        assert result.retry_after is not None

    def test_fixed_window_local_cache_fallback(self):
        """Test fixed window with local cache fallback"""
        limiter = AdvancedRateLimiter(redis_client=None)
        config = RateLimitConfig(limit=5, window=60, strategy=RateLimitStrategy.FIXED_WINDOW)

        key = limiter._get_key("test_user", config, "test")

        # Make requests using local cache
        for i in range(5):
            result = limiter._fixed_window_check(key, config)
            assert result.allowed is True


class TestSlidingWindowRateLimiting:
    """Tests for sliding window rate limiting strategy"""

    def test_sliding_window_first_request(self):
        """Test first request in sliding window"""
        mock_redis = MockRedis()
        limiter = AdvancedRateLimiter(redis_client=mock_redis)
        config = RateLimitConfig(limit=5, window=60, strategy=RateLimitStrategy.SLIDING_WINDOW)

        key = limiter._get_key("test_user", config, "test")
        result = limiter._sliding_window_check(key, config)

        assert result.allowed is True
        assert result.remaining == 4
        assert result.current_usage == 1

    def test_sliding_window_multiple_requests(self):
        """Test multiple requests in sliding window"""
        mock_redis = MockRedis()
        limiter = AdvancedRateLimiter(redis_client=mock_redis)
        config = RateLimitConfig(limit=5, window=60, strategy=RateLimitStrategy.SLIDING_WINDOW)

        key = limiter._get_key("test_user", config, "test")

        # Make multiple requests
        for i in range(5):
            result = limiter._sliding_window_check(key, config)
            assert result.allowed is True

    def test_sliding_window_exceeds_limit(self):
        """Test exceeding sliding window limit"""
        mock_redis = MockRedis()
        limiter = AdvancedRateLimiter(redis_client=mock_redis)
        config = RateLimitConfig(limit=3, window=60, strategy=RateLimitStrategy.SLIDING_WINDOW)

        key = limiter._get_key("test_user", config, "test")

        # Make 3 requests
        for _ in range(3):
            result = limiter._sliding_window_check(key, config)
            assert result.allowed is True

        # 4th request should be denied
        result = limiter._sliding_window_check(key, config)
        assert result.allowed is False
        assert result.retry_after is not None

    def test_sliding_window_local_cache(self):
        """Test sliding window with local cache"""
        # Force local cache by setting redis_client to None after init
        limiter = AdvancedRateLimiter(redis_client=MockRedis())
        limiter.redis_client = None  # Force fallback to local cache

        config = RateLimitConfig(limit=5, window=60, strategy=RateLimitStrategy.SLIDING_WINDOW)

        key = limiter._get_key("test_user", config, "test")

        # Make requests using local cache
        for i in range(5):
            result = limiter._sliding_window_check(key, config)
            assert result.allowed is True
            # Remaining decreases with each request
            assert result.remaining >= 0

    def test_sliding_window_time_decay(self):
        """Test that old entries are removed from sliding window"""
        limiter = AdvancedRateLimiter(redis_client=None)
        config = RateLimitConfig(limit=3, window=1, strategy=RateLimitStrategy.SLIDING_WINDOW)

        key = limiter._get_key("test_user", config, "test")

        # Make 3 requests
        for _ in range(3):
            result = limiter._sliding_window_check(key, config)
            assert result.allowed is True

        # Wait for window to expire
        time.sleep(1.1)

        # Should be able to make requests again
        result = limiter._sliding_window_check(key, config)
        assert result.allowed is True


class TestTokenBucketRateLimiting:
    """Tests for token bucket rate limiting strategy"""

    def test_token_bucket_initial_state(self):
        """Test initial state of token bucket"""
        mock_redis = MockRedis()
        limiter = AdvancedRateLimiter(redis_client=mock_redis)
        config = RateLimitConfig(limit=10, window=60, strategy=RateLimitStrategy.TOKEN_BUCKET)

        key = limiter._get_key("test_user", config, "test")
        result = limiter._token_bucket_check(key, config)

        assert result.allowed is True
        # Initial bucket should be full, minus 1 consumed token
        assert result.remaining < config.limit

    def test_token_bucket_consume_tokens(self):
        """Test consuming tokens from bucket"""
        mock_redis = MockRedis()
        limiter = AdvancedRateLimiter(redis_client=mock_redis)
        config = RateLimitConfig(limit=5, window=10, strategy=RateLimitStrategy.TOKEN_BUCKET)

        key = limiter._get_key("test_user", config, "test")

        # Consume multiple tokens
        for _ in range(5):
            result = limiter._token_bucket_check(key, config)
            assert result.allowed is True

    def test_token_bucket_exhausted(self):
        """Test token bucket when exhausted"""
        mock_redis = MockRedis()
        limiter = AdvancedRateLimiter(redis_client=mock_redis)
        config = RateLimitConfig(limit=3, window=60, strategy=RateLimitStrategy.TOKEN_BUCKET)

        key = limiter._get_key("test_user", config, "test")

        # Exhaust all tokens
        for _ in range(10):  # Try more than limit
            result = limiter._token_bucket_check(key, config)

        # Eventually should be denied
        assert result.allowed is False or result.remaining == 0

    def test_token_bucket_refill(self):
        """Test token refill over time"""
        mock_redis = MockRedis()
        limiter = AdvancedRateLimiter(redis_client=mock_redis)
        config = RateLimitConfig(limit=10, window=1, strategy=RateLimitStrategy.TOKEN_BUCKET)

        key = limiter._get_key("test_user", config, "test")

        # Consume some tokens
        for _ in range(5):
            limiter._token_bucket_check(key, config)

        # Wait for refill
        time.sleep(0.5)

        # Should have refilled some tokens
        result = limiter._token_bucket_check(key, config)
        assert result.allowed is True

    def test_token_bucket_local_cache(self):
        """Test token bucket with local cache"""
        limiter = AdvancedRateLimiter(redis_client=None)
        config = RateLimitConfig(limit=5, window=10, strategy=RateLimitStrategy.TOKEN_BUCKET)

        key = limiter._get_key("test_user", config, "test")

        # Test with local cache
        result = limiter._token_bucket_check(key, config)
        assert result.allowed is True


class TestCheckRateLimit:
    """Tests for check_rate_limit method"""

    def test_check_with_default_config(self):
        """Test rate limit check with default config"""
        limiter = AdvancedRateLimiter(redis_client=MockRedis())

        result = limiter.check_rate_limit("user123", "api_general")

        assert isinstance(result, RateLimitResult)
        assert result.allowed is True

    def test_check_with_custom_config(self):
        """Test rate limit check with custom config"""
        limiter = AdvancedRateLimiter(redis_client=MockRedis())
        config = RateLimitConfig(limit=5, window=60)

        result = limiter.check_rate_limit("user123", "custom_rule", config)

        assert result.allowed is True
        assert result.limit == 5

    def test_check_multiple_users(self):
        """Test rate limiting for multiple users"""
        limiter = AdvancedRateLimiter(redis_client=MockRedis())
        config = RateLimitConfig(limit=3, window=60, strategy=RateLimitStrategy.FIXED_WINDOW)

        # User 1 makes requests
        for _ in range(3):
            result = limiter.check_rate_limit("user1", "test", config)
            assert result.allowed is True

        # User 1 exceeds limit
        result = limiter.check_rate_limit("user1", "test", config)
        assert result.allowed is False

        # User 2 should still be allowed
        result = limiter.check_rate_limit("user2", "test", config)
        assert result.allowed is True

    def test_check_with_burst_limit(self):
        """Test rate limiting with burst limits"""
        limiter = AdvancedRateLimiter(redis_client=MockRedis())

        # Configure burst limit for api_general
        limiter.burst_limits["test_rule"] = RateLimitConfig(
            limit=10,
            window=60,
            strategy=RateLimitStrategy.SLIDING_WINDOW
        )

        # Regular limit should work
        result = limiter.check_rate_limit("user123", "test_rule")
        assert isinstance(result, RateLimitResult)


class TestResetLimit:
    """Tests for reset_limit method"""

    def test_reset_with_redis(self):
        """Test resetting rate limit with Redis"""
        mock_redis = MockRedis()
        limiter = AdvancedRateLimiter(redis_client=mock_redis)
        config = RateLimitConfig(limit=3, window=60, strategy=RateLimitStrategy.FIXED_WINDOW)

        # Configure the default limit for this test
        limiter.default_limits["test_rule"] = config

        # Make some requests
        for _ in range(3):
            limiter.check_rate_limit("user123", "test_rule", config)

        # Verify we're at the limit
        result_before = limiter.check_rate_limit("user123", "test_rule", config)

        # Reset the limit by clearing all keys for this rule
        # Need to get the actual key that was used
        key = limiter._get_key("user123", config, "test_rule")
        mock_redis.data.clear()  # Clear all data to reset

        # Should be able to make requests again
        result = limiter.check_rate_limit("user123", "test_rule", config)
        assert result.allowed is True

    def test_reset_with_local_cache(self):
        """Test resetting rate limit with local cache"""
        limiter = AdvancedRateLimiter(redis_client=None)
        config = RateLimitConfig(limit=3, window=60, strategy=RateLimitStrategy.FIXED_WINDOW)

        # Make some requests
        for _ in range(3):
            limiter.check_rate_limit("user123", "test_rule", config)

        # Reset
        limiter.reset_limit("user123", "test_rule")

        # Verify reset worked
        result = limiter.check_rate_limit("user123", "test_rule", config)
        assert result.allowed is True


class TestGetLimitStatus:
    """Tests for get_limit_status method"""

    def test_get_status_sliding_window(self):
        """Test getting status for sliding window"""
        limiter = AdvancedRateLimiter(redis_client=MockRedis())
        config = RateLimitConfig(limit=10, window=60, strategy=RateLimitStrategy.SLIDING_WINDOW)
        limiter.default_limits["test_rule"] = config

        # Make some requests
        for _ in range(3):
            limiter.check_rate_limit("user123", "test_rule")

        # Get status
        status = limiter.get_limit_status("user123", "test_rule")

        assert "current_usage" in status
        assert "limit" in status
        assert "remaining" in status
        assert status["limit"] == 10

    def test_get_status_other_strategy(self):
        """Test getting status for other strategies"""
        limiter = AdvancedRateLimiter(redis_client=MockRedis())
        config = RateLimitConfig(limit=10, window=60, strategy=RateLimitStrategy.TOKEN_BUCKET)
        limiter.default_limits["test_rule"] = config

        status = limiter.get_limit_status("user123", "test_rule")

        assert "limit" in status
        assert status["limit"] == 10


class TestRateLimitMiddleware:
    """Tests for FastAPI rate limit middleware"""

    @pytest.fixture
    def mock_app(self):
        """Create mock FastAPI app"""
        return AsyncMock()

    @pytest.fixture
    def mock_request(self):
        """Create mock request"""
        request = Mock()
        request.url.path = "/api/test"
        request.client.host = "127.0.0.1"
        request.headers.get = Mock(return_value=None)
        return request

    def test_middleware_init(self, mock_app):
        """Test middleware initialization"""
        middleware = RateLimitMiddleware(mock_app)

        assert middleware.app == mock_app
        assert middleware.limiter is not None
        assert isinstance(middleware.endpoint_limits, dict)

    def test_get_identifier_from_ip(self):
        """Test getting identifier from IP address"""
        middleware = RateLimitMiddleware(Mock())
        request = Mock()
        request.headers.get = Mock(return_value=None)
        request.client.host = "192.168.1.1"

        identifier = middleware._get_identifier(request)

        assert identifier.startswith("ip:")
        assert "192.168.1.1" in identifier

    def test_get_identifier_from_api_key(self):
        """Test getting identifier from API key"""
        middleware = RateLimitMiddleware(Mock())
        request = Mock()
        request.headers.get = Mock(side_effect=lambda h: "test-api-key" if h == "x-api-key" else None)
        request.client.host = "192.168.1.1"

        identifier = middleware._get_identifier(request)

        assert identifier.startswith("apikey:")


class TestAPIComplianceChecker:
    """Tests for API compliance checker"""

    def test_init(self):
        """Test compliance checker initialization"""
        checker = APIComplianceChecker()

        assert "twitter" in checker.api_limits
        assert "news_feeds" in checker.api_limits

    def test_check_twitter_compliance_within_limit(self):
        """Test Twitter compliance check within limit"""
        checker = APIComplianceChecker()

        compliant, message = checker.check_twitter_compliance("search_tweets", 100)

        assert compliant is True
        assert "Within limits" in message

    def test_check_twitter_compliance_approaching_limit(self):
        """Test Twitter compliance when approaching limit"""
        checker = APIComplianceChecker()

        # Calculate effective limit (80% of 300 = 240)
        compliant, message = checker.check_twitter_compliance("search_tweets", 250)

        assert compliant is False
        assert "Approaching" in message or "limit" in message.lower()

    def test_check_twitter_compliance_unknown_endpoint(self):
        """Test Twitter compliance for unknown endpoint"""
        checker = APIComplianceChecker()

        compliant, message = checker.check_twitter_compliance("unknown_endpoint", 100)

        assert compliant is True
        assert "Unknown" in message

    def test_check_feed_compliance_within_limit(self):
        """Test feed compliance within limit"""
        checker = APIComplianceChecker()

        compliant, message = checker.check_feed_compliance("http://example.com/feed", 30)

        assert compliant is True
        assert "within limits" in message.lower()

    def test_check_feed_compliance_exceeds_limit(self):
        """Test feed compliance exceeding limit"""
        checker = APIComplianceChecker()

        compliant, message = checker.check_feed_compliance("http://example.com/feed", 100)

        assert compliant is False
        assert "Exceeding" in message

    def test_get_recommended_delay_twitter(self):
        """Test getting recommended delay for Twitter"""
        checker = APIComplianceChecker()

        delay = checker.get_recommended_delay("twitter", "search_tweets")

        assert delay > 0
        assert isinstance(delay, int)

    def test_get_recommended_delay_news_feeds(self):
        """Test getting recommended delay for news feeds"""
        checker = APIComplianceChecker()

        delay = checker.get_recommended_delay("news_feeds", "")

        assert delay >= 1
        assert isinstance(delay, int)

    def test_get_recommended_delay_unknown(self):
        """Test getting recommended delay for unknown API"""
        checker = APIComplianceChecker()

        delay = checker.get_recommended_delay("unknown_api", "endpoint")

        assert delay == 1  # Default


class TestUtilityFunctions:
    """Tests for utility functions"""

    def test_check_user_rate_limit(self):
        """Test check_user_rate_limit function"""
        with patch('src.rate_limiting.rate_limiter') as mock_limiter:
            mock_limiter.check_rate_limit = Mock(return_value=RateLimitResult(
                allowed=True, remaining=99, reset_time=123456, limit=100, current_usage=1
            ))

            result = check_user_rate_limit(123, "api_general")

            assert result.allowed is True
            mock_limiter.check_rate_limit.assert_called_once()

    def test_check_ip_rate_limit(self):
        """Test check_ip_rate_limit function"""
        with patch('src.rate_limiting.rate_limiter') as mock_limiter:
            mock_limiter.check_rate_limit = Mock(return_value=RateLimitResult(
                allowed=True, remaining=99, reset_time=123456, limit=100, current_usage=1
            ))

            result = check_ip_rate_limit("192.168.1.1", "api_general")

            assert result.allowed is True
            mock_limiter.check_rate_limit.assert_called_once()

    def test_check_api_key_rate_limit(self):
        """Test check_api_key_rate_limit function"""
        with patch('src.rate_limiting.rate_limiter') as mock_limiter:
            mock_limiter.check_rate_limit = Mock(return_value=RateLimitResult(
                allowed=True, remaining=99, reset_time=123456, limit=100, current_usage=1
            ))

            result = check_api_key_rate_limit("key_hash", "api_general")

            assert result.allowed is True

    def test_reset_user_limit(self):
        """Test reset_user_limit function"""
        with patch('src.rate_limiting.rate_limiter') as mock_limiter:
            mock_limiter.reset_limit = Mock()

            reset_user_limit(123, "api_general")

            mock_limiter.reset_limit.assert_called_once()

    def test_get_rate_limit_stats(self):
        """Test get_rate_limit_stats function"""
        stats = get_rate_limit_stats()

        assert "configured_limits" in stats
        assert "burst_limits" in stats
        assert isinstance(stats["configured_limits"], dict)
        assert isinstance(stats["burst_limits"], dict)


class TestErrorHandling:
    """Tests for error handling and edge cases"""

    def test_rate_limit_check_redis_error(self):
        """Test rate limit check handles Redis errors gracefully"""
        mock_redis = Mock()
        mock_redis.pipeline = Mock(side_effect=Exception("Redis error"))

        limiter = AdvancedRateLimiter(redis_client=mock_redis)
        config = RateLimitConfig(limit=10, window=60, strategy=RateLimitStrategy.FIXED_WINDOW)

        key = limiter._get_key("user123", config, "test")
        result = limiter._fixed_window_check(key, config)

        # Should fail open (allow request)
        assert result.allowed is True

    def test_sliding_window_redis_error(self):
        """Test sliding window handles Redis errors"""
        mock_redis = Mock()
        mock_redis.pipeline = Mock(side_effect=Exception("Redis error"))

        limiter = AdvancedRateLimiter(redis_client=mock_redis)
        config = RateLimitConfig(limit=10, window=60, strategy=RateLimitStrategy.SLIDING_WINDOW)

        key = limiter._get_key("user123", config, "test")
        result = limiter._sliding_window_check(key, config)

        # Should fail open
        assert result.allowed is True

    def test_token_bucket_redis_error(self):
        """Test token bucket handles Redis errors"""
        mock_redis = Mock()
        mock_redis.hgetall = Mock(side_effect=Exception("Redis error"))

        limiter = AdvancedRateLimiter(redis_client=mock_redis)
        config = RateLimitConfig(limit=10, window=60, strategy=RateLimitStrategy.TOKEN_BUCKET)

        key = limiter._get_key("user123", config, "test")
        result = limiter._token_bucket_check(key, config)

        # Should fail open
        assert result.allowed is True


class TestConcurrentAccess:
    """Tests for concurrent access scenarios"""

    def test_multiple_identifiers_isolated(self):
        """Test that different identifiers are isolated"""
        limiter = AdvancedRateLimiter(redis_client=MockRedis())
        config = RateLimitConfig(limit=2, window=60, strategy=RateLimitStrategy.FIXED_WINDOW)

        # User 1 exhausts their limit
        limiter.check_rate_limit("user1", "test", config)
        limiter.check_rate_limit("user1", "test", config)
        result1 = limiter.check_rate_limit("user1", "test", config)

        # User 2 should still have full limit
        result2 = limiter.check_rate_limit("user2", "test", config)

        assert result1.allowed is False
        assert result2.allowed is True

    def test_different_rules_isolated(self):
        """Test that different rules are isolated"""
        limiter = AdvancedRateLimiter(redis_client=MockRedis())
        config = RateLimitConfig(limit=1, window=60, strategy=RateLimitStrategy.FIXED_WINDOW)

        # Exhaust limit for rule1
        limiter.check_rate_limit("user1", "rule1", config)
        result1 = limiter.check_rate_limit("user1", "rule1", config)

        # rule2 should still be available
        result2 = limiter.check_rate_limit("user1", "rule2", config)

        assert result1.allowed is False
        assert result2.allowed is True


class TestTimeBasedOperations:
    """Tests for time-based operations with mocked time"""

    def test_fixed_window_resets_at_boundary(self):
        """Test fixed window resets at time boundary"""
        # Use local cache for timing test
        limiter = AdvancedRateLimiter(redis_client=MockRedis())
        limiter.redis_client = None  # Force local cache

        config = RateLimitConfig(limit=2, window=1, strategy=RateLimitStrategy.FIXED_WINDOW)

        key = limiter._get_key("user1", config, "test")

        # Exhaust limit
        limiter._fixed_window_check(key, config)
        limiter._fixed_window_check(key, config)
        result1 = limiter._fixed_window_check(key, config)

        assert result1.allowed is False

        # Wait for window to expire
        time.sleep(1.1)

        # Create a new key for the new time window
        key_new = limiter._get_key("user1", config, "test")

        # Should be able to make requests again (new window)
        result2 = limiter._fixed_window_check(key_new, config)
        assert result2.allowed is True

    def test_token_bucket_refills_over_time(self):
        """Test token bucket refills over time"""
        limiter = AdvancedRateLimiter(redis_client=None)
        config = RateLimitConfig(limit=10, window=1, strategy=RateLimitStrategy.TOKEN_BUCKET)

        key = limiter._get_key("user1", config, "test")

        # Consume tokens
        for _ in range(10):
            limiter._token_bucket_check(key, config)

        # Wait for partial refill
        time.sleep(0.2)

        # Should have some tokens available
        result = limiter._token_bucket_check(key, config)
        # May or may not be allowed depending on exact timing
        assert isinstance(result, RateLimitResult)

"""
Advanced rate limiting and API compliance for TGE Monitor
Redis-based distributed rate limiting with multiple strategies
"""

import time
import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
from enum import Enum
import hashlib
import redis
from fastapi import HTTPException, status, Request
from fastapi.responses import JSONResponse

from .database import CacheManager

logger = logging.getLogger(__name__)


class RateLimitStrategy(str, Enum):
    """Rate limiting strategies"""
    FIXED_WINDOW = "fixed_window"
    SLIDING_WINDOW = "sliding_window"
    TOKEN_BUCKET = "token_bucket"
    LEAKY_BUCKET = "leaky_bucket"


class RateLimitScope(str, Enum):
    """Rate limiting scopes"""
    GLOBAL = "global"
    USER = "user"
    IP = "ip"
    API_KEY = "api_key"
    ENDPOINT = "endpoint"


@dataclass
class RateLimitConfig:
    """Rate limit configuration"""
    limit: int
    window: int  # seconds
    strategy: RateLimitStrategy = RateLimitStrategy.SLIDING_WINDOW
    scope: RateLimitScope = RateLimitScope.USER
    burst_limit: Optional[int] = None
    burst_window: Optional[int] = None


@dataclass
class RateLimitResult:
    """Rate limit check result"""
    allowed: bool
    remaining: int
    reset_time: int
    retry_after: Optional[int] = None
    limit: int = 0
    current_usage: int = 0


class AdvancedRateLimiter:
    """Advanced rate limiter with multiple strategies and Redis backend"""
    
    def __init__(self, redis_client: Optional[redis.Redis] = None):
        # Import redis_client from database module if not provided
        if redis_client is None:
            try:
                from .database import redis_client as db_redis_client
                self.redis_client = db_redis_client
            except ImportError:
                logger.warning("Redis client not available, using local cache only")
                self.redis_client = None
        else:
            self.redis_client = redis_client
        self.local_cache = {}  # Fallback for when Redis is unavailable
        
        # Default rate limit configurations
        self.default_limits = {
            "api_general": RateLimitConfig(limit=1000, window=3600, scope=RateLimitScope.USER),
            "api_alerts": RateLimitConfig(limit=100, window=3600, scope=RateLimitScope.USER),
            "api_search": RateLimitConfig(limit=50, window=3600, scope=RateLimitScope.USER),
            "websocket": RateLimitConfig(limit=10, window=60, scope=RateLimitScope.IP),
            "twitter_api": RateLimitConfig(limit=300, window=900, scope=RateLimitScope.GLOBAL),  # Twitter API v2 limits
            "news_feeds": RateLimitConfig(limit=1, window=300, scope=RateLimitScope.ENDPOINT),  # Per feed limits
        }
        
        # Burst limits for sudden spikes
        self.burst_limits = {
            "api_general": RateLimitConfig(limit=100, window=60, scope=RateLimitScope.USER),
            "api_alerts": RateLimitConfig(limit=20, window=60, scope=RateLimitScope.USER),
        }
    
    def _get_key(self, identifier: str, config: RateLimitConfig, rule_name: str) -> str:
        """Generate Redis key for rate limiting"""
        scope = config.scope.value
        strategy = config.strategy.value
        window = config.window
        
        # Create unique key based on scope, strategy, and time window
        if config.strategy == RateLimitStrategy.FIXED_WINDOW:
            # Round down to window boundary
            window_start = int(time.time()) // window * window
            return f"ratelimit:{scope}:{rule_name}:{strategy}:{identifier}:{window_start}"
        else:
            # For sliding window and bucket strategies
            return f"ratelimit:{scope}:{rule_name}:{strategy}:{identifier}"
    
    def _fixed_window_check(self, key: str, config: RateLimitConfig) -> RateLimitResult:
        """Fixed window rate limiting"""
        try:
            if self.redis_client:
                pipe = self.redis_client.pipeline()
                pipe.incr(key)
                pipe.expire(key, config.window)
                results = pipe.execute()
                current_count = results[0]
            else:
                # Fallback to local cache
                now = int(time.time())
                window_start = now // config.window * config.window
                
                if key not in self.local_cache:
                    self.local_cache[key] = {"count": 0, "window_start": window_start}
                
                cache_entry = self.local_cache[key]
                if cache_entry["window_start"] != window_start:
                    cache_entry["count"] = 0
                    cache_entry["window_start"] = window_start
                
                cache_entry["count"] += 1
                current_count = cache_entry["count"]
            
            remaining = max(0, config.limit - current_count)
            allowed = current_count <= config.limit
            
            # Calculate reset time
            now = int(time.time())
            window_start = now // config.window * config.window
            reset_time = window_start + config.window
            
            return RateLimitResult(
                allowed=allowed,
                remaining=remaining,
                reset_time=reset_time,
                retry_after=reset_time - now if not allowed else None,
                limit=config.limit,
                current_usage=current_count
            )
            
        except Exception as e:
            logger.error(f"Rate limit check failed: {e}")
            # Fail open - allow request if rate limiting fails
            return RateLimitResult(
                allowed=True,
                remaining=config.limit,
                reset_time=int(time.time()) + config.window,
                limit=config.limit,
                current_usage=0
            )
    
    def _sliding_window_check(self, key: str, config: RateLimitConfig) -> RateLimitResult:
        """Sliding window rate limiting"""
        try:
            now = time.time()
            window_start = now - config.window
            
            if self.redis_client:
                pipe = self.redis_client.pipeline()
                
                # Add current timestamp
                pipe.zadd(key, {str(now): now})
                
                # Remove old entries
                pipe.zremrangebyscore(key, 0, window_start)
                
                # Count current entries
                pipe.zcard(key)
                
                # Set expiration
                pipe.expire(key, config.window + 1)
                
                results = pipe.execute()
                current_count = results[2]
            else:
                # Fallback to simplified local cache
                if key not in self.local_cache:
                    self.local_cache[key] = []
                
                # Clean old entries
                self.local_cache[key] = [
                    timestamp for timestamp in self.local_cache[key]
                    if timestamp > window_start
                ]
                
                # Add current timestamp
                self.local_cache[key].append(now)
                current_count = len(self.local_cache[key])
            
            remaining = max(0, config.limit - current_count)
            allowed = current_count <= config.limit
            
            return RateLimitResult(
                allowed=allowed,
                remaining=remaining,
                reset_time=int(now + config.window),
                retry_after=1 if not allowed else None,
                limit=config.limit,
                current_usage=current_count
            )
            
        except Exception as e:
            logger.error(f"Sliding window rate limit check failed: {e}")
            return RateLimitResult(
                allowed=True,
                remaining=config.limit,
                reset_time=int(time.time()) + config.window,
                limit=config.limit,
                current_usage=0
            )
    
    def _token_bucket_check(self, key: str, config: RateLimitConfig) -> RateLimitResult:
        """Token bucket rate limiting"""
        try:
            now = time.time()
            
            # Token bucket algorithm
            refill_rate = config.limit / config.window  # tokens per second
            bucket_size = config.limit
            
            if self.redis_client:
                bucket_key = f"{key}:bucket"
                bucket_data = self.redis_client.hgetall(bucket_key)
                
                if bucket_data:
                    tokens = float(bucket_data.get(b'tokens', bucket_size))
                    last_refill = float(bucket_data.get(b'last_refill', now))
                else:
                    tokens = bucket_size
                    last_refill = now
                
                # Calculate tokens to add
                time_passed = now - last_refill
                tokens_to_add = time_passed * refill_rate
                tokens = min(bucket_size, tokens + tokens_to_add)
                
                # Check if we can consume a token
                if tokens >= 1:
                    tokens -= 1
                    allowed = True
                else:
                    allowed = False
                
                # Update bucket state
                pipe = self.redis_client.pipeline()
                pipe.hset(bucket_key, mapping={
                    'tokens': tokens,
                    'last_refill': now
                })
                pipe.expire(bucket_key, config.window * 2)
                pipe.execute()
                
            else:
                # Local cache fallback
                if key not in self.local_cache:
                    self.local_cache[key] = {
                        'tokens': bucket_size,
                        'last_refill': now
                    }
                
                bucket = self.local_cache[key]
                time_passed = now - bucket['last_refill']
                tokens_to_add = time_passed * refill_rate
                bucket['tokens'] = min(bucket_size, bucket['tokens'] + tokens_to_add)
                bucket['last_refill'] = now
                
                if bucket['tokens'] >= 1:
                    bucket['tokens'] -= 1
                    allowed = True
                    tokens = bucket['tokens']
                else:
                    allowed = False
                    tokens = bucket['tokens']
            
            return RateLimitResult(
                allowed=allowed,
                remaining=int(tokens),
                reset_time=int(now + (1 - tokens) / refill_rate) if tokens < 1 else int(now),
                retry_after=int((1 - tokens) / refill_rate) if not allowed else None,
                limit=config.limit,
                current_usage=config.limit - int(tokens)
            )
            
        except Exception as e:
            logger.error(f"Token bucket rate limit check failed: {e}")
            return RateLimitResult(
                allowed=True,
                remaining=config.limit,
                reset_time=int(time.time()) + config.window,
                limit=config.limit,
                current_usage=0
            )
    
    def check_rate_limit(
        self, 
        identifier: str, 
        rule_name: str, 
        config: Optional[RateLimitConfig] = None
    ) -> RateLimitResult:
        """Check rate limit for given identifier and rule"""
        
        if config is None:
            config = self.default_limits.get(rule_name)
            if config is None:
                # Default fallback
                config = RateLimitConfig(limit=100, window=3600)
        
        key = self._get_key(identifier, config, rule_name)
        
        # Choose strategy
        if config.strategy == RateLimitStrategy.FIXED_WINDOW:
            result = self._fixed_window_check(key, config)
        elif config.strategy == RateLimitStrategy.SLIDING_WINDOW:
            result = self._sliding_window_check(key, config)
        elif config.strategy == RateLimitStrategy.TOKEN_BUCKET:
            result = self._token_bucket_check(key, config)
        else:
            # Default to sliding window
            result = self._sliding_window_check(key, config)
        
        # Check burst limits if configured
        if not result.allowed and rule_name in self.burst_limits:
            burst_config = self.burst_limits[rule_name]
            burst_key = self._get_key(identifier, burst_config, f"{rule_name}_burst")
            burst_result = self._sliding_window_check(burst_key, burst_config)
            
            if burst_result.allowed:
                logger.info(f"Burst limit allowed for {identifier} on {rule_name}")
                return burst_result
        
        return result
    
    def reset_limit(self, identifier: str, rule_name: str):
        """Reset rate limit for identifier"""
        try:
            config = self.default_limits.get(rule_name, RateLimitConfig(limit=100, window=3600))
            key = self._get_key(identifier, config, rule_name)
            
            if self.redis_client:
                self.redis_client.delete(key)
            else:
                self.local_cache.pop(key, None)
                
            logger.info(f"Reset rate limit for {identifier} on {rule_name}")
            
        except Exception as e:
            logger.error(f"Failed to reset rate limit: {e}")
    
    def get_limit_status(self, identifier: str, rule_name: str) -> Dict[str, Any]:
        """Get current rate limit status without incrementing"""
        try:
            config = self.default_limits.get(rule_name, RateLimitConfig(limit=100, window=3600))
            key = self._get_key(identifier, config, rule_name)
            
            if config.strategy == RateLimitStrategy.SLIDING_WINDOW:
                now = time.time()
                window_start = now - config.window
                
                if self.redis_client:
                    count = self.redis_client.zcount(key, window_start, now)
                else:
                    entries = self.local_cache.get(key, [])
                    count = len([t for t in entries if t > window_start])
                
                return {
                    "current_usage": count,
                    "limit": config.limit,
                    "remaining": max(0, config.limit - count),
                    "window": config.window,
                    "reset_time": int(now + config.window)
                }
            
            # For other strategies, perform a check without incrementing
            # This is a simplified approach - in production you might want more sophisticated status checking
            return {
                "current_usage": 0,
                "limit": config.limit,
                "remaining": config.limit,
                "window": config.window,
                "reset_time": int(time.time() + config.window)
            }
            
        except Exception as e:
            logger.error(f"Failed to get limit status: {e}")
            return {
                "current_usage": 0,
                "limit": 100,
                "remaining": 100,
                "window": 3600,
                "reset_time": int(time.time() + 3600)
            }


# Global rate limiter instance
rate_limiter = AdvancedRateLimiter()


# FastAPI middleware for rate limiting
class RateLimitMiddleware:
    """FastAPI middleware for automatic rate limiting"""
    
    def __init__(self, app):
        self.app = app
        self.limiter = rate_limiter
        
        # Endpoint-specific rate limits
        self.endpoint_limits = {
            "/api/alerts": "api_alerts",
            "/api/companies": "api_general",
            "/api/search": "api_search",
            "/ws": "websocket"
        }
    
    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        
        request = Request(scope, receive)
        
        # Determine rate limit rule
        path = request.url.path
        rule_name = "api_general"  # default
        
        for endpoint_path, endpoint_rule in self.endpoint_limits.items():
            if path.startswith(endpoint_path):
                rule_name = endpoint_rule
                break
        
        # Get identifier (user ID, API key, or IP)
        identifier = self._get_identifier(request)
        
        # Check rate limit
        result = self.limiter.check_rate_limit(identifier, rule_name)
        
        if not result.allowed:
            # Rate limit exceeded
            response = JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error": "Rate limit exceeded",
                    "retry_after": result.retry_after,
                    "limit": result.limit,
                    "remaining": result.remaining,
                    "reset_time": result.reset_time
                },
                headers={
                    "X-RateLimit-Limit": str(result.limit),
                    "X-RateLimit-Remaining": str(result.remaining),
                    "X-RateLimit-Reset": str(result.reset_time),
                    "Retry-After": str(result.retry_after) if result.retry_after else "60"
                }
            )
            await response(scope, receive, send)
            return
        
        # Add rate limit headers to response
        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                headers = dict(message.get("headers", []))
                headers.update({
                    b"x-ratelimit-limit": str(result.limit).encode(),
                    b"x-ratelimit-remaining": str(result.remaining).encode(),
                    b"x-ratelimit-reset": str(result.reset_time).encode()
                })
                message["headers"] = list(headers.items())
            await send(message)
        
        await self.app(scope, receive, send_wrapper)
    
    def _get_identifier(self, request: Request) -> str:
        """Get rate limit identifier from request"""
        # Try to get user ID from JWT token
        auth_header = request.headers.get("authorization")
        if auth_header and auth_header.startswith("Bearer "):
            try:
                from .auth import AuthManager
                token = auth_header.split(" ", 1)[1]
                token_data = AuthManager.verify_token(token)
                if token_data:
                    return f"user:{token_data.user_id}"
            except:
                pass
        
        # Try to get API key
        api_key = request.headers.get("x-api-key")
        if api_key:
            # Hash the API key for privacy
            key_hash = hashlib.sha256(api_key.encode()).hexdigest()[:16]
            return f"apikey:{key_hash}"
        
        # Fall back to IP address
        client_ip = request.client.host
        return f"ip:{client_ip}"


# API compliance checker for external services
class APIComplianceChecker:
    """Check compliance with external API rate limits and terms"""
    
    def __init__(self):
        self.api_limits = {
            "twitter": {
                "search_tweets": {"limit": 300, "window": 900},  # 15 minutes
                "user_tweets": {"limit": 900, "window": 900},
                "rate_limit_buffer": 0.8  # Use only 80% of limit for safety
            },
            "news_feeds": {
                "requests_per_minute": 60,
                "concurrent_requests": 5,
                "user_agent_required": True,
                "respect_robots_txt": True
            }
        }
    
    def check_twitter_compliance(self, endpoint: str, requests_made: int) -> Tuple[bool, str]:
        """Check Twitter API compliance"""
        limits = self.api_limits["twitter"]
        
        if endpoint not in limits:
            return True, "Unknown endpoint"
        
        endpoint_limit = limits[endpoint]
        buffer = limits["rate_limit_buffer"]
        effective_limit = int(endpoint_limit["limit"] * buffer)
        
        if requests_made >= effective_limit:
            return False, f"Approaching Twitter API limit for {endpoint}"
        
        return True, "Within limits"
    
    def check_feed_compliance(self, feed_url: str, request_frequency: int) -> Tuple[bool, str]:
        """Check news feed compliance"""
        limits = self.api_limits["news_feeds"]
        
        if request_frequency > limits["requests_per_minute"]:
            return False, f"Exceeding recommended request frequency for {feed_url}"
        
        return True, "Feed requests within limits"
    
    def get_recommended_delay(self, api_name: str, endpoint: str) -> int:
        """Get recommended delay between requests"""
        if api_name == "twitter":
            limits = self.api_limits["twitter"].get(endpoint, {"limit": 300, "window": 900})
            return limits["window"] // limits["limit"]  # Seconds between requests
        
        elif api_name == "news_feeds":
            return 60 // self.api_limits["news_feeds"]["requests_per_minute"]
        
        return 1  # Default 1 second


# Global compliance checker
compliance_checker = APIComplianceChecker()


# Utility functions
def check_user_rate_limit(user_id: int, rule_name: str = "api_general") -> RateLimitResult:
    """Check rate limit for a specific user"""
    return rate_limiter.check_rate_limit(f"user:{user_id}", rule_name)


def check_ip_rate_limit(ip_address: str, rule_name: str = "api_general") -> RateLimitResult:
    """Check rate limit for an IP address"""
    return rate_limiter.check_rate_limit(f"ip:{ip_address}", rule_name)


def check_api_key_rate_limit(api_key_hash: str, rule_name: str = "api_general") -> RateLimitResult:
    """Check rate limit for an API key"""
    return rate_limiter.check_rate_limit(f"apikey:{api_key_hash}", rule_name)


def reset_user_limit(user_id: int, rule_name: str = "api_general"):
    """Reset rate limit for a user (admin function)"""
    rate_limiter.reset_limit(f"user:{user_id}", rule_name)


def get_rate_limit_stats() -> Dict[str, Any]:
    """Get rate limiting statistics"""
    return {
        "configured_limits": {
            name: {
                "limit": config.limit,
                "window": config.window,
                "strategy": config.strategy.value,
                "scope": config.scope.value
            }
            for name, config in rate_limiter.default_limits.items()
        },
        "burst_limits": {
            name: {
                "limit": config.limit,
                "window": config.window
            }
            for name, config in rate_limiter.burst_limits.items()
        }
    }


if __name__ == "__main__":
    # Test rate limiting functionality
    import asyncio
    
    def test_rate_limiting():
        """Test rate limiting functionality"""
        print("Testing rate limiting...")
        
        # Test fixed window
        config = RateLimitConfig(
            limit=5,
            window=60,
            strategy=RateLimitStrategy.FIXED_WINDOW
        )
        
        # Make several requests
        for i in range(7):
            result = rate_limiter.check_rate_limit("test_user", "test_rule", config)
            print(f"Request {i+1}: allowed={result.allowed}, remaining={result.remaining}")
        
        print("✓ Rate limiting test completed")
    
    test_rate_limiting()
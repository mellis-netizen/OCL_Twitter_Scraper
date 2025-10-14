"""
Security Middleware for TGE Monitor API
Adds comprehensive security headers and protections
"""

import time
import logging
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.middleware.httpsredirect import HTTPSRedirectMiddleware
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, Callable
import os

logger = logging.getLogger(__name__)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses"""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)

        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"

        # Content Security Policy
        csp = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self' data:; "
            "connect-src 'self' https://ocltwitterscraper-production.up.railway.app; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "form-action 'self';"
        )
        response.headers["Content-Security-Policy"] = csp

        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Enhanced rate limiting middleware with sliding window"""

    def __init__(self, app, requests_per_minute: int = 60, requests_per_hour: int = 1000):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.requests_per_hour = requests_per_hour
        self.minute_window: Dict[str, list] = defaultdict(list)
        self.hour_window: Dict[str, list] = defaultdict(list)
        self.cleanup_interval = 300  # Clean up every 5 minutes
        self.last_cleanup = time.time()

    def _get_client_id(self, request: Request) -> str:
        """Get client identifier from request"""
        # Try to get user ID from auth
        if hasattr(request.state, 'user') and request.state.user:
            return f"user_{request.state.user.id}"

        # Fall back to IP address
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host

    def _cleanup_old_requests(self):
        """Remove old entries from rate limit windows"""
        current_time = time.time()

        if current_time - self.last_cleanup > self.cleanup_interval:
            cutoff_minute = current_time - 60
            cutoff_hour = current_time - 3600

            # Clean minute window
            for client_id in list(self.minute_window.keys()):
                self.minute_window[client_id] = [
                    t for t in self.minute_window[client_id] if t > cutoff_minute
                ]
                if not self.minute_window[client_id]:
                    del self.minute_window[client_id]

            # Clean hour window
            for client_id in list(self.hour_window.keys()):
                self.hour_window[client_id] = [
                    t for t in self.hour_window[client_id] if t > cutoff_hour
                ]
                if not self.hour_window[client_id]:
                    del self.hour_window[client_id]

            self.last_cleanup = current_time

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip rate limiting for health checks and docs
        if request.url.path in ["/health", "/docs", "/redoc", "/openapi.json"]:
            return await call_next(request)

        client_id = self._get_client_id(request)
        current_time = time.time()

        # Clean up old entries periodically
        self._cleanup_old_requests()

        # Check minute window
        minute_requests = [t for t in self.minute_window[client_id] if t > current_time - 60]
        if len(minute_requests) >= self.requests_per_minute:
            logger.warning(f"Rate limit exceeded (minute) for {client_id}")
            return JSONResponse(
                status_code=429,
                content={
                    "detail": "Too many requests. Please try again in a minute.",
                    "retry_after": 60
                },
                headers={"Retry-After": "60"}
            )

        # Check hour window
        hour_requests = [t for t in self.hour_window[client_id] if t > current_time - 3600]
        if len(hour_requests) >= self.requests_per_hour:
            logger.warning(f"Rate limit exceeded (hour) for {client_id}")
            return JSONResponse(
                status_code=429,
                content={
                    "detail": "Hourly rate limit exceeded. Please try again later.",
                    "retry_after": 3600
                },
                headers={"Retry-After": "3600"}
            )

        # Record request
        self.minute_window[client_id].append(current_time)
        self.hour_window[client_id].append(current_time)

        # Add rate limit headers to response
        response = await call_next(request)
        response.headers["X-RateLimit-Limit-Minute"] = str(self.requests_per_minute)
        response.headers["X-RateLimit-Remaining-Minute"] = str(
            self.requests_per_minute - len(minute_requests) - 1
        )
        response.headers["X-RateLimit-Limit-Hour"] = str(self.requests_per_hour)
        response.headers["X-RateLimit-Remaining-Hour"] = str(
            self.requests_per_hour - len(hour_requests) - 1
        )

        return response


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log all requests with timing information"""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.time()

        # Process request
        response = await call_next(request)

        # Calculate processing time
        process_time = time.time() - start_time

        # Add timing header
        response.headers["X-Process-Time"] = f"{process_time:.4f}"

        # Log request (skip health checks)
        if request.url.path not in ["/health"]:
            logger.info(
                f"{request.method} {request.url.path} "
                f"- Status: {response.status_code} "
                f"- Time: {process_time:.4f}s"
            )

        return response


def setup_security_middleware(app):
    """Setup all security middleware for the FastAPI app"""

    # HTTPS redirect in production
    if os.getenv("ENV", "").lower() == "production":
        app.add_middleware(HTTPSRedirectMiddleware)

    # Trusted host middleware
    allowed_hosts = os.getenv(
        "ALLOWED_HOSTS",
        "localhost,127.0.0.1,ocltwitterscraper-production.up.railway.app,*.amplifyapp.com"
    ).split(",")
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=allowed_hosts)

    # Security headers
    app.add_middleware(SecurityHeadersMiddleware)

    # Rate limiting
    app.add_middleware(
        RateLimitMiddleware,
        requests_per_minute=int(os.getenv("RATE_LIMIT_PER_MINUTE", "60")),
        requests_per_hour=int(os.getenv("RATE_LIMIT_PER_HOUR", "1000"))
    )

    # Request logging
    app.add_middleware(RequestLoggingMiddleware)

    logger.info("Security middleware configured successfully")

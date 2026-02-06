"""
Rate Limiting Middleware for Kilo's Bastion AI

Provides in-memory rate limiting to prevent abuse of API endpoints.
Uses a sliding window algorithm for smooth rate limiting.

Usage:
    from kilo_v2.rate_limiter import RateLimiter, rate_limit_dependency
    
    # As a dependency
    @app.get("/api/endpoint")
    async def endpoint(rate_check: None = Depends(rate_limit_dependency(limit=100, window=60))):
        ...
    
    # Or use the middleware for global limiting
    app.add_middleware(RateLimitMiddleware, default_limit=1000, window_seconds=60)
"""

import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from functools import wraps
from typing import Callable, Dict, Optional

from fastapi import HTTPException, Request, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)


@dataclass
class RateLimitState:
    """Tracks request counts for a single client."""

    requests: list = field(default_factory=list)
    blocked_until: float = 0.0


class RateLimiter:
    """
    In-memory rate limiter using sliding window algorithm.

    Args:
        default_limit: Maximum requests per window
        window_seconds: Time window in seconds
        burst_multiplier: Allow burst up to limit * multiplier
        block_duration: How long to block after exceeding limit (seconds)
    """

    def __init__(
        self,
        default_limit: int = 100,
        window_seconds: int = 60,
        burst_multiplier: float = 1.5,
        block_duration: int = 60,
    ):
        self.default_limit = default_limit
        self.window_seconds = window_seconds
        self.burst_multiplier = burst_multiplier
        self.block_duration = block_duration

        # Client state: IP -> RateLimitState
        self._state: Dict[str, RateLimitState] = defaultdict(RateLimitState)

        # Endpoint-specific limits
        self._endpoint_limits: Dict[str, int] = {}

        # Whitelisted IPs (bypass rate limiting)
        self._whitelist: set = {"127.0.0.1", "::1"}

        # Last cleanup time
        self._last_cleanup = time.time()
        self._cleanup_interval = 300  # 5 minutes

    def set_endpoint_limit(self, path: str, limit: int):
        """Set custom limit for specific endpoint."""
        self._endpoint_limits[path] = limit

    def add_to_whitelist(self, ip: str):
        """Add IP to whitelist (bypasses rate limiting)."""
        self._whitelist.add(ip)

    def remove_from_whitelist(self, ip: str):
        """Remove IP from whitelist."""
        self._whitelist.discard(ip)

    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP from request, handling proxies."""
        # Check X-Forwarded-For header (set by reverse proxy like Caddy)
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            # Take first IP (original client)
            return forwarded.split(",")[0].strip()

        # Check X-Real-IP header
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip.strip()

        # Fall back to direct connection IP
        if request.client:
            return request.client.host

        return "unknown"

    def _cleanup_old_entries(self):
        """Remove stale entries to prevent memory growth."""
        now = time.time()

        if now - self._last_cleanup < self._cleanup_interval:
            return

        self._last_cleanup = now
        cutoff = now - self.window_seconds * 2

        stale_keys = []
        for ip, state in self._state.items():
            # Remove old requests
            state.requests = [t for t in state.requests if t > cutoff]

            # Mark for removal if empty and not blocked
            if not state.requests and state.blocked_until < now:
                stale_keys.append(ip)

        for key in stale_keys:
            del self._state[key]

        if stale_keys:
            logger.debug(
                f"Rate limiter cleanup: removed {len(stale_keys)} stale entries"
            )

    def check_rate_limit(
        self,
        request: Request,
        limit: Optional[int] = None,
    ) -> tuple[bool, dict]:
        """
        Check if request is within rate limit.

        Returns:
            (allowed: bool, info: dict with remaining, reset_time, etc.)
        """
        client_ip = self._get_client_ip(request)

        # Whitelist bypass
        if client_ip in self._whitelist:
            return True, {"remaining": -1, "whitelisted": True}

        # Get limit for this endpoint
        path = request.url.path
        effective_limit = limit or self._endpoint_limits.get(path, self.default_limit)
        burst_limit = int(effective_limit * self.burst_multiplier)

        now = time.time()
        state = self._state[client_ip]

        # Check if client is blocked
        if state.blocked_until > now:
            retry_after = int(state.blocked_until - now)
            return False, {
                "blocked": True,
                "retry_after": retry_after,
                "reason": "Too many requests",
            }

        # Periodic cleanup
        self._cleanup_old_entries()

        # Remove requests outside window
        window_start = now - self.window_seconds
        state.requests = [t for t in state.requests if t > window_start]

        # Count requests in window
        request_count = len(state.requests)

        # Check burst limit
        if request_count >= burst_limit:
            # Block client temporarily
            state.blocked_until = now + self.block_duration
            logger.warning(
                f"Rate limit exceeded for {client_ip}: {request_count} requests, "
                f"blocked for {self.block_duration}s"
            )
            return False, {
                "blocked": True,
                "retry_after": self.block_duration,
                "reason": "Burst limit exceeded",
            }

        # Check normal limit (soft limit - just warn)
        if request_count >= effective_limit:
            remaining = burst_limit - request_count
            logger.info(
                f"Rate limit warning for {client_ip}: {request_count}/{effective_limit}"
            )
        else:
            remaining = effective_limit - request_count

        # Record this request
        state.requests.append(now)

        # Calculate reset time
        if state.requests:
            oldest = min(state.requests)
            reset_time = int(oldest + self.window_seconds - now)
        else:
            reset_time = self.window_seconds

        return True, {
            "remaining": remaining,
            "limit": effective_limit,
            "reset": reset_time,
        }

    def get_stats(self) -> dict:
        """Get rate limiter statistics."""
        now = time.time()
        active_clients = sum(
            1
            for state in self._state.values()
            if state.requests or state.blocked_until > now
        )
        blocked_clients = sum(
            1 for state in self._state.values() if state.blocked_until > now
        )

        return {
            "active_clients": active_clients,
            "blocked_clients": blocked_clients,
            "total_tracked": len(self._state),
            "whitelist_size": len(self._whitelist),
            "default_limit": self.default_limit,
            "window_seconds": self.window_seconds,
        }


# Global rate limiter instance
_rate_limiter: Optional[RateLimiter] = None


def get_rate_limiter() -> RateLimiter:
    """Get or create the global rate limiter instance."""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimiter()
    return _rate_limiter


def rate_limit_dependency(
    limit: Optional[int] = None,
    window: Optional[int] = None,
):
    """
    FastAPI dependency for rate limiting specific endpoints.

    Usage:
        @app.get("/api/expensive")
        async def expensive(
            _: None = Depends(rate_limit_dependency(limit=10, window=60))
        ):
            ...
    """

    async def dependency(request: Request):
        limiter = get_rate_limiter()

        # Override window if specified
        if window is not None:
            original_window = limiter.window_seconds
            limiter.window_seconds = window

        allowed, info = limiter.check_rate_limit(request, limit=limit)

        # Restore original window
        if window is not None:
            limiter.window_seconds = original_window

        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "error": "Rate limit exceeded",
                    "retry_after": info.get("retry_after", 60),
                    "message": info.get("reason", "Too many requests"),
                },
                headers={"Retry-After": str(info.get("retry_after", 60))},
            )

        return None

    return dependency


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Global rate limiting middleware.

    Applies rate limiting to all requests, with configurable exclusions.
    """

    def __init__(
        self,
        app,
        default_limit: int = 1000,
        window_seconds: int = 60,
        exclude_paths: Optional[list] = None,
    ):
        super().__init__(app)
        self.limiter = get_rate_limiter()
        self.limiter.default_limit = default_limit
        self.limiter.window_seconds = window_seconds

        # Paths to exclude from rate limiting
        self.exclude_paths = set(exclude_paths or [])
        self.exclude_paths.add("/api/system/health")  # Always allow health checks
        self.exclude_paths.add("/metrics")  # Always allow metrics

    async def dispatch(self, request: Request, call_next):
        # Skip rate limiting for excluded paths
        path = request.url.path
        if path in self.exclude_paths:
            return await call_next(request)

        # Skip for static files
        if path.startswith("/static/") or path.startswith("/assets/"):
            return await call_next(request)

        # Check rate limit
        allowed, info = self.limiter.check_rate_limit(request)

        if not allowed:
            return JSONResponse(
                status_code=429,
                content={
                    "error": "Rate limit exceeded",
                    "retry_after": info.get("retry_after", 60),
                    "message": info.get("reason", "Too many requests"),
                },
                headers={
                    "Retry-After": str(info.get("retry_after", 60)),
                    "X-RateLimit-Limit": str(self.limiter.default_limit),
                    "X-RateLimit-Remaining": "0",
                },
            )

        # Process request
        response = await call_next(request)

        # Add rate limit headers to response
        if "remaining" in info and info["remaining"] >= 0:
            response.headers["X-RateLimit-Limit"] = str(
                info.get("limit", self.limiter.default_limit)
            )
            response.headers["X-RateLimit-Remaining"] = str(info["remaining"])
            response.headers["X-RateLimit-Reset"] = str(
                info.get("reset", self.limiter.window_seconds)
            )

        return response

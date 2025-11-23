"""
Rate Limiting Middleware

FastAPI middleware for automatic rate limiting on all endpoints.
"""

from __future__ import annotations

import logging
from typing import Callable, Optional

from fastapi import Request, Response, status
from starlette.middleware.base import BaseHTTPMiddleware

from backend.core.rate_limiting.limiter import AdvancedRateLimiter, RateLimitTier

logger = logging.getLogger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware for FastAPI.
    
    Automatically applies rate limits to all requests based on:
    - User ID (from request.state.user)
    - Endpoint path
    - Client IP address
    - User's tier (free, premium, etc.)
    
    Returns 429 Too Many Requests with Retry-After header when limit exceeded.
    """
    
    # Paths exempt from rate limiting
    EXEMPT_PATHS = {
        "/",
        "/healthz",
        "/ready",
        "/health",
        "/docs",
        "/redoc",
        "/openapi.json",
    }
    
    def __init__(self, app, limiter: AdvancedRateLimiter):
        super().__init__(app)
        self.limiter = limiter
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process each request through rate limiter"""
        
        # Skip rate limiting for exempt paths
        if request.url.path in self.EXEMPT_PATHS:
            return await call_next(request)
        
        # Extract user info
        user = getattr(request.state, "user", None)
        user_id = str(user.id) if user else None
        tier = self._get_user_tier(user)
        
        # Extract IP address
        ip_address = self._get_client_ip(request)
        
        # Extract endpoint path
        endpoint = request.url.path
        
        # Check rate limit
        result = await self.limiter.check_limit(
            user_id=user_id,
            endpoint=endpoint,
            ip_address=ip_address,
            tier=tier,
        )
        
        if not result.allowed:
            logger.warning(
                f"Rate limit exceeded for user={user_id} ip={ip_address} "
                f"endpoint={endpoint} limit_type={result.limit_type}"
            )
            
            # Build response headers
            headers = {
                "X-RateLimit-Limit": str(result.limit),
                "X-RateLimit-Remaining": str(result.remaining),
                "X-RateLimit-Reset": str(result.reset_timestamp),
            }
            
            if result.retry_after:
                headers["Retry-After"] = str(result.retry_after)
            
            return Response(
                content='{"detail":"Rate limit exceeded","limit_type":"' + (result.limit_type or "unknown") + '"}',
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                headers=headers,
                media_type="application/json",
            )
        
        # Add rate limit headers to response
        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(result.limit)
        response.headers["X-RateLimit-Remaining"] = str(result.remaining)
        response.headers["X-RateLimit-Reset"] = str(result.reset_timestamp)
        
        return response
    
    def _get_user_tier(self, user) -> RateLimitTier:
        """
        Determine user's rate limit tier.
        
        Maps user.user_type to RateLimitTier.
        """
        if not user:
            return RateLimitTier.FREE
        
        user_type = getattr(user, "user_type", None)
        
        # Map user types to tiers
        tier_mapping = {
            "SUPER_ADMIN": RateLimitTier.ADMIN,
            "INTERNAL": RateLimitTier.INTERNAL,
            "EXTERNAL": RateLimitTier.BASIC,  # Default for external users
        }
        
        tier = tier_mapping.get(user_type, RateLimitTier.FREE)
        
        # Check if user has premium subscription (if you have that field)
        if hasattr(user, "subscription_tier"):
            tier_str = user.subscription_tier
            try:
                tier = RateLimitTier(tier_str)
            except ValueError:
                pass
        
        return tier
    
    def _get_client_ip(self, request: Request) -> str:
        """
        Extract client IP address from request.
        
        Checks X-Forwarded-For header (for proxies/load balancers)
        then falls back to client.host.
        """
        # Check X-Forwarded-For (can be comma-separated list)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            # Take first IP (original client)
            return forwarded_for.split(",")[0].strip()
        
        # Check X-Real-IP
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        # Fallback to direct client IP
        if request.client:
            return request.client.host
        
        return "unknown"

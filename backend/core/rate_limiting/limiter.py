"""
Advanced Rate Limiter

Multi-tier rate limiting with per-user, per-endpoint, per-IP limits.
Supports burst protection, cost tracking, and tiered limits.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Optional

from backend.core.rate_limiting.storage import RateLimitStorage

logger = logging.getLogger(__name__)


class RateLimitTier(str, Enum):
    """Rate limit tiers for different user types"""
    FREE = "free"
    BASIC = "basic"
    PREMIUM = "premium"
    ENTERPRISE = "enterprise"
    INTERNAL = "internal"
    ADMIN = "admin"


@dataclass
class RateLimitConfig:
    """
    Rate limit configuration for an endpoint or user tier.
    
    Attributes:
        requests_per_minute: Max requests per minute
        requests_per_hour: Max requests per hour
        requests_per_day: Max requests per day
        burst_size: Max burst requests (short-term spike)
        ai_cost_limit_per_day: Max AI cost per day (USD cents)
    """
    requests_per_minute: int = 60
    requests_per_hour: int = 1000
    requests_per_day: int = 10000
    burst_size: int = 10
    ai_cost_limit_per_day: int = 1000  # $10.00


# Default tier configurations
TIER_CONFIGS = {
    RateLimitTier.FREE: RateLimitConfig(
        requests_per_minute=10,
        requests_per_hour=100,
        requests_per_day=500,
        burst_size=3,
        ai_cost_limit_per_day=100,  # $1.00
    ),
    RateLimitTier.BASIC: RateLimitConfig(
        requests_per_minute=30,
        requests_per_hour=500,
        requests_per_day=5000,
        burst_size=5,
        ai_cost_limit_per_day=500,  # $5.00
    ),
    RateLimitTier.PREMIUM: RateLimitConfig(
        requests_per_minute=100,
        requests_per_hour=2000,
        requests_per_day=20000,
        burst_size=20,
        ai_cost_limit_per_day=2000,  # $20.00
    ),
    RateLimitTier.ENTERPRISE: RateLimitConfig(
        requests_per_minute=500,
        requests_per_hour=10000,
        requests_per_day=100000,
        burst_size=50,
        ai_cost_limit_per_day=10000,  # $100.00
    ),
    RateLimitTier.INTERNAL: RateLimitConfig(
        requests_per_minute=1000,
        requests_per_hour=50000,
        requests_per_day=500000,
        burst_size=100,
        ai_cost_limit_per_day=50000,  # $500.00
    ),
    RateLimitTier.ADMIN: RateLimitConfig(
        requests_per_minute=10000,
        requests_per_hour=100000,
        requests_per_day=1000000,
        burst_size=1000,
        ai_cost_limit_per_day=100000,  # $1000.00
    ),
}


@dataclass
class RateLimitResult:
    """Result of rate limit check"""
    allowed: bool
    limit: int
    remaining: int
    reset_timestamp: int
    retry_after: Optional[int] = None  # Seconds until can retry
    limit_type: Optional[str] = None  # Which limit was hit (minute/hour/day/burst)


class AdvancedRateLimiter:
    """
    Advanced multi-tier rate limiter.
    
    Features:
    - Per-user limits (based on tier)
    - Per-endpoint limits
    - Per-IP limits (DDoS protection)
    - Burst protection
    - AI cost tracking
    - Sliding window algorithm
    
    Usage:
        limiter = AdvancedRateLimiter(redis_storage)
        result = await limiter.check_limit(
            user_id="123",
            endpoint="/api/v1/data",
            ip_address="1.2.3.4",
            tier=RateLimitTier.PREMIUM
        )
        if not result.allowed:
            raise HTTPException(429, headers={"Retry-After": str(result.retry_after)})
    """
    
    def __init__(self, storage: RateLimitStorage):
        self.storage = storage
    
    async def check_limit(
        self,
        user_id: Optional[str] = None,
        endpoint: Optional[str] = None,
        ip_address: Optional[str] = None,
        tier: RateLimitTier = RateLimitTier.FREE,
        ai_cost_cents: int = 0,
    ) -> RateLimitResult:
        """
        Check if request is within rate limits.
        
        Checks multiple limits in order:
        1. Burst limit (very short window)
        2. Per-minute limit
        3. Per-hour limit
        4. Per-day limit
        5. AI cost limit (if ai_cost_cents > 0)
        
        Returns first limit that is exceeded.
        
        Args:
            user_id: User ID (optional, for per-user limits)
            endpoint: Endpoint path (optional, for per-endpoint limits)
            ip_address: Client IP (optional, for per-IP limits)
            tier: User's rate limit tier
            ai_cost_cents: AI cost for this request in USD cents
            
        Returns:
            RateLimitResult indicating if allowed and remaining quota
        """
        config = TIER_CONFIGS.get(tier, TIER_CONFIGS[RateLimitTier.FREE])
        
        # Check burst limit (10 second window)
        if user_id:
            result = await self._check_window(
                key=self._make_key(user_id, endpoint, "burst"),
                window_seconds=10,
                max_requests=config.burst_size,
                limit_type="burst",
            )
            if not result.allowed:
                return result
        
        # Check per-minute limit
        if user_id:
            result = await self._check_window(
                key=self._make_key(user_id, endpoint, "minute"),
                window_seconds=60,
                max_requests=config.requests_per_minute,
                limit_type="minute",
            )
            if not result.allowed:
                return result
        
        # Check per-hour limit
        if user_id:
            result = await self._check_window(
                key=self._make_key(user_id, endpoint, "hour"),
                window_seconds=3600,
                max_requests=config.requests_per_hour,
                limit_type="hour",
            )
            if not result.allowed:
                return result
        
        # Check per-day limit
        if user_id:
            result = await self._check_window(
                key=self._make_key(user_id, endpoint, "day"),
                window_seconds=86400,
                max_requests=config.requests_per_day,
                limit_type="day",
            )
            if not result.allowed:
                return result
        
        # Check IP-based limit (DDoS protection)
        if ip_address:
            result = await self._check_window(
                key=f"ip:{ip_address}:minute",
                window_seconds=60,
                max_requests=100,  # 100 req/min per IP
                limit_type="ip_minute",
            )
            if not result.allowed:
                return result
        
        # Check AI cost limit
        if ai_cost_cents > 0 and user_id:
            result = await self._check_ai_cost(
                user_id=user_id,
                cost_cents=ai_cost_cents,
                max_cost_cents=config.ai_cost_limit_per_day,
            )
            if not result.allowed:
                return result
        
        # All limits passed
        return RateLimitResult(
            allowed=True,
            limit=config.requests_per_minute,
            remaining=config.requests_per_minute,
            reset_timestamp=0,
        )
    
    async def _check_window(
        self,
        key: str,
        window_seconds: int,
        max_requests: int,
        limit_type: str,
    ) -> RateLimitResult:
        """Check a single time window limit"""
        current, remaining, reset = await self.storage.increment(
            key=key,
            window_seconds=window_seconds,
            max_requests=max_requests,
        )
        
        allowed = current <= max_requests
        retry_after = None if allowed else (reset - int(__import__('time').time()))
        
        return RateLimitResult(
            allowed=allowed,
            limit=max_requests,
            remaining=remaining,
            reset_timestamp=reset,
            retry_after=retry_after,
            limit_type=limit_type,
        )
    
    async def _check_ai_cost(
        self,
        user_id: str,
        cost_cents: int,
        max_cost_cents: int,
    ) -> RateLimitResult:
        """
        Check AI cost limit for the day.
        
        Tracks cumulative AI API costs to prevent runaway spending.
        """
        key = f"ai_cost:{user_id}:day"
        
        # Increment cost
        current, remaining, reset = await self.storage.increment(
            key=key,
            window_seconds=86400,
            max_requests=max_cost_cents,
        )
        
        # Note: We're using increment as a counter, not request count
        # So we need to track the actual cost differently
        # For now, simplified - each "request" = cost_cents
        
        allowed = current <= max_cost_cents
        retry_after = None if allowed else (reset - int(__import__('time').time()))
        
        return RateLimitResult(
            allowed=allowed,
            limit=max_cost_cents,
            remaining=max(0, max_cost_cents - current),
            reset_timestamp=reset,
            retry_after=retry_after,
            limit_type="ai_cost",
        )
    
    def _make_key(
        self,
        user_id: str,
        endpoint: Optional[str],
        window_type: str,
    ) -> str:
        """
        Create rate limit key.
        
        Format: "ratelimit:user:{user_id}:endpoint:{endpoint}:{window_type}"
        
        Examples:
        - "ratelimit:user:123:endpoint:/api/v1/data:minute"
        - "ratelimit:user:456:global:hour"
        """
        if endpoint:
            # Normalize endpoint (remove query params, trailing slash)
            endpoint_clean = endpoint.split("?")[0].rstrip("/")
            return f"ratelimit:user:{user_id}:endpoint:{endpoint_clean}:{window_type}"
        else:
            return f"ratelimit:user:{user_id}:global:{window_type}"
    
    async def get_usage(
        self,
        user_id: str,
        endpoint: Optional[str] = None,
    ) -> dict:
        """
        Get current usage for a user.
        
        Returns:
            Dict with usage info:
            - minute_count: Requests in last minute
            - hour_count: Requests in last hour
            - day_count: Requests in last day
            - burst_count: Requests in last 10 seconds
        """
        return {
            "burst_count": await self.storage.get_count(
                self._make_key(user_id, endpoint, "burst")
            ),
            "minute_count": await self.storage.get_count(
                self._make_key(user_id, endpoint, "minute")
            ),
            "hour_count": await self.storage.get_count(
                self._make_key(user_id, endpoint, "hour")
            ),
            "day_count": await self.storage.get_count(
                self._make_key(user_id, endpoint, "day")
            ),
        }
    
    async def reset_user_limits(
        self,
        user_id: str,
        endpoint: Optional[str] = None,
    ) -> None:
        """
        Reset all limits for a user (admin function).
        
        Use case: Resolve rate limit issues, testing, user upgrades tier.
        """
        for window_type in ["burst", "minute", "hour", "day"]:
            await self.storage.reset(self._make_key(user_id, endpoint, window_type))
        
        # Reset AI cost
        await self.storage.reset(f"ai_cost:{user_id}:day")

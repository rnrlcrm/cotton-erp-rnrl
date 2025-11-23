"""
Rate Limit Storage

Abstract storage interface and Redis implementation for rate limiting.
Uses sliding window algorithm for accurate rate limiting.
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from typing import Optional

from redis.asyncio import Redis


class RateLimitStorage(ABC):
    """Abstract storage interface for rate limiting"""
    
    @abstractmethod
    async def increment(
        self,
        key: str,
        window_seconds: int,
        max_requests: int,
    ) -> tuple[int, int, int]:
        """
        Increment request count for key within window.
        
        Args:
            key: Rate limit key (e.g., "user:123:endpoint:/api/v1/data")
            window_seconds: Time window in seconds
            max_requests: Maximum requests allowed in window
            
        Returns:
            Tuple of (current_count, remaining, reset_timestamp)
        """
        pass
    
    @abstractmethod
    async def get_count(self, key: str) -> int:
        """Get current request count for key"""
        pass
    
    @abstractmethod
    async def reset(self, key: str) -> None:
        """Reset counter for key"""
        pass


class RedisRateLimitStorage(RateLimitStorage):
    """
    Redis-based rate limit storage using sliding window algorithm.
    
    Uses sorted sets (ZSET) to track request timestamps within window.
    This provides accurate rate limiting without fixed windows.
    
    Algorithm:
    1. Remove timestamps older than window
    2. Count remaining timestamps
    3. Add current timestamp
    4. Check if count exceeds limit
    """
    
    def __init__(self, redis: Redis):
        self.redis = redis
    
    async def increment(
        self,
        key: str,
        window_seconds: int,
        max_requests: int,
    ) -> tuple[int, int, int]:
        """
        Increment using sliding window algorithm.
        
        Implementation:
        - Use Redis ZSET with timestamps as scores
        - Remove old entries outside window
        - Count entries in window
        - Add new entry
        - Calculate remaining and reset time
        """
        now = time.time()
        window_start = now - window_seconds
        
        pipe = self.redis.pipeline()
        
        # Remove old entries outside window
        pipe.zremrangebyscore(key, 0, window_start)
        
        # Count entries in current window
        pipe.zcard(key)
        
        # Add current request timestamp
        pipe.zadd(key, {str(now): now})
        
        # Set expiry on key (cleanup)
        pipe.expire(key, window_seconds * 2)
        
        results = await pipe.execute()
        current_count = results[1] + 1  # +1 for the request we just added
        
        remaining = max(0, max_requests - current_count)
        reset_timestamp = int(now + window_seconds)
        
        return current_count, remaining, reset_timestamp
    
    async def get_count(self, key: str) -> int:
        """Get current count by counting entries in sorted set"""
        now = time.time()
        # Count is number of entries in the set
        count = await self.redis.zcard(key)
        return count or 0
    
    async def reset(self, key: str) -> None:
        """Delete the sorted set to reset"""
        await self.redis.delete(key)
    
    async def increment_fixed_window(
        self,
        key: str,
        window_seconds: int,
        max_requests: int,
    ) -> tuple[int, int, int]:
        """
        Alternative: Fixed window implementation (simpler, less accurate).
        
        Uses simple counter with TTL. Faster but has edge case issues
        at window boundaries.
        """
        now = int(time.time())
        window_id = now // window_seconds
        window_key = f"{key}:{window_id}"
        
        pipe = self.redis.pipeline()
        pipe.incr(window_key)
        pipe.expire(window_key, window_seconds * 2)
        results = await pipe.execute()
        
        current_count = results[0]
        remaining = max(0, max_requests - current_count)
        reset_timestamp = (window_id + 1) * window_seconds
        
        return current_count, remaining, reset_timestamp

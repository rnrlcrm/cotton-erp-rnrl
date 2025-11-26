"""
Account Lockout Service

Prevents brute force attacks by locking accounts after failed login attempts.
Uses Redis for distributed rate limiting and lockout tracking.
"""
from __future__ import annotations

from typing import Optional
from datetime import datetime, timedelta, timezone
import redis.asyncio as redis


class AccountLockoutService:
    """
    Manages account lockout for failed login attempts.
    
    Features:
    - Lock account after 5 failed attempts
    - 15-minute lockout duration
    - Automatic unlock after timeout
    - Clear attempts on successful login
    """
    
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self.max_attempts = 5
        self.lockout_duration = 900  # 15 minutes in seconds
        
    async def record_failed_attempt(self, identifier: str) -> dict:
        """
        Record a failed login attempt.
        
        Args:
            identifier: Email or mobile number
            
        Returns:
            Dict with lockout status and remaining attempts
        """
        key = f"login_attempts:{identifier}"
        lockout_key = f"account_locked:{identifier}"
        
        # Check if already locked
        if await self.redis.exists(lockout_key):
            ttl = await self.redis.ttl(lockout_key)
            return {
                "locked": True,
                "remaining_attempts": 0,
                "lockout_expires_in": ttl,
                "message": f"Account locked. Try again in {ttl // 60} minutes."
            }
        
        # Increment attempts
        attempts = await self.redis.incr(key)
        
        # Set TTL on first attempt (reset window after 15 minutes)
        if attempts == 1:
            await self.redis.expire(key, self.lockout_duration)
        
        remaining = self.max_attempts - attempts
        
        # Lock account if max attempts reached
        if attempts >= self.max_attempts:
            await self.redis.setex(lockout_key, self.lockout_duration, "1")
            await self.redis.delete(key)  # Clear attempts counter
            return {
                "locked": True,
                "remaining_attempts": 0,
                "lockout_expires_in": self.lockout_duration,
                "message": f"Account locked due to too many failed attempts. Try again in 15 minutes."
            }
        
        return {
            "locked": False,
            "remaining_attempts": remaining,
            "lockout_expires_in": 0,
            "message": f"{remaining} attempts remaining before account lockout."
        }
    
    async def clear_failed_attempts(self, identifier: str) -> None:
        """
        Clear failed attempts after successful login.
        
        Args:
            identifier: Email or mobile number
        """
        key = f"login_attempts:{identifier}"
        await self.redis.delete(key)
    
    async def is_locked(self, identifier: str) -> tuple[bool, int]:
        """
        Check if account is locked.
        
        Args:
            identifier: Email or mobile number
            
        Returns:
            Tuple of (is_locked, seconds_until_unlock)
        """
        lockout_key = f"account_locked:{identifier}"
        
        if await self.redis.exists(lockout_key):
            ttl = await self.redis.ttl(lockout_key)
            return True, ttl
        
        return False, 0
    
    async def unlock_account(self, identifier: str) -> None:
        """
        Manually unlock an account (admin function).
        
        Args:
            identifier: Email or mobile number
        """
        key = f"login_attempts:{identifier}"
        lockout_key = f"account_locked:{identifier}"
        
        await self.redis.delete(key)
        await self.redis.delete(lockout_key)
    
    async def get_attempt_count(self, identifier: str) -> int:
        """
        Get current failed attempt count.
        
        Args:
            identifier: Email or mobile number
            
        Returns:
            Number of failed attempts
        """
        key = f"login_attempts:{identifier}"
        attempts = await self.redis.get(key)
        return int(attempts) if attempts else 0

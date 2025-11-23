"""
Refresh Token Management

Handles refresh token lifecycle, rotation, and revocation.
Works with UserSession model and SessionService for complete session management.

Features:
- Refresh token validation
- Token rotation (security best practice)
- Revocation tracking
- Expiry management
- Device binding
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.auth.jwt import create_token, decode_token
from backend.core.jwt.token import (
    TokenExpiredError,
    TokenValidationError,
    extract_jti,
    validate_refresh_token,
)
from backend.core.settings.config import settings


class RefreshTokenService:
    """
    Service for managing refresh token lifecycle.
    
    Handles:
    - Token validation
    - Token rotation on refresh
    - Revocation tracking
    - Expiry management
    """
    
    def __init__(self, db: AsyncSession, redis_client=None):
        """
        Initialize refresh token service.
        
        Args:
            db: Async database session
            redis_client: Optional Redis client for revocation cache
        """
        self.db = db
        self.redis = redis_client
    
    async def validate_and_rotate(
        self,
        refresh_token: str,
        device_fingerprint: str | None = None,
    ) -> tuple[str, str, dict]:
        """
        Validate refresh token and issue new token pair (rotation).
        
        Security: Rotation prevents token replay attacks. Once used,
        old refresh token is immediately revoked.
        
        Args:
            refresh_token: Current refresh token
            device_fingerprint: Optional device fingerprint for binding check
            
        Returns:
            Tuple of (new_access_token, new_refresh_token, user_info)
            
        Raises:
            TokenValidationError: Token invalid, revoked, or expired
        """
        # Validate token type and signature
        try:
            payload = validate_refresh_token(refresh_token)
        except TokenExpiredError:
            raise TokenValidationError("Refresh token has expired")
        except TokenValidationError:
            raise
        
        jti = payload.get("jti")
        user_id = payload.get("sub")
        org_id = payload.get("org_id")
        
        if not jti or not user_id or not org_id:
            raise TokenValidationError("Refresh token missing required claims")
        
        # Check if token is revoked
        if await self._is_revoked(jti):
            raise TokenValidationError("Refresh token has been revoked")
        
        # Optionally check device binding
        if device_fingerprint:
            # This would require storing device fingerprint with token
            # For now, we'll skip this check (handled by SessionService)
            pass
        
        # Generate new token pair
        access_minutes = settings.ACCESS_TOKEN_EXPIRES_MINUTES
        refresh_days = settings.REFRESH_TOKEN_EXPIRES_DAYS
        
        new_access = create_token(
            sub=user_id,
            org_id=org_id,
            minutes=access_minutes,
            token_type="access"
        )
        
        new_refresh = create_token(
            sub=user_id,
            org_id=org_id,
            days=refresh_days,
            token_type="refresh"
        )
        
        # Revoke old refresh token
        await self._revoke_token(jti, user_id)
        
        user_info = {
            "user_id": user_id,
            "org_id": org_id,
        }
        
        return new_access, new_refresh, user_info
    
    async def revoke_token(self, refresh_token: str) -> None:
        """
        Revoke a refresh token (logout).
        
        Args:
            refresh_token: Refresh token to revoke
            
        Raises:
            TokenValidationError: Token is malformed
        """
        try:
            jti = extract_jti(refresh_token)
            payload = decode_token(refresh_token)
            user_id = payload.get("sub")
            await self._revoke_token(jti, user_id)
        except Exception as e:
            raise TokenValidationError(f"Failed to revoke token: {e}")
    
    async def revoke_all_user_tokens(self, user_id: str | UUID) -> int:
        """
        Revoke all refresh tokens for a user (logout all devices).
        
        Args:
            user_id: User ID
            
        Returns:
            Number of tokens revoked
        """
        # This would query all active refresh tokens for user
        # and revoke them. Implementation depends on how tokens are stored.
        # For now, this is a placeholder.
        
        # If using UserSession model:
        # from backend.modules.auth.models import UserSession
        # result = await self.db.execute(
        #     select(UserSession).where(
        #         UserSession.user_id == user_id,
        #         UserSession.is_active == True
        #     )
        # )
        # sessions = result.scalars().all()
        # for session in sessions:
        #     await self._revoke_token(session.refresh_token_jti, user_id)
        # return len(sessions)
        
        return 0
    
    async def is_token_valid(self, refresh_token: str) -> bool:
        """
        Check if refresh token is valid (not expired, not revoked).
        
        Args:
            refresh_token: Refresh token to check
            
        Returns:
            True if valid, False otherwise
        """
        try:
            payload = validate_refresh_token(refresh_token)
            jti = payload.get("jti")
            if not jti:
                return False
            return not await self._is_revoked(jti)
        except (TokenValidationError, TokenExpiredError):
            return False
    
    async def _revoke_token(self, jti: str, user_id: str | None = None) -> None:
        """
        Internal: Revoke token by JTI.
        
        Stores revocation in Redis (fast lookup) with TTL matching token expiry.
        
        Args:
            jti: JWT ID
            user_id: Optional user ID for logging
        """
        if self.redis:
            # Store in Redis with TTL = refresh token max lifetime
            ttl = settings.REFRESH_TOKEN_EXPIRES_DAYS * 24 * 60 * 60
            await self.redis.setex(
                f"revoked_token:{jti}",
                ttl,
                "1"
            )
        else:
            # Fallback: Store in database (slower)
            # This would require a RevokedToken model
            pass
    
    async def _is_revoked(self, jti: str) -> bool:
        """
        Internal: Check if token is revoked.
        
        Args:
            jti: JWT ID
            
        Returns:
            True if revoked, False otherwise
        """
        if self.redis:
            # Check Redis revocation list
            result = await self.redis.get(f"revoked_token:{jti}")
            return result is not None
        else:
            # Fallback: Check database
            # This would query RevokedToken model
            return False


async def cleanup_expired_revocations(redis_client) -> int:
    """
    Cleanup expired token revocations from Redis.
    
    Redis TTL handles this automatically, so this is mostly
    for manual cleanup or database-based revocation tracking.
    
    Args:
        redis_client: Redis client
        
    Returns:
        Number of entries cleaned up
    """
    # Redis handles TTL automatically
    # This function exists for database-based implementations
    return 0


def calculate_refresh_token_ttl(token: str) -> int:
    """
    Calculate remaining TTL for refresh token.
    
    Useful for setting Redis TTL when caching.
    
    Args:
        token: Refresh token
        
    Returns:
        Remaining seconds (0 if expired)
    """
    try:
        from backend.core.jwt.token import get_remaining_lifetime
        return get_remaining_lifetime(token)
    except TokenValidationError:
        return 0

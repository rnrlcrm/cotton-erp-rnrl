"""
Session Management Service

Handles user sessions across multiple devices with refresh token rotation.

Features:
- Multi-device session tracking
- Refresh token rotation (security)
- Session persistence (Redis + PostgreSQL)
- Remote logout (revoke specific device)
- Session expiry (30 days inactive)
- Suspicious login detection
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as redis

from backend.core.jwt.device import DeviceFingerprint
from backend.core.auth.jwt import create_token, decode_token
from backend.core.settings.config import settings


# Redis client for session caching
redis_client = redis.Redis(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    decode_responses=True,
    max_connections=50
)


class SessionService:
    """
    Manage user sessions across devices.
    
    Session Flow:
    1. User logs in → Create session with refresh token
    2. Access token expires (15 min) → Use refresh token to get new access token
    3. Refresh token used → Rotate (issue new refresh token)
    4. Session inactive 30 days → Expire session
    5. User logs out → Revoke session
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.redis = redis_client
        
        # Token expiry times
        self.ACCESS_TOKEN_EXPIRES = timedelta(minutes=15)
        self.REFRESH_TOKEN_EXPIRES = timedelta(days=30)
        self.SESSION_INACTIVE_EXPIRES = timedelta(days=30)
    
    async def create_session(
        self,
        user_id: UUID,
        user_agent: str,
        ip_address: str,
        organization_id: Optional[UUID] = None
    ) -> dict:
        """
        Create new session (login).
        
        Returns:
            {
                'session_id': UUID,
                'access_token': str,
                'refresh_token': str,
                'access_token_expires_at': datetime,
                'refresh_token_expires_at': datetime,
                'device_info': {...}
            }
        """
        # Import here to avoid circular dependency
        from backend.modules.auth.models import UserSession
        
        # Generate device fingerprint
        device_fingerprint = DeviceFingerprint.generate(user_agent, ip_address)
        device_info = DeviceFingerprint.parse_device_info(user_agent)
        
        # Check for suspicious login
        existing_sessions = await self.get_user_sessions(user_id)
        known_devices = [s.device_fingerprint for s in existing_sessions]
        known_ips = [s.ip_address for s in existing_sessions]
        
        is_suspicious, reason = DeviceFingerprint.is_suspicious_login(
            user_id=str(user_id),
            device_fingerprint=device_fingerprint,
            ip_address=ip_address,
            known_devices=[{'device_fingerprint': d} for d in known_devices],
            known_ips=known_ips
        )
        
        # Generate tokens
        access_token_jti = str(uuid4())
        refresh_token_jti = str(uuid4())
        
        now = datetime.now(timezone.utc)
        access_expires_at = now + self.ACCESS_TOKEN_EXPIRES
        refresh_expires_at = now + self.REFRESH_TOKEN_EXPIRES
        
        # Create access token
        access_token = create_token(
            sub=str(user_id),
            org_id=str(organization_id) if organization_id else "default",
            minutes=int(self.ACCESS_TOKEN_EXPIRES.total_seconds() / 60),
            token_type="access"
        )
        
        # Create refresh token
        refresh_token = create_token(
            sub=str(user_id),
            org_id=str(organization_id) if organization_id else "default",
            days=int(self.REFRESH_TOKEN_EXPIRES.total_seconds() / 86400),
            token_type="refresh"
        )
        
        # Create session record
        session = UserSession(
            id=uuid4(),
            user_id=user_id,
            device_fingerprint=device_fingerprint,
            device_name=device_info['device_name'],
            device_type=device_info['device_type'],
            os_name=device_info['os_name'],
            os_version=device_info['os_version'],
            browser_name=device_info['browser_name'],
            browser_version=device_info['browser_version'],
            ip_address=ip_address,
            user_agent=user_agent,
            refresh_token_jti=refresh_token_jti,
            access_token_jti=access_token_jti,
            access_token_expires_at=access_expires_at,
            refresh_token_expires_at=refresh_expires_at,
            last_active_at=now,
            is_active=True,
            is_suspicious=is_suspicious,
            suspicious_reason=reason if is_suspicious else None,
            total_logins=1,
            created_at=now
        )
        
        self.db.add(session)
        await self.db.commit()
        await self.db.refresh(session)
        
        # Cache session in Redis (for fast lookup)
        await self._cache_session(session)
        
        # Cache tokens in Redis (for revocation checking)
        await self._cache_token(access_token_jti, str(user_id), int(self.ACCESS_TOKEN_EXPIRES.total_seconds()))
        await self._cache_token(refresh_token_jti, str(user_id), int(self.REFRESH_TOKEN_EXPIRES.total_seconds()))
        
        # Send alert if suspicious
        if is_suspicious:
            # TODO: Send email/SMS alert to user
            pass
        
        return {
            'session_id': session.id,
            'access_token': access_token,
            'refresh_token': refresh_token,
            'access_token_expires_at': access_expires_at,
            'refresh_token_expires_at': refresh_expires_at,
            'device_info': device_info,
            'is_suspicious': is_suspicious,
            'suspicious_reason': reason if is_suspicious else None
        }
    
    async def refresh_session(
        self,
        refresh_token: str,
        user_agent: str,
        ip_address: str
    ) -> dict:
        """
        Refresh access token using refresh token.
        
        Security: Token rotation - issue new refresh token on each refresh.
        
        Returns:
            {
                'access_token': str,
                'refresh_token': str,  # New refresh token
                'access_token_expires_at': datetime,
                'refresh_token_expires_at': datetime
            }
        """
        # Decode refresh token
        try:
            payload = decode_token(refresh_token)
        except Exception:
            raise ValueError("Invalid refresh token")
        
        if payload.get('type') != 'refresh':
            raise ValueError("Not a refresh token")
        
        user_id = UUID(payload['sub'])
        old_refresh_jti = payload['jti']
        
        # Check if token is revoked
        is_revoked = await self._is_token_revoked(old_refresh_jti)
        if is_revoked:
            raise ValueError("Refresh token has been revoked")
        
        # Find session by refresh token JTI
        from backend.modules.auth.models import UserSession
        
        query = select(UserSession).where(
            and_(
                UserSession.refresh_token_jti == old_refresh_jti,
                UserSession.is_active == True
            )
        )
        result = await self.db.execute(query)
        session = result.scalar_one_or_none()
        
        if not session:
            raise ValueError("Session not found or expired")
        
        # Check if session expired
        if session.refresh_token_expires_at < datetime.now(timezone.utc):
            session.is_active = False
            await self.db.commit()
            raise ValueError("Session expired - please login again")
        
        # Generate new tokens (token rotation)
        new_access_jti = str(uuid4())
        new_refresh_jti = str(uuid4())
        
        now = datetime.now(timezone.utc)
        access_expires_at = now + self.ACCESS_TOKEN_EXPIRES
        refresh_expires_at = now + self.REFRESH_TOKEN_EXPIRES
        
        # Create new access token
        access_token = create_token(
            sub=str(user_id),
            org_id=payload.get('org_id', 'default'),
            minutes=int(self.ACCESS_TOKEN_EXPIRES.total_seconds() / 60),
            token_type="access"
        )
        
        # Create new refresh token
        new_refresh_token = create_token(
            sub=str(user_id),
            org_id=payload.get('org_id', 'default'),
            days=int(self.REFRESH_TOKEN_EXPIRES.total_seconds() / 86400),
            token_type="refresh"
        )
        
        # Update session with new tokens
        session.access_token_jti = new_access_jti
        session.refresh_token_jti = new_refresh_jti
        session.access_token_expires_at = access_expires_at
        session.refresh_token_expires_at = refresh_expires_at
        session.last_active_at = now
        session.ip_address = ip_address  # Update to latest IP
        session.total_logins += 1
        
        await self.db.commit()
        
        # Revoke old tokens
        await self._revoke_token(old_refresh_jti)
        
        # Cache new tokens
        await self._cache_token(new_access_jti, str(user_id), int(self.ACCESS_TOKEN_EXPIRES.total_seconds()))
        await self._cache_token(new_refresh_jti, str(user_id), int(self.REFRESH_TOKEN_EXPIRES.total_seconds()))
        
        # Update cached session
        await self._cache_session(session)
        
        return {
            'access_token': access_token,
            'refresh_token': new_refresh_token,
            'access_token_expires_at': access_expires_at,
            'refresh_token_expires_at': refresh_expires_at
        }
    
    async def get_user_sessions(self, user_id: UUID) -> list:
        """
        Get all active sessions for user.
        
        Returns list of active sessions with device info.
        """
        from backend.modules.auth.models import UserSession
        
        query = select(UserSession).where(
            and_(
                UserSession.user_id == user_id,
                UserSession.is_active == True
            )
        ).order_by(UserSession.last_active_at.desc())
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def revoke_session(self, session_id: UUID, user_id: UUID):
        """
        Revoke specific session (remote logout).
        """
        from backend.modules.auth.models import UserSession
        
        query = select(UserSession).where(
            and_(
                UserSession.id == session_id,
                UserSession.user_id == user_id  # Ensure user owns session
            )
        )
        result = await self.db.execute(query)
        session = result.scalar_one_or_none()
        
        if not session:
            raise ValueError("Session not found")
        
        # Mark session as inactive
        session.is_active = False
        await self.db.commit()
        
        # Revoke tokens
        await self._revoke_token(session.access_token_jti)
        await self._revoke_token(session.refresh_token_jti)
        
        # Remove from cache
        await self.redis.delete(f"session:{session.id}")
    
    async def revoke_all_sessions(self, user_id: UUID, except_session_id: Optional[UUID] = None):
        """
        Revoke all sessions (logout all devices).
        
        Args:
            user_id: User ID
            except_session_id: Optional session to keep active (current device)
        """
        from backend.modules.auth.models import UserSession
        
        query = select(UserSession).where(
            and_(
                UserSession.user_id == user_id,
                UserSession.is_active == True
            )
        )
        
        if except_session_id:
            query = query.where(UserSession.id != except_session_id)
        
        result = await self.db.execute(query)
        sessions = result.scalars().all()
        
        for session in sessions:
            session.is_active = False
            await self._revoke_token(session.access_token_jti)
            await self._revoke_token(session.refresh_token_jti)
            await self.redis.delete(f"session:{session.id}")
        
        await self.db.commit()
    
    async def cleanup_expired_sessions(self):
        """
        Background task: Remove expired sessions.
        Run daily via Cloud Tasks/Celery.
        """
        from backend.modules.auth.models import UserSession
        
        now = datetime.now(timezone.utc)
        
        # Find expired sessions
        query = select(UserSession).where(
            and_(
                UserSession.is_active == True,
                UserSession.refresh_token_expires_at < now
            )
        )
        
        result = await self.db.execute(query)
        expired_sessions = result.scalars().all()
        
        for session in expired_sessions:
            session.is_active = False
            await self._revoke_token(session.access_token_jti)
            await self._revoke_token(session.refresh_token_jti)
        
        await self.db.commit()
        
        return len(expired_sessions)
    
    # Private helper methods
    
    async def _cache_session(self, session):
        """Cache session in Redis for fast lookup"""
        session_data = {
            'id': str(session.id),
            'user_id': str(session.user_id),
            'device_name': session.device_name,
            'is_active': session.is_active,
        }
        await self.redis.setex(
            f"session:{session.id}",
            int(self.SESSION_INACTIVE_EXPIRES.total_seconds()),
            str(session_data)
        )
    
    async def _cache_token(self, jti: str, user_id: str, ttl: int):
        """Cache token JTI for revocation checking"""
        await self.redis.setex(f"token:{jti}", ttl, user_id)
    
    async def _revoke_token(self, jti: str):
        """Revoke token by adding to blacklist"""
        await self.redis.setex(f"revoked:{jti}", 86400 * 30, "1")  # 30 days
    
    async def _is_token_revoked(self, jti: str) -> bool:
        """Check if token is revoked"""
        revoked = await self.redis.get(f"revoked:{jti}")
        return revoked is not None

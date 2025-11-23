"""
User Session Model

Tracks user sessions across multiple devices with security features.

Features:
- Multi-device session tracking
- Device fingerprinting
- Suspicious login detection
- Session expiry
- Last active tracking

Database Schema:
- user_sessions table
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.db.base import Base


class UserSession(Base):
    """
    User session across devices.
    
    Enables:
    - Cross-device continuity (phone → desktop)
    - Session management (see all devices)
    - Remote logout (revoke specific device)
    - Security monitoring (detect suspicious logins)
    
    GDPR Compliance:
    - Logs device info for security (GDPR Article 32)
    - Audit trail for access (GDPR Article 30)
    - Data retention (30 days inactive)
    """
    
    __tablename__ = "user_sessions"
    
    # Primary key
    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4
    )
    
    # User reference
    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        nullable=False,
        index=True,
        comment="User who owns this session"
    )
    
    # Device fingerprinting
    device_fingerprint: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
        comment="SHA256 hash of user-agent (for device identification)"
    )
    device_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Friendly device name (e.g., 'iPhone 13 (iOS 15.0)')"
    )
    device_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="mobile, desktop, tablet, bot"
    )
    os_name: Mapped[str] = mapped_column(
        String(100),
        nullable=True,
        comment="Operating system (iOS, Android, Windows, macOS)"
    )
    os_version: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        comment="OS version"
    )
    browser_name: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment="Browser name (Chrome, Safari, Firefox)"
    )
    browser_version: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        comment="Browser version"
    )
    ip_address: Mapped[str] = mapped_column(
        String(45),
        nullable=False,
        comment="IP address (IPv4 or IPv6)"
    )
    user_agent: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Full User-Agent header"
    )
    
    # Token tracking
    refresh_token_jti: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        unique=True,
        index=True,
        comment="JWT ID of current refresh token"
    )
    access_token_jti: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        comment="JWT ID of current access token"
    )
    access_token_expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        comment="Access token expiration"
    )
    refresh_token_expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
        comment="Refresh token expiration (session expiry)"
    )
    
    # Session activity
    last_active_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
        comment="Last API request from this session"
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        index=True,
        comment="Session is active (not logged out)"
    )
    
    # Security
    is_suspicious: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="Flagged as suspicious login"
    )
    suspicious_reason: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        comment="Why flagged as suspicious"
    )
    is_verified: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="Device verified via email/SMS"
    )
    
    # Statistics
    total_logins: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        comment="Total logins from this device"
    )
    failed_logins_last_24h: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Failed login attempts (security monitoring)"
    )
    
    # Audit
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        comment="Session created (first login)"
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Last updated"
    )
    
    def __repr__(self) -> str:
        return f"<UserSession {self.device_name} ({self.device_type})>"
    
    def to_dict(self) -> dict:
        """Convert to dict for API response"""
        return {
            'id': str(self.id),
            'device_name': self.device_name,
            'device_type': self.device_type,
            'os_name': self.os_name,
            'os_version': self.os_version,
            'browser_name': self.browser_name,
            'browser_version': self.browser_version,
            'ip_address': self.ip_address,
            'last_active_at': self.last_active_at.isoformat() if self.last_active_at else None,
            'is_active': self.is_active,
            'is_suspicious': self.is_suspicious,
            'is_verified': self.is_verified,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }

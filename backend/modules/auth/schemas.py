"""
Session API Schemas

Pydantic models for session management API requests/responses.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class RefreshTokenRequest(BaseModel):
    """Request to refresh access token"""
    refresh_token: str = Field(..., description="Refresh token from login")


class TokenResponse(BaseModel):
    """Token response (login or refresh)"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    access_token_expires_at: datetime
    refresh_token_expires_at: datetime
    device_info: Optional[dict] = None
    is_suspicious: bool = False
    suspicious_reason: Optional[str] = None


class SessionInfo(BaseModel):
    """User session information"""
    id: UUID
    device_name: str
    device_type: str
    os_name: Optional[str]
    os_version: Optional[str]
    browser_name: Optional[str]
    browser_version: Optional[str]
    ip_address: str
    last_active_at: datetime
    is_active: bool
    is_suspicious: bool
    is_verified: bool
    created_at: datetime
    is_current: bool = False  # Is this the current session?


class SessionListResponse(BaseModel):
    """List of active sessions"""
    sessions: list[SessionInfo]
    total: int


class LogoutResponse(BaseModel):
    """Logout response"""
    message: str
    sessions_revoked: int = 1

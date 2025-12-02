"""Shared authentication-related response models."""

from __future__ import annotations

from datetime import datetime
from typing import Optional, Dict, Any

from pydantic import BaseModel, Field


class TokenResponse(BaseModel):
    """Standardized token pair payload used across auth flows."""

    access_token: str
    refresh_token: str
    token_type: str = Field("bearer", description="OAuth token type")
    expires_in: Optional[int] = Field(
        None,
        description="Access token lifetime in seconds when precise expiry timestamps are unavailable.",
    )
    access_token_expires_at: Optional[datetime] = Field(
        None, description="Timestamp when the access token expires (UTC)."
    )
    refresh_token_expires_at: Optional[datetime] = Field(
        None, description="Timestamp when the refresh token expires (UTC)."
    )
    device_info: Optional[Dict[str, Any]] = Field(
        None, description="Optional device context captured during session establishment."
    )
    is_suspicious: Optional[bool] = Field(
        None, description="Flag indicating whether the login was classified as suspicious."
    )
    suspicious_reason: Optional[str] = Field(
        None, description="Human-readable reason when a login is marked suspicious."
    )


class OTPResponse(BaseModel):
    """Outcome of sending or verifying a one-time password."""

    success: bool
    message: str
    otp_sent_at: Optional[datetime] = Field(
        None, description="Timestamp when the OTP was issued (UTC)."
    )
    expires_in_seconds: int = Field(
        300,
        ge=0,
        description="Number of seconds the OTP remains valid (default 5 minutes).",
    )

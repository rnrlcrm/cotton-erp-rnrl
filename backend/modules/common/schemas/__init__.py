"""Shared Pydantic schemas reused across multiple modules."""

from .auth import TokenResponse, OTPResponse

__all__ = [
    "TokenResponse",
    "OTPResponse",
]

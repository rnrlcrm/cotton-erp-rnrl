"""
Enhanced JWT Token Utilities

Provides advanced token creation, validation, and management utilities.
Complements core/auth/jwt.py with additional security features.

Features:
- Token type validation (access, refresh, temporary)
- Expiration checking
- JTI (JWT ID) extraction and validation
- Token claims validation
- Token metadata extraction
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import UUID

import jwt
from jwt.exceptions import ExpiredSignatureError, InvalidTokenError

from backend.core.settings.config import settings


TokenType = Literal["access", "refresh", "temporary"]


class TokenValidationError(Exception):
    """Raised when token validation fails"""
    pass


class TokenExpiredError(TokenValidationError):
    """Raised when token has expired"""
    pass


class InvalidTokenTypeError(TokenValidationError):
    """Raised when token type doesn't match expected"""
    pass


def validate_token_type(token: str, expected_type: TokenType) -> dict[str, Any]:
    """
    Validate token and ensure it matches expected type.
    
    Args:
        token: JWT token string
        expected_type: Expected token type (access, refresh, temporary)
        
    Returns:
        Decoded token payload
        
    Raises:
        TokenExpiredError: Token has expired
        InvalidTokenTypeError: Token type doesn't match
        TokenValidationError: Other validation errors
    """
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALG])
    except ExpiredSignatureError:
        raise TokenExpiredError("Token has expired")
    except InvalidTokenError as e:
        raise TokenValidationError(f"Invalid token: {e}")
    
    token_type = payload.get("type")
    if token_type != expected_type:
        raise InvalidTokenTypeError(
            f"Expected {expected_type} token, got {token_type or 'unknown'}"
        )
    
    return payload


def validate_access_token(token: str) -> dict[str, Any]:
    """Validate that token is an access token"""
    return validate_token_type(token, "access")


def validate_refresh_token(token: str) -> dict[str, Any]:
    """Validate that token is a refresh token"""
    return validate_token_type(token, "refresh")


def validate_temporary_token(token: str) -> dict[str, Any]:
    """Validate that token is a temporary token"""
    return validate_token_type(token, "temporary")


def extract_jti(token: str) -> str:
    """
    Extract JTI (JWT ID) from token without full validation.
    
    Useful for revocation checks before full validation.
    
    Args:
        token: JWT token string
        
    Returns:
        JTI string
        
    Raises:
        TokenValidationError: Token is malformed or missing JTI
    """
    try:
        # Decode without verification to extract JTI
        payload = jwt.decode(token, options={"verify_signature": False})
        jti = payload.get("jti")
        if not jti:
            raise TokenValidationError("Token missing JTI claim")
        return jti
    except Exception as e:
        raise TokenValidationError(f"Failed to extract JTI: {e}")


def extract_user_id(token: str) -> str:
    """
    Extract user ID (sub claim) from token without full validation.
    
    Args:
        token: JWT token string
        
    Returns:
        User ID string
        
    Raises:
        TokenValidationError: Token is malformed or missing sub
    """
    try:
        payload = jwt.decode(token, options={"verify_signature": False})
        sub = payload.get("sub")
        if not sub:
            raise TokenValidationError("Token missing sub claim")
        return sub
    except Exception as e:
        raise TokenValidationError(f"Failed to extract user ID: {e}")


def extract_organization_id(token: str) -> str:
    """
    Extract organization ID from token without full validation.
    
    Args:
        token: JWT token string
        
    Returns:
        Organization ID string
        
    Raises:
        TokenValidationError: Token is malformed or missing org_id
    """
    try:
        payload = jwt.decode(token, options={"verify_signature": False})
        org_id = payload.get("org_id")
        if not org_id:
            raise TokenValidationError("Token missing org_id claim")
        return org_id
    except Exception as e:
        raise TokenValidationError(f"Failed to extract organization ID: {e}")


def is_token_expired(token: str) -> bool:
    """
    Check if token is expired without raising exception.
    
    Args:
        token: JWT token string
        
    Returns:
        True if expired, False if valid
    """
    try:
        payload = jwt.decode(token, options={"verify_signature": False})
        exp = payload.get("exp")
        if not exp:
            return True  # No expiration = treat as expired
        
        exp_dt = datetime.fromtimestamp(exp, tz=timezone.utc)
        return datetime.now(timezone.utc) >= exp_dt
    except Exception:
        return True  # Invalid token = treat as expired


def get_token_expiry(token: str) -> datetime:
    """
    Get token expiration datetime.
    
    Args:
        token: JWT token string
        
    Returns:
        Expiration datetime (timezone-aware UTC)
        
    Raises:
        TokenValidationError: Token is malformed or missing exp
    """
    try:
        payload = jwt.decode(token, options={"verify_signature": False})
        exp = payload.get("exp")
        if not exp:
            raise TokenValidationError("Token missing exp claim")
        return datetime.fromtimestamp(exp, tz=timezone.utc)
    except TokenValidationError:
        raise
    except Exception as e:
        raise TokenValidationError(f"Failed to extract expiry: {e}")


def get_token_metadata(token: str) -> dict[str, Any]:
    """
    Extract all token metadata without validation.
    
    Useful for logging, debugging, or displaying token info to users.
    
    Args:
        token: JWT token string
        
    Returns:
        Dictionary with token metadata:
        - jti: JWT ID
        - sub: User ID
        - org_id: Organization ID
        - type: Token type (access, refresh, temporary)
        - iat: Issued at timestamp
        - exp: Expiration timestamp
        - iss: Issuer
        - is_expired: Boolean
        
    Raises:
        TokenValidationError: Token is malformed
    """
    try:
        payload = jwt.decode(token, options={"verify_signature": False})
        
        exp_timestamp = payload.get("exp")
        is_expired = False
        if exp_timestamp:
            exp_dt = datetime.fromtimestamp(exp_timestamp, tz=timezone.utc)
            is_expired = datetime.now(timezone.utc) >= exp_dt
        
        return {
            "jti": payload.get("jti"),
            "sub": payload.get("sub"),
            "org_id": payload.get("org_id"),
            "type": payload.get("type"),
            "iat": payload.get("iat"),
            "exp": payload.get("exp"),
            "iss": payload.get("iss"),
            "is_expired": is_expired,
        }
    except Exception as e:
        raise TokenValidationError(f"Failed to extract metadata: {e}")


def validate_token_claims(
    token: str,
    required_claims: list[str] | None = None,
    expected_values: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Validate token has required claims and expected values.
    
    Args:
        token: JWT token string
        required_claims: List of claim names that must be present
        expected_values: Dict of claim_name -> expected_value
        
    Returns:
        Decoded token payload
        
    Raises:
        TokenValidationError: Missing claims or mismatched values
    """
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALG])
    except ExpiredSignatureError:
        raise TokenExpiredError("Token has expired")
    except InvalidTokenError as e:
        raise TokenValidationError(f"Invalid token: {e}")
    
    # Check required claims
    if required_claims:
        missing_claims = [claim for claim in required_claims if claim not in payload]
        if missing_claims:
            raise TokenValidationError(f"Missing required claims: {', '.join(missing_claims)}")
    
    # Check expected values
    if expected_values:
        for claim, expected in expected_values.items():
            actual = payload.get(claim)
            if actual != expected:
                raise TokenValidationError(
                    f"Claim '{claim}' has value '{actual}', expected '{expected}'"
                )
    
    return payload


def get_remaining_lifetime(token: str) -> int:
    """
    Get remaining lifetime of token in seconds.
    
    Args:
        token: JWT token string
        
    Returns:
        Remaining seconds (0 if expired)
        
    Raises:
        TokenValidationError: Token is malformed
    """
    try:
        exp = get_token_expiry(token)
        now = datetime.now(timezone.utc)
        remaining = (exp - now).total_seconds()
        return max(0, int(remaining))
    except TokenValidationError:
        raise

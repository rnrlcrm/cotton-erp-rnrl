from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict
from uuid import uuid4

import jwt

from backend.core.settings.config import settings


def _now() -> datetime:
    return datetime.now(timezone.utc)


def create_token(sub: str, org_id: str, minutes: int | None = None, days: int | None = None, token_type: str = "access") -> str:
    iat = _now()
    if minutes is not None:
        exp = iat + timedelta(minutes=minutes)
    elif days is not None:
        exp = iat + timedelta(days=days)
    else:
        exp = iat + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRES_MINUTES)
    payload: Dict[str, Any] = {
        "sub": sub,
        "org_id": org_id,
        "iat": int(iat.timestamp()),
        "exp": int(exp.timestamp()),
        "jti": str(uuid4()),
        "type": token_type,
        "iss": "cotton-erp",
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALG)


def decode_token(token: str) -> dict:
    return jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALG])


# Alias for backward compatibility
def create_access_token(sub: str, org_id: str = "default", minutes: int | None = None) -> str:
    """Create access token (alias for create_token)"""
    return create_token(sub=sub, org_id=org_id, minutes=minutes, token_type="access")

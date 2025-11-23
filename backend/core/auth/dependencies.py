"""
Authentication dependencies for WebSocket and HTTP endpoints.

Provides:
- get_current_user: HTTP auth (Bearer token in header)
- get_current_user_ws: WebSocket auth (token in query param)
"""

from __future__ import annotations

from typing import Annotated, Optional

from fastapi import Depends, Header, HTTPException, Query, WebSocket, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.auth.jwt import decode_token
from backend.db.async_session import get_db
from backend.modules.settings.repositories.settings_repositories import UserRepository


async def get_current_user(
    authorization: Annotated[str | None, Header(alias="Authorization")] = None,
    db: AsyncSession = Depends(get_db),
):
    """
    Get current user from HTTP Authorization header.
    
    Usage:
    ```python
    @router.get("/protected")
    async def protected_route(user: User = Depends(get_current_user)):
        return {"user_id": user.id}
    ```
    """
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token",
        )
    
    token = authorization.split(" ", 1)[1]
    
    try:
        payload = decode_token(token)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )
    
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )
    
    user = await UserRepository(db).get_by_id(user_id)
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Inactive or missing user",
        )
    
    return user


async def get_current_user_ws(
    websocket: WebSocket,
    token: Annotated[str | None, Query()] = None,
    db: AsyncSession = Depends(get_db),
):
    """
    Get current user from WebSocket query parameter.
    
    WebSocket auth uses query param since headers aren't easily accessible.
    
    Usage:
    ```python
    @router.websocket("/ws")
    async def websocket_endpoint(
        websocket: WebSocket,
        user: User = Depends(get_current_user_ws)
    ):
        await websocket.accept()
        ...
    ```
    
    Client usage:
    ```javascript
    const ws = new WebSocket('ws://localhost:8000/ws?token=JWT_TOKEN');
    ```
    """
    if not token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing token",
        )
    
    try:
        payload = decode_token(token)
    except Exception:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )
    
    user_id = payload.get("sub")
    if not user_id:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )
    
    user = await UserRepository(db).get_by_id(user_id)
    if user is None or not user.is_active:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Inactive or missing user",
        )
    
    return user


def require_permissions(*codes: str):
    """
    Require specific permissions for endpoint access.
    
    Usage:
    ```python
    @router.post("/admin")
    async def admin_route(
        user: User = Depends(get_current_user),
        _: None = Depends(require_permissions("admin.access"))
    ):
        return {"message": "Admin only"}
    ```
    """
    from backend.modules.settings.services.settings_services import RBACService
    
    async def _dep(user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
        svc = RBACService(db)
        if not await svc.user_has_permissions(user.id, list(codes)):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Forbidden",
            )
    
    return _dep

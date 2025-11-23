"""
Session Management API

Endpoints for multi-device session management.

Features:
- Refresh access token
- List all active sessions
- Logout specific device (remote logout)
- Logout all devices

Security:
- Refresh token rotation
- Device fingerprinting
- Suspicious login detection
- Session expiry
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from backend.db.session import get_async_db
from backend.modules.auth.schemas import (
    RefreshTokenRequest,
    TokenResponse,
    SessionListResponse,
    SessionInfo,
    LogoutResponse
)
from backend.core.jwt.session import SessionService
from backend.app.middleware.auth import get_current_user


router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Refresh Access Token",
    description="""
    Refresh expired access token using refresh token.
    
    **Token Rotation:**
    - Issues new access token (15 min expiry)
    - Issues new refresh token (30 day expiry)
    - Revokes old refresh token (security)
    
    **Security:**
    - Validates refresh token signature
    - Checks if token is revoked
    - Updates session last active time
    - Detects suspicious activity
    """
)
async def refresh_token(
    request: Request,
    body: RefreshTokenRequest,
    db: AsyncSession = Depends(get_async_db)
):
    """
    Refresh access token.
    
    Use this endpoint when access token expires (every 15 minutes).
    You'll get a new access token AND a new refresh token.
    """
    session_service = SessionService(db)
    
    # Get client info
    user_agent = request.headers.get('user-agent', '')
    ip_address = request.client.host
    
    try:
        result = await session_service.refresh_session(
            refresh_token=body.refresh_token,
            user_agent=user_agent,
            ip_address=ip_address
        )
        
        return TokenResponse(**result)
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"}
        )


@router.get(
    "/sessions",
    response_model=SessionListResponse,
    summary="List Active Sessions",
    description="""
    Get all active sessions for current user.
    
    Shows all devices where user is logged in:
    - Device name (e.g., "iPhone 13 (iOS 15.0)")
    - Device type (mobile, desktop, tablet)
    - Last active time
    - IP address
    - Is current device
    
    **Use Case:**
    - User can see where they're logged in
    - Detect unauthorized access
    - Remote logout from specific devices
    """
)
async def list_sessions(
    request: Request,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """
    List all active sessions for current user.
    
    Requires: Valid access token
    """
    session_service = SessionService(db)
    
    sessions = await session_service.get_user_sessions(current_user['user_id'])
    
    # Get current session JTI from token
    current_jti = current_user.get('jti')
    
    session_list = []
    for session in sessions:
        session_dict = session.to_dict()
        session_dict['is_current'] = (session.access_token_jti == current_jti)
        session_list.append(SessionInfo(**session_dict))
    
    return SessionListResponse(
        sessions=session_list,
        total=len(session_list)
    )


@router.delete(
    "/sessions/{session_id}",
    response_model=LogoutResponse,
    summary="Logout Specific Device",
    description="""
    Logout from specific device (remote logout).
    
    **Use Case:**
    - User forgot to logout from public computer
    - Detected unauthorized access
    - Lost/stolen device
    
    **Security:**
    - Revokes refresh token
    - Revokes access token
    - Marks session as inactive
    - Cannot be undone (must login again)
    """
)
async def logout_device(
    session_id: UUID,
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Logout from specific device.
    
    Requires: Valid access token
    """
    session_service = SessionService(db)
    
    try:
        await session_service.revoke_session(
            session_id=session_id,
            user_id=current_user['user_id']
        )
        
        return LogoutResponse(
            message=f"Successfully logged out from device",
            sessions_revoked=1
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.delete(
    "/sessions/all",
    response_model=LogoutResponse,
    summary="Logout All Devices",
    description="""
    Logout from all devices except current.
    
    **Use Case:**
    - Security concern (might have been hacked)
    - Want to force re-login on all devices
    - Password changed
    
    **Security:**
    - Revokes all refresh tokens
    - Revokes all access tokens
    - Current device remains logged in
    """
)
async def logout_all_devices(
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Logout from all devices except current.
    
    Requires: Valid access token
    """
    session_service = SessionService(db)
    
    # Get current session ID (from token)
    current_jti = current_user.get('jti')
    
    # Find current session
    sessions = await session_service.get_user_sessions(current_user['user_id'])
    current_session = next(
        (s for s in sessions if s.access_token_jti == current_jti),
        None
    )
    
    current_session_id = current_session.id if current_session else None
    
    # Revoke all except current
    await session_service.revoke_all_sessions(
        user_id=current_user['user_id'],
        except_session_id=current_session_id
    )
    
    sessions_revoked = len(sessions) - (1 if current_session else 0)
    
    return LogoutResponse(
        message=f"Successfully logged out from {sessions_revoked} device(s)",
        sessions_revoked=sessions_revoked
    )


@router.delete(
    "/logout",
    response_model=LogoutResponse,
    summary="Logout Current Device",
    description="""
    Logout from current device only.
    
    **Standard logout flow.**
    """
)
async def logout(
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Logout from current device.
    
    Requires: Valid access token
    """
    session_service = SessionService(db)
    
    # Get current session ID (from token)
    current_jti = current_user.get('jti')
    
    # Find current session
    sessions = await session_service.get_user_sessions(current_user['user_id'])
    current_session = next(
        (s for s in sessions if s.access_token_jti == current_jti),
        None
    )
    
    if not current_session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Current session not found"
        )
    
    await session_service.revoke_session(
        session_id=current_session.id,
        user_id=current_user['user_id']
    )
    
    return LogoutResponse(
        message="Successfully logged out",
        sessions_revoked=1
    )

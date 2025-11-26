from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.audit import audit_log
from backend.db.async_session import get_db
from backend.modules.settings.schemas.settings_schemas import (
    LoginRequest,
    SignupRequest,
    TokenResponse,
    UserOut,
    CreateSubUserRequest,
    SubUserOut,
)
from backend.modules.settings.services.settings_services import AuthService
from backend.core.auth.deps import get_current_user
from backend.modules.settings.organization.router import router as organization_router
from backend.modules.settings.commodities.router import router as commodities_router
from backend.modules.settings.locations.router import router as locations_router

router = APIRouter()
router.include_router(organization_router)
router.include_router(commodities_router)
router.include_router(locations_router)


@router.get("/health", tags=["health"])  # lightweight placeholder
def health() -> dict:
    return {"status": "ok"}


@router.post("/auth/signup", response_model=UserOut, tags=["auth"])
async def signup(payload: SignupRequest, db: AsyncSession = Depends(get_db)) -> UserOut:
    svc = AuthService(db)
    try:
        user = await svc.signup(payload.email, payload.password, payload.full_name)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    audit_log("user.signup", None, "user", str(user.id), {"email": user.email})
    return UserOut(
        id=str(user.id),
        email=user.email,
        full_name=user.full_name,
        organization_id=str(user.organization_id),
        is_active=user.is_active,
        created_at=user.created_at,
        updated_at=user.updated_at,
    )


@router.post("/auth/login", response_model=TokenResponse, tags=["auth"])
async def login(payload: LoginRequest, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    svc = AuthService(db)
    try:
        access, refresh, expires_in = await svc.login(payload.email, payload.password)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))
    audit_log("user.login", None, "user", None, {"email": payload.email})
    return TokenResponse(access_token=access, refresh_token=refresh, expires_in=expires_in)


@router.post("/auth/refresh", response_model=TokenResponse, tags=["auth"])
async def refresh(token: str, db: AsyncSession = Depends(get_db)) -> TokenResponse:  # noqa: D401 - simple endpoint
    svc = AuthService(db)
    try:
        access, new_refresh, expires_in = await svc.refresh(token)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))
    audit_log("user.refresh", None, "refresh_token", None, {})
    return TokenResponse(access_token=access, refresh_token=new_refresh, expires_in=expires_in)


@router.post("/auth/logout", tags=["auth"])
async def logout(token: str, db: AsyncSession = Depends(get_db)) -> dict:
    svc = AuthService(db)
    try:
        await svc.logout(token)
    except ValueError:
        pass
    audit_log("user.logout", None, "refresh_token", None, {})
    return {"message": "Logged out successfully"}

@router.get("/auth/me", response_model=UserOut, tags=["auth"])
def me(user=Depends(get_current_user)) -> UserOut:  # noqa: ANN001
    return UserOut(
        id=str(user.id),
        email=user.email,
        full_name=user.full_name,
        organization_id=str(user.organization_id),
        is_active=user.is_active,
        parent_user_id=str(user.parent_user_id) if user.parent_user_id else None,
        role=user.role,
        created_at=user.created_at,
        updated_at=user.updated_at,
    )


@router.post("/auth/sub-users", response_model=SubUserOut, status_code=status.HTTP_201_CREATED, tags=["auth", "sub-users"])
async def create_sub_user(
    payload: CreateSubUserRequest,
    user=Depends(get_current_user),  # noqa: ANN001
    db: AsyncSession = Depends(get_db)
) -> SubUserOut:
    """Create a sub-user (max 2 per parent)."""
    svc = AuthService(db)
    try:
        sub_user = await svc.create_sub_user(
            parent_user_id=str(user.id),
            email=payload.email,
            password=payload.password,
            full_name=payload.full_name,
            role=payload.role
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    
    audit_log("sub_user.created", str(user.id), "user", str(sub_user.id), {"email": sub_user.email})
    return SubUserOut(
        id=str(sub_user.id),
        email=sub_user.email,
        full_name=sub_user.full_name,
        role=sub_user.role,
        is_active=sub_user.is_active,
        parent_user_id=str(sub_user.parent_user_id),
        created_at=sub_user.created_at,
        updated_at=sub_user.updated_at,
    )


@router.get("/auth/sub-users", response_model=list[SubUserOut], tags=["auth", "sub-users"])
async def list_sub_users(
    user=Depends(get_current_user),  # noqa: ANN001
    db: AsyncSession = Depends(get_db)
) -> list[SubUserOut]:
    """List all sub-users for the authenticated parent user."""
    svc = AuthService(db)
    sub_users = await svc.get_sub_users(str(user.id))
    
    return [
        SubUserOut(
            id=str(su.id),
            email=su.email,
            full_name=su.full_name,
            role=su.role,
            is_active=su.is_active,
            parent_user_id=str(su.parent_user_id),
            created_at=su.created_at,
            updated_at=su.updated_at,
        )
        for su in sub_users
    ]


@router.delete("/auth/sub-users/{sub_user_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["auth", "sub-users"])
async def delete_sub_user(
    sub_user_id: str,
    user=Depends(get_current_user),  # noqa: ANN001
    db: AsyncSession = Depends(get_db)
):
    """Delete a sub-user (only your own sub-users)."""
    svc = AuthService(db)
    try:
        await svc.delete_sub_user(str(user.id), sub_user_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    
    audit_log("sub_user.deleted", str(user.id), "user", sub_user_id, {})

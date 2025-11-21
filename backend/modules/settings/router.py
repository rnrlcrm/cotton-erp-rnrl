from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.core.audit import audit_log
from backend.db.session import get_db
from backend.modules.settings.schemas.settings_schemas import LoginRequest, SignupRequest, TokenResponse, UserOut
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
def signup(payload: SignupRequest, db: Session = Depends(get_db)) -> UserOut:
    svc = AuthService(db)
    try:
        user = svc.signup(payload.email, payload.password, payload.full_name)
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
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    svc = AuthService(db)
    try:
        access, refresh, expires_in = svc.login(payload.email, payload.password)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))
    audit_log("user.login", None, "user", None, {"email": payload.email})
    return TokenResponse(access_token=access, refresh_token=refresh, expires_in=expires_in)


@router.post("/auth/refresh", response_model=TokenResponse, tags=["auth"])
def refresh(token: str, db: Session = Depends(get_db)) -> TokenResponse:  # noqa: D401 - simple endpoint
    svc = AuthService(db)
    try:
        access, new_refresh, expires_in = svc.refresh(token)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))
    audit_log("user.refresh", None, "refresh_token", None, {})
    return TokenResponse(access_token=access, refresh_token=new_refresh, expires_in=expires_in)


@router.post("/auth/logout", tags=["auth"])
def logout(token: str, db: Session = Depends(get_db)) -> dict:
    svc = AuthService(db)
    try:
        svc.logout(token)
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
        created_at=user.created_at,
        updated_at=user.updated_at,
    )

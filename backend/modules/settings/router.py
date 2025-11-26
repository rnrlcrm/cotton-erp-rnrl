from __future__ import annotations

from typing import AsyncGenerator
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as redis

from backend.core.audit import audit_log
from backend.db.async_session import get_db
from backend.app.middleware.rate_limit import limiter
from backend.core.security.account_lockout import AccountLockoutService
from backend.modules.settings.schemas.settings_schemas import (
    LoginRequest,
    SignupRequest,
    InternalUserSignupRequest,
    ChangePasswordRequest,
    TokenResponse,
    UserOut,
    CreateSubUserRequest,
    SubUserOut,
    Setup2FARequest,
    Verify2FARequest,
    TwoFAStatusResponse,
    LoginWith2FAResponse,
    SendOTPRequest,
    VerifyOTPRequest,
    OTPResponse,
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


async def get_redis() -> AsyncGenerator[redis.Redis, None]:
    """Get Redis client for OTP storage"""
    redis_client = redis.from_url(
        "redis://localhost:6379",
        encoding="utf-8",
        decode_responses=False
    )
    try:
        yield redis_client
    finally:
        await redis_client.aclose()


@router.get("/health", tags=["health"])  # lightweight placeholder
def health() -> dict:
    return {"status": "ok"}


@router.post("/auth/signup", response_model=UserOut, tags=["auth"])
# @limiter.limit("5/minute")  # Prevent signup abuse - TEMP DISABLED FOR TESTING
async def signup(payload: SignupRequest, db: AsyncSession = Depends(get_db)) -> UserOut:
    """Generic signup - password policy NOT enforced here. Use /auth/signup-internal for INTERNAL users."""
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


@router.post("/auth/signup-internal", response_model=UserOut, tags=["auth"])
# @limiter.limit("5/minute")  # Prevent signup abuse - TEMP DISABLED FOR TESTING
async def signup_internal(
    payload: InternalUserSignupRequest,
    db: AsyncSession = Depends(get_db)
) -> UserOut:
    """Signup for INTERNAL users with enforced password policy."""
    svc = AuthService(db)
    try:
        user = await svc.signup(payload.email, payload.password, payload.full_name)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    audit_log("user.signup_internal", None, "user", str(user.id), {"email": user.email})
    return UserOut(
        id=str(user.id),
        email=user.email,
        full_name=user.full_name,
        organization_id=str(user.organization_id),
        is_active=user.is_active,
        created_at=user.created_at,
        updated_at=user.updated_at,
    )


@router.post("/auth/login", tags=["auth"])
# @limiter.limit("10/minute")  # Prevent brute force attacks - TEMP DISABLED FOR TESTING
async def login(
    payload: LoginRequest,
    db: AsyncSession = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis)
) -> TokenResponse | LoginWith2FAResponse:
    # Initialize account lockout service
    lockout_service = AccountLockoutService(redis_client)
    
    # Check if account is locked
    is_locked, ttl = await lockout_service.is_locked(payload.email)
    if is_locked:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Account locked due to too many failed login attempts. Try again in {ttl // 60} minutes."
        )
    
    svc = AuthService(db)
    try:
        # Check if user exists and validate password
        from backend.modules.settings.repositories.settings_repositories import UserRepository
        user_repo = UserRepository(db)
        user = await user_repo.get_by_email(payload.email)
        
        if not user:
            # Record failed attempt
            lockout_info = await lockout_service.record_failed_attempt(payload.email)
            raise ValueError("Invalid credentials")
        if not user.is_active:
            raise ValueError("User account is inactive")
        if not svc.hasher.verify(payload.password, user.password_hash):
            # Record failed attempt
            lockout_info = await lockout_service.record_failed_attempt(payload.email)
            if lockout_info["locked"]:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=lockout_info["message"]
                )
            raise ValueError(f"Invalid credentials. {lockout_info['remaining_attempts']} attempts remaining.")
        
        # Clear failed attempts on successful password verification
        await lockout_service.clear_failed_attempts(payload.email)
        
        # Check if 2FA is enabled
        if user.two_fa_enabled:
            return LoginWith2FAResponse(
                two_fa_required=True,
                message="2FA enabled. Please verify with PIN.",
                email=payload.email
            )
        
        # No 2FA - proceed with normal login
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
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))
    audit_log("user.logout", None, "refresh_token", None, {})
    return {"message": "Logged out successfully"}


@router.post("/auth/logout-all", tags=["auth"])
async def logout_all_devices(
    request: Request,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> dict:
    """
    Logout user from all devices by revoking all refresh tokens.
    Useful for security incidents or when user wants to terminate all sessions.
    """
    svc = AuthService(db)
    user_id = current_user["sub"]
    
    try:
        count = await svc.logout_all_devices(user_id)
        audit_log("user.logout_all", user_id, "security", user_id, {"tokens_revoked": count})
        return {
            "message": f"Logged out from all devices successfully",
            "tokens_revoked": count
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to logout from all devices: {str(e)}"
        )


@router.post("/auth/send-otp", response_model=OTPResponse, tags=["auth"])
# @limiter.limit("3/minute")  # Prevent OTP spam - TEMP DISABLED FOR TESTING
async def send_otp_for_external_user(
    payload: SendOTPRequest,
    redis_client: redis.Redis = Depends(get_redis)
) -> OTPResponse:
    """
    Send OTP to EXTERNAL user's mobile number for authentication.
    
    EXTERNAL users (business partners and sub-users) authenticate via mobile OTP only.
    INTERNAL users (backoffice) must use email/password login.
    """
    from backend.modules.user_onboarding.services.otp_service import OTPService
    
    # Handle mobile number formatting
    mobile = payload.mobile_number.strip()
    if not mobile.startswith("+"):
        full_mobile = f"{payload.country_code}{mobile}"
    else:
        full_mobile = mobile
    
    otp_service = OTPService(redis_client)
    
    try:
        result = await otp_service.send_otp(full_mobile)
        
        audit_log("user.send_otp", None, "external_auth", None, {"mobile": full_mobile})
        
        return OTPResponse(
            success=True,
            message=f"OTP sent to {full_mobile}. Valid for 5 minutes.",
            otp_sent_at=result["expires_at"],
            expires_in_seconds=300
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send OTP: {str(e)}"
        )


@router.post("/auth/verify-otp", response_model=TokenResponse, tags=["auth"])
# @limiter.limit("10/minute")  # Prevent OTP brute force - TEMP DISABLED FOR TESTING
async def verify_otp_for_external_user(
    payload: VerifyOTPRequest,
    redis_client: redis.Redis = Depends(get_redis),
    db: AsyncSession = Depends(get_db)
) -> TokenResponse:
    """
    Verify OTP and login EXTERNAL user (business partner or sub-user).
    
    Returns JWT tokens for authenticated session.
    User must exist in database (created during partner onboarding or as sub-user).
    """
    from backend.modules.user_onboarding.services.otp_service import OTPService
    from backend.modules.settings.repositories.settings_repositories import UserRepository
    from backend.core.auth.jwt import create_token
    
    otp_service = OTPService(redis_client)
    user_repo = UserRepository(db)
    
    # Verify OTP
    await otp_service.verify_otp(payload.mobile_number, payload.otp)
    
    # Get user by mobile number
    user = await user_repo.get_by_mobile(payload.mobile_number)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found. Please complete partner onboarding first."
        )
    
    # Verify user is EXTERNAL type
    if user.user_type not in ['EXTERNAL']:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This login method is only for EXTERNAL users (business partners). INTERNAL users must use email/password."
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive. Please contact support."
        )
    
    # Generate JWT tokens
    from backend.modules.settings.services.settings_services import AuthService
    from backend.core.settings.config import settings
    svc = AuthService(db)
    
    # Use business_partner_id for EXTERNAL users
    org_or_partner_id = str(user.business_partner_id) if user.business_partner_id else None
    
    if not org_or_partner_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User has no associated business partner"
        )
    
    access_minutes = settings.ACCESS_TOKEN_EXPIRES_MINUTES
    refresh_days = settings.REFRESH_TOKEN_EXPIRES_DAYS
    
    access = create_token(str(user.id), org_or_partner_id, minutes=access_minutes, token_type="access")
    refresh = create_token(str(user.id), org_or_partner_id, days=refresh_days, token_type="refresh")
    
    # Store refresh token
    from backend.modules.settings.models.settings_models import RefreshToken
    from backend.core.auth.jwt import decode_token
    from datetime import datetime, timezone
    
    payload_data = decode_token(refresh)
    rt = RefreshToken(
        user_id=user.id,
        jti=payload_data["jti"],
        expires_at=datetime.fromtimestamp(payload_data["exp"], tz=timezone.utc),
        revoked=False,
    )
    db.add(rt)
    await db.flush()
    
    audit_log("user.otp_login", str(user.id), "external_auth", str(user.id), {"mobile": payload.mobile_number})
    
    return TokenResponse(
        access_token=access,
        refresh_token=refresh,
        expires_in=access_minutes * 60
    )


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
    """Create a sub-user (max 2 per parent). Sub-users login via mobile OTP or PIN."""
    svc = AuthService(db)
    try:
        sub_user = await svc.create_sub_user(
            parent_user_id=str(user.id),
            mobile_number=payload.mobile_number,
            full_name=payload.full_name,
            pin=payload.pin,
            role=payload.role
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    
    audit_log("sub_user.created", str(user.id), "user", str(sub_user.id), {"mobile_number": sub_user.mobile_number})
    return SubUserOut(
        id=str(sub_user.id),
        mobile_number=sub_user.mobile_number,
        full_name=sub_user.full_name,
        role=sub_user.role,
        is_active=sub_user.is_active,
        parent_user_id=str(sub_user.parent_user_id),
        business_partner_id=str(sub_user.business_partner_id),
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
            mobile_number=su.mobile_number,
            full_name=su.full_name,
            role=su.role,
            is_active=su.is_active,
            parent_user_id=str(su.parent_user_id),
            business_partner_id=str(su.business_partner_id),
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


@router.post("/auth/sub-users/{sub_user_id}/disable", response_model=SubUserOut, tags=["auth", "sub-users"])
async def disable_sub_user(
    sub_user_id: str,
    user=Depends(get_current_user),  # noqa: ANN001
    db: AsyncSession = Depends(get_db)
) -> SubUserOut:
    """Disable a sub-user (only your own sub-users)."""
    svc = AuthService(db)
    try:
        sub_user = await svc.disable_sub_user(str(user.id), sub_user_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    
    audit_log("sub_user.disabled", str(user.id), "user", sub_user_id, {})
    return SubUserOut(
        id=str(sub_user.id),
        mobile_number=sub_user.mobile_number,
        full_name=sub_user.full_name,
        role=sub_user.role,
        is_active=sub_user.is_active,
        parent_user_id=str(sub_user.parent_user_id),
        business_partner_id=str(sub_user.business_partner_id),
        created_at=sub_user.created_at,
        updated_at=sub_user.updated_at,
    )


@router.post("/auth/sub-users/{sub_user_id}/enable", response_model=SubUserOut, tags=["auth", "sub-users"])
async def enable_sub_user(
    sub_user_id: str,
    user=Depends(get_current_user),  # noqa: ANN001
    db: AsyncSession = Depends(get_db)
) -> SubUserOut:
    """Enable a sub-user (only your own sub-users)."""
    svc = AuthService(db)
    try:
        sub_user = await svc.enable_sub_user(str(user.id), sub_user_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    
    audit_log("sub_user.enabled", str(user.id), "user", sub_user_id, {})
    return SubUserOut(
        id=str(sub_user.id),
        mobile_number=sub_user.mobile_number,
        full_name=sub_user.full_name,
        role=sub_user.role,
        is_active=sub_user.is_active,
        parent_user_id=str(sub_user.parent_user_id),
        business_partner_id=str(sub_user.business_partner_id),
        created_at=sub_user.created_at,
        updated_at=sub_user.updated_at,
    )


# ============================================
# 2FA ENDPOINTS (Phase 3)
# ============================================

@router.post("/auth/2fa-setup", response_model=TwoFAStatusResponse, tags=["auth", "2fa"])
async def setup_2fa(
    payload: Setup2FARequest,
    user=Depends(get_current_user),  # noqa: ANN001
    db: AsyncSession = Depends(get_db)
) -> TwoFAStatusResponse:
    """Enable 2FA and set PIN for the authenticated user."""
    svc = AuthService(db)
    try:
        await svc.setup_2fa(str(user.id), payload.pin)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    
    audit_log("user.2fa_enabled", str(user.id), "user", str(user.id), {})
    return TwoFAStatusResponse(
        two_fa_enabled=True,
        message="2FA enabled successfully. Use your PIN for future logins."
    )


@router.post("/auth/2fa-verify", response_model=TokenResponse, tags=["auth", "2fa"])
async def verify_2fa(
    payload: Verify2FARequest,
    db: AsyncSession = Depends(get_db)
) -> TokenResponse:
    """Verify 2FA PIN and issue tokens."""
    svc = AuthService(db)
    try:
        access, refresh, expires_in = await svc.verify_pin(payload.email, payload.pin)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))
    
    audit_log("user.2fa_verified", None, "user", None, {"email": payload.email})
    return TokenResponse(access_token=access, refresh_token=refresh, expires_in=expires_in)


@router.post("/auth/2fa-disable", response_model=TwoFAStatusResponse, tags=["auth", "2fa"])
async def disable_2fa(
    user=Depends(get_current_user),  # noqa: ANN001
    db: AsyncSession = Depends(get_db)
) -> TwoFAStatusResponse:
    """Disable 2FA for the authenticated user."""
    svc = AuthService(db)
    try:
        await svc.disable_2fa(str(user.id))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    
    audit_log("user.2fa_disabled", str(user.id), "user", str(user.id), {})
    return TwoFAStatusResponse(
        two_fa_enabled=False,
        message="2FA disabled successfully."
    )

"""
Authentication Router for Mobile OTP Flow

Endpoints:
- POST /auth/send-otp - Send OTP to mobile number
- POST /auth/verify-otp - Verify OTP and get JWT token
- POST /auth/complete-profile - Complete user profile
- GET /auth/me - Get current user details
"""

from typing import AsyncGenerator, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status, Header
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as redis

from backend.core.auth.deps import get_current_user
from backend.core.capabilities import Capabilities, RequireCapability
from backend.db import get_db
from backend.modules.user_onboarding.schemas.auth_schemas import (
    AuthTokenResponse,
    CompleteProfileRequest,
    OTPResponse,
    SendOTPRequest,
    UserProfileResponse,
    VerifyOTPRequest,
)
from backend.modules.user_onboarding.services.auth_service import UserAuthService
from backend.modules.user_onboarding.services.otp_service import OTPService

router = APIRouter(prefix="/auth", tags=["authentication"])


# ===== DEPENDENCIES =====

async def get_redis() -> AsyncGenerator[redis.Redis, None]:
    """
    Get Redis client for OTP storage
    
    TODO: Configure Redis connection from settings
    For now using localhost defaults
    """
    redis_client = redis.from_url(
        "redis://localhost:6379",
        encoding="utf-8",
        decode_responses=False
    )
    try:
        yield redis_client
    finally:
        await redis_client.aclose()


# ===== ENDPOINTS =====

@router.post(
    "/send-otp",
    response_model=OTPResponse,
    summary="Send OTP to Mobile Number",
    description="""
    Send OTP to user's mobile number for authentication.
    
    **Flow:**
    1. User enters mobile number
    2. System generates 6-digit OTP
    3. OTP stored in Redis with 5-minute expiry
    4. SMS sent to user (placeholder - to be implemented)
    
    **Rate Limiting:**
    - One OTP per mobile number per minute
    - OTP valid for 5 minutes
    - Maximum 3 verification attempts
    
    **Example:**
    ```json
    {
      "mobile_number": "9876543210",
      "country_code": "+91"
    }
    ```
    """
)
async def send_otp(
    request: SendOTPRequest,
    redis_client: redis.Redis = Depends(get_redis),
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    _check: None = Depends(RequireCapability(Capabilities.PUBLIC_ACCESS))
):
    """Send OTP to mobile number. Requires PUBLIC_ACCESS capability (unauthenticated endpoint)."""
    # Handle mobile number formatting
    mobile = request.mobile_number.strip()
    if not mobile.startswith("+"):
        full_mobile = f"{request.country_code}{mobile}"
    else:
        full_mobile = mobile
    
    otp_service = OTPService(redis_client)
    
    try:
        result = await otp_service.send_otp(full_mobile)
        
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


@router.post(
    "/verify-otp",
    response_model=AuthTokenResponse,
    summary="Verify OTP and Login",
    description="""
    Verify OTP and get JWT access token.
    
    **Flow:**
    1. User enters OTP received via SMS
    2. System verifies OTP against Redis
    3. Creates new user if first-time login
    4. Generates JWT token
    5. Returns token with next step instructions
    
    **Next Steps:**
    - `complete_profile`: New user needs to provide name/email
    - `start_onboarding`: Existing user without partner, start onboarding
    - `dashboard`: Existing user with partner, go to dashboard
    
    **Example:**
    ```json
    {
      "mobile_number": "9876543210",
      "otp": "123456"
    }
    ```
    """
)
async def verify_otp(
    http_request: Request,  # Renamed to avoid conflict
    request: VerifyOTPRequest,
    redis_client: redis.Redis = Depends(get_redis),
    db: AsyncSession = Depends(get_db),
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    _check: None = Depends(RequireCapability(Capabilities.PUBLIC_ACCESS))
):
    """Verify OTP and return JWT token with session. Requires PUBLIC_ACCESS capability (unauthenticated endpoint)."""
    otp_service = OTPService(redis_client)
    user_service = UserAuthService(db)
    
    # Verify OTP
    await otp_service.verify_otp(request.mobile_number, request.otp)
    
    # Get or create user
    user_data = await user_service.get_or_create_user(request.mobile_number)
    
    # For NEW implementation: Create session using SessionService
    if not user_data["is_new_user"] and user_data.get("user_id"):
        # Existing user - create full session with refresh token
        from backend.core.jwt.session import SessionService
        session_service = SessionService(db)
        
        # Get client info
        user_agent = http_request.headers.get('user-agent', '')
        ip_address = http_request.client.host
        
        # Create session (returns access + refresh tokens)
        session_result = await session_service.create_session(
            user_id=user_data["user_id"],
            user_agent=user_agent,
            ip_address=ip_address
        )
        
        # Determine next step
        next_step = user_service.determine_next_step(
            is_new_user=user_data["is_new_user"],
            profile_complete=user_data["profile_complete"]
        )
        
        return {
            **session_result,  # access_token, refresh_token, expires_at, device_info
            "user_id": str(user_data["user_id"]),
            "mobile_number": request.mobile_number,
            "is_new_user": False,
            "profile_complete": user_data.get("profile_complete", False),
            "next_step": next_step
        }
    else:
        # New user OR user without ID - temporary token (old flow)
        # For new users, generate a temporary token with mobile number
        access_token = user_service.generate_jwt_token(
            user_id=request.mobile_number,  # Use mobile as temp ID
            mobile_number=request.mobile_number
        )
        next_step = "start_onboarding"
        
        return AuthTokenResponse(
            access_token=access_token,
            token_type="bearer",
            user_id=user_data.get("user_id"),
            mobile_number=request.mobile_number,
            is_new_user=user_data["is_new_user"],
            profile_complete=user_data.get("profile_complete", False),
            next_step=next_step
        )


@router.post(
    "/complete-profile",
    response_model=UserProfileResponse,
    summary="Complete User Profile",
    description="""
    Complete profile for new users.
    
    **Required:**
    - Full name (mandatory)
    - Email (optional)
    
    **Authentication Required:** Bearer token from `/verify-otp`
    
    **After completion:**
    - User can start partner onboarding
    - Or go to dashboard if already linked to partner
    
    **Example:**
    ```json
    {
      "full_name": "Ramesh Kumar",
      "email": "ramesh@example.com"
    }
    ```
    """
)
async def complete_profile(
    request: CompleteProfileRequest,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    _check: None = Depends(RequireCapability(Capabilities.AUTH_UPDATE_PROFILE))
):
    """Complete user profile after OTP verification. Requires AUTH_UPDATE_PROFILE capability."""
    user_service = UserAuthService(db)
    
    user = await user_service.complete_profile(
        user_id=current_user.id,
        full_name=request.full_name,
        email=request.email
    )
    
    return UserProfileResponse(
        id=user.id,
        mobile_number=user.mobile_number,
        full_name=user.full_name,
        email=user.email,
        role=user.role,
        is_active=user.is_active,
        profile_complete=bool(user.full_name and user.email),
        created_at=user.created_at
    )


@router.get(
    "/me",
    response_model=UserProfileResponse,
    summary="Get Current User",
    description="""
    Get current user details from JWT token.
    
    **Authentication Required:** Bearer token
    
    **Returns:**
    - User ID, mobile number, name, email
    - Profile completion status
    - Role and account status
    """
)
async def get_current_user_details(
    current_user = Depends(get_current_user)
):
    """Get current user information"""
    return UserProfileResponse(
        id=current_user.id,
        mobile_number=current_user.mobile_number,
        full_name=current_user.full_name,
        email=current_user.email,
        role=current_user.role,
        is_active=current_user.is_active,
        profile_complete=bool(current_user.full_name and current_user.email),
        created_at=current_user.created_at
    )

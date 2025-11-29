"""
Mobile OTP Authentication Implementation Guide

CRITICAL: This must be implemented BEFORE onboarding flow
User Flow: Mobile → OTP → Verify → Profile → Onboarding
"""

from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as redis
import random

# ============================================
# SCHEMAS
# ============================================

class SendOTPRequest(BaseModel):
    """Request to send OTP"""
    mobile_number: str = Field(..., min_length=10, max_length=15, pattern=r"^\+?[1-9]\d{9,14}$")
    country_code: str = Field(default="+91", pattern=r"^\+\d{1,3}$")


class VerifyOTPRequest(BaseModel):
    """Request to verify OTP"""
    mobile_number: str = Field(..., min_length=10, max_length=15)
    otp: str = Field(..., min_length=6, max_length=6, pattern=r"^\d{6}$")


class CompleteProfileRequest(BaseModel):
    """Complete user profile for new users"""
    full_name: str = Field(..., min_length=2, max_length=200)
    email: Optional[str] = None


class OTPResponse(BaseModel):
    """OTP send response"""
    success: bool
    message: str
    otp_sent_at: datetime
    expires_in_seconds: int = 300  # 5 minutes


class AuthTokenResponse(BaseModel):
    """JWT token response after successful OTP verification"""
    access_token: str
    token_type: str = "bearer"
    user_id: UUID
    mobile_number: str
    is_new_user: bool
    profile_complete: bool


# ============================================
# SERVICE
# ============================================

class OTPService:
    """Handle OTP generation, storage, and verification"""
    
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self.otp_ttl = 300  # 5 minutes
        self.max_attempts = 3
        
    def generate_otp(self) -> str:
        """Generate 6-digit OTP"""
        return str(random.randint(100000, 999999))
    
    async def send_otp(self, mobile_number: str) -> dict:
        """
        Generate OTP and store in Redis
        
        Returns:
            {
                "otp": "123456",  # In production, don't return this
                "expires_at": datetime,
                "sent_via": "sms"
            }
        """
        # Generate OTP
        otp = self.generate_otp()
        
        # Store in Redis with TTL
        key = f"otp:{mobile_number}"
        attempts_key = f"otp_attempts:{mobile_number}"
        
        # Store OTP
        await self.redis.setex(key, self.otp_ttl, otp)
        
        # Reset attempts counter
        await self.redis.setex(attempts_key, self.otp_ttl, "0")
        
        # Send SMS (integrate with Twilio/MSG91/AWS SNS)
        await self._send_sms(mobile_number, otp)
        
        return {
            "otp": otp,  # Remove this in production
            "expires_at": datetime.utcnow() + timedelta(seconds=self.otp_ttl),
            "sent_via": "sms"
        }
    
    async def verify_otp(self, mobile_number: str, otp: str) -> bool:
        """
        Verify OTP from Redis
        
        Returns:
            True if OTP is valid and not expired
            False if OTP is invalid or expired
        
        Raises:
            HTTPException if too many attempts
        """
        key = f"otp:{mobile_number}"
        attempts_key = f"otp_attempts:{mobile_number}"
        
        # Check attempts
        attempts = await self.redis.get(attempts_key)
        if attempts and int(attempts) >= self.max_attempts:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many OTP verification attempts. Please request a new OTP."
            )
        
        # Get stored OTP
        stored_otp = await self.redis.get(key)
        
        if not stored_otp:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="OTP expired or not found. Please request a new OTP."
            )
        
        # Increment attempts
        if attempts:
            await self.redis.incr(attempts_key)
        
        # Verify OTP
        if stored_otp.decode() != otp:
            return False
        
        # OTP verified - delete from Redis
        await self.redis.delete(key)
        await self.redis.delete(attempts_key)
        
        return True
    
    async def _send_sms(self, mobile_number: str, otp: str):
        """
        Send SMS via provider (Twilio/MSG91/AWS SNS)
        
        TODO: Integrate with actual SMS provider
        """
        # Example with Twilio:
        """
        from twilio.rest import Client
        
        client = Client(account_sid, auth_token)
        message = client.messages.create(
            body=f"Your Cotton ERP verification code is: {otp}. Valid for 5 minutes.",
            from_='+1234567890',
            to=mobile_number
        )
        """
        
        # Example with MSG91 (India):
        """
        import httpx
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                'https://api.msg91.com/api/v5/otp',
                json={
                    'template_id': 'your_template_id',
                    'mobile': mobile_number,
                    'otp': otp
                },
                headers={'authkey': 'your_auth_key'}
            )
        """
        
        # For now, just log (development mode)
        print(f"📱 SMS to {mobile_number}: Your OTP is {otp}")


# ============================================
# USER SERVICE
# ============================================

class UserAuthService:
    """Handle user creation and JWT token generation"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_or_create_user(self, mobile_number: str) -> dict:
        """
        Get existing user or create new user
        
        Returns:
            {
                "user_id": UUID,
                "is_new_user": bool,
                "profile_complete": bool
            }
        """
        from backend.modules.settings.repositories.settings_repositories import UserRepository
        
        user_repo = UserRepository(self.db)
        
        # Try to find existing user by mobile
        user = await user_repo.get_by_mobile(mobile_number)
        
        if user:
            return {
                "user_id": user.id,
                "is_new_user": False,
                "profile_complete": bool(user.full_name and user.email)
            }
        
        # Create new user
        new_user = await user_repo.create(
            mobile_number=mobile_number,
            is_active=True,
            is_verified=True,  # Mobile verified via OTP
            role="partner_user"  # Default role
        )
        
        await self.db.commit()
        
        return {
            "user_id": new_user.id,
            "is_new_user": True,
            "profile_complete": False
        }
    
    async def complete_profile(
        self,
        user_id: UUID,
        full_name: str,
        email: Optional[str] = None
    ):
        """Update user profile with name and email"""
        from backend.modules.settings.repositories.settings_repositories import UserRepository
        
        user_repo = UserRepository(self.db)
        user = await user_repo.get_by_id(user_id)
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        user.full_name = full_name
        if email:
            user.email = email
        user.profile_completed_at = datetime.utcnow()
        
        await self.db.commit()
        await self.db.refresh(user)
        
        return user
    
    def generate_jwt_token(self, user_id: UUID, mobile_number: str) -> str:
        """Generate JWT access token"""
        from backend.core.auth.jwt import create_access_token
        
        token_data = {
            "sub": str(user_id),
            "mobile": mobile_number,
            "type": "access"
        }
        
        return create_access_token(token_data)


# ============================================
# ROUTER
# ============================================

router = APIRouter(prefix="/auth", tags=["authentication"])


async def get_redis() -> redis.Redis:
    """Get Redis client for OTP storage"""
    # TODO: Configure Redis connection
    return redis.from_url("redis://localhost:6379", decode_responses=False)


@router.post(
    "/send-otp",
    response_model=OTPResponse,
    summary="Send OTP to Mobile Number",
    description="""
    Send OTP to user's mobile number for authentication.
    
    - OTP is valid for 5 minutes
    - Maximum 3 verification attempts
    - After 3 failed attempts, user must request new OTP
    """
)
async def send_otp(
    request: SendOTPRequest,
    redis_client: redis.Redis = Depends(get_redis)
):
    """Send OTP to mobile number"""
    full_mobile = f"{request.country_code}{request.mobile_number}"
    
    otp_service = OTPService(redis_client)
    
    try:
        result = await otp_service.send_otp(full_mobile)
        
        return OTPResponse(
            success=True,
            message=f"OTP sent to {full_mobile}",
            otp_sent_at=datetime.utcnow(),
            expires_in_seconds=300
        )
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
    
    - Creates new user if first-time login
    - Returns JWT token for API access
    - Indicates if profile completion required
    """
)
async def verify_otp(
    request: VerifyOTPRequest,
    redis_client: redis.Redis = Depends(get_redis),
    db: AsyncSession = Depends(get_db)
):
    """Verify OTP and return JWT token"""
    otp_service = OTPService(redis_client)
    user_service = UserAuthService(db)
    
    # Verify OTP
    is_valid = await otp_service.verify_otp(request.mobile_number, request.otp)
    
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid OTP. Please try again."
        )
    
    # Get or create user
    user_data = await user_service.get_or_create_user(request.mobile_number)
    
    # Generate JWT token
    access_token = user_service.generate_jwt_token(
        user_id=user_data["user_id"],
        mobile_number=request.mobile_number
    )
    
    return AuthTokenResponse(
        access_token=access_token,
        token_type="bearer",
        user_id=user_data["user_id"],
        mobile_number=request.mobile_number,
        is_new_user=user_data["is_new_user"],
        profile_complete=user_data["profile_complete"]
    )


@router.post(
    "/complete-profile",
    summary="Complete User Profile",
    description="""
    Complete profile for new users.
    
    Required for new users before starting onboarding:
    - Full name (mandatory)
    - Email (optional)
    """
)
async def complete_profile(
    request: CompleteProfileRequest,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Complete user profile after OTP verification"""
    user_service = UserAuthService(db)
    
    user = await user_service.complete_profile(
        user_id=current_user.id,
        full_name=request.full_name,
        email=request.email
    )
    
    return {
        "success": True,
        "message": "Profile completed successfully",
        "user": {
            "id": str(user.id),
            "mobile_number": user.mobile_number,
            "full_name": user.full_name,
            "email": user.email
        },
        "next_step": "start_onboarding"
    }


@router.get(
    "/me",
    summary="Get Current User",
    description="Get current user details from JWT token"
)
async def get_current_user_details(
    current_user = Depends(get_current_user)
):
    """Get current user information"""
    return {
        "id": str(current_user.id),
        "mobile_number": current_user.mobile_number,
        "full_name": current_user.full_name,
        "email": current_user.email,
        "role": current_user.role,
        "is_active": current_user.is_active,
        "profile_complete": bool(current_user.full_name and current_user.email)
    }


# ============================================
# FRONTEND INTEGRATION
# ============================================

"""
FRONTEND FLOW:

1. Login Screen
   - User enters mobile number
   - Click "Send OTP"
   - POST /api/v1/auth/send-otp

2. OTP Verification Screen
   - User enters 6-digit OTP
   - Click "Verify"
   - POST /api/v1/auth/verify-otp
   - Store JWT token in localStorage

3. Profile Completion (if is_new_user = true)
   - Show form for full name and email
   - Submit profile
   - POST /api/v1/auth/complete-profile

4. Redirect to Dashboard or Onboarding
   - If profile_complete = true → Dashboard
   - If profile_complete = false → Complete Profile
   - If no partner linked → Start Onboarding

Example API Calls:

```javascript
// Step 1: Send OTP
const sendOTP = async (mobile) => {
  const response = await fetch('/api/v1/auth/send-otp', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      mobile_number: mobile,
      country_code: '+91'
    })
  });
  return response.json();
};

// Step 2: Verify OTP
const verifyOTP = async (mobile, otp) => {
  const response = await fetch('/api/v1/auth/verify-otp', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      mobile_number: mobile,
      otp: otp
    })
  });
  const data = await response.json();
  
  // Store token
  localStorage.setItem('access_token', data.access_token);
  
  return data;
};

// Step 3: Complete Profile (if needed)
const completeProfile = async (name, email) => {
  const token = localStorage.getItem('access_token');
  const response = await fetch('/api/v1/auth/complete-profile', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`
    },
    body: JSON.stringify({
      full_name: name,
      email: email
    })
  });
  return response.json();
};
```
"""

# ============================================
# CONFIGURATION
# ============================================

"""
Environment Variables Required:

# Redis (for OTP storage)
REDIS_URL=redis://localhost:6379

# SMS Provider (choose one)

# Option 1: Twilio
TWILIO_ACCOUNT_SID=your_account_sid
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_PHONE_NUMBER=+1234567890

# Option 2: MSG91 (India)
MSG91_AUTH_KEY=your_auth_key
MSG91_SENDER_ID=your_sender_id
MSG91_TEMPLATE_ID=your_template_id

# Option 3: AWS SNS
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_REGION=us-east-1

# JWT
JWT_SECRET_KEY=your-secret-key-change-this
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=43200  # 30 days
"""

# ============================================
# DEPENDENCIES TO INSTALL
# ============================================

"""
Add to requirements.txt:

redis==5.0.1
twilio==8.10.0  # If using Twilio
httpx==0.25.2   # If using MSG91 or custom SMS API
boto3==1.34.7   # If using AWS SNS
"""

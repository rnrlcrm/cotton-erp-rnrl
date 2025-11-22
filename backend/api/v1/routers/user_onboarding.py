"""
User Onboarding API Router

Includes:
- Mobile OTP Authentication
- Profile Management
"""

from fastapi import APIRouter

from backend.modules.user_onboarding.routes.auth_router import router as auth_router

router = APIRouter()

# Include authentication endpoints
router.include_router(auth_router)

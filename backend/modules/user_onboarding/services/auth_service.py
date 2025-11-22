"""
User Authentication Service

Handles user creation, profile completion, and JWT token generation
"""

from datetime import datetime
from typing import Dict, Optional
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.auth.jwt import create_access_token


class UserAuthService:
    """Handle user authentication and profile management"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_or_create_user(self, mobile_number: str) -> Dict:
        """
        Get existing user or create new user
        
        Args:
            mobile_number: User's mobile number
        
        Returns:
            {
                "user_id": UUID,
                "is_new_user": bool,
                "profile_complete": bool,
                "full_name": str or None,
                "email": str or None
            }
        """
        # Import here to avoid circular imports
        from backend.modules.settings.models.settings_models import User
        
        # Try to find existing user by mobile
        query = select(User).where(User.mobile_number == mobile_number)
        result = await self.db.execute(query)
        user = result.scalar_one_or_none()
        
        if user:
            return {
                "user_id": user.id,
                "is_new_user": False,
                "profile_complete": bool(user.full_name and user.email),
                "full_name": user.full_name,
                "email": user.email,
                "role": user.role
            }
        
        # New user - verified mobile but no account yet
        # Return success with indication that onboarding is needed
        # Don't create User record yet - that happens during onboarding
        # when we have business_partner_id to satisfy the constraint
        
        return {
            "user_id": None,  # No user ID yet
            "is_new_user": True,
            "profile_complete": False,
            "full_name": None,
            "email": None,
            "role": None,
            "mobile_number": mobile_number,
            "needs_onboarding": True
        }
    
    async def complete_profile(
        self,
        user_id: UUID,
        full_name: str,
        email: Optional[str] = None
    ):
        """
        Update user profile with name and email
        
        Args:
            user_id: User's ID
            full_name: User's full name
            email: User's email (optional)
        
        Returns:
            Updated user object
        
        Raises:
            HTTPException: If user not found
        """
        from backend.modules.settings.models.settings_models import User
        
        query = select(User).where(User.id == user_id)
        result = await self.db.execute(query)
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        user.full_name = full_name
        if email:
            user.email = email
        user.updated_at = datetime.utcnow()
        
        await self.db.commit()
        await self.db.refresh(user)
        
        return user
    
    async def get_user_by_id(self, user_id: UUID):
        """Get user by ID"""
        from backend.modules.settings.models.settings_models import User
        
        query = select(User).where(User.id == user_id)
        result = await self.db.execute(query)
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        return user
    
    def generate_jwt_token(self, user_id: UUID, mobile_number: str) -> str:
        """
        Generate JWT access token
        
        Args:
            user_id: User's ID
            mobile_number: User's mobile number
        
        Returns:
            JWT access token string
        """
        token_data = {
            "sub": str(user_id),
            "mobile": mobile_number,
            "type": "access"
        }
        
        return create_access_token(token_data)
    
    def determine_next_step(
        self,
        is_new_user: bool,
        profile_complete: bool,
        has_partner_id: bool = False
    ) -> str:
        """
        Determine what the user should do next
        
        Args:
            is_new_user: Is this a new user
            profile_complete: Is profile complete
            has_partner_id: Does user have linked partner
        
        Returns:
            "complete_profile" | "start_onboarding" | "dashboard"
        """
        if is_new_user or not profile_complete:
            return "complete_profile"
        
        if not has_partner_id:
            return "start_onboarding"
        
        return "dashboard"

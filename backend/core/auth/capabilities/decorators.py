"""
Capability Decorators

FastAPI dependencies and decorators for capability-based authorization.
"""

from __future__ import annotations

from functools import wraps
from typing import Callable

from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.auth.capabilities.definitions import Capabilities
from backend.core.auth.capabilities.service import CapabilityService, get_capability_service
from backend.db.async_session import get_db


class RequireCapability:
    """
    FastAPI dependency for requiring specific capabilities.
    
    Usage in routes:
        @router.post("/availability")
        async def create_availability(
            db: AsyncSession = Depends(get_db),
            user: User = Depends(get_current_user),
            _check: None = Depends(RequireCapability(Capabilities.AVAILABILITY_CREATE)),
        ):
            ...
    """
    
    def __init__(self, *capabilities: Capabilities | str):
        """
        Initialize capability requirement.
        
        Args:
            *capabilities: One or more capabilities required (user must have ALL)
        """
        self.capabilities = capabilities
    
    async def __call__(
        self,
        current_user: dict = Depends(lambda: {}),  # Will be replaced with actual get_current_user
        db: AsyncSession = Depends(get_db),
    ) -> None:
        """
        Check if current user has required capabilities.
        
        Special handling for:
        - PUBLIC_ACCESS: Allows unauthenticated access
        - AUTH_LOGIN: Allows unauthenticated access (it's the login endpoint!)
        - AUTH_CREATE_ACCOUNT: Allows unauthenticated access (for signup)
        
        Raises:
            HTTPException: 403 Forbidden if user lacks capability
        """
        # Get capability codes for comparison
        cap_codes = [
            cap.value if isinstance(cap, Capabilities) else cap 
            for cap in self.capabilities
        ]
        
        # Public capabilities that don't require authentication (using enum values only)
        public_capability_values = {
            Capabilities.PUBLIC_ACCESS.value,
            Capabilities.AUTH_LOGIN.value,
            Capabilities.AUTH_CREATE_ACCOUNT.value,
        }
        
        # Check if all requested capabilities are public (don't require auth)
        if all(cap in public_capability_values for cap in cap_codes):
            # Public endpoint - no authentication required
            return
        
        if not current_user or "id" not in current_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated",
            )
        
        user_id = current_user["id"]
        capability_service = CapabilityService(db)
        
        for capability in self.capabilities:
            # Skip public capabilities in the check
            cap_code = capability.value if isinstance(capability, Capabilities) else capability
            if cap_code in public_capability_values:
                continue
                
            has_capability = await capability_service.user_has_capability(
                user_id, capability
            )
            
            if not has_capability:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Missing required capability: {cap_code}",
                )


def require_capability(*capabilities: Capabilities | str):
    """
    Decorator for requiring capabilities on service methods.
    
    Usage in services:
        class AvailabilityService:
            @require_capability(Capabilities.AVAILABILITY_CREATE)
            async def create_availability(self, user_id: UUID, data: dict):
                ...
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract user_id from arguments
            user_id = None
            if "user_id" in kwargs:
                user_id = kwargs["user_id"]
            elif len(args) > 1 and hasattr(args[1], "id"):
                user_id = args[1].id
            
            if not user_id:
                raise ValueError("Cannot determine user_id for capability check")
            
            # Extract session from arguments
            session = None
            if "session" in kwargs:
                session = kwargs["session"]
            elif len(args) > 0 and hasattr(args[0], "session"):
                session = args[0].session
            
            if not session:
                raise ValueError("Cannot determine session for capability check")
            
            # Check capabilities
            capability_service = CapabilityService(session)
            for capability in capabilities:
                has_capability = await capability_service.user_has_capability(
                    user_id, capability
                )
                
                if not has_capability:
                    cap_code = capability.value if isinstance(capability, Capabilities) else capability
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=f"Missing required capability: {cap_code}",
                    )
            
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator


# Convenience function for manual checks
async def check_capability(
    user_id: str,
    capability: Capabilities | str,
    session: AsyncSession,
) -> bool:
    """
    Manually check if a user has a capability.
    
    Usage:
        if await check_capability(user.id, Capabilities.AVAILABILITY_APPROVE, db):
            # User has capability
            ...
    """
    service = CapabilityService(session)
    return await service.user_has_capability(user_id, capability)

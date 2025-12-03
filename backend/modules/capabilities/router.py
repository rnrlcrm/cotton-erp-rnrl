"""
Capability Management API Router

Provides REST API endpoints for:
- Listing all capabilities
- Checking user capabilities
- Granting/revoking capabilities to users
- Granting/revoking capabilities to roles
- Getting user's complete capability set
"""

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.auth.capabilities import (
    Capabilities,
    CapabilityService,
    get_capability_service,
)
from backend.core.auth.capabilities.decorators import RequireCapability
from backend.core.auth.capabilities.models import Capability, RoleCapability, UserCapability
from backend.core.auth.deps import get_current_user
from backend.db.session import get_db
from backend.modules.settings.models.settings_models import User
from backend.modules.capabilities.schemas import (
    CapabilityCheckRequest,
    CapabilityCheckResponse,
    CapabilityListResponse,
    CapabilityResponse,
    GrantCapabilityToRoleRequest,
    GrantCapabilityToUserRequest,
    RevokeCapabilityFromUserRequest,
    RoleCapabilityResponse,
    UserCapabilitiesResponse,
    UserCapabilityResponse,
)

router = APIRouter(prefix="/capabilities", tags=["Capabilities"])


@router.get(
    "",
    response_model=CapabilityListResponse,
    summary="List All Capabilities",
    description="Get complete list of all available capabilities in the system"
)
async def list_capabilities(
    category: Optional[str] = Query(None, description="Filter by category"),
    is_system: Optional[bool] = Query(None, description="Filter by system capabilities"),
    db: AsyncSession = Depends(get_db),
):
    """
    List all capabilities in the system.
    
    Useful for:
    - Admin UI to show available permissions
    - Role management screens
    - User permission assignment
    """
    query = select(Capability)
    
    if category:
        query = query.where(Capability.category == category)
    if is_system is not None:
        query = query.where(Capability.is_system == is_system)
    
    result = await db.execute(query)
    capabilities = result.scalars().all()
    
    return CapabilityListResponse(
        total=len(capabilities),
        capabilities=[CapabilityResponse.model_validate(cap) for cap in capabilities]
    )


@router.get(
    "/users/{user_id}",
    response_model=UserCapabilitiesResponse,
    summary="Get User Capabilities",
    description="Get all capabilities for a specific user (direct + role-based)"
)
@RequireCapability(Capabilities.ADMIN_MANAGE_USERS)
async def get_user_capabilities(
    user_id: UUID,
    capability_service: CapabilityService = Depends(get_capability_service),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get complete capability set for a user.
    
    Returns:
    - All capability codes (as strings)
    - Direct capability assignments
    - Role-based capability assignments
    """
    # Get capability codes
    capability_codes = await capability_service.get_user_capabilities(user_id)
    
    # Get direct capabilities
    direct_query = (
        select(UserCapability)
        .where(UserCapability.user_id == user_id)
        .where(UserCapability.revoked_at.is_(None))
    )
    direct_result = await db.execute(direct_query)
    direct_caps = direct_result.scalars().all()
    
    # Get role capabilities
    from backend.modules.settings.models.settings_models import UserRole
    
    role_query = (
        select(RoleCapability)
        .join(UserRole, UserRole.role_id == RoleCapability.role_id)
        .where(UserRole.user_id == user_id)
    )
    role_result = await db.execute(role_query)
    role_caps = role_result.scalars().all()
    
    return UserCapabilitiesResponse(
        user_id=user_id,
        capabilities=list(capability_codes),
        direct_capabilities=[
            UserCapabilityResponse.model_validate(uc) for uc in direct_caps
        ],
        role_capabilities=[
            RoleCapabilityResponse.model_validate(rc) for rc in role_caps
        ]
    )


@router.post(
    "/users/{user_id}/grant",
    response_model=UserCapabilityResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Grant Capability to User",
    description="Grant a specific capability directly to a user"
)
@RequireCapability(Capabilities.ADMIN_MANAGE_USERS)
async def grant_capability_to_user(
    user_id: UUID,
    request: GrantCapabilityToUserRequest,
    capability_service: CapabilityService = Depends(get_capability_service),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Grant a capability directly to a user.
    
    Use cases:
    - Temporary elevated permissions
    - Special case permissions
    - Emergency access grants
    """
    try:
        user_capability = await capability_service.grant_capability_to_user(
            user_id=user_id,
            capability_code=request.capability_code,
            granted_by=current_user.id,
            expires_at=request.expires_at,
            reason=request.reason,
        )
        
        await db.commit()
        await db.refresh(user_capability)
        
        return UserCapabilityResponse.model_validate(user_capability)
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post(
    "/users/{user_id}/revoke",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Revoke Capability from User",
    description="Revoke a capability that was directly granted to a user"
)
@RequireCapability(Capabilities.ADMIN_MANAGE_USERS)
async def revoke_capability_from_user(
    user_id: UUID,
    request: RevokeCapabilityFromUserRequest,
    capability_service: CapabilityService = Depends(get_capability_service),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Revoke a capability from a user.
    
    Note: This only revokes direct capability grants.
    If user has capability via role, they will keep it until removed from role.
    """
    await capability_service.revoke_capability_from_user(
        user_id=user_id,
        capability_code=request.capability_code,
        revoked_by=current_user.id,
        reason=request.reason,
    )
    
    await db.commit()


@router.post(
    "/users/{user_id}/check",
    response_model=CapabilityCheckResponse,
    summary="Check User Capability",
    description="Check if a user has a specific capability"
)
@RequireCapability(Capabilities.ADMIN_MANAGE_USERS)
async def check_user_capability(
    user_id: UUID,
    request: CapabilityCheckRequest,
    capability_service: CapabilityService = Depends(get_capability_service),
    current_user: User = Depends(get_current_user),
):
    """
    Check if user has a specific capability.
    
    Useful for:
    - Admin UI to show what user can do
    - Debugging permission issues
    - Audit trails
    """
    has_capability = await capability_service.user_has_capability(
        user_id=user_id,
        capability_code=request.capability_code,
    )
    
    return CapabilityCheckResponse(
        user_id=user_id,
        capability_code=request.capability_code,
        has_capability=has_capability,
    )


@router.get(
    "/me",
    response_model=UserCapabilitiesResponse,
    summary="Get My Capabilities",
    description="Get all capabilities for the currently authenticated user"
)
async def get_my_capabilities(
    capability_service: CapabilityService = Depends(get_capability_service),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get your own capabilities.
    
    Mobile/web apps use this to:
    - Show/hide UI elements based on permissions
    - Enable/disable features
    - Sync capabilities to local storage
    """
    # Get capability codes
    capability_codes = await capability_service.get_user_capabilities(current_user.id)
    
    # Get direct capabilities
    direct_query = (
        select(UserCapability)
        .where(UserCapability.user_id == current_user.id)
        .where(UserCapability.revoked_at.is_(None))
    )
    direct_result = await db.execute(direct_query)
    direct_caps = direct_result.scalars().all()
    
    # Get role capabilities
    from backend.modules.settings.models.settings_models import UserRole
    
    role_query = (
        select(RoleCapability)
        .join(UserRole, UserRole.role_id == RoleCapability.role_id)
        .where(UserRole.user_id == current_user.id)
    )
    role_result = await db.execute(role_query)
    role_caps = role_result.scalars().all()
    
    return UserCapabilitiesResponse(
        user_id=current_user.id,
        capabilities=list(capability_codes),
        direct_capabilities=[
            UserCapabilityResponse.model_validate(uc) for uc in direct_caps
        ],
        role_capabilities=[
            RoleCapabilityResponse.model_validate(rc) for rc in role_caps
        ]
    )


@router.post(
    "/roles/{role_id}/grant",
    response_model=RoleCapabilityResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Grant Capability to Role",
    description="Grant a capability to a role (all users with this role inherit it)"
)
@RequireCapability(Capabilities.ADMIN_MANAGE_ROLES)
async def grant_capability_to_role(
    role_id: UUID,
    request: GrantCapabilityToRoleRequest,
    capability_service: CapabilityService = Depends(get_capability_service),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Grant a capability to a role.
    
    All users assigned to this role will inherit this capability.
    
    Use cases:
    - Define "Trader" role with all trade-related capabilities
    - Define "Approver" role with approval capabilities
    - Define "Viewer" role with read-only capabilities
    """
    try:
        role_capability = await capability_service.grant_capability_to_role(
            role_id=role_id,
            capability_code=request.capability_code,
            granted_by=current_user.id,
        )
        
        await db.commit()
        await db.refresh(role_capability)
        
        return RoleCapabilityResponse.model_validate(role_capability)
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.delete(
    "/roles/{role_id}/capabilities/{capability_code}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Revoke Capability from Role",
    description="Revoke a capability from a role (users with this role lose this capability)"
)
@RequireCapability(Capabilities.ADMIN_MANAGE_ROLES)
async def revoke_capability_from_role(
    role_id: UUID,
    capability_code: str,
    capability_service: CapabilityService = Depends(get_capability_service),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Revoke a capability from a role.
    
    All users with this role will lose this capability
    (unless they have it via direct grant or another role).
    """
    await capability_service.revoke_capability_from_role(
        role_id=role_id,
        capability_code=capability_code,
    )
    
    await db.commit()


@router.get(
    "/roles/{role_id}",
    response_model=List[RoleCapabilityResponse],
    summary="Get Role Capabilities",
    description="Get all capabilities assigned to a specific role"
)
@RequireCapability(Capabilities.ADMIN_MANAGE_ROLES)
async def get_role_capabilities(
    role_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get all capabilities for a role.
    
    Useful for role management UI.
    """
    query = select(RoleCapability).where(RoleCapability.role_id == role_id)
    result = await db.execute(query)
    role_caps = result.scalars().all()
    
    return [RoleCapabilityResponse.model_validate(rc) for rc in role_caps]

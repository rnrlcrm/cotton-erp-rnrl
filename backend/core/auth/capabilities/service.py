"""
Capability Service

Business logic for checking and managing capabilities.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import List, Optional, Set

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.auth.capabilities.definitions import Capabilities
from backend.core.auth.capabilities.models import Capability, RoleCapability, UserCapability


class CapabilityService:
    """
    Service for capability-based authorization.
    
    Provides methods to:
    - Check if user has specific capability
    - Grant/revoke capabilities to users
    - Grant/revoke capabilities to roles
    - Get all capabilities for a user
    """
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def user_has_capability(
        self,
        user_id: uuid.UUID,
        capability_code: str | Capabilities,
    ) -> bool:
        """
        Check if a user has a specific capability.
        
        Checks both:
        1. Direct user capabilities
        2. Inherited role capabilities
        
        Args:
            user_id: User ID to check
            capability_code: Capability code (e.g., "AVAILABILITY_CREATE")
        
        Returns:
            True if user has the capability, False otherwise
        """
        if isinstance(capability_code, Capabilities):
            capability_code = capability_code.value
        
        # Get capability ID
        capability = await self._get_capability_by_code(capability_code)
        if not capability:
            return False
        
        # Check direct user capability
        user_cap_query = select(UserCapability).where(
            and_(
                UserCapability.user_id == user_id,
                UserCapability.capability_id == capability.id,
                UserCapability.revoked_at.is_(None),
                or_(
                    UserCapability.expires_at.is_(None),
                    UserCapability.expires_at > datetime.utcnow()
                )
            )
        )
        result = await self.session.execute(user_cap_query)
        if result.scalar_one_or_none():
            return True
        
        # Check role-based capability
        # Get user's roles
        from backend.modules.auth.models import User, UserRole
        
        user_roles_query = select(UserRole.role_id).where(UserRole.user_id == user_id)
        role_ids_result = await self.session.execute(user_roles_query)
        role_ids = [row[0] for row in role_ids_result.fetchall()]
        
        if not role_ids:
            return False
        
        # Check if any role has the capability
        role_cap_query = select(RoleCapability).where(
            and_(
                RoleCapability.role_id.in_(role_ids),
                RoleCapability.capability_id == capability.id,
            )
        )
        result = await self.session.execute(role_cap_query)
        return result.scalar_one_or_none() is not None
    
    async def get_user_capabilities(self, user_id: uuid.UUID) -> Set[str]:
        """
        Get all capabilities for a user (direct + inherited from roles).
        
        Returns:
            Set of capability codes
        """
        capabilities = set()
        
        # Get direct capabilities
        direct_query = (
            select(Capability.code)
            .join(UserCapability)
            .where(
                and_(
                    UserCapability.user_id == user_id,
                    UserCapability.revoked_at.is_(None),
                    or_(
                        UserCapability.expires_at.is_(None),
                        UserCapability.expires_at > datetime.utcnow()
                    )
                )
            )
        )
        direct_result = await self.session.execute(direct_query)
        capabilities.update(row[0] for row in direct_result.fetchall())
        
        # Get role-based capabilities
        from backend.modules.auth.models import UserRole
        
        role_query = (
            select(Capability.code)
            .join(RoleCapability)
            .join(UserRole, UserRole.role_id == RoleCapability.role_id)
            .where(UserRole.user_id == user_id)
        )
        role_result = await self.session.execute(role_query)
        capabilities.update(row[0] for row in role_result.fetchall())
        
        return capabilities
    
    async def grant_capability_to_user(
        self,
        user_id: uuid.UUID,
        capability_code: str | Capabilities,
        granted_by: uuid.UUID,
        expires_at: Optional[datetime] = None,
        reason: Optional[str] = None,
    ) -> UserCapability:
        """
        Grant a capability directly to a user.
        
        Args:
            user_id: User to grant capability to
            capability_code: Capability to grant
            granted_by: User ID of the granter
            expires_at: Optional expiration date for temporal capabilities
            reason: Optional reason for granting
        
        Returns:
            UserCapability record
        """
        if isinstance(capability_code, Capabilities):
            capability_code = capability_code.value
        
        capability = await self._get_capability_by_code(capability_code)
        if not capability:
            raise ValueError(f"Capability {capability_code} not found")
        
        # Check if already exists
        existing_query = select(UserCapability).where(
            and_(
                UserCapability.user_id == user_id,
                UserCapability.capability_id == capability.id,
            )
        )
        result = await self.session.execute(existing_query)
        existing = result.scalar_one_or_none()
        
        if existing:
            # Update existing
            existing.revoked_at = None
            existing.expires_at = expires_at
            existing.granted_by = granted_by
            existing.reason = reason
            await self.session.flush()
            return existing
        
        # Create new
        user_capability = UserCapability(
            user_id=user_id,
            capability_id=capability.id,
            granted_by=granted_by,
            expires_at=expires_at,
            reason=reason,
        )
        
        self.session.add(user_capability)
        await self.session.flush()
        await self.session.refresh(user_capability)
        
        return user_capability
    
    async def revoke_capability_from_user(
        self,
        user_id: uuid.UUID,
        capability_code: str | Capabilities,
    ) -> None:
        """Revoke a capability from a user"""
        if isinstance(capability_code, Capabilities):
            capability_code = capability_code.value
        
        capability = await self._get_capability_by_code(capability_code)
        if not capability:
            return
        
        query = select(UserCapability).where(
            and_(
                UserCapability.user_id == user_id,
                UserCapability.capability_id == capability.id,
            )
        )
        result = await self.session.execute(query)
        user_capability = result.scalar_one_or_none()
        
        if user_capability:
            user_capability.revoked_at = datetime.utcnow()
            await self.session.flush()
    
    async def grant_capability_to_role(
        self,
        role_id: uuid.UUID,
        capability_code: str | Capabilities,
        granted_by: uuid.UUID,
    ) -> RoleCapability:
        """Grant a capability to a role"""
        if isinstance(capability_code, Capabilities):
            capability_code = capability_code.value
        
        capability = await self._get_capability_by_code(capability_code)
        if not capability:
            raise ValueError(f"Capability {capability_code} not found")
        
        # Check if already exists
        existing_query = select(RoleCapability).where(
            and_(
                RoleCapability.role_id == role_id,
                RoleCapability.capability_id == capability.id,
            )
        )
        result = await self.session.execute(existing_query)
        if result.scalar_one_or_none():
            return result.scalar_one()
        
        # Create new
        role_capability = RoleCapability(
            role_id=role_id,
            capability_id=capability.id,
            granted_by=granted_by,
        )
        
        self.session.add(role_capability)
        await self.session.flush()
        await self.session.refresh(role_capability)
        
        return role_capability
    
    async def revoke_capability_from_role(
        self,
        role_id: uuid.UUID,
        capability_code: str | Capabilities,
    ) -> None:
        """Revoke a capability from a role"""
        if isinstance(capability_code, Capabilities):
            capability_code = capability_code.value
        
        capability = await self._get_capability_by_code(capability_code)
        if not capability:
            return
        
        query = select(RoleCapability).where(
            and_(
                RoleCapability.role_id == role_id,
                RoleCapability.capability_id == capability.id,
            )
        )
        result = await self.session.execute(query)
        role_capability = result.scalar_one_or_none()
        
        if role_capability:
            await self.session.delete(role_capability)
            await self.session.flush()
    
    async def _get_capability_by_code(self, code: str) -> Optional[Capability]:
        """Helper to get capability by code"""
        query = select(Capability).where(Capability.code == code)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()


# Dependency injection
async def get_capability_service(session: AsyncSession) -> CapabilityService:
    """FastAPI dependency for capability service"""
    return CapabilityService(session)

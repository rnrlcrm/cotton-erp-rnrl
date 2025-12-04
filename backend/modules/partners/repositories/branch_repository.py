"""
Partner Branch Repository - Multi-Location Data Access Layer

Features:
- CRUD operations for partner branches
- Query by capabilities (ship-to, ship-from, warehouse)
- Geolocation-based distance queries for AI suggestions
- Capacity availability checking
- Default branch management

Architecture:
- AsyncSession for high concurrency
- EventMixin integration for event-driven updates
- Geo-spatial support for distance calculations
- JSONB queries for commodity filtering
"""

from __future__ import annotations

from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from sqlalchemy import and_, desc, func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from backend.modules.partners.models import PartnerBranch


class BranchRepository:
    """
    Repository for Partner Branch management.
    
    Handles multi-location support for AI branch suggestions.
    """
    
    def __init__(self, db: AsyncSession):
        """
        Initialize repository.
        
        Args:
            db: Async SQLAlchemy session
        """
        self.db = db
    
    # ========================
    # Basic CRUD Operations
    # ========================
    
    async def get_by_id(
        self,
        branch_id: UUID,
        load_relationships: bool = False
    ) -> Optional[PartnerBranch]:
        """
        Get branch by ID.
        
        Args:
            branch_id: Branch UUID
            load_relationships: If True, eager load partner
        
        Returns:
            Branch if found, None otherwise
        """
        query = select(PartnerBranch).where(
            and_(
                PartnerBranch.id == branch_id,
                PartnerBranch.is_active == True  # noqa: E712
            )
        )
        
        if load_relationships:
            query = query.options(joinedload(PartnerBranch.partner))
        
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def get_by_partner(
        self,
        partner_id: UUID,
        is_active: bool = True
    ) -> List[PartnerBranch]:
        """
        Get all branches for a partner.
        
        Args:
            partner_id: Business partner UUID
            is_active: Filter by active status
        
        Returns:
            List of branches
        """
        query = select(PartnerBranch).where(
            and_(
                PartnerBranch.partner_id == partner_id,
                PartnerBranch.is_active == is_active
            )
        )
        
        query = query.order_by(PartnerBranch.is_head_office.desc())
        query = query.order_by(PartnerBranch.branch_code)
        
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def get_by_code(
        self,
        partner_id: UUID,
        branch_code: str
    ) -> Optional[PartnerBranch]:
        """
        Get branch by code (unique within partner).
        
        Args:
            partner_id: Business partner UUID
            branch_code: Branch code (e.g., 'HO', 'WH-01')
        
        Returns:
            Branch if found, None otherwise
        """
        query = select(PartnerBranch).where(
            and_(
                PartnerBranch.partner_id == partner_id,
                PartnerBranch.branch_code == branch_code,
                PartnerBranch.is_active == True  # noqa: E712
            )
        )
        
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def create(self, branch: PartnerBranch) -> PartnerBranch:
        """
        Create new branch.
        
        Args:
            branch: Branch model instance
        
        Returns:
            Created branch
        """
        self.db.add(branch)
        await self.db.flush()
        await self.db.refresh(branch)
        return branch
    
    async def update(self, branch: PartnerBranch) -> PartnerBranch:
        """
        Update branch (already modified in-memory).
        
        Args:
            branch: Modified branch instance
        
        Returns:
            Updated branch
        """
        await self.db.flush()
        await self.db.refresh(branch)
        return branch
    
    async def delete(self, branch: PartnerBranch) -> None:
        """
        Soft delete branch (set is_active = False).
        
        Args:
            branch: Branch to delete
        """
        branch.is_active = False
        await self.db.flush()
    
    # ========================
    # Capability Queries
    # ========================
    
    async def get_ship_to_branches(
        self,
        partner_id: UUID,
        commodity_code: Optional[str] = None,
        required_capacity_qtls: Optional[int] = None
    ) -> List[PartnerBranch]:
        """
        Get branches that can receive shipments (ship-to).
        
        Args:
            partner_id: Business partner UUID
            commodity_code: Optional filter by commodity support
            required_capacity_qtls: Optional filter by available capacity
        
        Returns:
            List of ship-to branches
        """
        conditions = [
            PartnerBranch.partner_id == partner_id,
            PartnerBranch.can_receive_shipments == True,  # noqa: E712
            PartnerBranch.is_active == True  # noqa: E712
        ]
        
        if commodity_code:
            # JSONB array contains check
            conditions.append(
                or_(
                    PartnerBranch.supported_commodities.is_(None),
                    PartnerBranch.supported_commodities.contains([commodity_code])
                )
            )
        
        if required_capacity_qtls:
            # Available capacity check
            conditions.append(
                or_(
                    PartnerBranch.warehouse_capacity_qtls.is_(None),
                    (
                        PartnerBranch.warehouse_capacity_qtls - 
                        func.coalesce(PartnerBranch.current_stock_qtls, 0)
                    ) >= required_capacity_qtls
                )
            )
        
        query = select(PartnerBranch).where(and_(*conditions))
        query = query.order_by(PartnerBranch.is_default_ship_to.desc())
        
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def get_ship_from_branches(
        self,
        partner_id: UUID,
        commodity_code: Optional[str] = None
    ) -> List[PartnerBranch]:
        """
        Get branches that can send shipments (ship-from).
        
        Args:
            partner_id: Business partner UUID
            commodity_code: Optional filter by commodity support
        
        Returns:
            List of ship-from branches
        """
        conditions = [
            PartnerBranch.partner_id == partner_id,
            PartnerBranch.can_send_shipments == True,  # noqa: E712
            PartnerBranch.is_active == True  # noqa: E712
        ]
        
        if commodity_code:
            conditions.append(
                or_(
                    PartnerBranch.supported_commodities.is_(None),
                    PartnerBranch.supported_commodities.contains([commodity_code])
                )
            )
        
        query = select(PartnerBranch).where(and_(*conditions))
        query = query.order_by(PartnerBranch.is_default_ship_from.desc())
        
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def get_head_office(
        self,
        partner_id: UUID
    ) -> Optional[PartnerBranch]:
        """
        Get head office branch (default bill-to).
        
        Args:
            partner_id: Business partner UUID
        
        Returns:
            Head office branch if exists
        """
        query = select(PartnerBranch).where(
            and_(
                PartnerBranch.partner_id == partner_id,
                PartnerBranch.is_head_office == True,  # noqa: E712
                PartnerBranch.is_active == True  # noqa: E712
            )
        )
        
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    # ========================
    # Default Branch Management
    # ========================
    
    async def get_default_ship_to(
        self,
        partner_id: UUID
    ) -> Optional[PartnerBranch]:
        """
        Get default ship-to branch.
        
        Args:
            partner_id: Business partner UUID
        
        Returns:
            Default ship-to branch if set
        """
        query = select(PartnerBranch).where(
            and_(
                PartnerBranch.partner_id == partner_id,
                PartnerBranch.is_default_ship_to == True,  # noqa: E712
                PartnerBranch.is_active == True  # noqa: E712
            )
        )
        
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def get_default_ship_from(
        self,
        partner_id: UUID
    ) -> Optional[PartnerBranch]:
        """
        Get default ship-from branch.
        
        Args:
            partner_id: Business partner UUID
        
        Returns:
            Default ship-from branch if set
        """
        query = select(PartnerBranch).where(
            and_(
                PartnerBranch.partner_id == partner_id,
                PartnerBranch.is_default_ship_from == True,  # noqa: E712
                PartnerBranch.is_active == True  # noqa: E712
            )
        )
        
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def set_default_ship_to(
        self,
        partner_id: UUID,
        branch_id: UUID
    ) -> None:
        """
        Set default ship-to branch (unset others).
        
        Args:
            partner_id: Business partner UUID
            branch_id: Branch to set as default
        """
        # Unset all current defaults
        await self.db.execute(
            text(
                "UPDATE partner_branches SET is_default_ship_to = FALSE "
                "WHERE partner_id = :partner_id"
            ).bindparams(partner_id=partner_id)
        )
        
        # Set new default
        await self.db.execute(
            text(
                "UPDATE partner_branches SET is_default_ship_to = TRUE "
                "WHERE id = :branch_id"
            ).bindparams(branch_id=branch_id)
        )
    
    async def set_default_ship_from(
        self,
        partner_id: UUID,
        branch_id: UUID
    ) -> None:
        """
        Set default ship-from branch (unset others).
        
        Args:
            partner_id: Business partner UUID
            branch_id: Branch to set as default
        """
        # Unset all current defaults
        await self.db.execute(
            text(
                "UPDATE partner_branches SET is_default_ship_from = FALSE "
                "WHERE partner_id = :partner_id"
            ).bindparams(partner_id=partner_id)
        )
        
        # Set new default
        await self.db.execute(
            text(
                "UPDATE partner_branches SET is_default_ship_from = TRUE "
                "WHERE id = :branch_id"
            ).bindparams(branch_id=branch_id)
        )
    
    # ========================
    # Geo-Spatial Queries (For AI Branch Suggestion)
    # ========================
    
    async def get_branches_by_state(
        self,
        partner_id: UUID,
        state: str,
        capability: str = "ship_to"  # or "ship_from"
    ) -> List[PartnerBranch]:
        """
        Get branches in same state (for GST optimization).
        
        Args:
            partner_id: Business partner UUID
            state: State name
            capability: 'ship_to' or 'ship_from'
        
        Returns:
            List of branches in state
        """
        conditions = [
            PartnerBranch.partner_id == partner_id,
            PartnerBranch.state == state,
            PartnerBranch.is_active == True  # noqa: E712
        ]
        
        if capability == "ship_to":
            conditions.append(PartnerBranch.can_receive_shipments == True)  # noqa: E712
        else:
            conditions.append(PartnerBranch.can_send_shipments == True)  # noqa: E712
        
        query = select(PartnerBranch).where(and_(*conditions))
        
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def calculate_distance(
        self,
        branch_id: UUID,
        target_lat: Decimal,
        target_long: Decimal
    ) -> Optional[float]:
        """
        Calculate distance between branch and target location.
        
        Uses Haversine formula for great-circle distance.
        
        Args:
            branch_id: Branch UUID
            target_lat: Target latitude
            target_long: Target longitude
        
        Returns:
            Distance in kilometers, None if branch has no coordinates
        """
        branch = await self.get_by_id(branch_id)
        
        if not branch or not branch.latitude or not branch.longitude:
            return None
        
        # Haversine formula (simplified)
        # In production, use PostGIS extension for accurate calculations
        query = select(
            func.acos(
                func.sin(func.radians(branch.latitude)) * func.sin(func.radians(target_lat)) +
                func.cos(func.radians(branch.latitude)) * func.cos(func.radians(target_lat)) *
                func.cos(func.radians(target_long) - func.radians(branch.longitude))
            ) * 6371  # Earth radius in km
        )
        
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    # ========================
    # Capacity Management
    # ========================
    
    async def update_stock(
        self,
        branch_id: UUID,
        quantity_delta: int
    ) -> PartnerBranch:
        """
        Update current stock level.
        
        Args:
            branch_id: Branch UUID
            quantity_delta: Change in stock (positive = increase, negative = decrease)
        
        Returns:
            Updated branch
        """
        branch = await self.get_by_id(branch_id)
        
        if branch:
            current = branch.current_stock_qtls or 0
            branch.current_stock_qtls = current + quantity_delta
            await self.db.flush()
            await self.db.refresh(branch)
        
        return branch
    
    async def get_available_capacity(
        self,
        branch_id: UUID
    ) -> Optional[int]:
        """
        Get available warehouse capacity.
        
        Args:
            branch_id: Branch UUID
        
        Returns:
            Available capacity in quintals, None if no limit
        """
        branch = await self.get_by_id(branch_id)
        
        if not branch or not branch.warehouse_capacity_qtls:
            return None
        
        current = branch.current_stock_qtls or 0
        return branch.warehouse_capacity_qtls - current

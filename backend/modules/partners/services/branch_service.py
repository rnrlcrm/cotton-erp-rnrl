"""
Branch Service - Multi-Location Management for Partners

Handles:
1. Branch CRUD (create, update, delete branches)
2. Default branch management
3. Capability validation (ship-to, ship-from)
4. Stock tracking updates
5. Branch queries for trade creation

Architecture:
- Validates branch capabilities
- Manages defaults (one per partner)
- Updates stock levels from inventory module
"""

from typing import List, Optional, Dict, Any
from uuid import UUID
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from backend.modules.partners.repositories.branch_repository import BranchRepository
from backend.modules.partners.models import PartnerBranch
from backend.core.errors.exceptions import (
    NotFoundException,
    ValidationException,
    BusinessRuleException
)


class BranchService:
    """
    Partner Branch management business logic.
    """
    
    def __init__(
        self,
        db: AsyncSession,
        branch_repo: BranchRepository
    ):
        self.db = db
        self.branch_repo = branch_repo
    
    # ========================================================================
    # CRUD OPERATIONS
    # ========================================================================
    
    async def create_branch(
        self,
        partner_id: UUID,
        branch_code: str,
        branch_name: str,
        address_data: Dict[str, Any],
        capabilities: Dict[str, Any],
        user_id: UUID
    ) -> PartnerBranch:
        """
        Create new branch for partner.
        
        Args:
            partner_id: Business partner UUID
            branch_code: Unique code within partner (e.g., 'HO', 'WH-01')
            branch_name: Display name
            address_data: Address fields
            capabilities: Capability flags and limits
            user_id: User creating
        
        Returns:
            Created branch
        """
        # Check branch code unique within partner
        existing = await self.branch_repo.get_by_code(partner_id, branch_code)
        if existing:
            raise BusinessRuleException(
                f"Branch code '{branch_code}' already exists for this partner"
            )
        
        # Create branch
        branch = PartnerBranch(
            partner_id=partner_id,
            branch_code=branch_code,
            branch_name=branch_name,
            branch_type=capabilities.get('branch_type'),
            
            # Address
            address_line_1=address_data['address_line_1'],
            address_line_2=address_data.get('address_line_2'),
            city=address_data['city'],
            state=address_data['state'],
            postal_code=address_data['postal_code'],
            country=address_data.get('country', 'India'),
            latitude=address_data.get('latitude'),
            longitude=address_data.get('longitude'),
            gstin=address_data.get('gstin'),
            
            # Capabilities
            can_receive_shipments=capabilities.get('can_receive_shipments', False),
            can_send_shipments=capabilities.get('can_send_shipments', False),
            warehouse_capacity_qtls=capabilities.get('warehouse_capacity_qtls'),
            supported_commodities=capabilities.get('supported_commodities'),
            
            # Flags
            is_head_office=capabilities.get('is_head_office', False),
            is_default_ship_to=capabilities.get('is_default_ship_to', False),
            is_default_ship_from=capabilities.get('is_default_ship_from', False),
            is_active=True,
            
            created_by=user_id
        )
        
        branch = await self.branch_repo.create(branch)
        
        # If set as default, unset others
        if branch.is_default_ship_to:
            await self.branch_repo.set_default_ship_to(partner_id, branch.id)
        
        if branch.is_default_ship_from:
            await self.branch_repo.set_default_ship_from(partner_id, branch.id)
        
        await self.db.commit()
        
        return branch
    
    async def update_branch(
        self,
        branch_id: UUID,
        update_data: Dict[str, Any],
        user_id: UUID
    ) -> PartnerBranch:
        """
        Update branch details.
        
        Args:
            branch_id: Branch UUID
            update_data: Fields to update
            user_id: User updating
        
        Returns:
            Updated branch
        """
        branch = await self.branch_repo.get_by_id(branch_id)
        
        if not branch:
            raise NotFoundException(f"Branch {branch_id} not found")
        
        # Update allowed fields
        if 'branch_name' in update_data:
            branch.branch_name = update_data['branch_name']
        
        if 'address_line_1' in update_data:
            branch.address_line_1 = update_data['address_line_1']
        
        if 'address_line_2' in update_data:
            branch.address_line_2 = update_data['address_line_2']
        
        if 'city' in update_data:
            branch.city = update_data['city']
        
        if 'state' in update_data:
            branch.state = update_data['state']
        
        if 'postal_code' in update_data:
            branch.postal_code = update_data['postal_code']
        
        if 'latitude' in update_data:
            branch.latitude = update_data['latitude']
        
        if 'longitude' in update_data:
            branch.longitude = update_data['longitude']
        
        if 'can_receive_shipments' in update_data:
            branch.can_receive_shipments = update_data['can_receive_shipments']
        
        if 'can_send_shipments' in update_data:
            branch.can_send_shipments = update_data['can_send_shipments']
        
        if 'warehouse_capacity_qtls' in update_data:
            branch.warehouse_capacity_qtls = update_data['warehouse_capacity_qtls']
        
        if 'supported_commodities' in update_data:
            branch.supported_commodities = update_data['supported_commodities']
        
        branch = await self.branch_repo.update(branch)
        await self.db.commit()
        
        return branch
    
    async def delete_branch(
        self,
        branch_id: UUID,
        user_id: UUID
    ) -> None:
        """
        Soft delete branch (set inactive).
        
        Args:
            branch_id: Branch UUID
            user_id: User deleting
        """
        branch = await self.branch_repo.get_by_id(branch_id)
        
        if not branch:
            raise NotFoundException(f"Branch {branch_id} not found")
        
        # Don't allow deleting head office if it's the only branch
        if branch.is_head_office:
            all_branches = await self.branch_repo.get_by_partner(branch.partner_id)
            if len(all_branches) == 1:
                raise BusinessRuleException(
                    "Cannot delete the only branch for this partner"
                )
        
        await self.branch_repo.delete(branch)
        await self.db.commit()
    
    # ========================================================================
    # DEFAULT MANAGEMENT
    # ========================================================================
    
    async def set_default_ship_to(
        self,
        partner_id: UUID,
        branch_id: UUID
    ) -> None:
        """Set default ship-to branch (unset others)."""
        await self.branch_repo.set_default_ship_to(partner_id, branch_id)
        await self.db.commit()
    
    async def set_default_ship_from(
        self,
        partner_id: UUID,
        branch_id: UUID
    ) -> None:
        """Set default ship-from branch (unset others)."""
        await self.branch_repo.set_default_ship_from(partner_id, branch_id)
        await self.db.commit()
    
    # ========================================================================
    # STOCK MANAGEMENT (Called by Inventory Module)
    # ========================================================================
    
    async def update_stock_level(
        self,
        branch_id: UUID,
        quantity_delta: int
    ) -> PartnerBranch:
        """
        Update current stock (called when inventory changes).
        
        Args:
            branch_id: Branch UUID
            quantity_delta: Change in stock (+ increase, - decrease)
        
        Returns:
            Updated branch
        """
        branch = await self.branch_repo.update_stock(branch_id, quantity_delta)
        await self.db.commit()
        return branch
    
    # ========================================================================
    # QUERIES
    # ========================================================================
    
    async def get_branch_by_id(
        self,
        branch_id: UUID,
        load_relationships: bool = False
    ) -> Optional[PartnerBranch]:
        """Get branch by ID."""
        return await self.branch_repo.get_by_id(branch_id, load_relationships)
    
    async def get_branches_by_partner(
        self,
        partner_id: UUID,
        is_active: bool = True
    ) -> List[PartnerBranch]:
        """Get all branches for partner."""
        return await self.branch_repo.get_by_partner(partner_id, is_active)
    
    async def get_ship_to_branches(
        self,
        partner_id: UUID,
        commodity_code: Optional[str] = None,
        required_capacity_qtls: Optional[int] = None
    ) -> List[PartnerBranch]:
        """Get branches that can receive shipments."""
        return await self.branch_repo.get_ship_to_branches(
            partner_id, commodity_code, required_capacity_qtls
        )
    
    async def get_ship_from_branches(
        self,
        partner_id: UUID,
        commodity_code: Optional[str] = None
    ) -> List[PartnerBranch]:
        """Get branches that can send shipments."""
        return await self.branch_repo.get_ship_from_branches(
            partner_id, commodity_code
        )

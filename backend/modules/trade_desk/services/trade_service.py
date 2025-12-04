"""
Trade Service - Complete Business Logic for Instant Contract Creation

Handles:
1. Accept negotiation → Create instant binding contract
2. Branch selection (AI suggestion or user override)
3. Address freezing (immutable JSONB snapshots)
4. GST calculation (INTRA_STATE vs INTER_STATE)
5. Contract document generation coordination
6. Trade lifecycle management

Flow:
- Negotiation accepted → Trade ACTIVE immediately (with disclaimer)
- Signature pre-validated (exists in business_partners)
- Branches auto-selected OR user prompted
- Addresses frozen at contract time
- PDF generated async (5-10 seconds)
- Legally binding from acceptance moment

NO business logic in routes - all orchestration here.
"""

from datetime import datetime, date, timezone
from decimal import Decimal
from typing import List, Optional, Dict, Any, Tuple
from uuid import UUID

from sqlalchemy import select, and_, or_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.modules.trade_desk.models.trade import Trade
from backend.modules.trade_desk.models.negotiation import Negotiation
from backend.modules.trade_desk.repositories.trade_repository import TradeRepository
from backend.modules.partners.repositories.branch_repository import BranchRepository
from backend.modules.partners.models import PartnerBranch, BusinessPartner
from backend.core.errors.exceptions import (
    NotFoundException,
    ValidationError,
    BusinessRuleException
)


class TradeService:
    """
    Trade Engine business logic - Instant binding contracts.
    
    Architecture:
    - Creates trades immediately on negotiation acceptance
    - Validates signatures exist before allowing trade
    - Auto-selects branches or prompts user
    - Freezes addresses as JSONB snapshots
    - Emits events for PDF generation (async)
    """
    
    def __init__(
        self,
        db: AsyncSession,
        trade_repo: TradeRepository,
        branch_repo: BranchRepository
    ):
        self.db = db
        self.trade_repo = trade_repo
        self.branch_repo = branch_repo
    
    # ========================================================================
    # INSTANT CONTRACT CREATION (Core Feature)
    # ========================================================================
    
    async def create_trade_from_negotiation(
        self,
        negotiation_id: UUID,
        user_id: UUID,
        branch_selections: Optional[Dict[str, UUID]] = None
    ) -> Trade:
        """
        Create instant binding contract from accepted negotiation.
        
        This is called when user accepts negotiation with disclaimer.
        
        Flow:
        1. Validate negotiation is ACCEPTED
        2. Check signatures exist for both parties
        3. Auto-select branches OR use user selections
        4. Freeze addresses as JSONB snapshots
        5. Calculate GST (INTRA_STATE vs INTER_STATE)
        6. Generate trade number (TR-2025-00001)
        7. Create Trade record with status ACTIVE
        8. Emit trade.created event (triggers PDF generation)
        9. Update negotiation.accepted_at timestamp
        
        Args:
            negotiation_id: Negotiation UUID
            user_id: User creating trade
            branch_selections: Optional dict with keys:
                - 'buyer_ship_to_branch_id': UUID
                - 'buyer_bill_to_branch_id': UUID
                - 'seller_ship_from_branch_id': UUID
        
        Returns:
            Trade: Created trade (ACTIVE status, legally binding)
        
        Raises:
            NotFoundException: Negotiation not found
            BusinessRuleException: Negotiation not accepted, signatures missing
            ValidationError: Invalid branch selections
        """
        # Load negotiation with all relationships
        stmt = select(Negotiation).where(
            Negotiation.id == negotiation_id
        ).options(
            selectinload(Negotiation.buyer_partner),
            selectinload(Negotiation.seller_partner),
            selectinload(Negotiation.requirement),
            selectinload(Negotiation.availability),
        )
        result = await self.db.execute(stmt)
        negotiation = result.scalar_one_or_none()
        
        if not negotiation:
            raise NotFoundException(f"Negotiation {negotiation_id} not found")
        
        # Validate negotiation is accepted
        if negotiation.status != "ACCEPTED":
            raise BusinessRuleException(
                f"Negotiation must be ACCEPTED to create trade (current: {negotiation.status})"
            )
        
        # Check if trade already exists
        existing = await self.trade_repo.get_by_negotiation(negotiation_id)
        if existing:
            raise BusinessRuleException(
                f"Trade already exists for negotiation: {existing.trade_number}"
            )
        
        # Validate signatures exist (critical!)
        await self._validate_signatures_exist(
            negotiation.buyer_partner_id,
            negotiation.seller_partner_id
        )
        
        # Select branches (auto or user override)
        branch_config = await self._select_branches(
            buyer_partner_id=negotiation.buyer_partner_id,
            seller_partner_id=negotiation.seller_partner_id,
            commodity_code=negotiation.requirement.commodity_code,
            quantity_qtls=int(negotiation.final_quantity or negotiation.current_quantity),
            user_selections=branch_selections
        )
        
        # Freeze addresses as immutable snapshots
        addresses = await self._freeze_addresses(branch_config)
        
        # Calculate GST type
        gst_details = self._calculate_gst(
            buyer_state=addresses['bill_to']['state'],
            seller_state=addresses['ship_from']['state'],
            base_amount=negotiation.final_total_amount or Decimal('0')
        )
        
        # Generate unique trade number
        trade_number = await self.trade_repo.generate_trade_number()
        
        # Create trade record
        trade = Trade(
            trade_number=trade_number,
            negotiation_id=negotiation.id,
            buyer_partner_id=negotiation.buyer_partner_id,
            seller_partner_id=negotiation.seller_partner_id,
            
            # Branch references (nullable)
            ship_to_branch_id=branch_config.get('ship_to_branch_id'),
            bill_to_branch_id=branch_config.get('bill_to_branch_id'),
            ship_from_branch_id=branch_config.get('ship_from_branch_id'),
            
            # Frozen address snapshots (JSONB - immutable)
            ship_to_address=addresses['ship_to'],
            bill_to_address=addresses['bill_to'],
            ship_from_address=addresses['ship_from'],
            ship_to_address_source=branch_config.get('ship_to_source', 'AUTO_PRIMARY'),
            ship_from_address_source=branch_config.get('ship_from_source', 'AUTO_PRIMARY'),
            
            # Commodity details
            commodity_id=negotiation.requirement.commodity_id,
            commodity_variety_id=negotiation.requirement.variety_id,
            quantity=negotiation.final_quantity or negotiation.current_quantity,
            unit="QUINTALS",
            quality_parameters=negotiation.requirement.quality_params,
            
            # Pricing
            price_per_unit=negotiation.final_price_per_unit or negotiation.current_price_per_unit,
            total_amount=negotiation.final_total_amount or Decimal('0'),
            
            # GST
            gst_type=gst_details['gst_type'],
            cgst_rate=gst_details.get('cgst_rate'),
            sgst_rate=gst_details.get('sgst_rate'),
            igst_rate=gst_details.get('igst_rate'),
            
            # Terms
            delivery_terms=negotiation.requirement.delivery_terms,
            payment_terms=negotiation.final_payment_terms,
            delivery_timeline=negotiation.requirement.delivery_timeline,
            delivery_city=negotiation.requirement.delivery_city,
            delivery_state=negotiation.requirement.delivery_state,
            
            # Status: ACTIVE immediately (legally binding)
            status="ACTIVE",
            trade_date=date.today(),
            expected_delivery_date=negotiation.requirement.delivery_date,
            
            # Audit
            created_by=user_id,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        
        # Save trade
        trade = await self.trade_repo.create(trade)
        
        # Update negotiation accepted_at timestamp
        negotiation.accepted_at = datetime.now(timezone.utc)
        await self.db.flush()
        
        # Emit event for PDF generation (async background job)
        await self._emit_contract_generation_event(trade)
        
        # Commit transaction
        await self.db.commit()
        
        return trade
    
    # ========================================================================
    # SIGNATURE VALIDATION
    # ========================================================================
    
    async def _validate_signatures_exist(
        self,
        buyer_partner_id: UUID,
        seller_partner_id: UUID
    ) -> None:
        """
        Validate both parties have uploaded signatures.
        
        Signatures are stored in business_partners.digital_signature_url.
        This check ensures we can generate instant signed PDFs.
        
        Raises:
            BusinessRuleException: If either party missing signature
        """
        # Check buyer signature
        stmt = select(BusinessPartner.digital_signature_url).where(
            BusinessPartner.id == buyer_partner_id
        )
        result = await self.db.execute(stmt)
        buyer_sig = result.scalar_one_or_none()
        
        if not buyer_sig:
            raise BusinessRuleException(
                "Buyer must upload digital signature before creating trade. "
                "Please complete signature upload in profile settings."
            )
        
        # Check seller signature
        stmt = select(BusinessPartner.digital_signature_url).where(
            BusinessPartner.id == seller_partner_id
        )
        result = await self.db.execute(stmt)
        seller_sig = result.scalar_one_or_none()
        
        if not seller_sig:
            raise BusinessRuleException(
                "Seller must upload digital signature before creating trade. "
                "Please complete signature upload in profile settings."
            )
    
    # ========================================================================
    # BRANCH SELECTION (AI Auto-Select or User Override)
    # ========================================================================
    
    async def _select_branches(
        self,
        buyer_partner_id: UUID,
        seller_partner_id: UUID,
        commodity_code: str,
        quantity_qtls: int,
        user_selections: Optional[Dict[str, UUID]] = None
    ) -> Dict[str, Any]:
        """
        Select branches for trade (auto or user override).
        
        Logic:
        1. If user provided selections → Use them
        2. Else if single branch → Auto-select
        3. Else if multiple branches → Use defaults
        4. If no branches → Status PENDING_BRANCH_SELECTION
        
        Args:
            buyer_partner_id: Buyer UUID
            seller_partner_id: Seller UUID
            commodity_code: Commodity code
            quantity_qtls: Quantity in quintals
            user_selections: Optional user-selected branches
        
        Returns:
            Dict with branch IDs and selection sources
        """
        config = {}
        
        # === BUYER BRANCHES ===
        
        # Ship-to (delivery address)
        if user_selections and 'buyer_ship_to_branch_id' in user_selections:
            # User override
            config['ship_to_branch_id'] = user_selections['buyer_ship_to_branch_id']
            config['ship_to_source'] = 'USER_SELECTED'
        else:
            # Auto-select
            ship_to_branches = await self.branch_repo.get_ship_to_branches(
                partner_id=buyer_partner_id,
                commodity_code=commodity_code,
                required_capacity_qtls=quantity_qtls
            )
            
            if len(ship_to_branches) == 1:
                config['ship_to_branch_id'] = ship_to_branches[0].id
                config['ship_to_source'] = 'AUTO_SINGLE_BRANCH'
            elif ship_to_branches:
                # Use default
                default = await self.branch_repo.get_default_ship_to(buyer_partner_id)
                if default:
                    config['ship_to_branch_id'] = default.id
                    config['ship_to_source'] = 'AUTO_DEFAULT'
        
        # Bill-to (invoice address - usually head office)
        if user_selections and 'buyer_bill_to_branch_id' in user_selections:
            config['bill_to_branch_id'] = user_selections['buyer_bill_to_branch_id']
        else:
            head_office = await self.branch_repo.get_head_office(buyer_partner_id)
            if head_office:
                config['bill_to_branch_id'] = head_office.id
        
        # === SELLER BRANCHES ===
        
        # Ship-from (dispatch address)
        if user_selections and 'seller_ship_from_branch_id' in user_selections:
            config['ship_from_branch_id'] = user_selections['seller_ship_from_branch_id']
            config['ship_from_source'] = 'USER_SELECTED'
        else:
            ship_from_branches = await self.branch_repo.get_ship_from_branches(
                partner_id=seller_partner_id,
                commodity_code=commodity_code
            )
            
            if len(ship_from_branches) == 1:
                config['ship_from_branch_id'] = ship_from_branches[0].id
                config['ship_from_source'] = 'AUTO_SINGLE_BRANCH'
            elif ship_from_branches:
                default = await self.branch_repo.get_default_ship_from(seller_partner_id)
                if default:
                    config['ship_from_branch_id'] = default.id
                    config['ship_from_source'] = 'AUTO_DEFAULT'
        
        return config
    
    # ========================================================================
    # ADDRESS FREEZING (Immutable Snapshots)
    # ========================================================================
    
    async def _freeze_addresses(
        self,
        branch_config: Dict[str, Any]
    ) -> Dict[str, Dict[str, Any]]:
        """
        Create immutable address snapshots from branches.
        
        These JSONB snapshots are frozen at contract creation time.
        Even if partner updates branch address later, contract retains original.
        
        Args:
            branch_config: Branch IDs from _select_branches
        
        Returns:
            Dict with ship_to, bill_to, ship_from address snapshots
        """
        addresses = {}
        
        # Ship-to address
        if 'ship_to_branch_id' in branch_config:
            branch = await self.branch_repo.get_by_id(branch_config['ship_to_branch_id'])
            if branch:
                addresses['ship_to'] = branch.to_address_dict()
        
        # Bill-to address
        if 'bill_to_branch_id' in branch_config:
            branch = await self.branch_repo.get_by_id(branch_config['bill_to_branch_id'])
            if branch:
                addresses['bill_to'] = branch.to_address_dict()
        
        # Ship-from address
        if 'ship_from_branch_id' in branch_config:
            branch = await self.branch_repo.get_by_id(branch_config['ship_from_branch_id'])
            if branch:
                addresses['ship_from'] = branch.to_address_dict()
        
        # Validate at least ship_to and ship_from exist
        if 'ship_to' not in addresses or 'ship_from' not in addresses:
            raise BusinessRuleException(
                "Cannot create trade without ship-to and ship-from addresses"
            )
        
        # Use ship_to as bill_to if not specified
        if 'bill_to' not in addresses:
            addresses['bill_to'] = addresses['ship_to']
        
        return addresses
    
    # ========================================================================
    # GST CALCULATION
    # ========================================================================
    
    def _calculate_gst(
        self,
        buyer_state: str,
        seller_state: str,
        base_amount: Decimal
    ) -> Dict[str, Any]:
        """
        Calculate GST type and rates based on state match.
        
        Logic:
        - Same state → INTRA_STATE (CGST 9% + SGST 9% = 18%)
        - Different state → INTER_STATE (IGST 18%)
        
        Args:
            buyer_state: Buyer's state
            seller_state: Seller's state
            base_amount: Base amount before tax
        
        Returns:
            Dict with gst_type, rates
        """
        if buyer_state == seller_state:
            # Intra-state: CGST + SGST
            return {
                'gst_type': 'INTRA_STATE',
                'cgst_rate': Decimal('9.00'),
                'sgst_rate': Decimal('9.00'),
                'igst_rate': None
            }
        else:
            # Inter-state: IGST
            return {
                'gst_type': 'INTER_STATE',
                'cgst_rate': None,
                'sgst_rate': None,
                'igst_rate': Decimal('18.00')
            }
    
    # ========================================================================
    # EVENT EMISSION (For PDF Generation)
    # ========================================================================
    
    async def _emit_contract_generation_event(self, trade: Trade) -> None:
        """
        Emit event to trigger async PDF generation.
        
        Background worker will:
        1. Fetch trade + signatures from DB
        2. Render Jinja2 template with trade data
        3. Generate PDF with WeasyPrint/ReportLab
        4. Embed signatures from business_partners
        5. Calculate SHA-256 hash
        6. Upload to S3
        7. Update trade.contract_pdf_url
        
        This happens async (5-10 seconds) while user sees confirmation.
        """
        # Emit domain event (will be picked up by event handlers)
        trade.emit_event(
            event_type="trade.created",
            payload={
                "trade_id": str(trade.id),
                "trade_number": trade.trade_number,
                "buyer_partner_id": str(trade.buyer_partner_id),
                "seller_partner_id": str(trade.seller_partner_id),
                "generate_contract": True
            }
        )
    
    # ========================================================================
    # TRADE LIFECYCLE MANAGEMENT
    # ========================================================================
    
    async def update_status(
        self,
        trade_id: UUID,
        new_status: str,
        user_id: UUID
    ) -> Trade:
        """
        Update trade status (ACTIVE → IN_TRANSIT → DELIVERED → COMPLETED).
        
        Args:
            trade_id: Trade UUID
            new_status: New status
            user_id: User updating
        
        Returns:
            Updated trade
        """
        trade = await self.trade_repo.get_by_id(trade_id)
        
        if not trade:
            raise NotFoundException(f"Trade {trade_id} not found")
        
        # Validate status transition
        valid_transitions = {
            'PENDING_BRANCH_SELECTION': ['ACTIVE', 'CANCELLED'],
            'ACTIVE': ['IN_TRANSIT', 'CANCELLED', 'DISPUTED'],
            'IN_TRANSIT': ['DELIVERED', 'DISPUTED'],
            'DELIVERED': ['COMPLETED', 'DISPUTED'],
            'COMPLETED': [],
            'CANCELLED': [],
            'DISPUTED': ['ACTIVE', 'CANCELLED']
        }
        
        if new_status not in valid_transitions.get(trade.status, []):
            raise BusinessRuleException(
                f"Cannot transition from {trade.status} to {new_status}"
            )
        
        # Update status
        trade.status = new_status
        trade.updated_at = datetime.now(timezone.utc)
        
        # Set actual delivery date if DELIVERED
        if new_status == 'DELIVERED' and not trade.actual_delivery_date:
            trade.actual_delivery_date = date.today()
        
        trade = await self.trade_repo.update(trade)
        await self.db.commit()
        
        return trade
    
    # ========================================================================
    # QUERIES
    # ========================================================================
    
    async def get_trade_by_id(
        self,
        trade_id: UUID,
        load_relationships: bool = True
    ) -> Optional[Trade]:
        """Get trade with optional eager loading."""
        return await self.trade_repo.get_by_id(trade_id, load_relationships)
    
    async def get_trades_by_partner(
        self,
        partner_id: UUID,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Trade]:
        """Get all trades for partner (buyer or seller)."""
        return await self.trade_repo.get_by_partner(
            partner_id, status, skip, limit
        )
    
    async def get_trade_statistics(
        self,
        partner_id: Optional[UUID] = None
    ) -> Dict[str, Any]:
        """Get comprehensive trade statistics."""
        return await self.trade_repo.get_trade_statistics(partner_id)

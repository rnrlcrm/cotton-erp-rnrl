"""
Insider Trading Validator

Prevents corporate insiders from trading with each other.

BLOCKING RULES:
1. Same Entity: Partner cannot trade with itself
2. Master-Branch: Master entity cannot trade with its own branches
3. Corporate Group: Entities in same corporate_group_id cannot trade
4. Same GST: Entities with same GST number cannot trade (even if different legal names)

These rules prevent:
- Artificial price manipulation
- Transfer pricing abuse
- Tax evasion through related party transactions
- Circular trading schemes
"""

from typing import Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, and_

from backend.modules.partners.models import BusinessPartner
from backend.modules.partners.repositories import BusinessPartnerRepository


class InsiderTradingError(Exception):
    """Raised when insider trading is detected."""
    
    def __init__(self, rule: str, message: str, buyer_id: UUID, seller_id: UUID):
        self.rule = rule
        self.message = message
        self.buyer_id = buyer_id
        self.seller_id = seller_id
        super().__init__(message)


class InsiderTradingValidator:
    """
    Validates that trading parties are not corporate insiders.
    
    Blocking Rules:
    1. Same Entity: buyer_id == seller_id
    2. Master-Branch: One is master, other is branch
    3. Corporate Group: Same corporate_group_id
    4. Same GST: Same GST number (different entities, same tax registration)
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = BusinessPartnerRepository(db)
    
    async def validate_trade_parties(
        self,
        buyer_id: UUID,
        seller_id: UUID,
        raise_exception: bool = True
    ) -> tuple[bool, Optional[str]]:
        """
        Validate that buyer and seller are not corporate insiders.
        
        Args:
            buyer_id: UUID of buying partner
            seller_id: UUID of selling partner
            raise_exception: If True, raise InsiderTradingError on violation
        
        Returns:
            tuple[bool, Optional[str]]: (is_valid, error_message)
            - is_valid: True if trade allowed, False if blocked
            - error_message: None if valid, error description if blocked
        
        Raises:
            InsiderTradingError: If raise_exception=True and violation detected
        """
        # Rule 1: Same Entity
        if buyer_id == seller_id:
            error_msg = "❌ INSIDER TRADING BLOCKED: Partner cannot trade with itself"
            if raise_exception:
                raise InsiderTradingError(
                    rule="SAME_ENTITY",
                    message=error_msg,
                    buyer_id=buyer_id,
                    seller_id=seller_id
                )
            return False, error_msg
        
        # Get both partners
        buyer = await self.repo.get_by_id(buyer_id)
        seller = await self.repo.get_by_id(seller_id)
        
        if not buyer or not seller:
            return False, "❌ One or both partners not found"
        
        # Rule 2: Master-Branch relationship
        is_master_branch = await self._check_master_branch_relationship(buyer, seller)
        if is_master_branch:
            error_msg = (
                f"❌ INSIDER TRADING BLOCKED: Master entity cannot trade with its branch\n"
                f"Buyer: {buyer.legal_name}\n"
                f"Seller: {seller.legal_name}"
            )
            if raise_exception:
                raise InsiderTradingError(
                    rule="MASTER_BRANCH",
                    message=error_msg,
                    buyer_id=buyer_id,
                    seller_id=seller_id
                )
            return False, error_msg
        
        # Rule 3: Corporate Group
        has_corporate_group = (
            hasattr(buyer, 'corporate_group_id') and 
            hasattr(seller, 'corporate_group_id') and
            buyer.corporate_group_id and 
            seller.corporate_group_id
        )
        
        if has_corporate_group and buyer.corporate_group_id == seller.corporate_group_id:
            error_msg = (
                f"❌ INSIDER TRADING BLOCKED: Entities belong to same corporate group\n"
                f"Buyer: {buyer.legal_name}\n"
                f"Seller: {seller.legal_name}\n"
                f"Corporate Group ID: {buyer.corporate_group_id}"
            )
            if raise_exception:
                raise InsiderTradingError(
                    rule="CORPORATE_GROUP",
                    message=error_msg,
                    buyer_id=buyer_id,
                    seller_id=seller_id
                )
            return False, error_msg
        
        # Rule 4: Same GST Number
        has_gst = (
            hasattr(buyer, 'gst_number') and 
            hasattr(seller, 'gst_number') and
            buyer.gst_number and 
            seller.gst_number
        )
        
        if has_gst and buyer.gst_number == seller.gst_number:
            error_msg = (
                f"❌ INSIDER TRADING BLOCKED: Same GST number (related entities)\n"
                f"Buyer: {buyer.legal_name}\n"
                f"Seller: {seller.legal_name}\n"
                f"GST Number: {buyer.gst_number}"
            )
            if raise_exception:
                raise InsiderTradingError(
                    rule="SAME_GST",
                    message=error_msg,
                    buyer_id=buyer_id,
                    seller_id=seller_id
                )
            return False, error_msg
        
        # All checks passed
        return True, None
    
    async def _check_master_branch_relationship(
        self,
        buyer: BusinessPartner,
        seller: BusinessPartner
    ) -> bool:
        """
        Check if buyer and seller have master-branch relationship.
        
        Cases:
        1. Buyer is master, seller is its branch
        2. Seller is master, buyer is its branch
        3. Both are branches of same master
        
        Returns:
            bool: True if master-branch relationship exists
        """
        # Check if entity_class field exists (new schema)
        if not hasattr(buyer, 'master_entity_id') or not hasattr(seller, 'master_entity_id'):
            return False
        
        # Case 1: Buyer is master of seller
        if hasattr(buyer, 'is_master_entity') and buyer.is_master_entity:
            if seller.master_entity_id == buyer.id:
                return True
        
        # Case 2: Seller is master of buyer
        if hasattr(seller, 'is_master_entity') and seller.is_master_entity:
            if buyer.master_entity_id == seller.id:
                return True
        
        # Case 3: Both are branches of same master
        if buyer.master_entity_id and seller.master_entity_id:
            if buyer.master_entity_id == seller.master_entity_id:
                return True
        
        return False
    
    async def get_all_insider_relationships(
        self,
        partner_id: UUID
    ) -> dict:
        """
        Get all insider relationships for a partner.
        
        Useful for:
        - Displaying blocked trading partners in UI
        - Pre-filtering trade desk listings
        - Compliance reporting
        
        Args:
            partner_id: Partner to check relationships for
        
        Returns:
            dict: {
                "same_entity": [partner_id],
                "master_branch": [list of master/branch IDs],
                "corporate_group": [list of group member IDs],
                "same_gst": [list of partners with same GST]
            }
        """
        partner = await self.repo.get_by_id(partner_id)
        
        if not partner:
            return {
                "same_entity": [],
                "master_branch": [],
                "corporate_group": [],
                "same_gst": []
            }
        
        relationships = {
            "same_entity": [partner_id],
            "master_branch": [],
            "corporate_group": [],
            "same_gst": []
        }
        
        # Get master-branch relationships
        if hasattr(partner, 'master_entity_id'):
            if hasattr(partner, 'is_master_entity') and partner.is_master_entity:
                # This is a master - get all branches
                branches = await self._get_branches(partner_id)
                relationships["master_branch"].extend([b.id for b in branches])
            elif partner.master_entity_id:
                # This is a branch - get master and other branches
                relationships["master_branch"].append(partner.master_entity_id)
                siblings = await self._get_branches(partner.master_entity_id)
                relationships["master_branch"].extend([
                    s.id for s in siblings if s.id != partner_id
                ])
        
        # Get corporate group members
        if hasattr(partner, 'corporate_group_id') and partner.corporate_group_id:
            group_members = await self._get_corporate_group_members(partner.corporate_group_id)
            relationships["corporate_group"].extend([
                m.id for m in group_members if m.id != partner_id
            ])
        
        # Get partners with same GST
        if hasattr(partner, 'gst_number') and partner.gst_number:
            same_gst_partners = await self._get_partners_by_gst(partner.gst_number)
            relationships["same_gst"].extend([
                p.id for p in same_gst_partners if p.id != partner_id
            ])
        
        return relationships
    
    async def _get_branches(self, master_entity_id: UUID) -> list[BusinessPartner]:
        """Get all branches of a master entity."""
        stmt = select(BusinessPartner).where(
            BusinessPartner.master_entity_id == master_entity_id
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()
    
    async def _get_corporate_group_members(self, corporate_group_id: UUID) -> list[BusinessPartner]:
        """Get all members of a corporate group."""
        stmt = select(BusinessPartner).where(
            BusinessPartner.corporate_group_id == corporate_group_id
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()
    
    async def _get_partners_by_gst(self, gst_number: str) -> list[BusinessPartner]:
        """Get all partners with same GST number."""
        stmt = select(BusinessPartner).where(
            BusinessPartner.gst_number == gst_number
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()
    
    async def validate_batch_trades(
        self,
        trade_pairs: list[tuple[UUID, UUID]]
    ) -> dict:
        """
        Validate multiple trade pairs at once.
        
        Useful for:
        - Bulk order validation
        - Trade desk matching engine
        - Compliance batch checking
        
        Args:
            trade_pairs: List of (buyer_id, seller_id) tuples
        
        Returns:
            dict: {
                "valid_trades": list[tuple[UUID, UUID]],
                "blocked_trades": list[dict],
                "total_checked": int,
                "total_valid": int,
                "total_blocked": int
            }
        """
        valid_trades = []
        blocked_trades = []
        
        for buyer_id, seller_id in trade_pairs:
            is_valid, error_msg = await self.validate_trade_parties(
                buyer_id=buyer_id,
                seller_id=seller_id,
                raise_exception=False
            )
            
            if is_valid:
                valid_trades.append((buyer_id, seller_id))
            else:
                blocked_trades.append({
                    "buyer_id": str(buyer_id),
                    "seller_id": str(seller_id),
                    "reason": error_msg
                })
        
        return {
            "valid_trades": valid_trades,
            "blocked_trades": blocked_trades,
            "total_checked": len(trade_pairs),
            "total_valid": len(valid_trades),
            "total_blocked": len(blocked_trades)
        }

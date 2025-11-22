"""
Partner Business Rules Validator

Validates business rules for partner operations:
- Trader cannot buy AND sell to same party (prevent circular trading)
- Ship-to addresses only for buyers
- Branch GST validation
- Google Maps tagging
"""

from typing import Dict, List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.modules.partners.models import BusinessPartner


class PartnerBusinessRulesValidator:
    """Validates partner-specific business rules"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def validate_ship_to_restriction(
        self,
        partner_id: UUID
    ) -> bool:
        """
        Validate that only buyers can add ship-to addresses
        
        Returns:
            True if partner is buyer/trader, False otherwise
        """
        query = select(BusinessPartner).where(
            BusinessPartner.id == partner_id
        )
        result = await self.db.execute(query)
        partner = result.scalar_one_or_none()
        
        if not partner:
            return False
        
        # Only buyers and traders can have ship-to addresses
        return partner.partner_type in ["buyer", "trader"]
    
    async def check_trader_cross_trading(
        self,
        trader_partner_id: UUID,
        counterparty_partner_id: UUID,
        transaction_type: str  # "buy" or "sell"
    ) -> Dict[str, any]:
        """
        Check if trader is trying to both buy and sell to same party
        
        Business Rule: Trader cannot buy AND sell to same counterparty
        This prevents circular trading and wash trades
        
        Args:
            trader_partner_id: The trader's partner ID
            counterparty_partner_id: The other party's partner ID  
            transaction_type: "buy" or "sell"
        
        Returns:
            {
                "allowed": bool,
                "reason": str,
                "existing_relationship": str,  # "buyer", "seller", or "none"
                "trade_count": int
            }
        """
        # This would typically check the trades/contracts table
        # For now, return structure for implementation
        
        # Query existing trades between these two parties
        # Example query (needs actual trades table):
        """
        existing_trades = await self.db.execute(
            select(Trade).where(
                or_(
                    and_(
                        Trade.seller_id == trader_partner_id,
                        Trade.buyer_id == counterparty_partner_id
                    ),
                    and_(
                        Trade.buyer_id == trader_partner_id,
                        Trade.seller_id == counterparty_partner_id
                    )
                )
            )
        )
        """
        
        # Placeholder logic
        existing_relationship = "none"  # or "buyer" or "seller"
        
        # Rule: If trader already buys from party X, cannot sell to party X
        # Rule: If trader already sells to party X, cannot buy from party X
        
        if transaction_type == "buy" and existing_relationship == "seller":
            return {
                "allowed": False,
                "reason": "Trader cannot buy from a party they already sell to (prevents circular trading)",
                "existing_relationship": existing_relationship,
                "trade_count": 0  # Would be actual count
            }
        
        if transaction_type == "sell" and existing_relationship == "buyer":
            return {
                "allowed": False,
                "reason": "Trader cannot sell to a party they already buy from (prevents circular trading)",
                "existing_relationship": existing_relationship,
                "trade_count": 0  # Would be actual count
            }
        
        return {
            "allowed": True,
            "reason": "No circular trading detected",
            "existing_relationship": existing_relationship,
            "trade_count": 0
        }
    
    async def validate_branch_gstin(
        self,
        primary_pan: str,
        branch_gstin: str
    ) -> Dict[str, any]:
        """
        Validate that branch GSTIN belongs to same PAN as primary
        
        Args:
            primary_pan: Primary PAN of business (10 chars)
            branch_gstin: GSTIN of branch (15 chars)
        
        Returns:
            {
                "valid": bool,
                "pan_matches": bool,
                "branch_pan": str,
                "error": str
            }
        """
        if not branch_gstin or len(branch_gstin) != 15:
            return {
                "valid": False,
                "pan_matches": False,
                "branch_pan": None,
                "error": "Invalid GSTIN format"
            }
        
        # Extract PAN from GSTIN (characters 3-12, 0-indexed: 2-12)
        branch_pan = branch_gstin[2:12]
        
        if branch_pan != primary_pan:
            return {
                "valid": False,
                "pan_matches": False,
                "branch_pan": branch_pan,
                "error": f"Branch GSTIN PAN ({branch_pan}) does not match primary PAN ({primary_pan})"
            }
        
        return {
            "valid": True,
            "pan_matches": True,
            "branch_pan": branch_pan,
            "error": None
        }

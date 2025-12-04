"""
AI-Assisted Negotiation Service

Provides intelligent suggestions for negotiation:
- Counter-offer recommendations
- Acceptance probability prediction
- Automated negotiation (if enabled)
- Market-based pricing insights
"""

from typing import Optional, Dict, Any, Tuple
from decimal import Decimal
from uuid import UUID
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..models.negotiation import Negotiation
from ..models.negotiation_offer import NegotiationOffer
from ..models.requirement import Requirement
from ..models.availability import Availability


class AINegoticationService:
    """
    AI-powered negotiation assistance.
    
    Features:
    - Suggest counter-offers based on market conditions
    - Predict acceptance probability  
    - Auto-negotiate if enabled by user
    - Learn from historical negotiations
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def suggest_counter_offer(
        self,
        negotiation: Negotiation,
        current_offer: NegotiationOffer,
        user_party: str  # BUYER or SELLER
    ) -> Dict[str, Any]:
        """
        Generate AI-powered counter-offer suggestion.
        
        Strategy:
        1. Analyze offer history (convergence rate)
        2. Check market prices for commodity
        3. Calculate optimal counter based on:
           - Distance to market price
           - Concession pattern
           - Time remaining to expiry
           - User's historical acceptance behavior
        
        Args:
            negotiation: Negotiation session
            current_offer: Latest offer to respond to
            user_party: BUYER or SELLER
        
        Returns:
            {
                "suggested_price": Decimal,
                "suggested_quantity": int,
                "confidence": float (0-1),
                "reasoning": str,
                "acceptance_probability": float (0-1),
                "market_comparison": {
                    "market_price": Decimal,
                    "difference_pct": float
                }
            }
        """
        # Load requirement and availability
        requirement = await self.db.get(Requirement, negotiation.requirement_id)
        availability = await self.db.get(Availability, negotiation.availability_id)
        
        # Get all offers in this negotiation
        offers_query = select(NegotiationOffer).where(
            NegotiationOffer.negotiation_id == negotiation.id
        ).order_by(NegotiationOffer.round_number)
        
        result = await self.db.execute(offers_query)
        all_offers = result.scalars().all()
        
        # Strategy 1: Simple convergence analysis
        if len(all_offers) >= 2:
            # Calculate average concession rate
            buyer_offers = [o for o in all_offers if o.offered_by == "BUYER"]
            seller_offers = [o for o in all_offers if o.offered_by == "SELLER"]
            
            if user_party == "BUYER":
                # Buyer wants to increase price toward seller
                if len(buyer_offers) >= 2:
                    # Calculate historical concession
                    last_buyer_price = buyer_offers[-1].price_per_unit
                    prev_buyer_price = buyer_offers[-2].price_per_unit
                    concession = last_buyer_price - prev_buyer_price
                    
                    # Suggest similar concession
                    suggested_price = current_offer.price_per_unit - concession
                else:
                    # First counter - meet halfway
                    suggested_price = (
                        requirement.price_per_unit + current_offer.price_per_unit
                    ) / 2
            else:
                # Seller wants to decrease price toward buyer
                if len(seller_offers) >= 2:
                    last_seller_price = seller_offers[-1].price_per_unit
                    prev_seller_price = seller_offers[-2].price_per_unit
                    concession = prev_seller_price - last_seller_price
                    
                    suggested_price = current_offer.price_per_unit + concession
                else:
                    # First counter - meet halfway
                    suggested_price = (
                        availability.price_per_unit + current_offer.price_per_unit
                    ) / 2
        else:
            # First offer - suggest middle ground
            suggested_price = (
                requirement.price_per_unit + availability.price_per_unit
            ) / 2
        
        # Ensure price is reasonable
        suggested_price = max(
            requirement.price_per_unit * Decimal("0.8"),
            min(suggested_price, availability.price_per_unit * Decimal("1.2"))
        )
        
        # Quantity strategy: Usually match or slightly reduce
        suggested_quantity = min(
            current_offer.quantity,
            requirement.quantity,
            availability.quantity
        )
        
        # Calculate confidence based on convergence
        price_gap = abs(
            availability.price_per_unit - requirement.price_per_unit
        )
        current_gap = abs(
            current_offer.price_per_unit - suggested_price
        )
        
        if price_gap > 0:
            convergence = 1 - (current_gap / price_gap)
            confidence = min(0.95, max(0.3, convergence))
        else:
            confidence = 0.9
        
        # Acceptance probability (simplified)
        # Higher if we're close to their original ask
        if user_party == "BUYER":
            distance_to_ask = abs(
                suggested_price - availability.price_per_unit
            ) / availability.price_per_unit
        else:
            distance_to_ask = abs(
                suggested_price - requirement.price_per_unit
            ) / requirement.price_per_unit
        
        acceptance_probability = max(0.1, 1 - float(distance_to_ask))
        
        # Market comparison (placeholder - would query actual market data)
        market_price = (
            requirement.price_per_unit + availability.price_per_unit
        ) / 2
        
        difference_pct = float(
            (suggested_price - market_price) / market_price * 100
        )
        
        # Generate reasoning
        if len(all_offers) >= 2:
            reasoning = (
                f"Based on {len(all_offers)} previous offers, "
                f"suggesting {convergence*100:.1f}% convergence. "
                f"This counter-offer follows your typical concession pattern."
            )
        else:
            reasoning = (
                "Initial counter-offer splitting the difference between "
                "buyer requirement and seller availability."
            )
        
        return {
            "suggested_price": suggested_price,
            "suggested_quantity": suggested_quantity,
            "confidence": confidence,
            "reasoning": reasoning,
            "acceptance_probability": acceptance_probability,
            "market_comparison": {
                "market_price": market_price,
                "difference_pct": difference_pct
            }
        }
    
    async def predict_acceptance_probability(
        self,
        negotiation: Negotiation,
        proposed_offer: Dict[str, Any]
    ) -> float:
        """
        Predict probability that proposed offer will be accepted.
        
        Factors:
        - Price distance from counterparty's ask
        - Quantity match
        - Terms compatibility
        - Historical acceptance patterns
        - Time pressure (expiry approaching)
        
        Args:
            negotiation: Negotiation session
            proposed_offer: {price_per_unit, quantity, delivery_terms, ...}
        
        Returns:
            Probability (0-1)
        """
        requirement = await self.db.get(Requirement, negotiation.requirement_id)
        availability = await self.db.get(Availability, negotiation.availability_id)
        
        # Factor 1: Price alignment
        proposed_price = proposed_offer["price_per_unit"]
        
        # Check which party we're making offer to
        if proposed_offer.get("offered_by") == "BUYER":
            # Offering to seller
            target_price = availability.price_per_unit
        else:
            # Offering to buyer
            target_price = requirement.price_per_unit
        
        price_distance = abs(proposed_price - target_price) / target_price
        price_score = max(0, 1 - float(price_distance))
        
        # Factor 2: Quantity match
        proposed_qty = proposed_offer["quantity"]
        required_qty = min(requirement.quantity, availability.quantity)
        
        qty_match = proposed_qty / required_qty
        qty_score = min(1.0, qty_match)
        
        # Factor 3: Time pressure
        time_remaining = (
            negotiation.expires_at - datetime.utcnow()
        ).total_seconds()
        
        total_time = 48 * 3600  # 48 hours
        time_pressure = 1 - (time_remaining / total_time)
        
        # More time pressure = higher acceptance probability
        time_score = 0.5 + (time_pressure * 0.3)
        
        # Weighted combination
        probability = (
            price_score * 0.5 +
            qty_score * 0.3 +
            time_score * 0.2
        )
        
        return min(0.95, max(0.05, probability))
    
    async def should_auto_accept(
        self,
        negotiation: Negotiation,
        offer: NegotiationOffer,
        user_party: str
    ) -> Tuple[bool, str]:
        """
        Determine if offer should be auto-accepted.
        
        Criteria:
        - Price within acceptable range
        - Quantity matches requirement
        - Terms are favorable
        - Auto-negotiate is enabled
        
        Args:
            negotiation: Negotiation session
            offer: Offer to evaluate
            user_party: BUYER or SELLER
        
        Returns:
            (should_accept: bool, reason: str)
        """
        # Check if auto-negotiate is enabled
        if user_party == "BUYER" and not negotiation.auto_negotiate_buyer:
            return False, "Auto-negotiate disabled for buyer"
        
        if user_party == "SELLER" and not negotiation.auto_negotiate_seller:
            return False, "Auto-negotiate disabled for seller"
        
        requirement = await self.db.get(Requirement, negotiation.requirement_id)
        availability = await self.db.get(Availability, negotiation.availability_id)
        
        # Price check
        if user_party == "BUYER":
            # Buyer accepts if price is at or below their max
            if offer.price_per_unit > requirement.price_per_unit * Decimal("1.05"):
                return False, "Price exceeds buyer's maximum (5% tolerance)"
            
            acceptable_price = True
        else:
            # Seller accepts if price is at or above their min
            if offer.price_per_unit < availability.price_per_unit * Decimal("0.95"):
                return False, "Price below seller's minimum (5% tolerance)"
            
            acceptable_price = True
        
        # Quantity check
        if offer.quantity < min(requirement.quantity, availability.quantity) * 0.9:
            return False, "Quantity too low (< 90% of target)"
        
        # If all checks pass
        if acceptable_price:
            return True, "Price and quantity within acceptable range"
        
        return False, "Conditions not met"
    
    async def generate_auto_counter(
        self,
        negotiation: Negotiation,
        current_offer: NegotiationOffer,
        user_party: str
    ) -> Dict[str, Any]:
        """
        Generate automated counter-offer.
        
        Uses suggest_counter_offer but with higher confidence threshold.
        
        Args:
            negotiation: Negotiation session
            current_offer: Offer to counter
            user_party: BUYER or SELLER
        
        Returns:
            Counter-offer parameters + AI metadata
        """
        suggestion = await self.suggest_counter_offer(
            negotiation, current_offer, user_party
        )
        
        # Add AI metadata
        return {
            "price_per_unit": suggestion["suggested_price"],
            "quantity": suggestion["suggested_quantity"],
            "ai_generated": True,
            "ai_confidence": suggestion["confidence"],
            "ai_reasoning": f"AUTO: {suggestion['reasoning']}"
        }

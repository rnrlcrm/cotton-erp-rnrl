"""
Negotiation Service - ALL Business Logic for Multi-Round Negotiations

Handles complete negotiation lifecycle:
1. Start negotiation (reveal identities from anonymous match)
2. Make offers/counter-offers
3. Accept/reject deals
4. Auto-expire inactive negotiations
5. Create trade contracts on acceptance

NO business logic in routes - all here in service layer.
"""

from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Optional, Dict, Any
from uuid import UUID

from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
import redis.asyncio as redis

from backend.modules.trade_desk.models.negotiation import Negotiation
from backend.modules.trade_desk.models.negotiation_offer import NegotiationOffer
from backend.modules.trade_desk.models.negotiation_message import NegotiationMessage
from backend.modules.trade_desk.models.match_token import MatchToken
from backend.modules.trade_desk.models.requirement import Requirement
from backend.modules.trade_desk.models.availability import Availability
from backend.core.errors.exceptions import (
    NotFoundException,
    DomainError as ValidationException,
    AuthorizationException,
    BusinessRuleException
)


class NegotiationService:
    """
    Negotiation engine business logic.
    
    Architecture:
    - All validation and business rules here
    - Routes are thin wrappers
    - Events emitted for real-time updates
    - Redis caching for performance
    """
    
    def __init__(self, db: AsyncSession, redis_client: Optional[redis.Redis] = None):
        self.db = db
        self.redis = redis_client
    
    # ========================================================================
    # START NEGOTIATION (Identity Revelation)
    # ========================================================================
    
    async def start_negotiation(
        self,
        match_token: str,
        user_partner_id: UUID,
        initial_message: Optional[str] = None
    ) -> Negotiation:
        """
        Start negotiation from anonymous match.
        
        Flow:
        1. Lookup MatchToken by token
        2. Verify user is buyer or seller
        3. Check if negotiation already exists
        4. Reveal identities (update MatchToken)
        5. Create Negotiation record
        6. Send initial system message
        7. Emit negotiation.started event
        
        Args:
            match_token: Anonymous token (e.g., MATCH-A7B2C)
            user_partner_id: Current user's partner ID
            initial_message: Optional opening message
        
        Returns:
            Negotiation: Created negotiation with revealed identities
        
        Raises:
            NotFoundException: Match token not found
            AuthorizationException: User not party to this match
            BusinessRuleException: Negotiation already exists or match expired
        """
        # Lookup match token
        stmt = select(MatchToken).where(
            MatchToken.token == match_token
        ).options(
            selectinload(MatchToken.requirement),
            selectinload(MatchToken.availability)
        )
        result = await self.db.execute(stmt)
        token = result.scalar_one_or_none()
        
        if not token:
            raise NotFoundException(f"Match token {match_token} not found")
        
        # Check token not expired
        if token.is_expired:
            raise BusinessRuleException("Match token has expired")
        
        # Verify user is buyer or seller
        requirement = token.requirement
        availability = token.availability
        
        is_buyer = requirement.party_id == user_partner_id
        is_seller = availability.party_id == user_partner_id
        
        if not (is_buyer or is_seller):
            raise AuthorizationException("You are not party to this match")
        
        # Check if negotiation already exists
        stmt = select(Negotiation).where(
            Negotiation.match_token_id == token.id
        )
        result = await self.db.execute(stmt)
        existing = result.scalar_one_or_none()
        
        if existing:
            raise BusinessRuleException("Negotiation already exists for this match")
        
        # Reveal identities (update MatchToken disclosure)
        token.reveal_to_buyer()
        token.reveal_to_seller()
        
        # Create negotiation
        negotiation = Negotiation(
            match_token_id=token.id,
            requirement_id=requirement.id,
            availability_id=availability.id,
            buyer_partner_id=requirement.party_id,
            seller_partner_id=availability.party_id,
            status="INITIATED",
            initiated_by="BUYER" if is_buyer else "SELLER",
            current_round=0,
            # Set initial terms from availability
            current_price_per_unit=availability.base_price,
            current_quantity=min(requirement.quantity, availability.total_quantity),
            initiated_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(hours=48)
        )
        
        self.db.add(negotiation)
        await self.db.flush()
        
        # Create initial system message
        system_msg = NegotiationMessage(
            negotiation_id=negotiation.id,
            sender="SYSTEM",
            message=f"Negotiation started by {'buyer' if is_buyer else 'seller'}. Identities revealed.",
            message_type="SYSTEM",
            is_ai_generated=False
        )
        self.db.add(system_msg)
        
        # Add initial user message if provided
        if initial_message:
            user_msg = NegotiationMessage(
                negotiation_id=negotiation.id,
                sender="BUYER" if is_buyer else "SELLER",
                message=initial_message,
                message_type="TEXT",
                is_ai_generated=False
            )
            self.db.add(user_msg)
        
        await self.db.commit()
        
        # Emit event for real-time notification
        negotiation.emit_event(
            event_type="negotiation.started",
            user_id=user_partner_id,
            data={
                "negotiation_id": str(negotiation.id),
                "match_token": match_token,
                "initiated_by": negotiation.initiated_by,
                "buyer_id": str(negotiation.buyer_partner_id),
                "seller_id": str(negotiation.seller_partner_id)
            }
        )
        
        return negotiation
    
    # ========================================================================
    # MAKE OFFER / COUNTER-OFFER
    # ========================================================================
    
    async def make_offer(
        self,
        negotiation_id: UUID,
        user_partner_id: UUID,
        price_per_unit: Decimal,
        quantity: Decimal,
        message: Optional[str] = None,
        delivery_terms: Optional[Dict] = None,
        payment_terms: Optional[Dict] = None,
        quality_conditions: Optional[Dict] = None,
        ai_generated: bool = False,
        ai_confidence: Optional[Decimal] = None,
        ai_reasoning: Optional[str] = None
    ) -> NegotiationOffer:
        """
        Make new offer or counter-offer.
        
        Business Rules:
        - Only buyer or seller can make offers
        - Can't make offer if negotiation closed/expired
        - Buyer and seller must alternate (can't counter own offer)
        - Price and quantity must be positive
        - Increments round number
        
        Args:
            negotiation_id: Negotiation UUID
            user_partner_id: Current user's partner ID
            price_per_unit: Offered price
            quantity: Offered quantity
            message: Optional message with offer
            delivery_terms: Optional delivery details
            payment_terms: Optional payment details
            quality_conditions: Optional quality specs
            ai_generated: Was this AI-suggested?
            ai_confidence: AI confidence if AI-generated
            ai_reasoning: AI explanation
        
        Returns:
            NegotiationOffer: Created offer
        
        Raises:
            NotFoundException: Negotiation not found
            AuthorizationException: User not party to negotiation
            BusinessRuleException: Invalid offer (expired, wrong turn, etc.)
        """
        # Load negotiation
        stmt = select(Negotiation).where(
            Negotiation.id == negotiation_id
        ).options(
            selectinload(Negotiation.offers)
        )
        result = await self.db.execute(stmt)
        negotiation = result.scalar_one_or_none()
        
        if not negotiation:
            raise NotFoundException(f"Negotiation {negotiation_id} not found")
        
        # Verify user is buyer or seller
        is_buyer = negotiation.buyer_partner_id == user_partner_id
        is_seller = negotiation.seller_partner_id == user_partner_id
        
        if not (is_buyer or is_seller):
            raise AuthorizationException("You are not party to this negotiation")
        
        offered_by = "BUYER" if is_buyer else "SELLER"
        
        # Business rule: Can't make offer if expired or closed
        if not negotiation.can_make_offer:
            if negotiation.is_expired:
                raise BusinessRuleException("Negotiation has expired")
            else:
                raise BusinessRuleException(f"Negotiation is {negotiation.status}, cannot make offers")
        
        # Business rule: Can't counter your own offer (must alternate)
        if negotiation.last_offer_by == offered_by:
            raise BusinessRuleException(f"Cannot make consecutive offers. Waiting for {('SELLER' if is_buyer else 'BUYER')} response.")
        
        # Validate price and quantity
        if price_per_unit <= 0:
            raise ValidationException("Price must be positive")
        if quantity <= 0:
            raise ValidationException("Quantity must be positive")
        
        # Increment round
        new_round = negotiation.current_round + 1
        
        # Create offer
        offer = NegotiationOffer(
            negotiation_id=negotiation.id,
            round_number=new_round,
            offered_by=offered_by,
            price_per_unit=price_per_unit,
            quantity=quantity,
            delivery_terms=delivery_terms,
            payment_terms=payment_terms,
            quality_conditions=quality_conditions,
            message=message,
            ai_generated=ai_generated,
            ai_confidence=ai_confidence,
            ai_reasoning=ai_reasoning,
            status="PENDING"
        )
        
        self.db.add(offer)
        
        # Update negotiation state
        negotiation.current_round = new_round
        negotiation.current_price_per_unit = price_per_unit
        negotiation.current_quantity = quantity
        negotiation.last_offer_by = offered_by
        negotiation.status = "IN_PROGRESS"
        negotiation.update_activity()
        
        # Update current terms if provided
        if delivery_terms:
            current_terms = negotiation.current_terms or {}
            current_terms["delivery"] = delivery_terms
            negotiation.current_terms = current_terms
        
        if payment_terms:
            current_terms = negotiation.current_terms or {}
            current_terms["payment"] = payment_terms
            negotiation.current_terms = current_terms
        
        if quality_conditions:
            current_terms = negotiation.current_terms or {}
            current_terms["quality"] = quality_conditions
            negotiation.current_terms = current_terms
        
        await self.db.commit()
        
        # Emit event for real-time notification
        negotiation.emit_event(
            event_type="negotiation.offer_made",
            user_id=user_partner_id,
            data={
                "negotiation_id": str(negotiation.id),
                "offer_id": str(offer.id),
                "round": new_round,
                "offered_by": offered_by,
                "price": float(price_per_unit),
                "quantity": float(quantity),
                "ai_generated": ai_generated
            }
        )
        
        return offer
    
    # ========================================================================
    # ACCEPT OFFER
    # ========================================================================
    
    async def accept_offer(
        self,
        negotiation_id: UUID,
        user_partner_id: UUID,
        acceptance_message: Optional[str] = None
    ) -> Negotiation:
        """
        Accept current offer and close negotiation.
        
        Business Rules:
        - Only counterparty can accept (not the one who made offer)
        - Must have active offer to accept
        - Creates trade contract automatically
        - Marks negotiation as ACCEPTED
        - Updates MatchToken disclosure to TRADE
        
        Args:
            negotiation_id: Negotiation UUID
            user_partner_id: Current user's partner ID
            acceptance_message: Optional acceptance message
        
        Returns:
            Negotiation: Updated negotiation (status=ACCEPTED)
        
        Raises:
            NotFoundException: Negotiation not found
            AuthorizationException: User not party to negotiation
            BusinessRuleException: No offer to accept or wrong party
        """
        # Load negotiation with offers
        stmt = select(Negotiation).where(
            Negotiation.id == negotiation_id
        ).options(
            selectinload(Negotiation.offers),
            selectinload(Negotiation.match_token)
        )
        result = await self.db.execute(stmt)
        negotiation = result.scalar_one_or_none()
        
        if not negotiation:
            raise NotFoundException(f"Negotiation {negotiation_id} not found")
        
        # Verify user is buyer or seller
        is_buyer = negotiation.buyer_partner_id == user_partner_id
        is_seller = negotiation.seller_partner_id == user_partner_id
        
        if not (is_buyer or is_seller):
            raise AuthorizationException("You are not party to this negotiation")
        
        accepted_by = "BUYER" if is_buyer else "SELLER"
        
        # Business rule: Can't accept if expired or already closed
        if not negotiation.is_active:
            raise BusinessRuleException(f"Negotiation is {negotiation.status}, cannot accept")
        
        if negotiation.is_expired:
            raise BusinessRuleException("Negotiation has expired")
        
        # Business rule: Must have an offer to accept
        if negotiation.current_round == 0:
            raise BusinessRuleException("No offer to accept")
        
        # Business rule: Can't accept own offer (must be counterparty)
        if negotiation.last_offer_by == accepted_by:
            raise BusinessRuleException("Cannot accept your own offer")
        
        # Get latest offer
        latest_offer = sorted(negotiation.offers, key=lambda x: x.round_number, reverse=True)[0]
        latest_offer.status = "ACCEPTED"
        latest_offer.responded_at = datetime.utcnow()
        latest_offer.response_message = acceptance_message
        
        # Update negotiation status
        negotiation.status = "ACCEPTED"
        negotiation.accepted_by = accepted_by
        negotiation.accepted_at = datetime.utcnow()
        negotiation.update_activity()
        
        # Update MatchToken disclosure to TRADE
        if negotiation.match_token:
            negotiation.match_token.mark_traded()
        
        # Create acceptance message
        msg = NegotiationMessage(
            negotiation_id=negotiation.id,
            sender=accepted_by,
            message=acceptance_message or "I accept your offer!",
            message_type="ACCEPTANCE",
            is_ai_generated=False
        )
        self.db.add(msg)
        
        # System message
        system_msg = NegotiationMessage(
            negotiation_id=negotiation.id,
            sender="SYSTEM",
            message=f"Offer accepted by {accepted_by.lower()}. Negotiation completed successfully.",
            message_type="SYSTEM",
            is_ai_generated=False
        )
        self.db.add(system_msg)
        
        await self.db.commit()
        
        # Emit event
        negotiation.emit_event(
            event_type="negotiation.accepted",
            user_id=user_partner_id,
            data={
                "negotiation_id": str(negotiation.id),
                "accepted_by": accepted_by,
                "final_price": float(negotiation.current_price_per_unit),
                "final_quantity": float(negotiation.current_quantity)
            }
        )
        
        # TODO: Create trade contract automatically
        # await self._create_trade_contract(negotiation)
        
        return negotiation
    
    # ========================================================================
    # REJECT OFFER
    # ========================================================================
    
    async def reject_offer(
        self,
        negotiation_id: UUID,
        user_partner_id: UUID,
        rejection_reason: str,
        make_counter: bool = False,
        counter_price: Optional[Decimal] = None,
        counter_quantity: Optional[Decimal] = None
    ) -> Negotiation:
        """
        Reject current offer (optionally with counter-offer).
        
        Args:
            negotiation_id: Negotiation UUID
            user_partner_id: Current user's partner ID
            rejection_reason: Why rejecting
            make_counter: If True, make counter-offer immediately
            counter_price: Counter-offer price
            counter_quantity: Counter-offer quantity
        
        Returns:
            Negotiation: Updated negotiation
        """
        # Load negotiation
        stmt = select(Negotiation).where(
            Negotiation.id == negotiation_id
        ).options(
            selectinload(Negotiation.offers)
        )
        result = await self.db.execute(stmt)
        negotiation = result.scalar_one_or_none()
        
        if not negotiation:
            raise NotFoundException(f"Negotiation {negotiation_id} not found")
        
        # Verify user is buyer or seller
        is_buyer = negotiation.buyer_partner_id == user_partner_id
        is_seller = negotiation.seller_partner_id == user_partner_id
        
        if not (is_buyer or is_seller):
            raise AuthorizationException("You are not party to this negotiation")
        
        rejected_by = "BUYER" if is_buyer else "SELLER"
        
        # Get latest offer
        if negotiation.current_round > 0:
            latest_offer = sorted(negotiation.offers, key=lambda x: x.round_number, reverse=True)[0]
            latest_offer.status = "REJECTED"
            latest_offer.responded_at = datetime.utcnow()
            latest_offer.response_message = rejection_reason
        
        # If not making counter-offer, close negotiation
        if not make_counter:
            negotiation.status = "REJECTED"
            negotiation.rejected_by = rejected_by
            negotiation.rejected_at = datetime.utcnow()
            negotiation.rejection_reason = rejection_reason
            
            # Create rejection message
            msg = NegotiationMessage(
                negotiation_id=negotiation.id,
                sender=rejected_by,
                message=rejection_reason,
                message_type="REJECTION",
                is_ai_generated=False
            )
            self.db.add(msg)
            
            await self.db.commit()
            
            # Emit event
            negotiation.emit_event(
                event_type="negotiation.rejected",
                user_id=user_partner_id,
                data={
                    "negotiation_id": str(negotiation.id),
                    "rejected_by": rejected_by,
                    "reason": rejection_reason
                }
            )
        else:
            # Make counter-offer
            if not counter_price or not counter_quantity:
                raise ValidationException("Counter price and quantity required")
            
            await self.make_offer(
                negotiation_id=negotiation.id,
                user_partner_id=user_partner_id,
                price_per_unit=counter_price,
                quantity=counter_quantity,
                message=f"Rejected. Counter-offer: {rejection_reason}"
            )
        
        return negotiation
    
    # ========================================================================
    # SEND MESSAGE
    # ========================================================================
    
    async def send_message(
        self,
        negotiation_id: UUID,
        user_partner_id: UUID,
        message: str,
        message_type: str = "TEXT",
        is_ai_generated: bool = False
    ) -> NegotiationMessage:
        """
        Send chat message during negotiation.
        
        Args:
            negotiation_id: Negotiation UUID
            user_partner_id: Current user's partner ID
            message: Message text
            message_type: TEXT, OFFER, ACCEPTANCE, REJECTION, SYSTEM
            is_ai_generated: If AI wrote this
        
        Returns:
            NegotiationMessage: Created message
        """
        # Load negotiation
        stmt = select(Negotiation).where(
            Negotiation.id == negotiation_id
        )
        result = await self.db.execute(stmt)
        negotiation = result.scalar_one_or_none()
        
        if not negotiation:
            raise NotFoundException(f"Negotiation {negotiation_id} not found")
        
        # Verify user is buyer or seller
        is_buyer = negotiation.buyer_partner_id == user_partner_id
        is_seller = negotiation.seller_partner_id == user_partner_id
        
        if not (is_buyer or is_seller):
            raise AuthorizationException("You are not party to this negotiation")
        
        sender = "BUYER" if is_buyer else "SELLER"
        
        # Create message
        msg = NegotiationMessage(
            negotiation_id=negotiation.id,
            sender=sender,
            message=message,
            message_type=message_type,
            is_ai_generated=is_ai_generated
        )
        
        self.db.add(msg)
        negotiation.update_activity()
        
        await self.db.commit()
        
        # Emit event
        negotiation.emit_event(
            event_type="negotiation.message_sent",
            user_id=user_partner_id,
            data={
                "negotiation_id": str(negotiation.id),
                "message_id": str(msg.id),
                "sender": sender,
                "message_type": message_type
            }
        )
        
        return msg
    
    # ========================================================================
    # QUERY METHODS
    # ========================================================================
    
    async def get_negotiation_by_id(
        self,
        negotiation_id: UUID,
        user_partner_id: UUID
    ) -> Negotiation:
        """
        Get negotiation details with authorization check.
        
        Args:
            negotiation_id: Negotiation UUID
            user_partner_id: Current user's partner ID
        
        Returns:
            Negotiation: With offers and messages loaded
        
        Raises:
            NotFoundException: Negotiation not found
            AuthorizationException: User not party to negotiation
        """
        stmt = select(Negotiation).where(
            Negotiation.id == negotiation_id
        ).options(
            selectinload(Negotiation.offers),
            selectinload(Negotiation.messages),
            selectinload(Negotiation.requirement),
            selectinload(Negotiation.availability),
            selectinload(Negotiation.buyer_partner),
            selectinload(Negotiation.seller_partner)
        )
        result = await self.db.execute(stmt)
        negotiation = result.scalar_one_or_none()
        
        if not negotiation:
            raise NotFoundException(f"Negotiation {negotiation_id} not found")
        
        # Authorization check
        is_buyer = negotiation.buyer_partner_id == user_partner_id
        is_seller = negotiation.seller_partner_id == user_partner_id
        
        if not (is_buyer or is_seller):
            raise AuthorizationException("You are not party to this negotiation")
        
        return negotiation
    
    async def get_user_negotiations(
        self,
        user_partner_id: UUID,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Negotiation]:
        """
        Get all negotiations for a user.
        
        Args:
            user_partner_id: User's partner ID
            status: Filter by status (optional)
            limit: Max results
            offset: Pagination offset
        
        Returns:
            List of negotiations
        """
        stmt = select(Negotiation).where(
            or_(
                Negotiation.buyer_partner_id == user_partner_id,
                Negotiation.seller_partner_id == user_partner_id
            )
        ).options(
            selectinload(Negotiation.requirement),
            selectinload(Negotiation.availability),
            selectinload(Negotiation.buyer_partner),
            selectinload(Negotiation.seller_partner)
        )
        
        if status:
            stmt = stmt.where(Negotiation.status == status)
        
        stmt = stmt.order_by(Negotiation.last_activity_at.desc())
        stmt = stmt.limit(limit).offset(offset)
        
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
    
    # ========================================================================
    # ADMIN MONITORING METHODS (READ-ONLY)
    # ========================================================================
    
    async def admin_get_all_negotiations(
        self,
        status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Negotiation]:
        """
        Admin: Get ALL negotiations across all users (no authorization filter).
        
        For back office monitoring only - NO participation.
        
        Args:
            status: Filter by status (optional)
            limit: Max results
            offset: Pagination offset
        
        Returns:
            List of all negotiations
        """
        stmt = select(Negotiation).options(
            selectinload(Negotiation.requirement),
            selectinload(Negotiation.availability),
            selectinload(Negotiation.buyer_partner),
            selectinload(Negotiation.seller_partner)
        )
        
        if status:
            stmt = stmt.where(Negotiation.status == status)
        
        stmt = stmt.order_by(Negotiation.last_activity_at.desc())
        stmt = stmt.limit(limit).offset(offset)
        
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
    
    async def admin_get_negotiation_by_id(
        self,
        negotiation_id: UUID
    ) -> Negotiation:
        """
        Admin: Get negotiation details without authorization check.
        
        For back office monitoring only - NO participation.
        
        Args:
            negotiation_id: Negotiation UUID
        
        Returns:
            Negotiation: With all related data loaded
        
        Raises:
            NotFoundException: Negotiation not found
        """
        stmt = select(Negotiation).where(
            Negotiation.id == negotiation_id
        ).options(
            selectinload(Negotiation.offers),
            selectinload(Negotiation.messages),
            selectinload(Negotiation.requirement),
            selectinload(Negotiation.availability),
            selectinload(Negotiation.buyer_partner),
            selectinload(Negotiation.seller_partner)
        )
        result = await self.db.execute(stmt)
        negotiation = result.scalar_one_or_none()
        
        if not negotiation:
            raise NotFoundException(f"Negotiation {negotiation_id} not found")
        
        return negotiation
    
    async def get_negotiation_messages(
        self,
        negotiation_id: UUID,
        user_partner_id: UUID,
        mark_as_read: bool = True
    ) -> List[NegotiationMessage]:
        """
        Get all messages for negotiation.
        
        Args:
            negotiation_id: Negotiation UUID
            user_partner_id: Current user's partner ID
            mark_as_read: Mark messages as read
        
        Returns:
            List of messages in chronological order
        """
        # Verify access
        await self.get_negotiation_by_id(negotiation_id, user_partner_id)
        
        stmt = select(NegotiationMessage).where(
            NegotiationMessage.negotiation_id == negotiation_id
        ).order_by(NegotiationMessage.created_at)
        
        result = await self.db.execute(stmt)
        messages = list(result.scalars().all())
        
        if mark_as_read:
            # Load negotiation to check if buyer or seller
            stmt = select(Negotiation).where(Negotiation.id == negotiation_id)
            result = await self.db.execute(stmt)
            negotiation = result.scalar_one()
            
            is_buyer = negotiation.buyer_partner_id == user_partner_id
            
            for msg in messages:
                if is_buyer and not msg.read_by_buyer:
                    msg.mark_read_by_buyer()
                elif not is_buyer and not msg.read_by_seller:
                    msg.mark_read_by_seller()
            
            await self.db.commit()
        
        return messages
    
    # ========================================================================
    # AUTO-EXPIRATION
    # ========================================================================
    
    async def expire_inactive_negotiations(self) -> int:
        """
        Auto-expire negotiations that have passed expiry time.
        
        Called by background job (e.g., every hour).
        
        Returns:
            Number of negotiations expired
        """
        stmt = select(Negotiation).where(
            and_(
                Negotiation.status.in_(["INITIATED", "IN_PROGRESS"]),
                Negotiation.expires_at < datetime.utcnow()
            )
        )
        
        result = await self.db.execute(stmt)
        expired = list(result.scalars().all())
        
        for negotiation in expired:
            negotiation.status = "EXPIRED"
            negotiation.expired_at = datetime.utcnow()
            
            # Create system message
            msg = NegotiationMessage(
                negotiation_id=negotiation.id,
                sender="SYSTEM",
                message="Negotiation expired due to inactivity.",
                message_type="SYSTEM",
                is_ai_generated=False
            )
            self.db.add(msg)
            
            # Emit event
            negotiation.emit_event(
                event_type="negotiation.expired",
                user_id=negotiation.buyer_partner_id,  # Notify both parties
                data={
                    "negotiation_id": str(negotiation.id)
                }
            )
        
        await self.db.commit()
        
        return len(expired)

"""
Negotiation Model - Engine 4: Multi-round price negotiation

Handles buyer-seller negotiations after matching. Supports:
- Multi-round offer/counter-offer workflow
- Real-time WebSocket communication
- AI-assisted negotiation suggestions
- Identity revelation from anonymous matches
- Automatic expiration after 48 hours
- Integration with trade finalization

State Machine:
    INITIATED → IN_PROGRESS → ACCEPTED/REJECTED/EXPIRED

Relationships:
    - 1 MatchToken → 1 Negotiation (UNIQUE)
    - 1 Negotiation → MANY Offers (rounds)
    - 1 Negotiation → MANY Messages (chat)
    - 1 Requirement → MANY Negotiations (multiple sellers)
    - 1 Availability → MANY Negotiations (multiple buyers)
"""

from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import (
    Column, String, DateTime, ForeignKey, Boolean, 
    Numeric, Integer, Index, CheckConstraint, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB
from sqlalchemy.orm import relationship

from backend.db.base import Base
from backend.core.events.mixins import EventMixin


class Negotiation(Base, EventMixin):
    """
    Main negotiation session between buyer and seller.
    
    Created when user clicks 'Start Negotiation' on anonymous match.
    MatchToken is updated to reveal identities to both parties.
    """
    __tablename__ = "negotiations"
    
    # Primary key
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    
    # Link to anonymous match (1-to-1)
    match_token_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("match_tokens.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,  # One match = one negotiation
        comment="Anonymous match token that initiated this negotiation"
    )
    
    # Trade entities (revealed after negotiation starts)
    requirement_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("requirements.id", ondelete="CASCADE"),
        nullable=False,
        comment="Buyer requirement ID"
    )
    
    availability_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("availabilities.id", ondelete="CASCADE"),
        nullable=False,
        comment="Seller availability ID"
    )
    
    # Parties (for quick access)
    buyer_partner_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("business_partners.id"),
        nullable=False,
        comment="Buyer partner ID"
    )
    
    seller_partner_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("business_partners.id"),
        nullable=False,
        comment="Seller partner ID"
    )
    
    # Status tracking
    status = Column(
        String(20),
        nullable=False,
        default="INITIATED",
        comment="INITIATED, IN_PROGRESS, ACCEPTED, REJECTED, EXPIRED"
    )
    
    # Current negotiation state (latest offer)
    current_round = Column(
        Integer,
        nullable=False,
        default=0,
        comment="Current round number (increments with each offer)"
    )
    
    current_price_per_unit = Column(
        Numeric(15, 2),
        nullable=True,
        comment="Current price being negotiated"
    )
    
    current_quantity = Column(
        Numeric(15, 3),
        nullable=True,
        comment="Current quantity being negotiated"
    )
    
    current_terms = Column(
        JSONB,
        nullable=True,
        comment="Current negotiation terms (delivery, payment, quality)"
    )
    
    # Initiator tracking
    initiated_by = Column(
        String(10),
        nullable=False,
        comment="BUYER or SELLER (who started negotiation)"
    )
    
    last_offer_by = Column(
        String(10),
        nullable=True,
        comment="BUYER or SELLER (who made last offer)"
    )
    
    # Timestamps
    initiated_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        comment="When negotiation started"
    )
    
    last_activity_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        comment="Last activity timestamp (for expiration)"
    )
    
    expires_at = Column(
        DateTime,
        nullable=False,
        comment="Auto-expire if no activity (default 48 hours)"
    )
    
    # Outcome tracking
    accepted_by = Column(
        String(10),
        nullable=True,
        comment="BUYER or SELLER (who accepted the deal)"
    )
    
    accepted_at = Column(
        DateTime,
        nullable=True,
        comment="When deal was accepted"
    )
    
    rejected_by = Column(
        String(10),
        nullable=True,
        comment="BUYER or SELLER (who rejected)"
    )
    
    rejected_at = Column(
        DateTime,
        nullable=True,
        comment="When deal was rejected"
    )
    
    rejection_reason = Column(
        String(500),
        nullable=True,
        comment="Reason for rejection"
    )
    
    expired_at = Column(
        DateTime,
        nullable=True,
        comment="When negotiation expired"
    )
    
    # AI assistance flags
    ai_suggestions_enabled = Column(
        Boolean,
        nullable=False,
        default=True,
        comment="Allow AI to suggest counter-offers"
    )
    
    auto_negotiate_buyer = Column(
        Boolean,
        nullable=False,
        default=False,
        comment="Allow AI to negotiate on buyer's behalf"
    )
    
    auto_negotiate_seller = Column(
        Boolean,
        nullable=False,
        default=False,
        comment="Allow AI to negotiate on seller's behalf"
    )
    
    # Trade creation (FK will be added when trade engine is implemented)
    trade_id = Column(
        PGUUID(as_uuid=True),
        nullable=True,
        comment="Trade contract created if accepted (FK to trades.id)"
    )
    
    # Metadata
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    match_token = relationship("MatchToken", back_populates="negotiation")
    requirement = relationship("Requirement")
    availability = relationship("Availability")
    buyer_partner = relationship("BusinessPartner", foreign_keys=[buyer_partner_id])
    seller_partner = relationship("BusinessPartner", foreign_keys=[seller_partner_id])
    
    offers = relationship(
        "NegotiationOffer",
        back_populates="negotiation",
        cascade="all, delete-orphan",
        order_by="NegotiationOffer.round_number"
    )
    
    messages = relationship(
        "NegotiationMessage",
        back_populates="negotiation",
        cascade="all, delete-orphan",
        order_by="NegotiationMessage.created_at"
    )
    
    # Constraints
    __table_args__ = (
        CheckConstraint("status IN ('INITIATED', 'IN_PROGRESS', 'ACCEPTED', 'REJECTED', 'EXPIRED')", name="check_negotiation_status"),
        CheckConstraint("initiated_by IN ('BUYER', 'SELLER')", name="check_initiated_by"),
        CheckConstraint("last_offer_by IS NULL OR last_offer_by IN ('BUYER', 'SELLER')", name="check_last_offer_by"),
        CheckConstraint("accepted_by IS NULL OR accepted_by IN ('BUYER', 'SELLER')", name="check_accepted_by"),
        CheckConstraint("rejected_by IS NULL OR rejected_by IN ('BUYER', 'SELLER')", name="check_rejected_by"),
        CheckConstraint("current_round >= 0", name="check_current_round_non_negative"),
        CheckConstraint("current_price_per_unit IS NULL OR current_price_per_unit > 0", name="check_price_positive"),
        CheckConstraint("current_quantity IS NULL OR current_quantity > 0", name="check_quantity_positive"),
        Index("idx_negotiations_match_token", "match_token_id"),
        Index("idx_negotiations_requirement", "requirement_id"),
        Index("idx_negotiations_availability", "availability_id"),
        Index("idx_negotiations_status", "status"),
        Index("idx_negotiations_expires", "expires_at"),
        Index("idx_negotiations_buyer", "buyer_partner_id"),
        Index("idx_negotiations_seller", "seller_partner_id"),
    )
    
    def __init__(self, **kwargs):
        """Initialize with default expiry (48 hours)"""
        super().__init__(**kwargs)
        if not self.expires_at:
            self.expires_at = datetime.utcnow() + timedelta(hours=48)
        # Initialize pending events list
        self._pending_events = []
    
    @property
    def is_expired(self) -> bool:
        """Check if negotiation has expired"""
        return datetime.utcnow() > self.expires_at
    
    @property
    def is_active(self) -> bool:
        """Check if negotiation is still active"""
        return self.status in ["INITIATED", "IN_PROGRESS"]
    
    @property
    def can_make_offer(self) -> bool:
        """Check if new offers can be made"""
        return self.is_active and not self.is_expired
    
    def update_activity(self):
        """Update last activity timestamp"""
        self.last_activity_at = datetime.utcnow()
    
    def __repr__(self) -> str:
        return f"<Negotiation {self.id} status={self.status} round={self.current_round}>"

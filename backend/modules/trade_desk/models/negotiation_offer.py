"""
Negotiation Offer Model - Individual rounds of offers/counter-offers

Each offer represents one round in the negotiation:
- Round 1: Initial offer
- Round 2: Counter-offer
- Round 3: Another counter-offer
- etc.

Tracks complete negotiation history for:
- Audit trail
- AI training data
- Analytics
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import (
    Column, String, DateTime, ForeignKey, Boolean,
    Numeric, Integer, Index, CheckConstraint, Text
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB
from sqlalchemy.orm import relationship

from backend.db.base import Base


class NegotiationOffer(Base):
    """
    Individual offer/counter-offer in negotiation rounds.
    
    Example flow:
        Round 1: Buyer offers ₹7,100/qtl
        Round 2: Seller counters ₹7,200/qtl
        Round 3: Buyer counters ₹7,150/qtl
        Round 4: Seller ACCEPTS
    """
    __tablename__ = "negotiation_offers"
    
    # Primary key
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    
    # Parent negotiation
    negotiation_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("negotiations.id", ondelete="CASCADE"),
        nullable=False,
        comment="Parent negotiation session"
    )
    
    # Round tracking
    round_number = Column(
        Integer,
        nullable=False,
        comment="Sequential round number (1, 2, 3...)"
    )
    
    # Who made this offer
    offered_by = Column(
        String(10),
        nullable=False,
        comment="BUYER or SELLER"
    )
    
    # Offer details
    price_per_unit = Column(
        Numeric(15, 2),
        nullable=False,
        comment="Offered price per unit"
    )
    
    quantity = Column(
        Numeric(15, 3),
        nullable=False,
        comment="Offered quantity"
    )
    
    # Additional terms
    delivery_terms = Column(
        JSONB,
        nullable=True,
        comment="Delivery location, timeline, Incoterms"
    )
    # Example: {
    #   "location": "Ex-Works Surat",
    #   "timeline_days": 7,
    #   "incoterms": "FOB"
    # }
    
    payment_terms = Column(
        JSONB,
        nullable=True,
        comment="Payment method, timeline, advance percentage"
    )
    # Example: {
    #   "method": "Bank Transfer",
    #   "advance_percent": 30,
    #   "payment_days": 15
    # }
    
    quality_conditions = Column(
        JSONB,
        nullable=True,
        comment="Quality parameters and acceptance criteria"
    )
    # Example: {
    #   "moisture_max": 8.0,
    #   "trash_max": 2.5,
    #   "inspection_agency": "BIS"
    # }
    
    # Human/AI message
    message = Column(
        Text,
        nullable=True,
        comment="Human or AI-written message accompanying offer"
    )
    
    # AI assistance tracking
    ai_generated = Column(
        Boolean,
        nullable=False,
        default=False,
        comment="Was this offer suggested by AI?"
    )
    
    ai_confidence = Column(
        Numeric(3, 2),
        nullable=True,
        comment="AI confidence score (0.00-1.00) if AI-generated"
    )
    
    ai_reasoning = Column(
        Text,
        nullable=True,
        comment="AI explanation for this offer"
    )
    
    # Response tracking
    status = Column(
        String(20),
        nullable=False,
        default="PENDING",
        comment="PENDING, ACCEPTED, REJECTED, COUNTERED, EXPIRED"
    )
    
    responded_at = Column(
        DateTime,
        nullable=True,
        comment="When counterparty responded"
    )
    
    response_message = Column(
        Text,
        nullable=True,
        comment="Response message if rejected"
    )
    
    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Relationships
    negotiation = relationship("Negotiation", back_populates="offers")
    
    # Constraints
    __table_args__ = (
        CheckConstraint("offered_by IN ('BUYER', 'SELLER')", name="check_offer_offered_by"),
        CheckConstraint("status IN ('PENDING', 'ACCEPTED', 'REJECTED', 'COUNTERED', 'EXPIRED')", name="check_offer_status"),
        CheckConstraint("round_number > 0", name="check_round_positive"),
        CheckConstraint("price_per_unit > 0", name="check_offer_price_positive"),
        CheckConstraint("quantity > 0", name="check_offer_quantity_positive"),
        CheckConstraint("ai_confidence IS NULL OR (ai_confidence >= 0 AND ai_confidence <= 1)", name="check_ai_confidence_range"),
        Index("idx_offers_negotiation", "negotiation_id"),
        Index("idx_offers_round", "negotiation_id", "round_number"),
        Index("idx_offers_status", "status"),
    )
    
    def __repr__(self) -> str:
        return f"<NegotiationOffer round={self.round_number} by={self.offered_by} price={self.price_per_unit}>"

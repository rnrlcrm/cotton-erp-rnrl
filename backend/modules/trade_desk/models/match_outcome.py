"""
Match Outcome Model - Track match success for ML training

Stores the results of every match attempt to train ML models that predict
match success probability.

Features:
- Tracks match score, negotiation rounds, and final outcome
- Stores feature values used for scoring (quality, price, distance, etc.)
- Records buyer/seller satisfaction ratings
- Enables model retraining on real outcomes
"""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PostgreSQLUUID
from sqlalchemy.orm import relationship

from backend.db.session import Base


class MatchOutcome(Base):
    """
    Track match outcomes for ML model training.
    
    Lifecycle:
    1. MATCHED - Initial match created
    2. NEGOTIATING - In negotiation phase
    3. COMPLETED - Trade successfully completed
    4. FAILED - Match/negotiation/trade failed
    
    Used for:
    - Training ML match success predictor
    - A/B testing scoring algorithms
    - Performance analytics
    """
    
    __tablename__ = "match_outcomes"
    
    # Primary Key
    id = Column(
        PostgreSQLUUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False
    )
    
    # Foreign Keys
    requirement_id = Column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("requirements.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    availability_id = Column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("availabilities.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    trade_id = Column(
        PostgreSQLUUID(as_uuid=True),
        ForeignKey("trades.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Trade created from this match (if successful)"
    )
    
    # Match Scoring Features (for ML training)
    match_score = Column(
        Numeric(5, 4),
        nullable=False,
        comment="Overall match score (0.0-1.0)"
    )
    
    quality_score = Column(
        Numeric(5, 4),
        nullable=False,
        comment="Quality compatibility score (0.0-1.0)"
    )
    
    price_score = Column(
        Numeric(5, 4),
        nullable=False,
        comment="Price competitiveness score (0.0-1.0)"
    )
    
    delivery_score = Column(
        Numeric(5, 4),
        nullable=False,
        comment="Delivery logistics score (0.0-1.0)"
    )
    
    risk_score = Column(
        Numeric(5, 4),
        nullable=False,
        comment="Risk assessment score (0.0-1.0)"
    )
    
    # Geographic distance (km)
    distance_km = Column(
        Numeric(10, 2),
        nullable=True,
        comment="Distance between buyer and seller locations"
    )
    
    # Price difference (%)
    price_difference_pct = Column(
        Numeric(6, 2),
        nullable=True,
        comment="Price diff: (availability_price - max_budget) / max_budget * 100"
    )
    
    # Negotiation tracking
    negotiation_started = Column(
        Boolean,
        nullable=False,
        default=False,
        comment="Whether negotiation was initiated"
    )
    
    negotiation_rounds = Column(
        Integer,
        nullable=True,
        comment="Number of negotiation rounds (if applicable)"
    )
    
    final_price = Column(
        Numeric(15, 2),
        nullable=True,
        comment="Final negotiated price per unit"
    )
    
    # Outcome tracking
    trade_completed = Column(
        Boolean,
        nullable=False,
        default=False,
        comment="Whether trade was successfully completed"
    )
    
    quality_accepted = Column(
        Boolean,
        nullable=True,
        comment="Whether quality was accepted on delivery"
    )
    
    payment_on_time = Column(
        Boolean,
        nullable=True,
        comment="Whether payment was made on time"
    )
    
    delivery_on_time = Column(
        Boolean,
        nullable=True,
        comment="Whether delivery was made on time"
    )
    
    # Satisfaction ratings (1-5 stars)
    buyer_satisfaction = Column(
        Integer,
        nullable=True,
        comment="Buyer satisfaction rating (1-5)"
    )
    
    seller_satisfaction = Column(
        Integer,
        nullable=True,
        comment="Seller satisfaction rating (1-5)"
    )
    
    # Additional features (stored as JSONB for flexibility)
    additional_features = Column(
        JSONB,
        nullable=True,
        comment="Additional features for ML: commodity_id, variety_id, buyer_rating, seller_rating, etc."
    )
    
    # Failure reason (if failed)
    failure_reason = Column(
        String(500),
        nullable=True,
        comment="Reason for match failure (if applicable)"
    )
    
    # Timestamps
    matched_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("now()"),
        comment="When match was created"
    )
    
    completed_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="When trade was completed (if successful)"
    )
    
    failed_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="When match failed (if failed)"
    )
    
    # Relationships
    # requirement = relationship("Requirement", foreign_keys=[requirement_id])
    # availability = relationship("Availability", foreign_keys=[availability_id])
    # trade = relationship("Trade", foreign_keys=[trade_id])
    
    def __repr__(self) -> str:
        return f"<MatchOutcome(id={self.id}, match_score={self.match_score}, completed={self.trade_completed})>"
    
    def to_ml_features(self) -> dict:
        """
        Convert to feature dict for ML model training.
        
        Returns:
            Dict with features ready for ML model
        """
        return {
            "match_score": float(self.match_score),
            "quality_score": float(self.quality_score),
            "price_score": float(self.price_score),
            "delivery_score": float(self.delivery_score),
            "risk_score": float(self.risk_score),
            "distance_km": float(self.distance_km) if self.distance_km else 0.0,
            "price_difference_pct": float(self.price_difference_pct) if self.price_difference_pct else 0.0,
            "negotiation_rounds": self.negotiation_rounds or 0,
            # Target variable
            "success": 1 if self.trade_completed else 0,
            # Additional features from JSONB
            **(self.additional_features or {})
        }

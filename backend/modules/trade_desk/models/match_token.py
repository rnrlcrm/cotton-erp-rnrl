"""
Anonymous Match Token Model

Generates anonymous tokens to hide party identities until negotiation starts.
Maps tokens to actual requirement/availability IDs for progressive disclosure.

Privacy Levels:
    - MATCHED: Anonymous token only (no identity)
    - NEGOTIATING: Identity revealed when negotiation begins
    - TRADE: Full details for completed trades
"""

from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID, uuid4
import secrets

from sqlalchemy import Column, String, DateTime, ForeignKey, Enum as SQLEnum, Index
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import relationship

from backend.db.base import Base


class MatchToken(Base):
    """
    Anonymous tokens for hiding party identities in match results.
    
    When a match is found, both parties get anonymous tokens instead of real IDs.
    Only when negotiation starts are identities revealed.
    
    Example:
        Buyer sees: "MATCH-A7B2C" (anonymous seller token)
        Seller sees: "MATCH-X9Y4Z" (anonymous buyer token)
        
        When negotiation starts → tokens map to real partner IDs
    """
    __tablename__ = "match_tokens"
    
    # Primary key
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    
    # Anonymous token (shown to users)
    token = Column(
        String(32), 
        unique=True, 
        nullable=False,
        index=True,
        comment="Anonymous token shown to users (e.g., MATCH-A7B2C)"
    )
    
    # Actual IDs (hidden until disclosure)
    requirement_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("requirements.id", ondelete="CASCADE"),
        nullable=False,
        comment="Buyer requirement ID (hidden)"
    )
    
    availability_id = Column(
        PGUUID(as_uuid=True),
        ForeignKey("availabilities.id", ondelete="CASCADE"),
        nullable=False,
        comment="Seller availability ID (hidden)"
    )
    
    # Match details
    match_score = Column(
        String(10),
        nullable=False,
        comment="Match score (0.00-1.00) as string for JSON"
    )
    
    # Disclosure tracking
    disclosed_to_buyer = Column(
        String(20),
        nullable=False,
        default="MATCHED",
        comment="Disclosure level for buyer: MATCHED, NEGOTIATING, TRADE"
    )
    
    disclosed_to_seller = Column(
        String(20),
        nullable=False,
        default="MATCHED",
        comment="Disclosure level for seller: MATCHED, NEGOTIATING, TRADE"
    )
    
    # Negotiation tracking (when identities revealed)
    negotiation_started_at = Column(
        DateTime,
        nullable=True,
        comment="When negotiation began and identities were revealed"
    )
    
    # Token lifecycle
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    expires_at = Column(
        DateTime,
        nullable=False,
        comment="Token expires after 30 days if no negotiation"
    )
    
    # Relationships
    requirement = relationship("Requirement", back_populates="match_tokens")
    availability = relationship("Availability", back_populates="match_tokens")
    
    # Indexes for fast lookups
    __table_args__ = (
        Index("idx_match_tokens_requirement", "requirement_id"),
        Index("idx_match_tokens_availability", "availability_id"),
        Index("idx_match_tokens_expires", "expires_at"),
    )
    
    def __init__(self, **kwargs):
        """Initialize with auto-generated token and expiry"""
        super().__init__(**kwargs)
        if not self.token:
            self.token = self._generate_token()
        if not self.expires_at:
            self.expires_at = datetime.utcnow() + timedelta(days=30)
    
    @staticmethod
    def _generate_token() -> str:
        """Generate cryptographically secure anonymous token"""
        # Format: MATCH-XXXXX (5 random chars)
        random_part = secrets.token_hex(3).upper()[:5]
        return f"MATCH-{random_part}"
    
    def reveal_to_buyer(self) -> None:
        """Reveal seller identity to buyer (negotiation started)"""
        self.disclosed_to_buyer = "NEGOTIATING"
        self.negotiation_started_at = datetime.utcnow()
    
    def reveal_to_seller(self) -> None:
        """Reveal buyer identity to seller (negotiation started)"""
        self.disclosed_to_seller = "NEGOTIATING"
        self.negotiation_started_at = datetime.utcnow()
    
    def mark_traded(self) -> None:
        """Mark as traded (full disclosure for both parties)"""
        self.disclosed_to_buyer = "TRADE"
        self.disclosed_to_seller = "TRADE"
    
    @property
    def is_expired(self) -> bool:
        """Check if token has expired"""
        return datetime.utcnow() > self.expires_at
    
    @property
    def is_negotiating(self) -> bool:
        """Check if negotiation has started"""
        return self.negotiation_started_at is not None
    
    def __repr__(self) -> str:
        return f"<MatchToken {self.token} req={self.requirement_id} avail={self.availability_id}>"

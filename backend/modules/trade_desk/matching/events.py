"""
Matching Engine Domain Events

Events emitted by matching engine for:
- Match found (buyer-seller matched)
- Match rejected (validation failed)
- Match allocated (quantity reserved)

Part of event-driven architecture for real-time notifications.
"""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID
from typing import Dict, List, Optional


@dataclass
class MatchFoundEvent:
    """
    Event: Match found between requirement and availability
    
    Emitted when matching engine finds a valid match above threshold.
    Triggers notifications to buyer and seller.
    """
    event_id: UUID
    event_type: str = "match.found"
    occurred_at: datetime = None
    
    # Match details
    requirement_id: UUID = None
    availability_id: UUID = None
    buyer_id: UUID = None
    seller_id: UUID = None
    commodity_id: UUID = None
    
    # Match score
    score: float = None
    base_score: float = None
    warn_penalty_applied: bool = False
    ai_boost_applied: bool = False
    
    # Score breakdown
    quality_score: float = None
    price_score: float = None
    delivery_score: float = None
    risk_score: float = None
    
    # Risk details
    risk_status: Optional[str] = None
    risk_score: Optional[int] = None
    
    # Match context
    matched_quantity: float = None
    matched_price: float = None
    location_id: Optional[UUID] = None
    
    # AI integration
    ai_recommended: bool = False
    ai_confidence: Optional[int] = None
    
    def __post_init__(self):
        if self.occurred_at is None:
            self.occurred_at = datetime.utcnow()
    
    def to_dict(self) -> Dict:
        """Convert event to dictionary for serialization"""
        return {
            "event_id": str(self.event_id),
            "event_type": self.event_type,
            "occurred_at": self.occurred_at.isoformat() if self.occurred_at else None,
            "requirement_id": str(self.requirement_id) if self.requirement_id else None,
            "availability_id": str(self.availability_id) if self.availability_id else None,
            "buyer_id": str(self.buyer_id) if self.buyer_id else None,
            "seller_id": str(self.seller_id) if self.seller_id else None,
            "commodity_id": str(self.commodity_id) if self.commodity_id else None,
            "score": self.score,
            "base_score": self.base_score,
            "warn_penalty_applied": self.warn_penalty_applied,
            "ai_boost_applied": self.ai_boost_applied,
            "score_breakdown": {
                "quality": self.quality_score,
                "price": self.price_score,
                "delivery": self.delivery_score,
                "risk": self.risk_score
            },
            "risk_status": self.risk_status,
            "risk_score": self.risk_score,
            "matched_quantity": self.matched_quantity,
            "matched_price": self.matched_price,
            "location_id": str(self.location_id) if self.location_id else None,
            "ai_recommended": self.ai_recommended,
            "ai_confidence": self.ai_confidence
        }


@dataclass
class MatchRejectedEvent:
    """
    Event: Match rejected due to validation failure
    
    Emitted when potential match fails validation (risk FAIL, budget exceeded, etc.)
    Used for analytics and debugging.
    """
    event_id: UUID
    event_type: str = "match.rejected"
    occurred_at: datetime = None
    
    # Match attempt details
    requirement_id: UUID = None
    availability_id: UUID = None
    buyer_id: UUID = None
    seller_id: UUID = None
    commodity_id: UUID = None
    
    # Rejection reasons
    rejection_reasons: List[str] = None
    warnings: List[str] = None
    ai_alerts: List[str] = None
    
    # Validation details
    risk_status: Optional[str] = None
    risk_score: Optional[int] = None
    location_matched: bool = True
    
    def __post_init__(self):
        if self.occurred_at is None:
            self.occurred_at = datetime.utcnow()
        if self.rejection_reasons is None:
            self.rejection_reasons = []
        if self.warnings is None:
            self.warnings = []
        if self.ai_alerts is None:
            self.ai_alerts = []
    
    def to_dict(self) -> Dict:
        """Convert event to dictionary for serialization"""
        return {
            "event_id": str(self.event_id),
            "event_type": self.event_type,
            "occurred_at": self.occurred_at.isoformat() if self.occurred_at else None,
            "requirement_id": str(self.requirement_id) if self.requirement_id else None,
            "availability_id": str(self.availability_id) if self.availability_id else None,
            "buyer_id": str(self.buyer_id) if self.buyer_id else None,
            "seller_id": str(self.seller_id) if self.seller_id else None,
            "commodity_id": str(self.commodity_id) if self.commodity_id else None,
            "rejection_reasons": self.rejection_reasons,
            "warnings": self.warnings,
            "ai_alerts": self.ai_alerts,
            "risk_status": self.risk_status,
            "risk_score": self.risk_score,
            "location_matched": self.location_matched
        }


@dataclass
class MatchAllocatedEvent:
    """
    Event: Match allocated (quantity reserved atomically)
    
    Emitted after successful atomic allocation of availability quantity.
    Triggers contract creation and fulfillment workflows.
    """
    event_id: UUID
    event_type: str = "match.allocated"
    occurred_at: datetime = None
    
    # Match details
    requirement_id: UUID = None
    availability_id: UUID = None
    buyer_id: UUID = None
    seller_id: UUID = None
    commodity_id: UUID = None
    
    # Allocation details
    allocated_quantity: float = None
    remaining_quantity: float = None
    allocation_type: str = None  # "FULL" or "PARTIAL"
    
    # Match score (for reference)
    match_score: float = None
    
    # Transaction details
    version_before: int = None
    version_after: int = None
    allocated_at: datetime = None
    
    def __post_init__(self):
        if self.occurred_at is None:
            self.occurred_at = datetime.utcnow()
        if self.allocated_at is None:
            self.allocated_at = datetime.utcnow()
    
    def to_dict(self) -> Dict:
        """Convert event to dictionary for serialization"""
        return {
            "event_id": str(self.event_id),
            "event_type": self.event_type,
            "occurred_at": self.occurred_at.isoformat() if self.occurred_at else None,
            "requirement_id": str(self.requirement_id) if self.requirement_id else None,
            "availability_id": str(self.availability_id) if self.availability_id else None,
            "buyer_id": str(self.buyer_id) if self.buyer_id else None,
            "seller_id": str(self.seller_id) if self.seller_id else None,
            "commodity_id": str(self.commodity_id) if self.commodity_id else None,
            "allocated_quantity": self.allocated_quantity,
            "remaining_quantity": self.remaining_quantity,
            "allocation_type": self.allocation_type,
            "match_score": self.match_score,
            "version_before": self.version_before,
            "version_after": self.version_after,
            "allocated_at": self.allocated_at.isoformat() if self.allocated_at else None
        }

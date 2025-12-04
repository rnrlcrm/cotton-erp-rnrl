"""
Pydantic Schemas for Negotiation API

Request/Response models for negotiation endpoints.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from decimal import Decimal
from uuid import UUID
from enum import Enum

from pydantic import BaseModel, Field, field_validator


# ---------- Enums ----------

class NegotiationStatus(str, Enum):
    """Negotiation status"""
    INITIATED = "INITIATED"
    IN_PROGRESS = "IN_PROGRESS"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"


class PartyEnum(str, Enum):
    """Party in negotiation"""
    BUYER = "BUYER"
    SELLER = "SELLER"


class MessageSender(str, Enum):
    """Message sender type"""
    BUYER = "BUYER"
    SELLER = "SELLER"
    SYSTEM = "SYSTEM"
    AI_BOT = "AI_BOT"


class MessageType(str, Enum):
    """Message type"""
    TEXT = "TEXT"
    OFFER = "OFFER"
    ACCEPTANCE = "ACCEPTANCE"
    REJECTION = "REJECTION"
    SYSTEM = "SYSTEM"
    AI_SUGGESTION = "AI_SUGGESTION"


# ---------- Request Schemas ----------

class StartNegotiationRequest(BaseModel):
    """Start negotiation from match token"""
    match_token: str = Field(..., description="Anonymous match token")
    initial_message: Optional[str] = Field(None, description="Opening message")


class MakeOfferRequest(BaseModel):
    """Make or counter an offer"""
    price_per_unit: Decimal = Field(..., gt=0, description="Price per unit")
    quantity: int = Field(..., gt=0, description="Quantity")
    delivery_terms: Optional[Dict[str, Any]] = Field(None, description="Delivery terms")
    payment_terms: Optional[Dict[str, Any]] = Field(None, description="Payment terms")
    quality_conditions: Optional[Dict[str, Any]] = Field(None, description="Quality specs")
    message: Optional[str] = Field(None, description="Message with offer")
    
    @field_validator("price_per_unit")
    @classmethod
    def validate_price(cls, v):
        if v <= 0:
            raise ValueError("Price must be positive")
        return v


class AcceptOfferRequest(BaseModel):
    """Accept the current offer"""
    acceptance_message: Optional[str] = Field(None, description="Acceptance message")


class RejectOfferRequest(BaseModel):
    """Reject offer with optional counter"""
    rejection_reason: Optional[str] = Field(None, description="Reason for rejection")
    make_counter_offer: bool = Field(False, description="Make counter immediately")
    
    # Counter-offer details (if make_counter_offer=True)
    counter_price: Optional[Decimal] = Field(None, gt=0)
    counter_quantity: Optional[int] = Field(None, gt=0)
    counter_delivery_terms: Optional[Dict[str, Any]] = None
    counter_payment_terms: Optional[Dict[str, Any]] = None
    counter_quality_conditions: Optional[Dict[str, Any]] = None
    counter_message: Optional[str] = None


class SendMessageRequest(BaseModel):
    """Send chat message"""
    message: str = Field(..., min_length=1, max_length=5000)
    message_type: MessageType = Field(MessageType.TEXT)


class AIAssistRequest(BaseModel):
    """Request AI suggestion"""
    offer_id: Optional[UUID] = Field(None, description="Offer to analyze")


# ---------- Response Schemas ----------

class PartnerSummary(BaseModel):
    """Partner summary (for response)"""
    id: UUID
    business_name: str
    business_type: str


class OfferResponse(BaseModel):
    """Negotiation offer response"""
    id: UUID
    negotiation_id: UUID
    round_number: int
    offered_by: PartyEnum
    price_per_unit: Decimal
    quantity: int
    delivery_terms: Optional[Dict[str, Any]]
    payment_terms: Optional[Dict[str, Any]]
    quality_conditions: Optional[Dict[str, Any]]
    message: Optional[str]
    status: str
    ai_generated: bool
    ai_confidence: Optional[float]
    created_at: datetime
    responded_at: Optional[datetime]
    response_message: Optional[str]
    
    class Config:
        from_attributes = True


class MessageResponse(BaseModel):
    """Chat message response"""
    id: UUID
    negotiation_id: UUID
    sender: MessageSender
    message: str
    message_type: MessageType
    read_by_buyer: bool
    read_by_seller: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


class NegotiationResponse(BaseModel):
    """Full negotiation response"""
    id: UUID
    match_token_id: UUID
    requirement_id: UUID
    availability_id: UUID
    buyer_partner_id: UUID
    seller_partner_id: UUID
    
    status: NegotiationStatus
    current_round: int
    current_price_per_unit: Optional[Decimal]
    current_quantity: Optional[int]
    current_terms: Optional[Dict[str, Any]]
    
    initiated_at: datetime
    last_activity_at: datetime
    expires_at: datetime
    
    # Outcome
    accepted_by: Optional[PartyEnum]
    rejected_by: Optional[PartyEnum]
    rejection_reason: Optional[str]
    trade_id: Optional[UUID]
    
    # AI settings
    ai_suggestions_enabled: bool
    auto_negotiate_buyer: bool
    auto_negotiate_seller: bool
    
    # User's role
    user_role: Optional[PartyEnum] = None
    
    # Related entities
    buyer: Optional[PartnerSummary] = None
    seller: Optional[PartnerSummary] = None
    offers: List[OfferResponse] = []
    messages: List[MessageResponse] = []
    
    class Config:
        from_attributes = True


class NegotiationListItem(BaseModel):
    """Negotiation list item (summary)"""
    id: UUID
    status: NegotiationStatus
    current_round: int
    current_price_per_unit: Optional[Decimal]
    user_role: PartyEnum
    counterparty_name: str
    commodity_name: str
    initiated_at: datetime
    expires_at: datetime
    unread_messages: int
    
    class Config:
        from_attributes = True


class NegotiationListResponse(BaseModel):
    """Paginated negotiation list"""
    items: List[NegotiationListItem]
    total: int
    limit: int
    offset: int


class AICounterOfferSuggestion(BaseModel):
    """AI-generated counter-offer suggestion"""
    suggested_price: Decimal
    suggested_quantity: int
    confidence: float = Field(..., ge=0, le=1)
    reasoning: str
    acceptance_probability: float = Field(..., ge=0, le=1)
    market_comparison: Dict[str, Any]


class WebSocketMessage(BaseModel):
    """WebSocket event message"""
    type: str
    negotiation_id: UUID
    data: Dict[str, Any]
    timestamp: datetime

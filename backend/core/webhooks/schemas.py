"""
Webhook Event Schemas

Defines webhook event types and payloads.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, HttpUrl


class WebhookEventType(str, Enum):
    """Webhook event types"""
    
    # Trade events
    TRADE_CREATED = "trade.created"
    TRADE_UPDATED = "trade.updated"
    TRADE_CONFIRMED = "trade.confirmed"
    TRADE_CANCELLED = "trade.cancelled"
    
    # Payment events
    PAYMENT_COMPLETED = "payment.completed"
    PAYMENT_FAILED = "payment.failed"
    
    # Contract events
    CONTRACT_SIGNED = "contract.signed"
    CONTRACT_EXPIRED = "contract.expired"
    
    # Quality events
    QUALITY_INSPECTION_COMPLETED = "quality.inspection.completed"
    
    # Shipment events
    SHIPMENT_DELIVERED = "shipment.delivered"
    
    # User events
    USER_CREATED = "user.created"
    USER_UPDATED = "user.updated"


class WebhookEvent(BaseModel):
    """
    Webhook event payload.
    
    Sent to subscriber endpoints.
    """
    
    id: str = Field(default_factory=lambda: str(uuid4()))
    event_type: WebhookEventType
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Data
    data: Dict[str, Any] = Field(default_factory=dict)
    
    # Context
    organization_id: Optional[UUID] = None
    user_id: Optional[UUID] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: lambda v: str(v),
        }


class WebhookSubscription(BaseModel):
    """
    Webhook subscription configuration.
    
    Defines what events a subscriber wants and where to send them.
    """
    
    id: UUID = Field(default_factory=uuid4)
    organization_id: UUID  # Multi-tenant: each org has its own subscriptions
    
    # Subscription details
    url: HttpUrl
    event_types: list[WebhookEventType]
    is_active: bool = True
    
    # Security
    secret: str  # HMAC signing secret
    
    # Retry configuration
    max_retries: int = 3
    retry_delay_seconds: int = 60
    
    # Metadata
    description: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    created_by: Optional[UUID] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: lambda v: str(v),
        }

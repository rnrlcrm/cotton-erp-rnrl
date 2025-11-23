"""
Domain Event Schemas

Common event types and schemas for the ERP system.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class EventType(str, Enum):
    """Domain event types"""
    
    # User events
    USER_CREATED = "user.created"
    USER_UPDATED = "user.updated"
    USER_DELETED = "user.deleted"
    USER_LOGIN = "user.login"
    USER_LOGOUT = "user.logout"
    
    # Trade events
    TRADE_CREATED = "trade.created"
    TRADE_UPDATED = "trade.updated"
    TRADE_CONFIRMED = "trade.confirmed"
    TRADE_CANCELLED = "trade.cancelled"
    TRADE_COMPLETED = "trade.completed"
    
    # Order events
    ORDER_CREATED = "order.created"
    ORDER_FILLED = "order.filled"
    ORDER_CANCELLED = "order.cancelled"
    
    # Payment events
    PAYMENT_INITIATED = "payment.initiated"
    PAYMENT_COMPLETED = "payment.completed"
    PAYMENT_FAILED = "payment.failed"
    
    # Contract events
    CONTRACT_CREATED = "contract.created"
    CONTRACT_SIGNED = "contract.signed"
    CONTRACT_EXPIRED = "contract.expired"
    
    # Quality events
    QUALITY_INSPECTION_REQUESTED = "quality.inspection.requested"
    QUALITY_INSPECTION_COMPLETED = "quality.inspection.completed"
    
    # Logistics events
    SHIPMENT_CREATED = "logistics.shipment.created"
    SHIPMENT_IN_TRANSIT = "logistics.shipment.in_transit"
    SHIPMENT_DELIVERED = "logistics.shipment.delivered"
    
    # Price events
    PRICE_UPDATED = "market.price.updated"
    PRICE_ALERT = "market.price.alert"
    
    # Notification events
    NOTIFICATION_SENT = "notification.sent"
    EMAIL_SENT = "notification.email.sent"
    SMS_SENT = "notification.sms.sent"
    
    # Audit events
    AUDIT_LOG_CREATED = "audit.log.created"
    
    # System events
    SYSTEM_ERROR = "system.error"
    SYSTEM_WARNING = "system.warning"


class EventPriority(str, Enum):
    """Event priority levels"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class DomainEvent(BaseModel):
    """
    Base domain event.
    
    All events in the system follow this schema.
    """
    
    # Event metadata
    id: str = Field(default_factory=lambda: str(uuid4()))
    event_type: EventType
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    version: str = "1.0"
    
    # Event context
    aggregate_id: Optional[UUID] = None  # ID of the entity (trade_id, user_id, etc.)
    aggregate_type: Optional[str] = None  # Type of entity (trade, user, etc.)
    user_id: Optional[UUID] = None  # User who triggered the event
    organization_id: Optional[UUID] = None  # Organization context
    
    # Event data
    data: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    # Event priority
    priority: EventPriority = EventPriority.NORMAL
    
    # Tracing
    trace_id: Optional[str] = None  # For distributed tracing
    correlation_id: Optional[str] = None  # For correlating related events
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: lambda v: str(v),
        }


class TradeCreatedEvent(DomainEvent):
    """Trade created event"""
    event_type: EventType = EventType.TRADE_CREATED
    aggregate_type: str = "trade"


class PaymentCompletedEvent(DomainEvent):
    """Payment completed event"""
    event_type: EventType = EventType.PAYMENT_COMPLETED
    aggregate_type: str = "payment"


class PriceUpdatedEvent(DomainEvent):
    """Price updated event"""
    event_type: EventType = EventType.PRICE_UPDATED
    aggregate_type: str = "price"


class UserLoginEvent(DomainEvent):
    """User login event"""
    event_type: EventType = EventType.USER_LOGIN
    aggregate_type: str = "user"

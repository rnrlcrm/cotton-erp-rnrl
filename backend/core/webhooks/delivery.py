"""
Webhook Delivery Tracking

Tracks webhook delivery attempts, retries, and failures.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class DeliveryStatus(str, Enum):
    """Webhook delivery status"""
    PENDING = "pending"
    SENDING = "sending"
    SUCCESS = "success"
    FAILED = "failed"
    RETRYING = "retrying"
    DEAD_LETTER = "dead_letter"  # Moved to DLQ after max retries


class WebhookDelivery(BaseModel):
    """
    Webhook delivery record.
    
    Tracks each attempt to deliver a webhook.
    """
    
    id: UUID = Field(default_factory=uuid4)
    subscription_id: UUID
    event_id: str
    
    # Delivery details
    status: DeliveryStatus = DeliveryStatus.PENDING
    attempt: int = 0
    max_attempts: int = 3
    
    # Request/response
    url: str
    request_body: str
    request_headers: dict = Field(default_factory=dict)
    
    response_status: Optional[int] = None
    response_body: Optional[str] = None
    response_headers: Optional[dict] = None
    
    # Timing
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    sent_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    next_retry_at: Optional[datetime] = None
    
    # Error tracking
    error_message: Optional[str] = None
    error_code: Optional[str] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: lambda v: str(v),
        }

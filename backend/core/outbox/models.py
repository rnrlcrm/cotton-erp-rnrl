"""
Outbox Pattern Implementation

Ensures transactional safety for event publishing using the Transactional Outbox pattern.
Events are written to the database in the same transaction as business data, then published
asynchronously by a background worker.

This guarantees:
- No lost events (if transaction commits, event is guaranteed to be published)
- No duplicate events (idempotency keys prevent duplicates)
- Exactly-once delivery semantics when combined with consumer idempotency
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Column, DateTime, Enum as SQLEnum, Integer, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB, UUID

from backend.db.session import Base


class OutboxStatus(str, enum.Enum):
    """Status of an outbox event"""
    PENDING = "pending"  # Waiting to be published
    PUBLISHED = "published"  # Successfully published to Pub/Sub
    FAILED = "failed"  # Failed after max retries
    PROCESSING = "processing"  # Currently being processed


class EventOutbox(Base):
    """
    Transactional Outbox for Domain Events
    
    All domain events are written here first, then published to GCP Pub/Sub
    by a background worker. This ensures events are never lost even if
    Pub/Sub is temporarily unavailable.
    
    Workflow:
    1. Service writes business data + event to outbox in SAME transaction
    2. Transaction commits (both succeed or both fail)
    3. Background worker polls outbox for PENDING events
    4. Worker publishes to Pub/Sub and marks as PUBLISHED
    5. If publish fails, retry with exponential backoff
    6. After max retries, mark as FAILED and alert ops team
    
    Retention: Keep published events for 30 days for audit/replay
    """
    
    __tablename__ = "event_outbox"
    
    # Primary fields
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    aggregate_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    aggregate_type = Column(String(50), nullable=False, index=True)
    event_type = Column(String(100), nullable=False, index=True)
    
    # Event payload
    payload = Column(JSONB, nullable=False)  # Full event data
    event_metadata = Column(JSONB, nullable=True)  # Renamed from 'metadata' to avoid SQLAlchemy conflict
    
    # Publishing status
    status = Column(
        SQLEnum(OutboxStatus),
        nullable=False,
        default=OutboxStatus.PENDING,
        index=True
    )
    
    # Retry management
    retry_count = Column(Integer, nullable=False, default=0)
    max_retries = Column(Integer, nullable=False, default=5)
    next_retry_at = Column(DateTime(timezone=True), nullable=True, index=True)
    last_error = Column(Text, nullable=True)
    
    # Pub/Sub configuration
    topic_name = Column(String(200), nullable=False, index=True)
    message_id = Column(String(200), nullable=True)  # Pub/Sub message ID after publishing
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=text("NOW()"), index=True)
    published_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=text("NOW()"), onupdate=text("NOW()"))
    
    # Idempotency
    idempotency_key = Column(String(255), nullable=True, unique=True, index=True)
    
    # Event versioning for 15-year compatibility
    version = Column(Integer, nullable=False, default=1)
    
    def __repr__(self):
        return (
            f"<EventOutbox(id={self.id}, event_type={self.event_type}, "
            f"status={self.status}, retry_count={self.retry_count})>"
        )

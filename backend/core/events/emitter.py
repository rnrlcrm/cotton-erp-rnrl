"""
Event Emitter

Service for emitting events using the Transactional Outbox pattern.
Events are written to the outbox table in the same transaction as business data,
then published asynchronously by the OutboxWorker.
"""

from __future__ import annotations

import os
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.events.base import BaseEvent
from backend.core.events.store import EventStore
from backend.core.events.versioning import validate_event_version
from backend.core.outbox.repository import OutboxRepository


class EventEmitter:
    """
    Service for emitting domain events using the Transactional Outbox pattern.
    
    ALL events are written to the event_outbox table in the SAME transaction
    as business data. A background worker (OutboxWorker) polls the outbox and
    publishes events to GCP Pub/Sub.
    
    This ensures:
    - No lost events (if transaction commits, event is guaranteed to be published)
    - No duplicate events (idempotency keys prevent duplicates)
    - Transactional consistency (business data + event commit together)
    
    Usage in services:
        await self.events.emit(
            OrganizationCreated(
                aggregate_id=org.id,
                user_id=current_user.id,
                data={"name": org.name, ...},
                metadata=EventMetadata(ip_address="...", ...)
            )
        )
    """
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.store = EventStore(session)
        self.outbox = OutboxRepository(session)
    
    async def emit(self, event: BaseEvent, topic_name: Optional[str] = None) -> None:
        """
        Emit an event using the Transactional Outbox pattern.
        
        This method:
        1. Validates the event version (15-year compatibility)
        2. Stores it in the event_store table (event sourcing)
        3. Stores it in the event_outbox table (for async publishing)
        4. OutboxWorker publishes to Pub/Sub asynchronously
        
        Args:
            event: Domain event to emit
            topic_name: GCP Pub/Sub topic name (defaults to environment variable)
        """
        # Validate event version (15-year compatibility check)
        validate_event_version(event)
        
        # 1. Store in event_store for event sourcing / audit
        await self.store.append(
            event_type=event.event_type,
            aggregate_id=event.aggregate_id,
            aggregate_type=event.aggregate_type,
            user_id=event.user_id,
            data=event.data,
            metadata=event.metadata.dict() if event.metadata else None,
            version=event.version,
        )
        
        # 2. Store in event_outbox for async publishing to Pub/Sub
        if topic_name is None:
            # Default topic from environment
            topic_name = os.getenv("PUBSUB_TOPIC_EVENTS", "commodity-erp-events")
        
        # Build idempotency key from event
        idempotency_key = None
        if event.metadata and hasattr(event.metadata, 'idempotency_key'):
            idempotency_key = event.metadata.idempotency_key
        
        await self.outbox.add_event(
            aggregate_id=event.aggregate_id,
            aggregate_type=event.aggregate_type,
            event_type=event.event_type,
            payload={
                "data": event.data,
                "user_id": str(event.user_id),
                "timestamp": event.timestamp.isoformat() if hasattr(event, 'timestamp') else None,
            },
            topic_name=topic_name,
            metadata=event.metadata.dict() if event.metadata else None,
            idempotency_key=idempotency_key,
            version=event.version,
        )
    
    async def emit_many(self, events: list[BaseEvent], topic_name: Optional[str] = None) -> None:
        """
        Emit multiple events in a batch.
        
        All events are written to outbox in the same transaction.
        """
        for event in events:
            await self.emit(event, topic_name=topic_name)


# Dependency injection helper
def get_event_emitter(session: AsyncSession) -> EventEmitter:
    """Dependency for FastAPI routes"""
    return EventEmitter(session)

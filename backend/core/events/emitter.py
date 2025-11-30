"""
Event Emitter

Service for emitting events to the event store.
"""

from __future__ import annotations

from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.events.base import BaseEvent
from backend.core.events.store import EventStore
from backend.core.events.versioning import validate_event_version


class EventEmitter:
    """
    Service for emitting domain events.
    
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
        self.store = EventStore(session)
    
    async def emit(self, event: BaseEvent) -> None:
        """
        Emit an event to the event store.
        
        This method:
        1. Validates the event version
        2. Stores it in the database
        3. (Future: publish to message queue for async processing)
        """
        # Validate event version (15-year compatibility check)
        validate_event_version(event)
        
        await self.store.append(
            event_type=event.event_type,
            aggregate_id=event.aggregate_id,
            aggregate_type=event.aggregate_type,
            user_id=event.user_id,
            data=event.data,
            metadata=event.metadata.dict() if event.metadata else None,
            version=event.version,
        )
    
    async def emit_many(self, events: list[BaseEvent]) -> None:
        """Emit multiple events in a batch"""
        for event in events:
            await self.emit(event)


# Dependency injection helper
def get_event_emitter(session: AsyncSession) -> EventEmitter:
    """Dependency for FastAPI routes"""
    return EventEmitter(session)

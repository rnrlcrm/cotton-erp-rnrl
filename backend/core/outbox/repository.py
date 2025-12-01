"""
Outbox Repository

Provides data access methods for the event outbox.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from typing import List, Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.outbox.models import EventOutbox, OutboxStatus


class OutboxRepository:
    """
    Repository for managing outbox events.
    
    Provides methods to:
    - Add events to outbox
    - Fetch pending events for processing
    - Update event status after publishing
    - Clean up old published events
    """
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def add_event(
        self,
        aggregate_id: uuid.UUID,
        aggregate_type: str,
        event_type: str,
        payload: dict,
        topic_name: str,
        metadata: Optional[dict] = None,
        idempotency_key: Optional[str] = None,
        version: int = 1,
    ) -> EventOutbox:
        """
        Add a new event to the outbox.
        
        This method should be called within the same transaction as the
        business operation to ensure atomicity.
        
        Args:
            aggregate_id: ID of the aggregate (entity) that triggered the event
            aggregate_type: Type of aggregate (e.g., "Organization", "Availability")
            event_type: Type of event (e.g., "OrganizationCreated", "AvailabilityPosted")
            payload: Event payload (will be published to Pub/Sub)
            topic_name: GCP Pub/Sub topic name
            metadata: Optional metadata (user_id, ip_address, trace_id, etc.)
            idempotency_key: Optional idempotency key for deduplication
            version: Event schema version for 15-year compatibility
        
        Returns:
            EventOutbox: The created outbox event
        """
        # Check for duplicate idempotency key
        if idempotency_key:
            existing = await self.session.execute(
                select(EventOutbox).where(EventOutbox.idempotency_key == idempotency_key)
            )
            if existing.scalar_one_or_none():
                # Event already exists, return existing event (idempotent)
                return existing.scalar_one()
        
        event = EventOutbox(
            aggregate_id=aggregate_id,
            aggregate_type=aggregate_type,
            event_type=event_type,
            payload=payload,
            event_metadata=metadata,
            topic_name=topic_name,
            idempotency_key=idempotency_key,
            version=version,
            status=OutboxStatus.PENDING,
        )
        
        self.session.add(event)
        await self.session.flush()
        await self.session.refresh(event)
        
        return event
    
    async def get_pending_events(
        self,
        limit: int = 100,
        lock: bool = True,
    ) -> List[EventOutbox]:
        """
        Get pending events ready for publishing.
        
        Args:
            limit: Maximum number of events to fetch
            lock: Whether to lock rows for update (prevents concurrent processing)
        
        Returns:
            List of pending events
        """
        query = (
            select(EventOutbox)
            .where(EventOutbox.status == OutboxStatus.PENDING)
            .where(
                (EventOutbox.next_retry_at.is_(None)) |
                (EventOutbox.next_retry_at <= datetime.utcnow())
            )
            .order_by(EventOutbox.created_at.asc())
            .limit(limit)
        )
        
        if lock:
            query = query.with_for_update(skip_locked=True)
        
        result = await self.session.execute(query)
        return list(result.scalars().all())
    
    async def mark_as_processing(self, event_id: uuid.UUID) -> None:
        """Mark an event as currently being processed"""
        await self.session.execute(
            update(EventOutbox)
            .where(EventOutbox.id == event_id)
            .values(status=OutboxStatus.PROCESSING)
        )
        await self.session.flush()
    
    async def mark_as_published(
        self,
        event_id: uuid.UUID,
        message_id: str,
    ) -> None:
        """
        Mark an event as successfully published.
        
        Args:
            event_id: ID of the outbox event
            message_id: Pub/Sub message ID returned after publishing
        """
        await self.session.execute(
            update(EventOutbox)
            .where(EventOutbox.id == event_id)
            .values(
                status=OutboxStatus.PUBLISHED,
                published_at=datetime.utcnow(),
                message_id=message_id,
                last_error=None,
            )
        )
        await self.session.flush()
    
    async def mark_as_failed(
        self,
        event_id: uuid.UUID,
        error_message: str,
        schedule_retry: bool = True,
    ) -> None:
        """
        Mark an event as failed and optionally schedule a retry.
        
        Args:
            event_id: ID of the outbox event
            error_message: Error message from the failed publish attempt
            schedule_retry: Whether to schedule a retry or mark as permanently failed
        """
        event = await self.session.get(EventOutbox, event_id)
        if not event:
            return
        
        event.retry_count += 1
        event.last_error = error_message[:1000]  # Truncate long errors
        
        if event.retry_count >= event.max_retries or not schedule_retry:
            # Max retries exceeded or manual failure
            event.status = OutboxStatus.FAILED
            event.next_retry_at = None
        else:
            # Schedule retry with exponential backoff
            event.status = OutboxStatus.PENDING
            backoff_seconds = min(2 ** event.retry_count * 60, 3600)  # Max 1 hour
            event.next_retry_at = datetime.utcnow() + timedelta(seconds=backoff_seconds)
        
        await self.session.flush()
    
    async def cleanup_old_events(self, days: int = 30) -> int:
        """
        Delete old published events (for audit/replay purposes, keep for 30 days).
        
        Args:
            days: Number of days to retain published events
        
        Returns:
            Number of events deleted
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        result = await self.session.execute(
            select(EventOutbox)
            .where(EventOutbox.status == OutboxStatus.PUBLISHED)
            .where(EventOutbox.published_at < cutoff_date)
        )
        events = result.scalars().all()
        
        for event in events:
            await self.session.delete(event)
        
        await self.session.flush()
        return len(events)
    
    async def get_failed_events(self, limit: int = 100) -> List[EventOutbox]:
        """Get permanently failed events for ops team review"""
        result = await self.session.execute(
            select(EventOutbox)
            .where(EventOutbox.status == OutboxStatus.FAILED)
            .order_by(EventOutbox.updated_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

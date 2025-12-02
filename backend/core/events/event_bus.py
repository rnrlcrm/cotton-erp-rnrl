"""
Event Bus - Central event publishing system

Activates the Pub/Sub infrastructure for event-driven architecture.
"""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.events.base import BaseEvent
from backend.core.events.pubsub.publisher import PubSubPublisher
from backend.core.outbox import OutboxRepository

logger = logging.getLogger(__name__)


class EventBus:
    """
    Central event bus for publishing domain events.
    
    Architecture:
    1. Events emitted → Saved to event_outbox (transactional outbox pattern)
    2. Background worker polls outbox → Publishes to Pub/Sub
    3. Subscribers consume events → Trigger downstream actions
    
    Usage:
        event_bus = EventBus(db)
        await event_bus.publish(PartnerCreatedEvent(...))
    """
    
    def __init__(
        self,
        db: AsyncSession,
        publisher: Optional[PubSubPublisher] = None,
    ):
        self.db = db
        self.outbox_repo = OutboxRepository(db)
        
        # Initialize Pub/Sub publisher
        self.publisher = publisher or PubSubPublisher(
            project_id=os.getenv("GCP_PROJECT_ID"),
            enable_batching=True,
        )
        
        self._is_local_mode = not os.getenv("GCP_PROJECT_ID")
        if self._is_local_mode:
            logger.warning(
                "Event Bus running in LOCAL MODE (no GCP_PROJECT_ID). "
                "Events saved to outbox but NOT published to Pub/Sub."
            )
    
    async def publish(
        self,
        event: BaseEvent,
        topic_name: Optional[str] = None,
    ) -> str:
        """
        Publish domain event.
        
        Steps:
        1. Save to outbox table (transactional)
        2. If Pub/Sub configured, publish immediately
        3. Background worker will retry if publish fails
        
        Args:
            event: Domain event to publish
            topic_name: Pub/Sub topic (default: auto-detect from event type)
            
        Returns:
            Event ID
        """
        # Default topic routing
        if topic_name is None:
            topic_name = self._get_topic_for_event(event)
        
        # Save to outbox (transactional)
        outbox_entry = await self.outbox_repo.add_event(
            aggregate_id=event.aggregate_id,
            aggregate_type=event.aggregate_type,
            event_type=event.event_type,
            payload={
                "data": event.data,
                "user_id": str(event.user_id) if event.user_id else None,
                "timestamp": event.timestamp.isoformat() if hasattr(event, 'timestamp') else None,
            },
            topic_name=topic_name,
            metadata=event.metadata.dict() if hasattr(event, 'metadata') and event.metadata else None,
        )
        
        # If Pub/Sub configured, publish immediately (best effort)
        if not self._is_local_mode:
            try:
                from backend.core.events.pubsub.schemas import DomainEvent, EventType
                
                # Convert to Pub/Sub event
                pubsub_event = DomainEvent(
                    event_id=str(outbox_entry.id),
                    event_type=EventType(event.event_type) if hasattr(EventType, event.event_type) else EventType.CUSTOM,
                    aggregate_type=event.aggregate_type,
                    aggregate_id=str(event.aggregate_id),
                    user_id=str(event.user_id) if event.user_id else None,
                    organization_id=str(event.organization_id) if hasattr(event, 'organization_id') and event.organization_id else None,
                    payload=event.data,
                )
                
                await self.publisher.publish_event(pubsub_event, topic_name=topic_name)
                
                # Mark as published
                await self.outbox_repo.mark_as_published(outbox_entry.id)
                
            except Exception as e:
                # Fail gracefully - background worker will retry
                logger.warning(f"Failed to publish event {outbox_entry.id} to Pub/Sub: {e}")
        
        return str(outbox_entry.id)
    
    def _get_topic_for_event(self, event: BaseEvent) -> str:
        """
        Route event to appropriate topic based on event type.
        
        Topic Strategy:
        - partner.* → partner-events
        - trade.* → trading-events
        - risk.* → risk-events
        - Default → domain-events
        """
        event_type = event.event_type.lower()
        
        if event_type.startswith("partner"):
            return "partner-events"
        elif event_type.startswith(("availability", "requirement", "match", "trade")):
            return "trading-events"
        elif event_type.startswith("risk"):
            return "risk-events"
        elif event_type.startswith(("user", "organization", "auth")):
            return "identity-events"
        else:
            return "domain-events"
    
    async def publish_batch(self, events: list[BaseEvent]) -> list[str]:
        """
        Publish multiple events efficiently.
        
        Args:
            events: List of domain events
            
        Returns:
            List of event IDs
        """
        event_ids = []
        for event in events:
            event_id = await self.publish(event)
            event_ids.append(event_id)
        return event_ids


# Singleton instance
_event_bus: Optional[EventBus] = None


def get_event_bus(db: AsyncSession) -> EventBus:
    """
    Get or create event bus instance.
    
    Usage in FastAPI:
        event_bus = get_event_bus(db)
        await event_bus.publish(event)
    """
    return EventBus(db)

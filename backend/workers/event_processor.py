"""
Event Processor Worker

Background worker that:
1. Polls event_outbox table
2. Publishes unpublished events to Pub/Sub
3. Marks events as published
4. Retries failed events

Run as separate process:
    python -m backend.workers.event_processor
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from backend.core.events.pubsub.publisher import PubSubPublisher
from backend.core.events.pubsub.schemas import DomainEvent, EventType
from backend.core.outbox import EventOutbox

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class EventProcessor:
    """
    Outbox event processor.
    
    Guarantees:
    - At-least-once delivery (events may be published multiple times)
    - Events published in order (per aggregate_id)
    - Transactional safety (event saved = event published eventually)
    """
    
    def __init__(
        self,
        database_url: str,
        project_id: Optional[str] = None,
        batch_size: int = 10,
        poll_interval: int = 5,
    ):
        self.database_url = database_url
        self.batch_size = batch_size
        self.poll_interval = poll_interval
        
        # Create async engine
        self.engine = create_async_engine(
            database_url,
            echo=False,
            pool_pre_ping=True,
        )
        
        self.async_session = sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
        
        # Pub/Sub publisher
        self.publisher = PubSubPublisher(
            project_id=project_id,
            enable_batching=True,
            max_batch_size=batch_size,
        )
        
        self._running = False
    
    async def start(self):
        """Start processing events."""
        self._running = True
        logger.info("Event processor started")
        
        while self._running:
            try:
                await self._process_batch()
                await asyncio.sleep(self.poll_interval)
            except KeyboardInterrupt:
                logger.info("Shutting down...")
                self._running = False
                break
            except Exception as e:
                logger.error(f"Error processing events: {e}", exc_info=True)
                await asyncio.sleep(self.poll_interval)
    
    async def _process_batch(self):
        """Process one batch of unpublished events."""
        async with self.async_session() as session:
            # Get unpublished events (oldest first)
            stmt = (
                select(EventOutbox)
                .where(EventOutbox.published_at.is_(None))
                .order_by(EventOutbox.created_at.asc())
                .limit(self.batch_size)
            )
            
            result = await session.execute(stmt)
            events = result.scalars().all()
            
            if not events:
                return
            
            logger.info(f"Processing {len(events)} events")
            
            # Publish each event
            for event in events:
                try:
                    await self._publish_event(event)
                    
                    # Mark as published
                    event.published_at = datetime.now(timezone.utc)
                    session.add(event)
                    
                except Exception as e:
                    logger.error(
                        f"Failed to publish event {event.id} "
                        f"(aggregate: {event.aggregate_type}:{event.aggregate_id}): {e}"
                    )
                    
                    # Increment retry count
                    event.retry_count = (event.retry_count or 0) + 1
                    session.add(event)
            
            await session.commit()
    
    async def _publish_event(self, event: EventOutbox):
        """Publish single event to Pub/Sub."""
        # Convert to Pub/Sub event
        try:
            event_type = EventType(event.event_type)
        except ValueError:
            event_type = EventType.CUSTOM
        
        pubsub_event = DomainEvent(
            event_id=str(event.id),
            event_type=event_type,
            aggregate_type=event.aggregate_type,
            aggregate_id=str(event.aggregate_id),
            user_id=event.payload.get("user_id") if event.payload else None,
            organization_id=event.metadata.get("organization_id") if event.metadata else None,
            payload=event.payload or {},
            timestamp=event.created_at,
        )
        
        # Publish
        await self.publisher.publish_event(
            pubsub_event,
            topic_name=event.topic_name or "domain-events",
            ordering_key=str(event.aggregate_id),  # Order by aggregate
        )
        
        logger.info(
            f"Published event {event.id} "
            f"({event.event_type} for {event.aggregate_type}:{event.aggregate_id})"
        )
    
    async def stop(self):
        """Stop processing."""
        self._running = False
        await self.engine.dispose()


async def main():
    """Main entry point."""
    # Get configuration from environment
    database_url = os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://commodity_user:commodity_password@localhost:5432/commodity_erp"
    )
    
    project_id = os.getenv("GCP_PROJECT_ID")
    
    if not project_id:
        logger.warning(
            "GCP_PROJECT_ID not set. Events will be logged but NOT published to Pub/Sub. "
            "Set GCP_PROJECT_ID environment variable to enable cloud publishing."
        )
    
    # Create and start processor
    processor = EventProcessor(
        database_url=database_url,
        project_id=project_id,
        batch_size=10,
        poll_interval=5,  # Poll every 5 seconds
    )
    
    try:
        await processor.start()
    except KeyboardInterrupt:
        await processor.stop()
        logger.info("Event processor stopped")


if __name__ == "__main__":
    asyncio.run(main())

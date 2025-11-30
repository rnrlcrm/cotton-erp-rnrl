"""
Outbox Worker

Background worker that polls the outbox table and publishes events to GCP Pub/Sub.
Runs as a separate Cloud Run service with scheduled Cloud Run Jobs.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Optional

from google.cloud import pubsub_v1
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.outbox.models import EventOutbox
from backend.core.outbox.repository import OutboxRepository

logger = logging.getLogger(__name__)


class OutboxWorker:
    """
    Background worker for publishing outbox events to Pub/Sub.
    
    Deployment options:
    1. Cloud Run Job (scheduled every 1 minute)
    2. Cloud Run Service with long-running process
    3. Cloud Functions (triggered by Cloud Scheduler)
    
    The worker:
    1. Fetches pending events from outbox
    2. Publishes each event to configured Pub/Sub topic
    3. Updates outbox status (PUBLISHED or FAILED)
    4. Retries failed events with exponential backoff
    """
    
    def __init__(
        self,
        session: AsyncSession,
        project_id: str,
        batch_size: int = 100,
    ):
        self.session = session
        self.project_id = project_id
        self.batch_size = batch_size
        self.repository = OutboxRepository(session)
        
        # Initialize Pub/Sub publisher
        self.publisher = pubsub_v1.PublisherClient()
    
    async def process_batch(self) -> int:
        """
        Process a single batch of pending events.
        
        Returns:
            Number of events processed
        """
        # Fetch pending events (locks rows to prevent concurrent processing)
        events = await self.repository.get_pending_events(
            limit=self.batch_size,
            lock=True,
        )
        
        if not events:
            logger.info("No pending events to process")
            return 0
        
        logger.info(f"Processing {len(events)} pending events")
        
        processed_count = 0
        for event in events:
            try:
                await self._process_event(event)
                processed_count += 1
            except Exception as e:
                logger.error(
                    f"Error processing event {event.id}: {e}",
                    exc_info=True,
                )
                await self.repository.mark_as_failed(
                    event.id,
                    error_message=str(e),
                    schedule_retry=True,
                )
        
        # Commit all status updates
        await self.session.commit()
        
        logger.info(f"Successfully processed {processed_count}/{len(events)} events")
        return processed_count
    
    async def _process_event(self, event: EventOutbox) -> None:
        """
        Process a single event by publishing to Pub/Sub.
        
        Args:
            event: Outbox event to process
        """
        # Mark as processing
        await self.repository.mark_as_processing(event.id)
        
        # Build Pub/Sub topic path
        topic_path = self.publisher.topic_path(self.project_id, event.topic_name)
        
        # Prepare message
        message_data = {
            "event_type": event.event_type,
            "aggregate_id": str(event.aggregate_id),
            "aggregate_type": event.aggregate_type,
            "payload": event.payload,
            "metadata": event.metadata or {},
            "version": event.version,
            "outbox_id": str(event.id),
        }
        
        # Prepare attributes for filtering
        attributes = {
            "event_type": event.event_type,
            "aggregate_type": event.aggregate_type,
            "version": str(event.version),
        }
        
        # Add idempotency key if present
        if event.idempotency_key:
            attributes["idempotency_key"] = event.idempotency_key
        
        # Publish to Pub/Sub (synchronous call)
        try:
            import json
            future = self.publisher.publish(
                topic_path,
                data=json.dumps(message_data).encode("utf-8"),
                **attributes,
            )
            
            # Wait for publish to complete
            message_id = future.result(timeout=30)
            
            # Mark as published
            await self.repository.mark_as_published(event.id, message_id)
            
            logger.info(
                f"Published event {event.id} to {event.topic_name} "
                f"(message_id: {message_id})"
            )
        
        except Exception as e:
            logger.error(
                f"Failed to publish event {event.id} to {event.topic_name}: {e}",
                exc_info=True,
            )
            raise  # Re-raise to trigger retry logic
    
    async def run_forever(self, poll_interval: int = 60) -> None:
        """
        Run the worker in a continuous loop.
        
        This is useful for Cloud Run services that run continuously.
        
        Args:
            poll_interval: Seconds to wait between polling cycles
        """
        logger.info(f"Starting outbox worker (poll_interval={poll_interval}s)")
        
        while True:
            try:
                await self.process_batch()
            except Exception as e:
                logger.error(f"Error in worker loop: {e}", exc_info=True)
            
            # Wait before next poll
            await asyncio.sleep(poll_interval)
    
    async def cleanup_old_events(self, days: int = 30) -> int:
        """
        Clean up old published events.
        
        Should be run periodically (e.g., daily via Cloud Scheduler).
        
        Args:
            days: Number of days to retain published events
        
        Returns:
            Number of events deleted
        """
        count = await self.repository.cleanup_old_events(days=days)
        await self.session.commit()
        
        logger.info(f"Cleaned up {count} old published events")
        return count


# Entry point for Cloud Run Job
async def run_outbox_worker_job(
    session: AsyncSession,
    project_id: str,
) -> None:
    """
    Entry point for Cloud Run Job.
    
    Processes one batch and exits (Cloud Scheduler calls this every minute).
    
    Usage in Cloud Run Job:
        from backend.core.outbox.worker import run_outbox_worker_job
        from backend.db.async_session import AsyncSessionLocal
        
        async def main():
            async with AsyncSessionLocal() as session:
                await run_outbox_worker_job(session, "your-project-id")
    """
    worker = OutboxWorker(session, project_id)
    await worker.process_batch()


# Entry point for Cloud Run Service (continuous)
async def run_outbox_worker_service(
    session: AsyncSession,
    project_id: str,
    poll_interval: int = 60,
) -> None:
    """
    Entry point for Cloud Run Service.
    
    Runs continuously, polling every poll_interval seconds.
    
    Usage in Cloud Run Service:
        from backend.core.outbox.worker import run_outbox_worker_service
        from backend.db.async_session import AsyncSessionLocal
        
        async def main():
            async with AsyncSessionLocal() as session:
                await run_outbox_worker_service(
                    session,
                    "your-project-id",
                    poll_interval=60,
                )
    """
    worker = OutboxWorker(session, project_id)
    await worker.run_forever(poll_interval=poll_interval)

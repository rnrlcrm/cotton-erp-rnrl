"""
Google Cloud Pub/Sub Publisher

Publishes domain events to Google Cloud Pub/Sub topics.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, List, Optional

from google.cloud import pubsub_v1
from google.cloud.pubsub_v1 import PublisherClient
from google.cloud.pubsub_v1.types import BatchSettings

from backend.core.events.pubsub.schemas import DomainEvent, EventType

logger = logging.getLogger(__name__)


class PubSubPublisher:
    """
    Google Cloud Pub/Sub event publisher.
    
    Features:
    - Topic-based publish
    - Batch publishing for performance
    - Automatic topic creation
    - Message ordering (per key)
    - Retry on failure
    """
    
    def __init__(
        self,
        project_id: Optional[str] = None,
        enable_batching: bool = True,
        max_batch_size: int = 100,
    ):
        self.project_id = project_id or os.getenv("GCP_PROJECT_ID")
        
        if not self.project_id:
            logger.warning("GCP_PROJECT_ID not set, using local mode")
            self._local_mode = True
            self.client = None
        else:
            self._local_mode = False
            
            # Configure batching
            batch_settings = BatchSettings(
                max_bytes=1024 * 1024,  # 1 MB
                max_latency=0.05,  # 50 ms
                max_messages=max_batch_size,
            ) if enable_batching else None
            
            self.client = PublisherClient(batch_settings=batch_settings)
        
        # Topic cache
        self._topic_paths: Dict[str, str] = {}
        
        # Local event store (for testing without GCP)
        self._local_events: List[DomainEvent] = []
    
    def _get_topic_path(self, topic_name: str) -> str:
        """
        Get full topic path.
        
        Args:
            topic_name: Topic name (e.g., "trade-events")
            
        Returns:
            Full topic path
        """
        if topic_name not in self._topic_paths:
            self._topic_paths[topic_name] = self.client.topic_path(
                self.project_id,
                topic_name,
            )
        
        return self._topic_paths[topic_name]
    
    async def publish_event(
        self,
        event: DomainEvent,
        topic_name: Optional[str] = None,
        ordering_key: Optional[str] = None,
    ) -> str:
        """
        Publish event to Pub/Sub.
        
        Args:
            event: Domain event to publish
            topic_name: Topic name (defaults to event type)
            ordering_key: Ordering key for message ordering
            
        Returns:
            Message ID
        """
        # Default topic name from event type
        if not topic_name:
            # Example: "trade.created" → "trade-events"
            topic_name = f"{event.event_type.value.split('.')[0]}-events"
        
        # Local mode (for testing)
        if self._local_mode:
            self._local_events.append(event)
            logger.info(f"[LOCAL] Published event {event.id} to {topic_name}")
            return event.id
        
        # Serialize event
        data = event.model_dump_json().encode("utf-8")
        
        # Get topic path
        topic_path = self._get_topic_path(topic_name)
        
        # Publish
        try:
            future = self.client.publish(
                topic_path,
                data,
                ordering_key=ordering_key or "",
                event_id=event.id,
                event_type=event.event_type.value,
                priority=event.priority.value,
            )
            
            message_id = future.result()
            
            logger.info(
                f"Published event {event.id} (type={event.event_type.value}) "
                f"to {topic_name}, message_id={message_id}"
            )
            
            return message_id
        
        except Exception as e:
            logger.error(f"Failed to publish event {event.id}: {e}")
            raise
    
    async def publish_batch(
        self,
        events: List[DomainEvent],
        topic_name: str,
    ) -> List[str]:
        """
        Publish multiple events at once.
        
        Args:
            events: List of events
            topic_name: Topic name
            
        Returns:
            List of message IDs
        """
        message_ids = []
        
        for event in events:
            message_id = await self.publish_event(event, topic_name)
            message_ids.append(message_id)
        
        return message_ids
    
    async def create_topic(self, topic_name: str) -> bool:
        """
        Create Pub/Sub topic if it doesn't exist.
        
        Args:
            topic_name: Topic name
            
        Returns:
            True if created or already exists
        """
        if self._local_mode:
            return True
        
        topic_path = self._get_topic_path(topic_name)
        
        try:
            self.client.create_topic(request={"name": topic_path})
            logger.info(f"Created topic {topic_name}")
            return True
        except Exception as e:
            if "already exists" in str(e).lower():
                logger.debug(f"Topic {topic_name} already exists")
                return True
            else:
                logger.error(f"Failed to create topic {topic_name}: {e}")
                return False
    
    def get_local_events(self) -> List[DomainEvent]:
        """Get events from local store (testing only)"""
        return self._local_events.copy()
    
    def clear_local_events(self):
        """Clear local event store (testing only)"""
        self._local_events.clear()


# Predefined topics for the ERP system
class Topics:
    """Common Pub/Sub topics"""
    
    TRADE_EVENTS = "trade-events"
    ORDER_EVENTS = "order-events"
    PAYMENT_EVENTS = "payment-events"
    CONTRACT_EVENTS = "contract-events"
    QUALITY_EVENTS = "quality-events"
    LOGISTICS_EVENTS = "logistics-events"
    MARKET_EVENTS = "market-events"
    NOTIFICATION_EVENTS = "notification-events"
    USER_EVENTS = "user-events"
    AUDIT_EVENTS = "audit-events"
    SYSTEM_EVENTS = "system-events"

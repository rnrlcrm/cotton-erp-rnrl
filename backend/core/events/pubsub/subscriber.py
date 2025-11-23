"""
Google Cloud Pub/Sub Subscriber

Subscribes to Pub/Sub topics and processes events.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from typing import Callable, Dict, List, Optional

from google.cloud import pubsub_v1
from google.cloud.pubsub_v1 import SubscriberClient
from google.cloud.pubsub_v1.subscriber.message import Message

from backend.core.events.pubsub.schemas import DomainEvent, EventType

logger = logging.getLogger(__name__)

# Type alias for event handler
EventHandler = Callable[[DomainEvent], None]


class PubSubSubscriber:
    """
    Google Cloud Pub/Sub event subscriber.
    
    Features:
    - Subscribe to topics
    - Event handler registration
    - Automatic ACK/NACK
    - Dead letter queue support
    - Concurrent message processing
    """
    
    def __init__(
        self,
        project_id: Optional[str] = None,
        max_messages: int = 10,
    ):
        self.project_id = project_id or os.getenv("GCP_PROJECT_ID")
        
        if not self.project_id:
            logger.warning("GCP_PROJECT_ID not set, using local mode")
            self._local_mode = True
            self.client = None
        else:
            self._local_mode = False
            self.client = SubscriberClient()
        
        # Event handlers: {event_type: [handlers]}
        self._handlers: Dict[EventType, List[EventHandler]] = {}
        
        # Active subscriptions: {subscription_name: future}
        self._subscriptions: Dict[str, any] = {}
        
        self.max_messages = max_messages
    
    def _get_subscription_path(self, subscription_name: str) -> str:
        """
        Get full subscription path.
        
        Args:
            subscription_name: Subscription name
            
        Returns:
            Full subscription path
        """
        return self.client.subscription_path(self.project_id, subscription_name)
    
    def register_handler(self, event_type: EventType, handler: EventHandler):
        """
        Register event handler.
        
        Args:
            event_type: Event type to handle
            handler: Handler function
        """
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        
        self._handlers[event_type].append(handler)
        logger.info(f"Registered handler for {event_type.value}")
    
    def _process_message(self, message: Message):
        """
        Process Pub/Sub message.
        
        Args:
            message: Pub/Sub message
        """
        try:
            # Parse event
            event_data = json.loads(message.data.decode("utf-8"))
            event = DomainEvent(**event_data)
            
            logger.debug(f"Processing event {event.id} (type={event.event_type.value})")
            
            # Call handlers
            if event.event_type in self._handlers:
                for handler in self._handlers[event.event_type]:
                    try:
                        handler(event)
                    except Exception as e:
                        logger.error(
                            f"Handler error for event {event.id}: {e}",
                            exc_info=True,
                        )
                        # NACK message for retry
                        message.nack()
                        return
            
            # ACK message
            message.ack()
            logger.debug(f"ACKed event {event.id}")
        
        except Exception as e:
            logger.error(f"Failed to process message: {e}", exc_info=True)
            message.nack()
    
    async def subscribe(
        self,
        subscription_name: str,
        topic_name: Optional[str] = None,
    ):
        """
        Subscribe to topic.
        
        Args:
            subscription_name: Subscription name
            topic_name: Topic name (optional, for creating subscription)
        """
        if self._local_mode:
            logger.info(f"[LOCAL] Subscribed to {subscription_name}")
            return
        
        subscription_path = self._get_subscription_path(subscription_name)
        
        # Create subscription if it doesn't exist
        if topic_name:
            await self.create_subscription(subscription_name, topic_name)
        
        # Start streaming pull
        future = self.client.subscribe(
            subscription_path,
            callback=self._process_message,
        )
        
        self._subscriptions[subscription_name] = future
        logger.info(f"Subscribed to {subscription_name}")
    
    async def create_subscription(
        self,
        subscription_name: str,
        topic_name: str,
        ack_deadline_seconds: int = 60,
    ) -> bool:
        """
        Create subscription if it doesn't exist.
        
        Args:
            subscription_name: Subscription name
            topic_name: Topic name
            ack_deadline_seconds: ACK deadline
            
        Returns:
            True if created or already exists
        """
        if self._local_mode:
            return True
        
        subscription_path = self._get_subscription_path(subscription_name)
        topic_path = self.client.topic_path(self.project_id, topic_name)
        
        try:
            self.client.create_subscription(
                request={
                    "name": subscription_path,
                    "topic": topic_path,
                    "ack_deadline_seconds": ack_deadline_seconds,
                }
            )
            logger.info(f"Created subscription {subscription_name}")
            return True
        except Exception as e:
            if "already exists" in str(e).lower():
                logger.debug(f"Subscription {subscription_name} already exists")
                return True
            else:
                logger.error(f"Failed to create subscription {subscription_name}: {e}")
                return False
    
    async def unsubscribe(self, subscription_name: str):
        """
        Unsubscribe from topic.
        
        Args:
            subscription_name: Subscription name
        """
        if subscription_name in self._subscriptions:
            future = self._subscriptions[subscription_name]
            future.cancel()
            del self._subscriptions[subscription_name]
            logger.info(f"Unsubscribed from {subscription_name}")
    
    async def stop_all(self):
        """Stop all subscriptions"""
        for subscription_name in list(self._subscriptions.keys()):
            await self.unsubscribe(subscription_name)

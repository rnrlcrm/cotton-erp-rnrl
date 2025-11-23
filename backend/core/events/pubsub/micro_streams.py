"""
Micro-Stream Channels for Domain Events

Implements micro-stream pattern for fine-grained event routing:
- Trade streams (per trade)
- User streams (per user)
- Organization streams (per org)
- Custom domain streams
"""

from __future__ import annotations

import asyncio
import logging
from typing import Callable, Dict, List, Optional
from uuid import UUID

from backend.core.events.pubsub.publisher import PubSubPublisher
from backend.core.events.pubsub.subscriber import PubSubSubscriber
from backend.core.events.pubsub.schemas import DomainEvent, EventType

logger = logging.getLogger(__name__)


class MicroStreamChannel:
    """
    Micro-stream channel for domain events.
    
    Creates fine-grained event streams for specific entities:
    - trade:{trade_id} - Events for specific trade
    - user:{user_id} - Events for specific user
    - org:{org_id} - Events for organization
    
    Benefits:
    - Reduced fan-out (only subscribers to that entity get events)
    - Better performance (less filtering)
    - Isolation (one trade's events don't affect others)
    """
    
    def __init__(
        self,
        publisher: PubSubPublisher,
        subscriber: PubSubSubscriber,
    ):
        self.publisher = publisher
        self.subscriber = subscriber
        
        # Active streams: {stream_key: topic_name}
        self._streams: Dict[str, str] = {}
    
    def _get_stream_topic(self, stream_key: str) -> str:
        """
        Get topic name for stream.
        
        Args:
            stream_key: Stream key (e.g., "trade:123")
            
        Returns:
            Topic name
        """
        # Sanitize stream key for topic name
        topic_name = f"stream-{stream_key.replace(':', '-')}"
        return topic_name
    
    async def create_stream(self, stream_key: str) -> str:
        """
        Create micro-stream.
        
        Args:
            stream_key: Stream key
            
        Returns:
            Topic name
        """
        topic_name = self._get_stream_topic(stream_key)
        
        # Create topic
        await self.publisher.create_topic(topic_name)
        
        self._streams[stream_key] = topic_name
        logger.info(f"Created micro-stream: {stream_key} → {topic_name}")
        
        return topic_name
    
    async def publish_to_stream(
        self,
        stream_key: str,
        event: DomainEvent,
    ):
        """
        Publish event to micro-stream.
        
        Args:
            stream_key: Stream key
            event: Event to publish
        """
        # Ensure stream exists
        if stream_key not in self._streams:
            await self.create_stream(stream_key)
        
        topic_name = self._streams[stream_key]
        
        # Publish
        await self.publisher.publish_event(
            event,
            topic_name=topic_name,
            ordering_key=stream_key,  # Maintain order per stream
        )
    
    async def subscribe_to_stream(
        self,
        stream_key: str,
        handler: Callable[[DomainEvent], None],
    ):
        """
        Subscribe to micro-stream.
        
        Args:
            stream_key: Stream key
            handler: Event handler
        """
        # Ensure stream exists
        if stream_key not in self._streams:
            await self.create_stream(stream_key)
        
        topic_name = self._streams[stream_key]
        subscription_name = f"{topic_name}-sub"
        
        # Register handler
        # Note: This is simplified - in production, you'd want per-stream handlers
        self.subscriber.register_handler(EventType.TRADE_CREATED, handler)
        
        # Subscribe
        await self.subscriber.subscribe(subscription_name, topic_name)


class EventRouter:
    """
    Routes events to appropriate micro-streams and handlers.
    
    Features:
    - Automatic routing based on event metadata
    - Multi-stream publishing (one event to multiple streams)
    - Handler registration per stream
    """
    
    def __init__(
        self,
        publisher: PubSubPublisher,
        subscriber: PubSubSubscriber,
    ):
        self.publisher = publisher
        self.subscriber = subscriber
        self.micro_streams = MicroStreamChannel(publisher, subscriber)
        
        # Event handlers: {stream_pattern: handlers}
        self._stream_handlers: Dict[str, List[Callable]] = {}
    
    async def route_event(self, event: DomainEvent):
        """
        Route event to appropriate streams.
        
        Args:
            event: Domain event
        """
        # Determine stream keys from event
        stream_keys = self._get_stream_keys(event)
        
        # Publish to each stream
        for stream_key in stream_keys:
            await self.micro_streams.publish_to_stream(stream_key, event)
        
        # Also publish to global topic
        await self.publisher.publish_event(event)
    
    def _get_stream_keys(self, event: DomainEvent) -> List[str]:
        """
        Get stream keys for event.
        
        Args:
            event: Domain event
            
        Returns:
            List of stream keys
        """
        stream_keys = []
        
        # User stream
        if event.user_id:
            stream_keys.append(f"user:{event.user_id}")
        
        # Organization stream
        if event.organization_id:
            stream_keys.append(f"org:{event.organization_id}")
        
        # Aggregate stream (entity-specific)
        if event.aggregate_id and event.aggregate_type:
            stream_keys.append(f"{event.aggregate_type}:{event.aggregate_id}")
        
        # Event type stream
        stream_keys.append(f"event-type:{event.event_type.value}")
        
        return stream_keys
    
    def register_stream_handler(
        self,
        stream_pattern: str,
        handler: Callable[[DomainEvent], None],
    ):
        """
        Register handler for stream pattern.
        
        Args:
            stream_pattern: Stream pattern (e.g., "trade:*", "user:123")
            handler: Event handler
        """
        if stream_pattern not in self._stream_handlers:
            self._stream_handlers[stream_pattern] = []
        
        self._stream_handlers[stream_pattern].append(handler)
        logger.info(f"Registered handler for stream pattern: {stream_pattern}")


# Stream patterns for common use cases
class StreamPatterns:
    """Common micro-stream patterns"""
    
    @staticmethod
    def trade_stream(trade_id: UUID) -> str:
        """Stream for specific trade"""
        return f"trade:{trade_id}"
    
    @staticmethod
    def user_stream(user_id: UUID) -> str:
        """Stream for specific user"""
        return f"user:{user_id}"
    
    @staticmethod
    def org_stream(org_id: UUID) -> str:
        """Stream for organization"""
        return f"org:{org_id}"
    
    @staticmethod
    def contract_stream(contract_id: UUID) -> str:
        """Stream for specific contract"""
        return f"contract:{contract_id}"
    
    @staticmethod
    def payment_stream(payment_id: UUID) -> str:
        """Stream for specific payment"""
        return f"payment:{payment_id}"
    
    @staticmethod
    def event_type_stream(event_type: EventType) -> str:
        """Stream for event type"""
        return f"event-type:{event_type.value}"

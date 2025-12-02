"""
Analytics Event Subscriber

Listens to domain events and tracks analytics metrics.

Events tracked:
- PartnerCreatedEvent → Track partner growth
- TradeMatchedEvent → Track trading volume
- PaymentReceivedEvent → Track revenue
- User login/logout → Track engagement
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict

from backend.core.events.base import BaseEvent

logger = logging.getLogger(__name__)


class AnalyticsSubscriber:
    """
    Subscribes to domain events and records analytics.
    
    Tracks:
    - Business metrics (revenue, trades, partners)
    - User engagement (logins, sessions)
    - System health (errors, latency)
    """
    
    def __init__(self, analytics_service=None):
        self.analytics_service = analytics_service
        self.events_processed = 0
    
    async def handle_event(self, event: BaseEvent):
        """Process any event for analytics."""
        try:
            self.events_processed += 1
            
            # Extract event metadata
            event_type = event.__class__.__name__
            timestamp = event.occurred_at or datetime.utcnow()
            
            # Log to analytics service
            if self.analytics_service:
                await self.analytics_service.track_event(
                    event_type=event_type,
                    aggregate_id=str(event.aggregate_id),
                    user_id=str(event.user_id) if event.user_id else None,
                    timestamp=timestamp,
                    data=event.data
                )
            
            # Log metrics based on event type
            await self._track_specific_metrics(event_type, event)
            
            logger.debug(f"📊 Analytics: {event_type} processed")
        
        except Exception as e:
            logger.error(f"❌ Analytics processing failed: {e}", exc_info=True)
    
    async def _track_specific_metrics(self, event_type: str, event: BaseEvent):
        """Track specific metrics for different event types."""
        
        # Partner metrics
        if event_type == "PartnerCreatedEvent":
            logger.info(f"📈 New partner created: {event.aggregate_id}")
            # Track partner type distribution
            partner_type = event.data.get("partner_type")
            if partner_type:
                await self._increment_counter(f"partners.created.{partner_type}")
        
        elif event_type == "PartnerApprovedEvent":
            logger.info(f"✅ Partner approved: {event.aggregate_id}")
            await self._increment_counter("partners.approved")
        
        # Trade metrics
        elif event_type == "TradeMatchedEvent":
            logger.info(f"🤝 Trade matched: {event.aggregate_id}")
            # Track trade volume
            quantity = event.data.get("quantity", 0)
            value = event.data.get("value", 0)
            await self._track_metric("trades.volume", quantity)
            await self._track_metric("trades.value", value)
        
        # Payment metrics
        elif event_type == "PaymentReceivedEvent":
            logger.info(f"💰 Payment received: {event.aggregate_id}")
            amount = event.data.get("amount", 0)
            await self._track_metric("revenue.total", amount)
        
        # User engagement
        elif event_type == "UserLoggedInEvent":
            await self._increment_counter("users.logins")
        
        elif event_type == "UserLoggedOutEvent":
            await self._increment_counter("users.logouts")
    
    async def _increment_counter(self, metric_name: str):
        """Increment a counter metric."""
        if self.analytics_service:
            await self.analytics_service.increment(metric_name)
        logger.debug(f"📊 Counter incremented: {metric_name}")
    
    async def _track_metric(self, metric_name: str, value: float):
        """Track a numeric metric."""
        if self.analytics_service:
            await self.analytics_service.record(metric_name, value)
        logger.debug(f"📊 Metric tracked: {metric_name} = {value}")


async def start_analytics_subscriber():
    """
    Start the analytics subscriber worker.
    
    Usage:
        python -m backend.workers.analytics_subscriber
    """
    from backend.core.events.pubsub.subscriber import PubSubSubscriber
    
    subscriber = AnalyticsSubscriber()
    
    # Connect to Pub/Sub
    pubsub_subscriber = PubSubSubscriber(
        subscription_name="analytics-worker-subscription"
    )
    
    logger.info("🚀 Analytics subscriber started")
    logger.info("Tracking all domain events for business intelligence...")
    
    # Start consuming events
    await pubsub_subscriber.consume(subscriber.handle_event)


if __name__ == "__main__":
    import asyncio
    asyncio.run(start_analytics_subscriber())

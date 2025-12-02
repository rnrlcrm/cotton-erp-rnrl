"""
Domain Events Subscriber

Subscribes to Pub/Sub topics and triggers event handlers.

Run as separate process:
    python -m backend.workers.event_subscriber
"""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Callable, Dict, List

from backend.core.events.pubsub.subscriber import PubSubSubscriber
from backend.core.events.pubsub.schemas import DomainEvent, EventType

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class EventSubscriber:
    """
    Domain events subscriber.
    
    Listens to Pub/Sub topics and routes events to handlers.
    """
    
    def __init__(self, project_id: str):
        self.subscriber = PubSubSubscriber(project_id=project_id)
        self._handlers: Dict[EventType, List[Callable]] = {}
    
    def register_handler(
        self,
        event_type: EventType,
        handler: Callable[[DomainEvent], None],
    ):
        """Register event handler."""
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        
        self._handlers[event_type].append(handler)
        logger.info(f"Registered handler for {event_type.value}")
    
    async def start(self):
        """Start subscribing to events."""
        # Register all handlers with subscriber
        for event_type, handlers in self._handlers.items():
            for handler in handlers:
                self.subscriber.register_handler(event_type, handler)
        
        # Subscribe to all topics
        await self.subscriber.subscribe(
            subscription_name="cotton-erp-domain-events-sub",
            topic_name="domain-events",
        )
        
        logger.info("Event subscriber started")
        
        # Keep running
        while True:
            await asyncio.sleep(60)


# ============================================================================
# Event Handlers (Add your business logic here)
# ============================================================================

async def handle_partner_created(event: DomainEvent):
    """Handle PartnerCreated event."""
    logger.info(f"Partner created: {event.aggregate_id}")
    
    # TODO: Trigger downstream actions:
    # - Send welcome email
    # - Create default settings
    # - Notify admin
    # - Update analytics


async def handle_requirement_created(event: DomainEvent):
    """Handle RequirementCreated event."""
    logger.info(f"Requirement created: {event.aggregate_id}")
    
    # TODO: Trigger matching engine
    # - Find potential matches
    # - Notify sellers
    # - Update market analytics


async def handle_availability_created(event: DomainEvent):
    """Handle AvailabilityCreated event."""
    logger.info(f"Availability created: {event.aggregate_id}")
    
    # TODO: Trigger matching engine
    # - Find potential buyers
    # - Notify buyers
    # - Update market analytics


async def handle_trade_created(event: DomainEvent):
    """Handle TradeCreated event."""
    logger.info(f"Trade created: {event.aggregate_id}")
    
    # TODO: Trigger post-trade workflow
    # - Generate contract
    # - Schedule payment
    # - Book logistics
    # - Notify parties


async def handle_risk_alert(event: DomainEvent):
    """Handle RiskAlert event."""
    logger.info(f"Risk alert: {event.payload}")
    
    # TODO: Trigger risk response
    # - Notify risk team
    # - Escalate to manager
    # - Update dashboard
    # - Log to compliance


# ============================================================================
# Main
# ============================================================================

async def main():
    """Main entry point."""
    project_id = os.getenv("GCP_PROJECT_ID")
    
    if not project_id:
        logger.error("GCP_PROJECT_ID not set. Cannot start subscriber.")
        return
    
    # Create subscriber
    subscriber = EventSubscriber(project_id=project_id)
    
    # Register all handlers
    subscriber.register_handler(EventType.PARTNER_CREATED, handle_partner_created)
    subscriber.register_handler(EventType.REQUIREMENT_CREATED, handle_requirement_created)
    subscriber.register_handler(EventType.AVAILABILITY_CREATED, handle_availability_created)
    subscriber.register_handler(EventType.TRADE_CREATED, handle_trade_created)
    subscriber.register_handler(EventType.RISK_ALERT, handle_risk_alert)
    
    # Start listening
    await subscriber.start()


if __name__ == "__main__":
    asyncio.run(main())

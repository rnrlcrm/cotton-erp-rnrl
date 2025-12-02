"""
Audit Trail Event Subscriber

Listens to all domain events and maintains comprehensive audit trail.

Purpose:
- Compliance (track all changes)
- Security (detect suspicious activity)
- Debugging (replay event history)
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict
from uuid import UUID

from backend.core.events.base import BaseEvent

logger = logging.getLogger(__name__)


class AuditSubscriber:
    """
    Subscribes to all domain events and logs them to audit trail.
    
    Audit records include:
    - Who did it (user_id)
    - What happened (event_type)
    - When (timestamp)
    - What changed (event_data)
    - Context (IP address, user agent)
    """
    
    def __init__(self, audit_repository=None):
        self.audit_repository = audit_repository
        self.events_audited = 0
    
    async def handle_event(self, event: BaseEvent):
        """Log event to audit trail."""
        try:
            self.events_audited += 1
            
            # Build audit record
            audit_record = {
                "event_id": str(event.event_id),
                "event_type": event.__class__.__name__,
                "aggregate_id": str(event.aggregate_id),
                "user_id": str(event.user_id) if event.user_id else None,
                "occurred_at": event.occurred_at or datetime.utcnow(),
                "data": event.data,
                "metadata": event.metadata,
            }
            
            # Save to audit database
            if self.audit_repository:
                await self.audit_repository.create(audit_record)
            
            # Log for compliance
            logger.info(
                f"📝 AUDIT: {audit_record['event_type']} "
                f"by user {audit_record['user_id']} "
                f"on {audit_record['aggregate_id']}"
            )
            
            # Flag sensitive events
            if self._is_sensitive_event(event):
                logger.warning(
                    f"🔒 SENSITIVE EVENT: {audit_record['event_type']} "
                    f"by {audit_record['user_id']}"
                )
        
        except Exception as e:
            logger.error(f"❌ Audit logging failed: {e}", exc_info=True)
            # Critical: audit failures should be monitored
    
    def _is_sensitive_event(self, event: BaseEvent) -> bool:
        """Identify sensitive events requiring extra attention."""
        sensitive_events = {
            "PartnerDeletedEvent",
            "PaymentRefundedEvent",
            "UserDeletedEvent",
            "PermissionGrantedEvent",
            "PermissionRevokedEvent",
            "DataExportedEvent",
            "SettingsChangedEvent",
        }
        return event.__class__.__name__ in sensitive_events


async def start_audit_subscriber():
    """
    Start the audit subscriber worker.
    
    Usage:
        python -m backend.workers.audit_subscriber
    """
    from backend.core.events.pubsub.subscriber import PubSubSubscriber
    
    subscriber = AuditSubscriber()
    
    # Connect to Pub/Sub
    pubsub_subscriber = PubSubSubscriber(
        subscription_name="audit-worker-subscription"
    )
    
    logger.info("🚀 Audit subscriber started")
    logger.info("Recording all events for compliance and security...")
    
    # Start consuming events
    await pubsub_subscriber.consume(subscriber.handle_event)


if __name__ == "__main__":
    import asyncio
    asyncio.run(start_audit_subscriber())

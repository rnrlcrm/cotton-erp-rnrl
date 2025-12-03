"""
Webhook API Router

Provides endpoints for managing webhook subscriptions.
"""

from __future__ import annotations

import logging
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, HttpUrl

from backend.app.dependencies import get_redis
from backend.core.auth.dependencies import get_current_user
from backend.core.webhooks import WebhookManager
from backend.core.webhooks.queue import QueuePriority
from backend.core.webhooks.schemas import WebhookEvent, WebhookEventType, WebhookSubscription
from backend.modules.settings.models.settings_models import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["webhooks"])

# Global webhook manager (singleton)
_webhook_manager: WebhookManager | None = None


def get_webhook_manager(redis=Depends(get_redis)) -> WebhookManager:
    """Get or create webhook manager"""
    global _webhook_manager
    if _webhook_manager is None:
        _webhook_manager = WebhookManager(redis)
    return _webhook_manager


# ============================================================================
# Request/Response Models
# ============================================================================

class CreateSubscriptionRequest(BaseModel):
    """Request to create webhook subscription"""
    url: HttpUrl
    event_types: List[WebhookEventType]
    description: str | None = None
    max_retries: int = 3


class SubscriptionResponse(BaseModel):
    """Webhook subscription response"""
    id: UUID
    organization_id: UUID
    url: str
    event_types: List[WebhookEventType]
    is_active: bool
    secret: str  # Show on creation only
    max_retries: int
    description: str | None = None
    
    class Config:
        from_attributes = True


class PublishEventRequest(BaseModel):
    """Request to manually publish webhook event (testing)"""
    event_type: WebhookEventType
    data: dict
    priority: QueuePriority = QueuePriority.NORMAL


# ============================================================================
# Webhook Subscription Endpoints
# ============================================================================

@router.post("/subscriptions", response_model=SubscriptionResponse, status_code=status.HTTP_201_CREATED)
async def create_subscription(
    request: CreateSubscriptionRequest,
    current_user: User = Depends(get_current_user),
    webhook_manager: WebhookManager = Depends(get_webhook_manager),
):
    """
    Create webhook subscription.
    
    Register a URL to receive webhook events.
    
    Features:
    - HMAC-SHA256 signature (secret provided in response)
    - Automatic retries (configurable)
    - Multi-tenant isolation
    
    Example:
    ```json
    {
        "url": "https://example.com/webhooks",
        "event_types": ["trade.created", "payment.completed"],
        "description": "Production webhook endpoint",
        "max_retries": 3
    }
    ```
    """
    # Get organization_id from current_user
    # SUPER_ADMIN users have NULL organization_id - they manage webhooks globally
    # INTERNAL users have organization_id - they manage webhooks for their org
    # EXTERNAL users (partners) have business_partner_id - not allowed to create webhooks
    organization_id = current_user.organization_id
    
    if organization_id is None and current_user.user_type != "SUPER_ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only SUPER_ADMIN or organization users can create webhooks"
        )
    
    # Generate secret
    import secrets
    secret = secrets.token_urlsafe(32)
    
    # Create subscription
    subscription = WebhookSubscription(
        organization_id=organization_id,
        url=request.url,
        event_types=request.event_types,
        secret=secret,
        max_retries=request.max_retries,
        description=request.description,
        created_by=current_user.id,
    )
    
    # Register
    await webhook_manager.register_subscription(subscription)
    
    logger.info(f"Created webhook subscription {subscription.id} for user {current_user.id}")
    
    return SubscriptionResponse(
        id=subscription.id,
        organization_id=subscription.organization_id,
        url=str(subscription.url),
        event_types=subscription.event_types,
        is_active=subscription.is_active,
        secret=secret,  # Show once
        max_retries=subscription.max_retries,
        description=subscription.description,
    )


@router.delete("/subscriptions/{subscription_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_subscription(
    subscription_id: UUID,
    current_user: User = Depends(get_current_user),
    webhook_manager: WebhookManager = Depends(get_webhook_manager),
):
    """
    Delete webhook subscription.
    
    Unregister webhook endpoint.
    """
    organization_id = current_user.id
    
    await webhook_manager.unregister_subscription(subscription_id, organization_id)
    
    logger.info(f"Deleted webhook subscription {subscription_id}")


@router.get("/stats")
async def get_webhook_stats(
    current_user: User = Depends(get_current_user),
    webhook_manager: WebhookManager = Depends(get_webhook_manager),
):
    """
    Get webhook statistics.
    
    Returns:
    - Queue sizes (by priority)
    - Dead-letter queue size
    - Delivery stats (total, success, failed, retries)
    - Active subscriptions
    """
    organization_id = current_user.id
    
    stats = await webhook_manager.get_stats(organization_id)
    
    return stats


@router.get("/dlq")
async def get_dead_letter_queue(
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    webhook_manager: WebhookManager = Depends(get_webhook_manager),
):
    """
    Get dead-letter queue items.
    
    Shows failed webhook deliveries that exceeded max retries.
    """
    organization_id = current_user.id
    
    dlq_items = await webhook_manager.queue.get_dlq_items(organization_id, limit)
    
    return {
        "items": [item.model_dump() for item in dlq_items],
        "total": len(dlq_items),
    }


@router.post("/dlq/{delivery_id}/retry", status_code=status.HTTP_202_ACCEPTED)
async def retry_dlq_item(
    delivery_id: UUID,
    current_user: User = Depends(get_current_user),
    webhook_manager: WebhookManager = Depends(get_webhook_manager),
):
    """
    Retry failed webhook delivery from DLQ.
    
    Moves item back to queue for retry.
    """
    organization_id = current_user.id
    
    success = await webhook_manager.queue.retry_dlq_item(delivery_id, organization_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Delivery not found in DLQ",
        )
    
    return {"message": "Delivery re-queued for retry"}


@router.post("/events/publish", status_code=status.HTTP_202_ACCEPTED)
async def publish_event(
    request: PublishEventRequest,
    current_user: User = Depends(get_current_user),
    webhook_manager: WebhookManager = Depends(get_webhook_manager),
):
    """
    Manually publish webhook event (for testing).
    
    In production, events are published automatically by the system.
    
    Example:
    ```json
    {
        "event_type": "trade.created",
        "data": {
            "trade_id": "123",
            "commodity": "wheat",
            "quantity": 1000
        },
        "priority": "high"
    }
    ```
    """
    organization_id = current_user.id
    
    # Create event
    event = WebhookEvent(
        event_type=request.event_type,
        data=request.data,
        organization_id=organization_id,
        user_id=current_user.id,
    )
    
    # Publish
    await webhook_manager.publish_event(event, request.priority)
    
    logger.info(f"Published webhook event {event.id} (type={event.event_type.value})")
    
    return {
        "event_id": event.id,
        "message": "Event published to webhook subscribers",
    }

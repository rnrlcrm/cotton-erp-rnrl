"""
Multi-Tenant Webhook Queue

Implements priority queues with retry logic and dead-letter queues.
"""

from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Dict, List, Optional
from uuid import UUID

from redis.asyncio import Redis

from backend.core.webhooks.delivery import DeliveryStatus, WebhookDelivery
from backend.core.webhooks.schemas import WebhookEvent

logger = logging.getLogger(__name__)


class QueuePriority(str, Enum):
    """Queue priority levels"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class WebhookQueue:
    """
    Multi-tenant webhook queue with priority and retry logic.
    
    Features:
    - Priority queues (CRITICAL > HIGH > NORMAL > LOW)
    - Per-organization queues (multi-tenant isolation)
    - Retry with exponential backoff
    - Dead-letter queue for failed deliveries
    - Rate limiting per organization
    """
    
    def __init__(
        self,
        redis: Redis,
        max_retries: int = 3,
        base_retry_delay: int = 60,  # 1 minute
        max_retry_delay: int = 3600,  # 1 hour
    ):
        self.redis = redis
        self.max_retries = max_retries
        self.base_retry_delay = base_retry_delay
        self.max_retry_delay = max_retry_delay
        
        # In-memory queues (for workers)
        # {org_id: {priority: [deliveries]}}
        self._queues: Dict[UUID, Dict[QueuePriority, List[WebhookDelivery]]] = defaultdict(
            lambda: {
                QueuePriority.CRITICAL: [],
                QueuePriority.HIGH: [],
                QueuePriority.NORMAL: [],
                QueuePriority.LOW: [],
            }
        )
        
        # Dead letter queue
        # {org_id: [deliveries]}
        self._dlq: Dict[UUID, List[WebhookDelivery]] = defaultdict(list)
        
        # Stats
        self.total_enqueued = 0
        self.total_delivered = 0
        self.total_failed = 0
        self.total_retries = 0
    
    async def enqueue(
        self,
        delivery: WebhookDelivery,
        organization_id: UUID,
        priority: QueuePriority = QueuePriority.NORMAL,
    ):
        """
        Enqueue webhook delivery.
        
        Args:
            delivery: Delivery record
            organization_id: Organization ID (multi-tenant)
            priority: Queue priority
        """
        # Add to in-memory queue
        self._queues[organization_id][priority].append(delivery)
        
        # Also persist to Redis for durability
        await self._persist_to_redis(delivery, organization_id, priority)
        
        self.total_enqueued += 1
        
        logger.info(
            f"Enqueued webhook delivery {delivery.id} "
            f"(org={organization_id}, priority={priority.value})"
        )
    
    async def dequeue(
        self,
        organization_id: UUID,
    ) -> Optional[WebhookDelivery]:
        """
        Dequeue highest priority delivery for organization.
        
        Args:
            organization_id: Organization ID
            
        Returns:
            WebhookDelivery or None
        """
        # Check queues in priority order
        for priority in [
            QueuePriority.CRITICAL,
            QueuePriority.HIGH,
            QueuePriority.NORMAL,
            QueuePriority.LOW,
        ]:
            queue = self._queues[organization_id][priority]
            if queue:
                delivery = queue.pop(0)
                logger.debug(f"Dequeued delivery {delivery.id} (priority={priority.value})")
                return delivery
        
        return None
    
    async def enqueue_retry(
        self,
        delivery: WebhookDelivery,
        organization_id: UUID,
    ):
        """
        Enqueue delivery for retry with exponential backoff.
        
        Args:
            delivery: Failed delivery
            organization_id: Organization ID
        """
        delivery.attempt += 1
        self.total_retries += 1
        
        # Check if max retries exceeded
        if delivery.attempt >= delivery.max_attempts:
            # Move to dead-letter queue
            await self.move_to_dlq(delivery, organization_id)
            return
        
        # Calculate retry delay (exponential backoff)
        delay = min(
            self.base_retry_delay * (2 ** (delivery.attempt - 1)),
            self.max_retry_delay,
        )
        
        delivery.next_retry_at = datetime.now(timezone.utc) + timedelta(seconds=delay)
        delivery.status = DeliveryStatus.RETRYING
        
        logger.info(
            f"Scheduling retry for delivery {delivery.id} "
            f"(attempt {delivery.attempt}/{delivery.max_attempts}, "
            f"delay={delay}s)"
        )
        
        # Re-enqueue with delay
        await asyncio.sleep(delay)
        await self.enqueue(
            delivery,
            organization_id,
            priority=QueuePriority.HIGH,  # Retries get higher priority
        )
    
    async def move_to_dlq(
        self,
        delivery: WebhookDelivery,
        organization_id: UUID,
    ):
        """
        Move delivery to dead-letter queue.
        
        Args:
            delivery: Failed delivery
            organization_id: Organization ID
        """
        delivery.status = DeliveryStatus.DEAD_LETTER
        delivery.completed_at = datetime.now(timezone.utc)
        
        self._dlq[organization_id].append(delivery)
        self.total_failed += 1
        
        # Persist to Redis
        await self.redis.lpush(
            f"webhook:dlq:{organization_id}",
            delivery.model_dump_json(),
        )
        
        logger.warning(
            f"Moved delivery {delivery.id} to DLQ "
            f"(org={organization_id}, attempts={delivery.attempt})"
        )
    
    async def mark_delivered(
        self,
        delivery: WebhookDelivery,
        response_status: int,
        response_body: Optional[str] = None,
    ):
        """
        Mark delivery as successful.
        
        Args:
            delivery: Delivery record
            response_status: HTTP response status
            response_body: Response body
        """
        delivery.status = DeliveryStatus.SUCCESS
        delivery.response_status = response_status
        delivery.response_body = response_body
        delivery.completed_at = datetime.now(timezone.utc)
        
        self.total_delivered += 1
        
        logger.info(f"Delivery {delivery.id} succeeded (status={response_status})")
    
    async def mark_failed(
        self,
        delivery: WebhookDelivery,
        error_message: str,
        error_code: Optional[str] = None,
    ):
        """
        Mark delivery as failed.
        
        Args:
            delivery: Delivery record
            error_message: Error message
            error_code: Optional error code
        """
        delivery.status = DeliveryStatus.FAILED
        delivery.error_message = error_message
        delivery.error_code = error_code
        
        logger.error(f"Delivery {delivery.id} failed: {error_message}")
    
    async def _persist_to_redis(
        self,
        delivery: WebhookDelivery,
        organization_id: UUID,
        priority: QueuePriority,
    ):
        """Persist delivery to Redis for durability"""
        key = f"webhook:queue:{organization_id}:{priority.value}"
        await self.redis.lpush(key, delivery.model_dump_json())
    
    async def get_queue_stats(self, organization_id: UUID) -> Dict[str, any]:
        """
        Get queue statistics for organization.
        
        Args:
            organization_id: Organization ID
            
        Returns:
            Queue stats
        """
        stats = {
            "organization_id": str(organization_id),
            "queues": {},
            "dlq_size": len(self._dlq[organization_id]),
            "total_enqueued": self.total_enqueued,
            "total_delivered": self.total_delivered,
            "total_failed": self.total_failed,
            "total_retries": self.total_retries,
        }
        
        for priority in QueuePriority:
            stats["queues"][priority.value] = len(
                self._queues[organization_id][priority]
            )
        
        return stats
    
    async def get_dlq_items(
        self,
        organization_id: UUID,
        limit: int = 100,
    ) -> List[WebhookDelivery]:
        """
        Get items from dead-letter queue.
        
        Args:
            organization_id: Organization ID
            limit: Max items to return
            
        Returns:
            List of failed deliveries
        """
        return self._dlq[organization_id][:limit]
    
    async def retry_dlq_item(
        self,
        delivery_id: UUID,
        organization_id: UUID,
    ) -> bool:
        """
        Retry item from dead-letter queue.
        
        Args:
            delivery_id: Delivery ID
            organization_id: Organization ID
            
        Returns:
            True if re-queued successfully
        """
        # Find in DLQ
        dlq = self._dlq[organization_id]
        delivery = next((d for d in dlq if d.id == delivery_id), None)
        
        if not delivery:
            return False
        
        # Remove from DLQ
        dlq.remove(delivery)
        
        # Reset for retry
        delivery.status = DeliveryStatus.PENDING
        delivery.attempt = 0
        delivery.error_message = None
        delivery.error_code = None
        
        # Re-enqueue
        await self.enqueue(delivery, organization_id, QueuePriority.NORMAL)
        
        logger.info(f"Re-queued DLQ item {delivery_id}")
        return True

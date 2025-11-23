"""
Webhook Manager

Main orchestrator for webhook operations.
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional
from uuid import UUID

import httpx
from redis.asyncio import Redis

from backend.core.webhooks.delivery import DeliveryStatus, WebhookDelivery
from backend.core.webhooks.queue import QueuePriority, WebhookQueue
from backend.core.webhooks.schemas import WebhookEvent, WebhookSubscription
from backend.core.webhooks.signer import WebhookSigner

logger = logging.getLogger(__name__)


class WebhookManager:
    """
    Webhook management system.
    
    Features:
    - Multi-tenant webhook subscriptions
    - Priority queuing
    - Automatic retries
    - HMAC signature verification
    - Delivery tracking
    - Dead-letter queue
    """
    
    def __init__(
        self,
        redis: Redis,
        timeout: int = 30,
        max_workers: int = 10,
    ):
        self.redis = redis
        self.timeout = timeout
        self.max_workers = max_workers
        
        # Queue system
        self.queue = WebhookQueue(redis)
        
        # Subscriptions: {org_id: [subscriptions]}
        self._subscriptions: Dict[UUID, List[WebhookSubscription]] = {}
        
        # HTTP client
        self._client: Optional[httpx.AsyncClient] = None
        
        # Workers
        self._workers: List[asyncio.Task] = []
        self._running = False
    
    async def get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client"""
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=self.timeout,
                follow_redirects=True,
            )
        return self._client
    
    async def register_subscription(
        self,
        subscription: WebhookSubscription,
    ):
        """
        Register webhook subscription.
        
        Args:
            subscription: Subscription to register
        """
        org_id = subscription.organization_id
        
        if org_id not in self._subscriptions:
            self._subscriptions[org_id] = []
        
        self._subscriptions[org_id].append(subscription)
        
        # Persist to Redis
        await self.redis.hset(
            f"webhook:subscriptions:{org_id}",
            str(subscription.id),
            subscription.model_dump_json(),
        )
        
        logger.info(
            f"Registered webhook subscription {subscription.id} "
            f"for org {org_id} (url={subscription.url})"
        )
    
    async def unregister_subscription(
        self,
        subscription_id: UUID,
        organization_id: UUID,
    ):
        """
        Unregister webhook subscription.
        
        Args:
            subscription_id: Subscription ID
            organization_id: Organization ID
        """
        if organization_id in self._subscriptions:
            self._subscriptions[organization_id] = [
                s for s in self._subscriptions[organization_id]
                if s.id != subscription_id
            ]
        
        # Remove from Redis
        await self.redis.hdel(
            f"webhook:subscriptions:{organization_id}",
            str(subscription_id),
        )
        
        logger.info(f"Unregistered webhook subscription {subscription_id}")
    
    async def publish_event(
        self,
        event: WebhookEvent,
        priority: QueuePriority = QueuePriority.NORMAL,
    ):
        """
        Publish webhook event to all subscribers.
        
        Args:
            event: Event to publish
            priority: Queue priority
        """
        org_id = event.organization_id
        if not org_id:
            logger.warning(f"Event {event.id} has no organization_id, skipping")
            return
        
        # Get subscriptions for this org
        subscriptions = self._subscriptions.get(org_id, [])
        
        # Filter by event type
        matching_subs = [
            sub for sub in subscriptions
            if sub.is_active and event.event_type in sub.event_types
        ]
        
        logger.info(
            f"Publishing event {event.id} (type={event.event_type.value}) "
            f"to {len(matching_subs)} subscribers"
        )
        
        # Create delivery for each subscription
        for subscription in matching_subs:
            delivery = await self._create_delivery(event, subscription)
            await self.queue.enqueue(delivery, org_id, priority)
    
    async def _create_delivery(
        self,
        event: WebhookEvent,
        subscription: WebhookSubscription,
    ) -> WebhookDelivery:
        """
        Create delivery record for event + subscription.
        
        Args:
            event: Webhook event
            subscription: Subscription
            
        Returns:
            WebhookDelivery
        """
        # Serialize event
        payload = event.model_dump_json()
        
        # Sign payload
        signer = WebhookSigner(subscription.secret)
        signature_header = signer.get_signature_header(payload)
        
        # Create delivery
        delivery = WebhookDelivery(
            subscription_id=subscription.id,
            event_id=event.id,
            url=str(subscription.url),
            request_body=payload,
            request_headers={
                "Content-Type": "application/json",
                **signature_header,
            },
            max_attempts=subscription.max_retries,
        )
        
        return delivery
    
    async def process_delivery(
        self,
        delivery: WebhookDelivery,
        organization_id: UUID,
    ):
        """
        Process webhook delivery (send HTTP request).
        
        Args:
            delivery: Delivery to process
            organization_id: Organization ID
        """
        delivery.status = DeliveryStatus.SENDING
        delivery.sent_at = datetime.now(timezone.utc)
        
        client = await self.get_client()
        
        try:
            logger.debug(f"Sending webhook {delivery.id} to {delivery.url}")
            
            response = await client.post(
                delivery.url,
                content=delivery.request_body,
                headers=delivery.request_headers,
            )
            
            # Check response status
            if 200 <= response.status_code < 300:
                # Success
                await self.queue.mark_delivered(
                    delivery,
                    response.status_code,
                    response.text,
                )
            else:
                # Failed (non-2xx)
                await self.queue.mark_failed(
                    delivery,
                    f"HTTP {response.status_code}: {response.text[:200]}",
                    error_code=str(response.status_code),
                )
                
                # Retry
                await self.queue.enqueue_retry(delivery, organization_id)
        
        except httpx.TimeoutException as e:
            await self.queue.mark_failed(delivery, f"Timeout: {e}", "TIMEOUT")
            await self.queue.enqueue_retry(delivery, organization_id)
        
        except httpx.ConnectError as e:
            await self.queue.mark_failed(delivery, f"Connection error: {e}", "CONNECT_ERROR")
            await self.queue.enqueue_retry(delivery, organization_id)
        
        except Exception as e:
            await self.queue.mark_failed(delivery, f"Error: {e}", "UNKNOWN_ERROR")
            await self.queue.enqueue_retry(delivery, organization_id)
    
    async def worker(self, worker_id: int):
        """
        Worker that processes webhook deliveries.
        
        Args:
            worker_id: Worker ID
        """
        logger.info(f"Worker {worker_id} started")
        
        while self._running:
            try:
                # Process deliveries for all organizations
                # (In production, you'd want better load balancing)
                for org_id in list(self._subscriptions.keys()):
                    delivery = await self.queue.dequeue(org_id)
                    
                    if delivery:
                        await self.process_delivery(delivery, org_id)
                
                # Sleep briefly if no work
                await asyncio.sleep(0.1)
            
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Worker {worker_id} error: {e}", exc_info=True)
                await asyncio.sleep(1)
        
        logger.info(f"Worker {worker_id} stopped")
    
    async def start_workers(self):
        """Start webhook delivery workers"""
        if self._running:
            return
        
        self._running = True
        
        # Start workers
        for i in range(self.max_workers):
            task = asyncio.create_task(self.worker(i))
            self._workers.append(task)
        
        logger.info(f"Started {self.max_workers} webhook workers")
    
    async def stop_workers(self):
        """Stop webhook delivery workers"""
        if not self._running:
            return
        
        self._running = False
        
        # Cancel workers
        for task in self._workers:
            task.cancel()
        
        # Wait for workers to finish
        await asyncio.gather(*self._workers, return_exceptions=True)
        
        self._workers.clear()
        
        logger.info("Stopped webhook workers")
    
    async def get_stats(self, organization_id: UUID) -> Dict[str, any]:
        """
        Get webhook statistics for organization.
        
        Args:
            organization_id: Organization ID
            
        Returns:
            Stats dict
        """
        stats = await self.queue.get_queue_stats(organization_id)
        
        stats["subscriptions"] = len(self._subscriptions.get(organization_id, []))
        stats["workers_running"] = len(self._workers)
        
        return stats
    
    async def close(self):
        """Close webhook manager"""
        await self.stop_workers()
        
        if self._client:
            await self._client.aclose()
            self._client = None

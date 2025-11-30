"""
Base Service Class with Complete Infrastructure Integration

Every service MUST inherit from this base class to get:
- Transactional outbox pattern
- Event emission
- Idempotency enforcement
- Redis caching
- Proper transaction management
"""

from __future__ import annotations

import json
from typing import Any, Dict, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as redis

from backend.core.outbox import OutboxRepository


class BaseService:
    """
    Base service class with complete infrastructure integration.
    
    ALL business logic services MUST inherit from this class.
    
    Provides:
    - Transactional outbox for event emission
    - Idempotency enforcement via Redis
    - Proper transaction management
    - Event publishing abstraction
    
    Usage:
        class PartnerService(BaseService):
            async def approve_partner(self, partner_id: UUID, ..., idempotency_key: Optional[str] = None):
                # Idempotency check (automatic)
                cached = await self.check_idempotency(idempotency_key)
                if cached:
                    return cached
                
                # Do business logic
                partner = await self.partner_repo.approve(partner_id)
                
                # Emit event (transactional outbox)
                await self.emit_event(
                    aggregate_id=partner.id,
                    aggregate_type="Partner",
                    event_type="PartnerApproved",
                    payload={"partner_id": str(partner.id), ...},
                    topic_name="partner-events",
                    idempotency_key=idempotency_key
                )
                
                # Commit transaction
                await self.commit()
                
                # Cache result
                await self.cache_result(idempotency_key, partner)
                
                return partner
    """
    
    def __init__(
        self,
        db: AsyncSession,
        redis_client: Optional[redis.Redis] = None,
        current_user_id: Optional[UUID] = None,
        organization_id: Optional[UUID] = None
    ):
        """
        Initialize base service.
        
        Args:
            db: SQLAlchemy async session
            redis_client: Redis client for idempotency caching
            current_user_id: Current authenticated user ID
            organization_id: Current organization ID (for multi-tenancy)
        """
        self.db = db
        self.redis = redis_client
        self.current_user_id = current_user_id
        self.organization_id = organization_id
        
        # Initialize outbox repository
        self.outbox_repo = OutboxRepository(db)
    
    async def check_idempotency(self, idempotency_key: Optional[str]) -> Optional[Dict[str, Any]]:
        """
        Check if operation was already performed (idempotency).
        
        Args:
            idempotency_key: Idempotency key from header
        
        Returns:
            Cached result if operation already performed, None otherwise
        """
        if not idempotency_key or not self.redis:
            return None
        
        try:
            cache_key = f"idempotency:{idempotency_key}"
            cached = await self.redis.get(cache_key)
            
            if cached:
                # Operation already performed, return cached result
                return json.loads(cached)
        except Exception as e:
            # Redis failure shouldn't block operation
            # Log error but continue
            print(f"Redis idempotency check failed: {e}")
        
        return None
    
    async def cache_result(
        self,
        idempotency_key: Optional[str],
        result: Any,
        ttl_seconds: int = 86400  # 24 hours
    ) -> None:
        """
        Cache operation result for idempotency.
        
        Args:
            idempotency_key: Idempotency key
            result: Operation result to cache
            ttl_seconds: Time to live in seconds (default 24 hours)
        """
        if not idempotency_key or not self.redis:
            return
        
        try:
            cache_key = f"idempotency:{idempotency_key}"
            
            # Convert result to dict if it's a model
            if hasattr(result, '__dict__'):
                result_dict = {k: str(v) if isinstance(v, UUID) else v 
                              for k, v in result.__dict__.items() 
                              if not k.startswith('_')}
            else:
                result_dict = result
            
            await self.redis.setex(
                cache_key,
                ttl_seconds,
                json.dumps(result_dict, default=str)
            )
        except Exception as e:
            # Redis failure shouldn't block operation
            print(f"Redis cache failed: {e}")
    
    async def emit_event(
        self,
        aggregate_id: UUID,
        aggregate_type: str,
        event_type: str,
        payload: Dict[str, Any],
        topic_name: str,
        metadata: Optional[Dict[str, Any]] = None,
        idempotency_key: Optional[str] = None,
        version: int = 1
    ) -> None:
        """
        Emit event through transactional outbox.
        
        Event will be persisted in the same transaction as business operation,
        then asynchronously published to GCP Pub/Sub.
        
        Args:
            aggregate_id: ID of the entity that triggered the event
            aggregate_type: Type of entity (e.g., "Partner", "Availability")
            event_type: Event type (e.g., "PartnerApproved", "AvailabilityPosted")
            payload: Event payload (published to Pub/Sub)
            topic_name: GCP Pub/Sub topic name
            metadata: Optional metadata (user_id, ip_address, trace_id)
            idempotency_key: Optional idempotency key
            version: Event schema version for 15-year compatibility
        """
        # Add user context to metadata
        event_metadata = metadata or {}
        if self.current_user_id:
            event_metadata["user_id"] = str(self.current_user_id)
        if self.organization_id:
            event_metadata["organization_id"] = str(self.organization_id)
        
        # Add event to outbox (transactional)
        await self.outbox_repo.add_event(
            aggregate_id=aggregate_id,
            aggregate_type=aggregate_type,
            event_type=event_type,
            payload=payload,
            topic_name=topic_name,
            metadata=event_metadata,
            idempotency_key=idempotency_key,
            version=version
        )
    
    async def commit(self) -> None:
        """
        Commit database transaction.
        
        This persists:
        - Business logic changes
        - Outbox events (atomically)
        
        Outbox worker will then publish events to Pub/Sub asynchronously.
        """
        await self.db.commit()
    
    async def rollback(self) -> None:
        """
        Rollback database transaction.
        
        Rolls back both business logic and outbox events.
        """
        await self.db.rollback()
    
    def check_organization_access(self, resource_org_id: UUID) -> None:
        """
        Check row-level security: user can only access their organization's data.
        
        Args:
            resource_org_id: Organization ID of the resource being accessed
        
        Raises:
            PermissionError: If user tries to access another organization's data
        """
        if self.organization_id and resource_org_id != self.organization_id:
            raise PermissionError(
                f"Access denied: Resource belongs to organization {resource_org_id}, "
                f"user belongs to {self.organization_id}"
            )

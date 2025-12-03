"""
AI Event Handlers

Connect AI services to event bus for automatic embedding generation.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from backend.core.events.base import BaseEvent
    from sqlalchemy.ext.asyncio import AsyncSession

from backend.ai.jobs.vector_sync import EmbeddingSyncJob

logger = logging.getLogger(__name__)


async def handle_requirement_created(event: BaseEvent, db: AsyncSession) -> None:
    """
    Handle requirement.created event.
    
    Generates embedding for semantic search.
    """
    logger.info(f"AI handler: requirement.created {event.aggregate_id}")
    
    job = EmbeddingSyncJob(db)
    await job.handle_requirement_event(event)


async def handle_requirement_updated(event: BaseEvent, db: AsyncSession) -> None:
    """
    Handle requirement.updated event.
    
    Regenerates embedding if text changed.
    """
    logger.info(f"AI handler: requirement.updated {event.aggregate_id}")
    
    job = EmbeddingSyncJob(db)
    await job.handle_requirement_event(event)


async def handle_availability_created(event: BaseEvent, db: AsyncSession) -> None:
    """
    Handle availability.created event.
    
    Generates embedding for semantic search.
    """
    logger.info(f"AI handler: availability.created {event.aggregate_id}")
    
    job = EmbeddingSyncJob(db)
    await job.handle_availability_event(event)


async def handle_availability_updated(event: BaseEvent, db: AsyncSession) -> None:
    """
    Handle availability.updated event.
    
    Regenerates embedding if text changed.
    """
    logger.info(f"AI handler: availability.updated {event.aggregate_id}")
    
    job = EmbeddingSyncJob(db)
    await job.handle_availability_event(event)


def register_ai_event_handlers(event_bus) -> None:
    """
    Register all AI event handlers with event bus.
    
    Call this during application startup.
    
    Usage:
        from backend.core.events.event_bus import get_event_bus
        from backend.ai.events.handlers import register_ai_event_handlers
        
        event_bus = get_event_bus(db)
        register_ai_event_handlers(event_bus)
    """
    # Register Trade Desk events
    event_bus.subscribe("requirement.created", handle_requirement_created)
    event_bus.subscribe("requirement.updated", handle_requirement_updated)
    event_bus.subscribe("availability.created", handle_availability_created)
    event_bus.subscribe("availability.updated", handle_availability_updated)
    
    logger.info("AI event handlers registered successfully")

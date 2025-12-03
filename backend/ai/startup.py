"""
AI Startup Integration

Wire AI services to application startup.
"""

import logging
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis

logger = logging.getLogger(__name__)


async def initialize_ai_services(
    db: AsyncSession,
    redis: Optional[Redis] = None,
    event_bus = None
) -> None:
    """
    Initialize AI services on application startup.
    
    Steps:
    1. Register event handlers for vector sync
    2. Initialize guardrails
    3. Initialize memory loader
    4. Warm up embedding service
    
    Usage (in main.py or app startup):
        from backend.ai.startup import initialize_ai_services
        from backend.core.database import get_db
        from backend.core.redis import get_redis
        from backend.core.events.event_bus import get_event_bus
        
        @app.on_event("startup")
        async def startup():
            db = await get_db()
            redis = await get_redis()
            event_bus = get_event_bus(db)
            
            await initialize_ai_services(db, redis, event_bus)
    
    Args:
        db: Database session
        redis: Redis client (optional)
        event_bus: Event bus instance (optional)
    """
    logger.info("Initializing AI services...")
    
    # Step 1: Register event handlers
    if event_bus:
        from backend.ai.events import register_ai_event_handlers
        
        register_ai_event_handlers(event_bus)
        logger.info("✅ AI event handlers registered")
    else:
        logger.warning("⚠️ Event bus not provided - vector sync disabled")
    
    # Step 2: Initialize guardrails
    if redis:
        from backend.ai.guardrails import get_guardrails
        
        guardrails = get_guardrails(redis)
        logger.info("✅ AI guardrails initialized")
    else:
        logger.warning("⚠️ Redis not provided - guardrails disabled")
    
    # Step 3: Initialize memory loader
    from backend.ai.memory import get_memory_loader
    
    memory_loader = get_memory_loader(db, redis)
    logger.info("✅ AI memory loader initialized")
    
    # Step 4: Warm up embedding service
    try:
        from backend.ai.services.embedding_service import get_embedding_service
        
        embedding_service = get_embedding_service()
        
        # Test encode (loads model into memory)
        test_embedding = embedding_service.encode("Test startup message")
        
        logger.info(f"✅ Embedding service warmed up (dim={len(test_embedding)})")
    
    except Exception as e:
        logger.warning(f"⚠️ Failed to warm up embedding service: {e}")
    
    logger.info("AI services initialized successfully ✨")


async def backfill_embeddings(
    db: AsyncSession,
    batch_size: int = 100
) -> None:
    """
    Backfill embeddings for existing requirements and availabilities.
    
    Run this once after enabling AI features on existing data.
    
    Usage:
        from backend.ai.startup import backfill_embeddings
        from backend.core.database import get_db
        
        db = await get_db()
        await backfill_embeddings(db, batch_size=100)
    
    Args:
        db: Database session
        batch_size: Number of records per batch
    """
    logger.info(f"Starting embedding backfill (batch_size={batch_size})...")
    
    from backend.ai.jobs.vector_sync import EmbeddingSyncJob
    
    job = EmbeddingSyncJob(db)
    
    await job.backfill_all_embeddings(batch_size=batch_size)
    
    logger.info("Embedding backfill completed ✨")

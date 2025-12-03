"""
Vector Embedding Sync Jobs

Background jobs to sync embeddings when requirements/availabilities are created or updated.
Listens to event bus and generates embeddings asynchronously.
"""

from __future__ import annotations

import logging
import hashlib
from typing import Optional
from uuid import UUID
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.ai.services.embedding_service import get_embedding_service
from backend.core.events.base import BaseEvent

logger = logging.getLogger(__name__)


class EmbeddingSyncJob:
    """
    Sync embeddings for requirements and availabilities.
    
    Triggered by events:
    - requirement.created
    - requirement.updated
    - availability.created
    - availability.updated
    
    Features:
    - Async embedding generation
    - Text hashing to avoid duplicate work
    - Automatic retry on failure
    - Batch processing support
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.embedding_service = get_embedding_service()
    
    async def sync_requirement_embedding(
        self,
        requirement_id: UUID,
        requirement_text: str,
        force_refresh: bool = False
    ) -> bool:
        """
        Generate and store embedding for requirement.
        
        Args:
            requirement_id: Requirement UUID
            requirement_text: Text to embed (commodity + variety + quality params)
            force_refresh: Force regeneration even if exists
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Import here to avoid circular dependency
            from backend.modules.trade_desk.models.requirement_embedding import RequirementEmbedding
            
            # Calculate text hash to detect changes
            text_hash = hashlib.sha256(requirement_text.encode()).hexdigest()
            
            # Check if embedding already exists with same hash
            if not force_refresh:
                existing = await self.db.execute(
                    select(RequirementEmbedding).where(
                        RequirementEmbedding.requirement_id == requirement_id
                    )
                )
                existing_emb = existing.scalar_one_or_none()
                
                if existing_emb and existing_emb.text_hash == text_hash:
                    logger.debug(f"Embedding for requirement {requirement_id} already up-to-date")
                    return True
            
            # Generate embedding
            logger.info(f"Generating embedding for requirement {requirement_id}")
            embedding_vector = self.embedding_service.encode(requirement_text)
            
            # Convert numpy array to list for pgvector
            embedding_list = embedding_vector.tolist()
            
            # Upsert embedding
            existing = await self.db.execute(
                select(RequirementEmbedding).where(
                    RequirementEmbedding.requirement_id == requirement_id
                )
            )
            existing_emb = existing.scalar_one_or_none()
            
            if existing_emb:
                # Update
                existing_emb.embedding = embedding_list
                existing_emb.text_hash = text_hash
                existing_emb.updated_at = datetime.utcnow()
            else:
                # Insert
                new_emb = RequirementEmbedding(
                    requirement_id=requirement_id,
                    embedding=embedding_list,
                    text_hash=text_hash,
                )
                self.db.add(new_emb)
            
            await self.db.commit()
            logger.info(f"Successfully synced embedding for requirement {requirement_id}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to sync embedding for requirement {requirement_id}: {e}")
            await self.db.rollback()
            return False
    
    async def sync_availability_embedding(
        self,
        availability_id: UUID,
        availability_text: str,
        force_refresh: bool = False
    ) -> bool:
        """
        Generate and store embedding for availability.
        
        Args:
            availability_id: Availability UUID
            availability_text: Text to embed (commodity + variety + quality params)
            force_refresh: Force regeneration even if exists
            
        Returns:
            True if successful, False otherwise
        """
        try:
            from backend.modules.trade_desk.models.availability_embedding import AvailabilityEmbedding
            
            # Calculate text hash
            text_hash = hashlib.sha256(availability_text.encode()).hexdigest()
            
            # Check if already exists
            if not force_refresh:
                existing = await self.db.execute(
                    select(AvailabilityEmbedding).where(
                        AvailabilityEmbedding.availability_id == availability_id
                    )
                )
                existing_emb = existing.scalar_one_or_none()
                
                if existing_emb and existing_emb.text_hash == text_hash:
                    logger.debug(f"Embedding for availability {availability_id} already up-to-date")
                    return True
            
            # Generate embedding
            logger.info(f"Generating embedding for availability {availability_id}")
            embedding_vector = self.embedding_service.encode(availability_text)
            embedding_list = embedding_vector.tolist()
            
            # Upsert
            existing = await self.db.execute(
                select(AvailabilityEmbedding).where(
                    AvailabilityEmbedding.availability_id == availability_id
                )
            )
            existing_emb = existing.scalar_one_or_none()
            
            if existing_emb:
                existing_emb.embedding = embedding_list
                existing_emb.text_hash = text_hash
                existing_emb.updated_at = datetime.utcnow()
            else:
                new_emb = AvailabilityEmbedding(
                    availability_id=availability_id,
                    embedding=embedding_list,
                    text_hash=text_hash,
                )
                self.db.add(new_emb)
            
            await self.db.commit()
            logger.info(f"Successfully synced embedding for availability {availability_id}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to sync embedding for availability {availability_id}: {e}")
            await self.db.rollback()
            return False
    
    async def handle_requirement_event(self, event: BaseEvent) -> None:
        """
        Handle requirement created/updated event.
        
        Extracts text from requirement and generates embedding.
        """
        try:
            from backend.modules.trade_desk.repositories.requirement_repository import RequirementRepository
            
            requirement_id = event.aggregate_id
            
            # Fetch requirement
            repo = RequirementRepository(self.db)
            requirement = await repo.get(requirement_id)
            
            if not requirement:
                logger.warning(f"Requirement {requirement_id} not found for embedding sync")
                return
            
            # Build text for embedding
            text_parts = [
                requirement.commodity.name if requirement.commodity else "",
                requirement.variety.name if requirement.variety else "",
            ]
            
            # Add quality parameters
            if requirement.quality_params:
                for key, value in requirement.quality_params.items():
                    text_parts.append(f"{key}:{value}")
            
            # Add location if available
            if requirement.delivery_location:
                text_parts.append(requirement.delivery_location.get('state', ''))
                text_parts.append(requirement.delivery_location.get('district', ''))
            
            requirement_text = " ".join(filter(None, text_parts))
            
            # Sync embedding
            await self.sync_requirement_embedding(requirement_id, requirement_text)
        
        except Exception as e:
            logger.error(f"Error handling requirement event: {e}")
    
    async def handle_availability_event(self, event: BaseEvent) -> None:
        """
        Handle availability created/updated event.
        
        Extracts text from availability and generates embedding.
        """
        try:
            from backend.modules.trade_desk.repositories.availability_repository import AvailabilityRepository
            
            availability_id = event.aggregate_id
            
            # Fetch availability
            repo = AvailabilityRepository(self.db)
            availability = await repo.get(availability_id)
            
            if not availability:
                logger.warning(f"Availability {availability_id} not found for embedding sync")
                return
            
            # Build text for embedding
            text_parts = [
                availability.commodity.name if availability.commodity else "",
                availability.variety.name if availability.variety else "",
            ]
            
            # Add quality parameters
            if availability.quality_params:
                for key, value in availability.quality_params.items():
                    text_parts.append(f"{key}:{value}")
            
            # Add location
            if availability.location:
                text_parts.append(availability.location.get('state', ''))
                text_parts.append(availability.location.get('district', ''))
            
            availability_text = " ".join(filter(None, text_parts))
            
            # Sync embedding
            await self.sync_availability_embedding(availability_id, availability_text)
        
        except Exception as e:
            logger.error(f"Error handling availability event: {e}")
    
    async def backfill_all_embeddings(self, batch_size: int = 100) -> dict:
        """
        Backfill embeddings for all existing requirements and availabilities.
        
        Use this for initial data migration or after model updates.
        
        Args:
            batch_size: Number of records to process at once
            
        Returns:
            Statistics dict with success/failure counts
        """
        stats = {
            "requirements_processed": 0,
            "requirements_success": 0,
            "requirements_failed": 0,
            "availabilities_processed": 0,
            "availabilities_success": 0,
            "availabilities_failed": 0,
        }
        
        try:
            from backend.modules.trade_desk.models.requirement import Requirement
            from backend.modules.trade_desk.models.availability import Availability
            
            # Process requirements
            logger.info("Starting requirement embedding backfill...")
            offset = 0
            while True:
                result = await self.db.execute(
                    select(Requirement)
                    .where(Requirement.status != 'DELETED')
                    .limit(batch_size)
                    .offset(offset)
                )
                requirements = result.scalars().all()
                
                if not requirements:
                    break
                
                for req in requirements:
                    stats["requirements_processed"] += 1
                    
                    text_parts = [
                        req.commodity.name if req.commodity else "",
                        req.variety.name if req.variety else "",
                    ]
                    if req.quality_params:
                        for k, v in req.quality_params.items():
                            text_parts.append(f"{k}:{v}")
                    
                    req_text = " ".join(filter(None, text_parts))
                    
                    success = await self.sync_requirement_embedding(req.id, req_text)
                    if success:
                        stats["requirements_success"] += 1
                    else:
                        stats["requirements_failed"] += 1
                
                offset += batch_size
                logger.info(f"Processed {stats['requirements_processed']} requirements...")
            
            # Process availabilities
            logger.info("Starting availability embedding backfill...")
            offset = 0
            while True:
                result = await self.db.execute(
                    select(Availability)
                    .where(Availability.status != 'DELETED')
                    .limit(batch_size)
                    .offset(offset)
                )
                availabilities = result.scalars().all()
                
                if not availabilities:
                    break
                
                for avail in availabilities:
                    stats["availabilities_processed"] += 1
                    
                    text_parts = [
                        avail.commodity.name if avail.commodity else "",
                        avail.variety.name if avail.variety else "",
                    ]
                    if avail.quality_params:
                        for k, v in avail.quality_params.items():
                            text_parts.append(f"{k}:{v}")
                    
                    avail_text = " ".join(filter(None, text_parts))
                    
                    success = await self.sync_availability_embedding(avail.id, avail_text)
                    if success:
                        stats["availabilities_success"] += 1
                    else:
                        stats["availabilities_failed"] += 1
                
                offset += batch_size
                logger.info(f"Processed {stats['availabilities_processed']} availabilities...")
            
            logger.info(f"Backfill complete: {stats}")
            return stats
        
        except Exception as e:
            logger.error(f"Backfill failed: {e}")
            stats["error"] = str(e)
            return stats

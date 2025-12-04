"""
Vector Search Service - Semantic search using pgvector

Provides semantic similarity search for requirements and availabilities
using cosine distance on 384-dimensional embeddings.
"""

from typing import List, Dict, Any, Optional
from uuid import UUID
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.modules.trade_desk.models.requirement_embedding import RequirementEmbedding
from backend.modules.trade_desk.models.availability_embedding import AvailabilityEmbedding
from backend.modules.trade_desk.models.requirement import Requirement
from backend.modules.trade_desk.models.availability import Availability


class VectorSearchService:
    """
    Semantic search service using pgvector cosine similarity.
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def find_similar_requirements(
        self,
        query_embedding: List[float],
        limit: int = 10,
        similarity_threshold: float = 0.7,
        exclude_ids: Optional[List[UUID]] = None
    ) -> List[Dict[str, Any]]:
        """
        Find requirements similar to query embedding using cosine similarity.
        
        Args:
            query_embedding: 384-dim vector to search with
            limit: Maximum results to return
            similarity_threshold: Minimum cosine similarity (0-1)
            exclude_ids: Requirement IDs to exclude from results
            
        Returns:
            List of dicts with requirement and similarity score
        """
        # Build query with cosine distance
        query = (
            select(
                Requirement,
                RequirementEmbedding,
                (1 - RequirementEmbedding.embedding.cosine_distance(query_embedding)).label("similarity")
            )
            .join(RequirementEmbedding, Requirement.id == RequirementEmbedding.requirement_id)
            .where(Requirement.status == "ACTIVE")
        )
        
        # Exclude specific IDs if provided
        if exclude_ids:
            query = query.where(~Requirement.id.in_(exclude_ids))
        
        # Filter by similarity threshold and order by similarity
        query = (
            query
            .having(func.literal(1) - RequirementEmbedding.embedding.cosine_distance(query_embedding) >= similarity_threshold)
            .order_by((1 - RequirementEmbedding.embedding.cosine_distance(query_embedding)).desc())
            .limit(limit)
        )
        
        result = await self.db.execute(query)
        rows = result.all()
        
        return [
            {
                "requirement": row[0],
                "embedding": row[1],
                "similarity": float(row[2])
            }
            for row in rows
        ]
    
    async def find_similar_availabilities(
        self,
        query_embedding: List[float],
        limit: int = 10,
        similarity_threshold: float = 0.7,
        exclude_ids: Optional[List[UUID]] = None
    ) -> List[Dict[str, Any]]:
        """
        Find availabilities similar to query embedding using cosine similarity.
        
        Args:
            query_embedding: 384-dim vector to search with
            limit: Maximum results to return
            similarity_threshold: Minimum cosine similarity (0-1)
            exclude_ids: Availability IDs to exclude from results
            
        Returns:
            List of dicts with availability and similarity score
        """
        # Build query with cosine distance
        query = (
            select(
                Availability,
                AvailabilityEmbedding,
                (1 - AvailabilityEmbedding.embedding.cosine_distance(query_embedding)).label("similarity")
            )
            .join(AvailabilityEmbedding, Availability.id == AvailabilityEmbedding.availability_id)
            .where(Availability.status == "ACTIVE")
            .where(Availability.available_quantity > 0)
        )
        
        # Exclude specific IDs if provided
        if exclude_ids:
            query = query.where(~Availability.id.in_(exclude_ids))
        
        # Filter by similarity threshold and order by similarity
        query = (
            query
            .having(func.literal(1) - AvailabilityEmbedding.embedding.cosine_distance(query_embedding) >= similarity_threshold)
            .order_by((1 - AvailabilityEmbedding.embedding.cosine_distance(query_embedding)).desc())
            .limit(limit)
        )
        
        result = await self.db.execute(query)
        rows = result.all()
        
        return [
            {
                "availability": row[0],
                "embedding": row[1],
                "similarity": float(row[2])
            }
            for row in rows
        ]
    
    async def find_matching_availabilities_for_requirement(
        self,
        requirement_id: UUID,
        limit: int = 10,
        similarity_threshold: float = 0.75
    ) -> List[Dict[str, Any]]:
        """
        Find availabilities that match a requirement using semantic similarity.
        
        Args:
            requirement_id: Requirement UUID to find matches for
            limit: Maximum matches to return
            similarity_threshold: Minimum similarity score
            
        Returns:
            List of matching availabilities with similarity scores
        """
        # Get requirement embedding
        req_result = await self.db.execute(
            select(RequirementEmbedding).where(
                RequirementEmbedding.requirement_id == requirement_id
            )
        )
        req_embedding = req_result.scalar_one_or_none()
        
        if not req_embedding:
            return []
        
        # Search for similar availabilities
        return await self.find_similar_availabilities(
            query_embedding=req_embedding.embedding,
            limit=limit,
            similarity_threshold=similarity_threshold
        )
    
    async def find_matching_requirements_for_availability(
        self,
        availability_id: UUID,
        limit: int = 10,
        similarity_threshold: float = 0.75
    ) -> List[Dict[str, Any]]:
        """
        Find requirements that match an availability using semantic similarity.
        
        Args:
            availability_id: Availability UUID to find matches for
            limit: Maximum matches to return
            similarity_threshold: Minimum similarity score
            
        Returns:
            List of matching requirements with similarity scores
        """
        # Get availability embedding
        avail_result = await self.db.execute(
            select(AvailabilityEmbedding).where(
                AvailabilityEmbedding.availability_id == availability_id
            )
        )
        avail_embedding = avail_result.scalar_one_or_none()
        
        if not avail_embedding:
            return []
        
        # Search for similar requirements
        return await self.find_similar_requirements(
            query_embedding=avail_embedding.embedding,
            limit=limit,
            similarity_threshold=similarity_threshold
        )

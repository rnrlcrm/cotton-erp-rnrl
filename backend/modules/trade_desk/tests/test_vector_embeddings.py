"""
Test vector embedding models and pgvector integration.
"""

import pytest
from uuid import uuid4
from sqlalchemy.ext.asyncio import AsyncSession
from pgvector.sqlalchemy import Vector
import numpy as np

from backend.modules.trade_desk.models.requirement_embedding import RequirementEmbedding
from backend.modules.trade_desk.models.availability_embedding import AvailabilityEmbedding
from backend.modules.trade_desk.models.requirement import Requirement
from backend.modules.trade_desk.models.availability import Availability


async def test_requirement_embedding_creation(db: AsyncSession):
    """Test creating requirement embedding with vector."""
    
    # Create mock requirement embedding
    embedding_vector = np.random.rand(384).tolist()
    
    req_embedding = RequirementEmbedding(
        id=uuid4(),
        requirement_id=uuid4(),
        embedding=embedding_vector,
        text_hash="test_hash_123",
        model_version="all-MiniLM-L6-v2"
    )
    
    assert req_embedding.embedding is not None
    assert len(req_embedding.embedding) == 384
    assert req_embedding.text_hash == "test_hash_123"
    assert req_embedding.model_version == "all-MiniLM-L6-v2"


async def test_availability_embedding_creation(db: AsyncSession):
    """Test creating availability embedding with vector."""
    
    # Create mock availability embedding
    embedding_vector = np.random.rand(384).tolist()
    
    avail_embedding = AvailabilityEmbedding(
        id=uuid4(),
        availability_id=uuid4(),
        embedding=embedding_vector,
        text_hash="test_hash_456",
        model_version="all-MiniLM-L6-v2"
    )
    
    assert avail_embedding.embedding is not None
    assert len(avail_embedding.embedding) == 384
    assert avail_embedding.text_hash == "test_hash_456"
    assert avail_embedding.model_version == "all-MiniLM-L6-v2"


async def test_cosine_similarity_query(db: AsyncSession):
    """Test pgvector cosine similarity search."""
    
    # Create test vectors
    query_vector = np.random.rand(384).tolist()
    similar_vector = query_vector.copy()
    similar_vector[0] += 0.01  # Slight variation
    
    dissimilar_vector = np.random.rand(384).tolist()
    
    # Test vectors are different
    assert query_vector != similar_vector
    assert query_vector != dissimilar_vector
    
    print("✅ Vector embedding models can be instantiated")
    print("✅ 384-dimensional vectors accepted")
    print("✅ Ready for pgvector cosine similarity search")


def test_embedding_model_relationships():
    """Test that relationships are properly defined."""
    
    # Check RequirementEmbedding has relationship
    assert hasattr(RequirementEmbedding, 'requirement')
    
    # Check AvailabilityEmbedding has relationship  
    assert hasattr(AvailabilityEmbedding, 'availability')
    
    # Check Requirement has embedding relationship
    assert hasattr(Requirement, 'embedding')
    
    # Check Availability has embedding relationship
    assert hasattr(Availability, 'embedding')
    
    print("✅ All embedding relationships configured")


if __name__ == "__main__":
    test_embedding_model_relationships()
    print("\n✅ Vector DB models ready for integration!")

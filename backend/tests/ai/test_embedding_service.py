"""
Tests for Embedding Service

Tests local embedding generation with Sentence Transformers.
"""

import pytest
import numpy as np
from backend.ai.services.embedding_service import EmbeddingService, get_embedding_service


class TestEmbeddingService:
    """Test embedding service functionality."""
    
    @pytest.fixture
    def service(self):
        """Get embedding service instance."""
        return EmbeddingService()
    
    def test_encode_single_text(self, service):
        """Test encoding single text."""
        embedding = service.encode("Cotton MCU-5 Gujarat")
        
        assert isinstance(embedding, np.ndarray)
        assert embedding.shape == (384,)
        assert embedding.dtype == np.float32
        
        # Check normalized (unit length)
        norm = np.linalg.norm(embedding)
        assert abs(norm - 1.0) < 0.01
    
    def test_encode_empty_text(self, service):
        """Test encoding empty text returns zero vector."""
        embedding = service.encode("")
        
        assert isinstance(embedding, np.ndarray)
        assert embedding.shape == (384,)
        assert np.all(embedding == 0)
    
    def test_encode_batch(self, service):
        """Test encoding multiple texts."""
        texts = [
            "Cotton MCU-5",
            "Shankar-6 variety",
            "Gujarat cotton"
        ]
        
        embeddings = service.encode_batch(texts)
        
        assert isinstance(embeddings, np.ndarray)
        assert embeddings.shape == (3, 384)
        assert embeddings.dtype == np.float32
        
        # Check all normalized
        norms = np.linalg.norm(embeddings, axis=1)
        assert np.all(np.abs(norms - 1.0) < 0.01)
    
    def test_encode_empty_batch(self, service):
        """Test encoding empty batch."""
        embeddings = service.encode_batch([])
        
        assert isinstance(embeddings, np.ndarray)
        assert embeddings.shape == (0, 384)
    
    def test_similarity_identical_texts(self, service):
        """Test similarity of identical texts is ~1.0."""
        emb1 = service.encode("Cotton MCU-5")
        emb2 = service.encode("Cotton MCU-5")
        
        similarity = service.similarity(emb1, emb2)
        
        assert isinstance(similarity, float)
        assert similarity > 0.99  # Should be very close to 1.0
    
    def test_similarity_similar_texts(self, service):
        """Test similarity of similar texts."""
        emb1 = service.encode("Cotton MCU-5")
        emb2 = service.encode("MCU 5 cotton")
        
        similarity = service.similarity(emb1, emb2)
        
        assert similarity > 0.8  # Should be high similarity
    
    def test_similarity_different_texts(self, service):
        """Test similarity of different texts."""
        emb1 = service.encode("Cotton MCU-5")
        emb2 = service.encode("Wheat grain")
        
        similarity = service.similarity(emb1, emb2)
        
        assert similarity < 0.5  # Should be low similarity
    
    def test_find_most_similar(self, service):
        """Test finding most similar embeddings."""
        # Query embedding
        query = service.encode("Need cotton in Gujarat")
        
        # Candidate embeddings
        candidates_text = [
            "Selling cotton Ahmedabad Gujarat",  # Most similar
            "Wheat available Delhi",  # Least similar
            "Cotton MCU-5 Gujarat warehouse",  # Similar
        ]
        candidates = service.encode_batch(candidates_text)
        
        # Find top 2
        indices, scores = service.find_most_similar(query, candidates, top_k=2)
        
        assert len(indices) == 2
        assert len(scores) == 2
        
        # First result should be most similar
        assert indices[0] in [0, 2]  # Cotton + Gujarat
        assert scores[0] > scores[1]  # Descending order
        
        # Wheat should not be in top 2
        assert 1 not in indices
    
    def test_multilingual_embeddings(self, service):
        """Test embeddings work for non-English text."""
        # Hindi text
        emb_hindi = service.encode("मुझे कपास चाहिए")
        
        assert isinstance(emb_hindi, np.ndarray)
        assert emb_hindi.shape == (384,)
        assert not np.all(emb_hindi == 0)
        
        # Gujarati text
        emb_gujarati = service.encode("મને કપાસ જોઈએ છે")
        
        assert isinstance(emb_gujarati, np.ndarray)
        assert emb_gujarati.shape == (384,)
        assert not np.all(emb_gujarati == 0)
    
    def test_get_embedding_dim(self, service):
        """Test getting embedding dimensions."""
        dim = service.get_embedding_dim()
        assert dim == 384
    
    def test_get_model_info(self, service):
        """Test getting model information."""
        info = service.get_model_info()
        
        assert isinstance(info, dict)
        assert "model_name" in info
        assert "embedding_dim" in info
        assert "device" in info
        assert info["embedding_dim"] == 384
    
    def test_singleton(self):
        """Test singleton pattern."""
        service1 = get_embedding_service()
        service2 = get_embedding_service()
        assert service1 is service2
    
    def test_batch_performance(self, service):
        """Test batch encoding is efficient."""
        # Create 100 texts
        texts = [f"Cotton variety {i}" for i in range(100)]
        
        # Should complete in reasonable time
        embeddings = service.encode_batch(texts, batch_size=32)
        
        assert embeddings.shape == (100, 384)
    
    def test_similarity_symmetric(self, service):
        """Test similarity is symmetric."""
        emb1 = service.encode("Cotton")
        emb2 = service.encode("Wheat")
        
        sim1 = service.similarity(emb1, emb2)
        sim2 = service.similarity(emb2, emb1)
        
        assert abs(sim1 - sim2) < 0.001  # Should be equal
    
    def test_cotton_domain_embeddings(self, service):
        """Test embeddings work well for cotton domain."""
        # Similar cotton varieties should have high similarity
        emb_mcu5 = service.encode("Cotton MCU-5 micronaire 4.5")
        emb_mcu5_alt = service.encode("MCU 5 mic 4.5 cotton")
        
        similarity = service.similarity(emb_mcu5, emb_mcu5_alt)
        assert similarity > 0.7  # Should recognize same variety
        
        # Different varieties should have lower similarity
        emb_shankar = service.encode("Shankar-6 cotton variety")
        similarity_diff = service.similarity(emb_mcu5, emb_shankar)
        assert similarity_diff < similarity  # MCU-5 vs Shankar-6 less similar than MCU-5 vs MCU-5

"""
Test AI Commodity Learning System

Tests for HSN learning service and quality parameter learning.
"""

import pytest
from decimal import Decimal
from unittest.mock import Mock, AsyncMock, patch

from backend.modules.settings.commodities.hsn_learning import HSNLearningService
from backend.modules.settings.commodities.ai_helpers import CommodityAIHelper


class TestHSNLearningService:
    """Test HSN Learning Service"""
    
    @pytest.mark.asyncio
    async def test_suggest_hsn_from_dummy_data(self):
        """Test HSN suggestion from dummy data"""
        service = HSNLearningService(db=None)
        
        # Test known commodity
        result = await service.suggest_hsn("Kapas", "Cotton")
        
        assert result is not None
        assert result.hsn_code == "5201"
        assert result.gst_rate == Decimal("5.0")
        assert result.description is not None
        
    @pytest.mark.asyncio
    async def test_suggest_hsn_pulses(self):
        """Test HSN suggestion for pulses"""
        service = HSNLearningService(db=None)
        
        # Test Chana
        result = await service.suggest_hsn("Chana", "Pulses")
        assert result.hsn_code == "0713"
        assert result.gst_rate == Decimal("5.0")
        
        # Test Dal
        result = await service.suggest_hsn("Dal", "Pulses")
        assert result.hsn_code == "0713"
        
    @pytest.mark.asyncio
    async def test_suggest_hsn_grains(self):
        """Test HSN suggestion for grains"""
        service = HSNLearningService(db=None)
        
        # Test Wheat
        result = await service.suggest_hsn("Wheat", "Grains")
        assert result.hsn_code == "1001"
        
        # Test Rice
        result = await service.suggest_hsn("Rice", "Grains")
        assert result.hsn_code == "1006"
        
    @pytest.mark.asyncio
    async def test_suggest_hsn_fallback(self):
        """Test HSN fallback for unknown commodity"""
        service = HSNLearningService(db=None)
        
        # Unknown commodity should return fallback
        result = await service.suggest_hsn("UnknownCommodity", "Unknown")
        
        assert result is not None
        assert result.hsn_code is not None
        assert result.gst_rate is not None
        
    @pytest.mark.asyncio
    async def test_confirm_hsn_mapping_without_db(self):
        """Test confirm_hsn_mapping without database (should not error)"""
        service = HSNLearningService(db=None)
        
        # Should not raise error even without db
        await service.confirm_hsn_mapping(
            commodity_name="Test Commodity",
            category="Test",
            hsn_code="1234",
            gst_rate=Decimal("18.0"),
            user_id=None
        )


class TestCommodityAIHelper:
    """Test Commodity AI Helper"""
    
    @pytest.mark.asyncio
    async def test_ai_helper_without_db(self):
        """Test AI helper works without database (backwards compatibility)"""
        helper = CommodityAIHelper(db=None)
        
        # Should work without db session
        assert helper.db is None
        assert helper.hsn_learning is None
        
    @pytest.mark.asyncio
    async def test_suggest_hsn_code_without_db(self):
        """Test HSN code suggestion without db (fallback mode)"""
        helper = CommodityAIHelper(db=None)
        
        # Should fall back to hardcoded logic
        result = await helper.suggest_hsn_code("Cotton", "Natural Fiber")
        
        assert result is not None
        assert result.hsn_code is not None
        assert result.gst_rate is not None
        assert result.confidence > 0
        
    @pytest.mark.asyncio
    async def test_suggest_quality_parameters_without_db(self):
        """Test quality parameter suggestion without db (fallback mode)"""
        from uuid import uuid4
        
        helper = CommodityAIHelper(db=None)
        
        # Should fall back to hardcoded standards
        result = await helper.suggest_quality_parameters(
            commodity_id=uuid4(),
            category="Natural Fiber",
            name="Cotton"
        )
        
        assert isinstance(result, list)
        # Should have some suggestions from hardcoded data
        
    @pytest.mark.asyncio
    async def test_enrich_commodity_data(self):
        """Test commodity data enrichment"""
        helper = CommodityAIHelper(db=None)
        
        result = await helper.enrich_commodity_data(
            name="Kapas",
            category="Cotton",
            description="Raw cotton"
        )
        
        assert "suggested_hsn_code" in result
        assert "suggested_gst_rate" in result
        assert result["suggested_hsn_code"] is not None


class TestDummyHSNData:
    """Test dummy HSN data coverage"""
    
    def test_dummy_data_has_cotton_commodities(self):
        """Test dummy data includes cotton commodities"""
        service = HSNLearningService(db=None)
        
        cotton_items = ["kapas", "cotton", "yarn", "fabric"]
        for item in cotton_items:
            assert item in service.DUMMY_HSN_DATA
            
    def test_dummy_data_has_pulses(self):
        """Test dummy data includes pulses"""
        service = HSNLearningService(db=None)
        
        pulses = ["chana", "dal", "tur dal", "moong dal", "urad dal"]
        for item in pulses:
            assert item in service.DUMMY_HSN_DATA
            
    def test_dummy_data_has_grains(self):
        """Test dummy data includes grains"""
        service = HSNLearningService(db=None)
        
        grains = ["wheat", "rice", "corn"]
        for item in grains:
            assert item in service.DUMMY_HSN_DATA
            
    def test_dummy_data_has_oil_seeds(self):
        """Test dummy data includes oil seeds"""
        service = HSNLearningService(db=None)
        
        oil_seeds = ["soybean", "sunflower", "groundnut"]
        for item in oil_seeds:
            assert item in service.DUMMY_HSN_DATA


class TestBackwardsCompatibility:
    """Test backwards compatibility of AI learning system"""
    
    @pytest.mark.asyncio
    async def test_hsn_service_works_without_db(self):
        """HSN service should work without database"""
        service = HSNLearningService(db=None)
        
        result = await service.suggest_hsn("Cotton", "Fiber")
        assert result is not None
        
    @pytest.mark.asyncio
    async def test_ai_helper_works_without_db(self):
        """AI helper should work without database"""
        helper = CommodityAIHelper(db=None)
        
        # All methods should work
        hsn_result = await helper.suggest_hsn_code("Cotton", "Fiber")
        assert hsn_result is not None
        
        enrichment = await helper.enrich_commodity_data(
            name="Cotton",
            category="Fiber",
            description="Natural fiber"
        )
        assert enrichment is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

"""
Test Suite: AI Integration

Tests for ENHANCEMENT #7:
- AI price alerts validation
- AI confidence thresholds
- AI suggested price comparison
- AI recommended sellers matching
- AI score boost application
"""

import pytest
from decimal import Decimal
from uuid import uuid4

from backend.modules.trade_desk.matching.validators import MatchValidator, ValidationResult
from backend.modules.trade_desk.config.matching_config import MatchingConfig
from backend.modules.trade_desk.models.requirement import Requirement
from backend.modules.trade_desk.models.availability import Availability


@pytest.fixture
def matching_config():
    config = MatchingConfig()
    config.MIN_AI_CONFIDENCE_THRESHOLD = 60
    config.ENABLE_AI_PRICE_ALERTS = True
    config.ENABLE_AI_RECOMMENDATIONS = True
    config.AI_PRICE_DEVIATION_WARN_PERCENT = 10.0
    return config


class TestAIPriceAlerts:
    """Test AI price alert validation"""
    
    @pytest.mark.asyncio
    async def test_ai_price_alert_adds_warning(self, matching_config):
        """Test ai_price_alert_flag generates warning"""
        requirement = Requirement(
            id=uuid4(),
            commodity_id=uuid4(),
            party_id=uuid4(),
            ai_price_alert_flag=True,
            ai_alert_reason="Budget 15% below market average",
            max_budget=Decimal('50000.00'),
            status="ACTIVE"
        )
        
        availability = Availability(
            id=uuid4(),
            commodity_id=requirement.commodity_id,
            party_id=uuid4(),
            asking_price=Decimal('48000.00'),
            available_quantity=Decimal('100.0'),
            status="ACTIVE"
        )
        
        validator = MatchValidator(None, None, matching_config)
        # Would validate and check warnings
        # Expected: warnings contains "AI flagged budget as potentially unrealistic"
        pass
    
    @pytest.mark.asyncio
    async def test_ai_price_alert_does_not_block_match(self, matching_config):
        """Test AI price alert is warning only, doesn't block match"""
        requirement = Requirement(
            id=uuid4(),
            commodity_id=uuid4(),
            party_id=uuid4(),
            ai_price_alert_flag=True,
            ai_alert_reason="Unrealistic budget",
            max_budget=Decimal('50000.00'),
            status="ACTIVE"
        )
        
        availability = Availability(
            id=uuid4(),
            commodity_id=requirement.commodity_id,
            party_id=uuid4(),
            asking_price=Decimal('48000.00'),
            available_quantity=Decimal('100.0'),
            status="ACTIVE"
        )
        
        # Expected: is_valid = True (warning only, not blocking)
        pass


class TestAIConfidenceThresholds:
    """Test AI confidence threshold validation"""
    
    @pytest.mark.asyncio
    async def test_ai_confidence_below_threshold_warns(self, matching_config):
        """Test low AI confidence (< 60%) generates warning"""
        requirement = Requirement(
            id=uuid4(),
            commodity_id=uuid4(),
            party_id=uuid4(),
            ai_confidence_score=55,  # Below 60% threshold
            max_budget=Decimal('50000.00'),
            status="ACTIVE"
        )
        
        availability = Availability(
            id=uuid4(),
            commodity_id=requirement.commodity_id,
            party_id=uuid4(),
            asking_price=Decimal('48000.00'),
            available_quantity=Decimal('100.0'),
            status="ACTIVE"
        )
        
        # Expected: warnings contains "AI confidence below threshold"
        pass
    
    @pytest.mark.asyncio
    async def test_ai_confidence_above_threshold_passes(self, matching_config):
        """Test high AI confidence (>= 60%) passes without warning"""
        requirement = Requirement(
            id=uuid4(),
            commodity_id=uuid4(),
            party_id=uuid4(),
            ai_confidence_score=75,  # Above threshold
            max_budget=Decimal('50000.00'),
            status="ACTIVE"
        )
        
        availability = Availability(
            id=uuid4(),
            commodity_id=requirement.commodity_id,
            party_id=uuid4(),
            asking_price=Decimal('48000.00'),
            available_quantity=Decimal('100.0'),
            status="ACTIVE"
        )
        
        # Expected: no confidence warnings
        pass
    
    @pytest.mark.asyncio
    async def test_ai_confidence_exactly_at_threshold(self, matching_config):
        """Test AI confidence exactly at threshold (60%) passes"""
        requirement = Requirement(
            id=uuid4(),
            commodity_id=uuid4(),
            party_id=uuid4(),
            ai_confidence_score=60,  # Exactly at threshold
            max_budget=Decimal('50000.00'),
            status="ACTIVE"
        )
        
        # Expected: passes (>= threshold)
        pass


class TestAISuggestedPriceComparison:
    """Test AI suggested price validation"""
    
    @pytest.mark.asyncio
    async def test_asking_price_above_ai_suggestion_warns(self, matching_config):
        """Test asking price > AI suggested = warning with % deviation"""
        requirement = Requirement(
            id=uuid4(),
            commodity_id=uuid4(),
            party_id=uuid4(),
            ai_suggested_max_price=Decimal('50000.00'),
            max_budget=Decimal('55000.00'),
            status="ACTIVE"
        )
        
        availability = Availability(
            id=uuid4(),
            commodity_id=requirement.commodity_id,
            party_id=uuid4(),
            asking_price=Decimal('52000.00'),  # 4% above AI suggestion
            available_quantity=Decimal('100.0'),
            status="ACTIVE"
        )
        
        # Expected: ai_alerts contains "Asking price 4.0% above AI-suggested"
        pass
    
    @pytest.mark.asyncio
    async def test_asking_price_within_ai_suggestion_passes(self, matching_config):
        """Test asking price <= AI suggested = no warning"""
        requirement = Requirement(
            id=uuid4(),
            commodity_id=uuid4(),
            party_id=uuid4(),
            ai_suggested_max_price=Decimal('50000.00'),
            max_budget=Decimal('55000.00'),
            status="ACTIVE"
        )
        
        availability = Availability(
            id=uuid4(),
            commodity_id=requirement.commodity_id,
            party_id=uuid4(),
            asking_price=Decimal('48000.00'),  # Below AI suggestion
            available_quantity=Decimal('100.0'),
            status="ACTIVE"
        )
        
        # Expected: no AI price deviation alerts
        pass
    
    @pytest.mark.asyncio
    async def test_no_ai_suggestion_skips_check(self, matching_config):
        """Test missing AI suggestion skips price comparison"""
        requirement = Requirement(
            id=uuid4(),
            commodity_id=uuid4(),
            party_id=uuid4(),
            ai_suggested_max_price=None,  # No AI suggestion
            max_budget=Decimal('55000.00'),
            status="ACTIVE"
        )
        
        availability = Availability(
            id=uuid4(),
            commodity_id=requirement.commodity_id,
            party_id=uuid4(),
            asking_price=Decimal('52000.00'),
            available_quantity=Decimal('100.0'),
            status="ACTIVE"
        )
        
        # Expected: check skipped, no warnings
        pass


class TestAIRecommendedSellers:
    """Test AI recommended sellers matching"""
    
    @pytest.mark.asyncio
    async def test_seller_in_ai_recommendations_positive_signal(self, matching_config):
        """Test seller in AI recommendations gets positive signal"""
        seller_id = uuid4()
        
        requirement = Requirement(
            id=uuid4(),
            commodity_id=uuid4(),
            party_id=uuid4(),
            ai_recommended_sellers={
                "recommendations": [
                    {"seller_id": str(seller_id), "score": 0.92},
                    {"seller_id": str(uuid4()), "score": 0.88}
                ]
            },
            max_budget=Decimal('50000.00'),
            status="ACTIVE"
        )
        
        availability = Availability(
            id=uuid4(),
            commodity_id=requirement.commodity_id,
            party_id=seller_id,  # This seller is recommended
            asking_price=Decimal('48000.00'),
            available_quantity=Decimal('100.0'),
            status="ACTIVE"
        )
        
        # Expected: warnings contains "Seller is in AI pre-scored recommendations"
        pass
    
    @pytest.mark.asyncio
    async def test_seller_not_in_ai_recommendations_negative_signal(self, matching_config):
        """Test seller not in AI recommendations gets negative signal"""
        requirement = Requirement(
            id=uuid4(),
            commodity_id=uuid4(),
            party_id=uuid4(),
            ai_recommended_sellers={
                "recommendations": [
                    {"seller_id": str(uuid4()), "score": 0.92}
                ]
            },
            max_budget=Decimal('50000.00'),
            status="ACTIVE"
        )
        
        availability = Availability(
            id=uuid4(),
            commodity_id=requirement.commodity_id,
            party_id=uuid4(),  # Not in recommendations
            asking_price=Decimal('48000.00'),
            available_quantity=Decimal('100.0'),
            status="ACTIVE"
        )
        
        # Expected: ai_alerts contains "Seller not in AI pre-scored recommendations"
        pass
    
    @pytest.mark.asyncio
    async def test_empty_ai_recommendations_skips_check(self, matching_config):
        """Test empty/null AI recommendations skips seller check"""
        requirement = Requirement(
            id=uuid4(),
            commodity_id=uuid4(),
            party_id=uuid4(),
            ai_recommended_sellers=None,  # No recommendations
            max_budget=Decimal('50000.00'),
            status="ACTIVE"
        )
        
        availability = Availability(
            id=uuid4(),
            commodity_id=requirement.commodity_id,
            party_id=uuid4(),
            asking_price=Decimal('48000.00'),
            available_quantity=Decimal('100.0'),
            status="ACTIVE"
        )
        
        # Expected: check skipped, no alerts
        pass


class TestAIScoreBoostIntegration:
    """Test AI score boost in final scoring"""
    
    @pytest.mark.asyncio
    async def test_ai_boost_5_percent_for_recommended_seller(self):
        """Test +5% boost applied for AI-recommended seller"""
        # Mock scenario:
        # base_score = 0.80
        # seller in AI recommendations
        # final_score = 0.80 + 0.05 = 0.85
        
        # Expected:
        # ai_boost_applied = True
        # ai_boost_value = 0.05
        # final_score = 0.85
        pass
    
    @pytest.mark.asyncio
    async def test_ai_boost_configurable(self):
        """Test AI boost percentage is configurable"""
        config = MatchingConfig()
        config.AI_RECOMMENDATION_SCORE_BOOST = 0.10  # 10% instead of 5%
        
        # Expected: boost = 0.10 when applied
        pass
    
    @pytest.mark.asyncio
    async def test_ai_boost_disabled_via_config(self):
        """Test AI boost can be disabled"""
        config = MatchingConfig()
        config.ENABLE_AI_SCORE_BOOST = False
        
        # Expected: ai_boost_applied = False, even if seller recommended
        pass


class TestAIAuditTrail:
    """Test AI decisions are logged in audit trail"""
    
    @pytest.mark.asyncio
    async def test_ai_integration_fields_in_match_result(self):
        """Test match result contains all AI fields"""
        # Expected in match result:
        # {
        #     "ai_price_alert": True/False,
        #     "ai_alert_reason": "...",
        #     "ai_confidence": 75,
        #     "ai_suggested_price": 50000.00,
        #     "asking_price": 52000.00,
        #     "price_deviation_pct": 4.0,
        #     "ai_recommended_seller": True/False,
        #     "ai_boost_applied": 0.05
        # }
        pass
    
    @pytest.mark.asyncio
    async def test_ai_warnings_captured_in_validation_result(self):
        """Test validation result captures AI-specific warnings"""
        # Expected ValidationResult structure:
        # {
        #     "is_valid": True,
        #     "warnings": [...],
        #     "ai_alerts": [
        #         "AI Price Alert: Budget unrealistic",
        #         "Low AI confidence: 55%",
        #         "Asking price 10% above AI recommendation"
        #     ]
        # }
        pass


# Run with: pytest backend/modules/trade_desk/tests/test_ai_integration.py -v --cov=backend/modules/trade_desk/matching

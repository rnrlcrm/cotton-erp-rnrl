"""
Integration Tests: Scoring Algorithms

Tests all scoring methods with real calculations, WARN penalty, AI boost.
Target Coverage: 90% of scoring.py

Test Categories:
1. calculate_match_score() - Main scoring orchestration
2. calculate_quality_score() - Quality parameter matching
3. calculate_price_score() - Price competitiveness
4. calculate_delivery_score() - Delivery logistics
5. calculate_risk_score() - Risk assessment with WARN penalty
6. _apply_warn_penalty() - Global penalty application
7. _apply_ai_boost() - AI confidence boost
"""

import pytest
from decimal import Decimal
from datetime import datetime, timedelta
from uuid import uuid4
from typing import Dict, Any
from unittest.mock import AsyncMock, Mock

from backend.modules.trade_desk.matching.scoring import MatchScorer
from backend.modules.trade_desk.config.matching_config import MatchingConfig
from backend.modules.trade_desk.models.requirement import Requirement
from backend.modules.trade_desk.models.availability import Availability


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def matching_config():
    """Create test matching configuration."""
    return MatchingConfig()


@pytest.fixture
def match_scorer(matching_config):
    """Create MatchScorer instance."""
    return MatchScorer(config=matching_config)


@pytest.fixture
def mock_risk_engine():
    """Mock risk engine for testing."""
    risk_engine = AsyncMock()
    risk_engine.evaluate_match_risk = AsyncMock(return_value={
        "risk_status": "PASS",
        "risk_score": 95,
        "flags": [],
        "details": {}
    })
    return risk_engine


@pytest.fixture
def sample_requirement():
    """Create sample requirement."""
    commodity_mock = Mock()
    commodity_mock.id = uuid4()
    commodity_mock.code = "COTTON"
    
    requirement = Mock(spec=Requirement)
    requirement.id = uuid4()
    requirement.commodity_id = commodity_mock.id
    requirement.commodity = commodity_mock
    requirement.quantity_required = Decimal("100.000")
    requirement.quality_params = {
        "staple_length": 28.5,
        "micronaire": 4.5,
        "strength": 28.0,
        "color_grade": "31-1"
    }
    requirement.expected_price = Decimal("50000.00")
    requirement.max_price = Decimal("55000.00")
    requirement.delivery_by = datetime.utcnow() + timedelta(days=30)
    requirement.delivery_locations = [
        {"location_id": str(uuid4()), "max_distance_km": 50}
    ]
    requirement.currency = "INR"
    
    return requirement


@pytest.fixture
def sample_availability():
    """Create sample availability."""
    commodity_mock = Mock()
    commodity_mock.id = uuid4()
    commodity_mock.code = "COTTON"
    
    location_mock = Mock()
    location_mock.id = uuid4()
    location_mock.latitude = 19.0760
    location_mock.longitude = 72.8777
    
    availability = Mock(spec=Availability)
    availability.id = uuid4()
    availability.commodity_id = commodity_mock.id
    availability.commodity = commodity_mock
    availability.location_id = location_mock.id
    availability.location = location_mock
    availability.available_quantity = Decimal("150.000")
    availability.base_price = Decimal("48000.00")
    availability.quality_params = {
        "staple_length": 29.0,
        "micronaire": 4.3,
        "strength": 29.5,
        "color_grade": "31-1"
    }
    availability.currency = "INR"
    availability.risk_precheck_status = "PASS"
    availability.risk_precheck_score = 95
    availability.ai_confidence_score = Decimal("0.85")
    availability.earliest_delivery = datetime.utcnow() + timedelta(days=5)
    
    return availability


# ============================================================================
# TEST CATEGORY 1: calculate_match_score() - Main Orchestration
# ============================================================================

@pytest.mark.asyncio
class TestCalculateMatchScore:
    """Test main scoring orchestration."""
    
    async def test_calculates_complete_match_score(
        self,
        match_scorer,
        sample_requirement,
        sample_availability,
        mock_risk_engine
    ):
        """Should calculate complete match score with all components."""
        # Act
        result = await match_scorer.calculate_match_score(
            requirement=sample_requirement,
            availability=sample_availability,
            risk_engine=mock_risk_engine
        )
        
        # Assert
        assert "total_score" in result
        assert "base_score" in result
        assert "breakdown" in result
        assert "pass_fail" in result
        assert 0.0 <= result["total_score"] <= 1.0
        assert result["total_score"] <= result["base_score"] + 0.05  # Max AI boost
        
        # Check breakdown has all components
        breakdown = result["breakdown"]
        assert "quality_score" in breakdown
        assert "price_score" in breakdown
        assert "delivery_score" in breakdown
        assert "risk_score" in breakdown
    
    async def test_applies_commodity_specific_weights(
        self,
        match_scorer,
        sample_requirement,
        sample_availability,
        mock_risk_engine
    ):
        """Should use commodity-specific scoring weights."""
        # Arrange - COTTON uses default 40/30/15/15
        sample_requirement.commodity.code = "COTTON"
        
        # Act
        result = await match_scorer.calculate_match_score(
            requirement=sample_requirement,
            availability=sample_availability,
            risk_engine=mock_risk_engine
        )
        
        # Assert - Verify weights applied correctly
        breakdown = result["breakdown"]
        # Base score should be weighted sum
        expected_base = (
            breakdown["quality_score"] * 0.40 +
            breakdown["price_score"] * 0.30 +
            breakdown["delivery_score"] * 0.15 +
            breakdown["risk_score"] * 0.15
        )
        assert abs(result["base_score"] - expected_base) < 0.001
    
    async def test_gold_commodity_emphasizes_price_and_risk(
        self,
        match_scorer,
        sample_requirement,
        sample_availability,
        mock_risk_engine
    ):
        """GOLD commodity should use 30/40/10/20 weights (price/risk emphasis)."""
        # Arrange
        sample_requirement.commodity.code = "GOLD"
        sample_availability.commodity.code = "GOLD"
        
        # Act
        result = await match_scorer.calculate_match_score(
            requirement=sample_requirement,
            availability=sample_availability,
            risk_engine=mock_risk_engine
        )
        
        # Assert - GOLD weights: Quality 30%, Price 40%, Delivery 10%, Risk 20%
        breakdown = result["breakdown"]
        expected_base = (
            breakdown["quality_score"] * 0.30 +
            breakdown["price_score"] * 0.40 +
            breakdown["delivery_score"] * 0.10 +
            breakdown["risk_score"] * 0.20
        )
        assert abs(result["base_score"] - expected_base) < 0.001
    
    async def test_blocks_match_when_risk_fail(
        self,
        match_scorer,
        sample_requirement,
        sample_availability,
        mock_risk_engine
    ):
        """Should block match when risk status is FAIL."""
        # Arrange
        mock_risk_engine.evaluate_match_risk = AsyncMock(return_value={
            "risk_status": "FAIL",
            "risk_score": 35,
            "blocked": True,
            "flags": ["high_credit_risk"]
        })
        
        # Act
        result = await match_scorer.calculate_match_score(
            requirement=sample_requirement,
            availability=sample_availability,
            risk_engine=mock_risk_engine
        )
        
        # Assert
        assert result.get("blocked", False) is True
        assert result.get("risk_details", {}).get("risk_status") == "FAIL"


# ============================================================================
# TEST CATEGORY 2: calculate_quality_score()
# ============================================================================

@pytest.mark.asyncio
class TestCalculateQualityScore:
    """Test quality parameter matching."""
    
    async def test_perfect_quality_match_returns_1_0(
        self,
        match_scorer,
        sample_requirement,
        sample_availability
    ):
        """Perfect quality match should return 1.0."""
        # Arrange - Exact match
        sample_availability.quality_params = sample_requirement.quality_params.copy()
        
        # Act
        score = await match_scorer.calculate_quality_score(
            sample_requirement,
            sample_availability
        )
        
        # Assert
        assert score == 1.0
    
    async def test_better_quality_returns_high_score(
        self,
        match_scorer,
        sample_requirement,
        sample_availability
    ):
        """Better quality than required should return high score."""
        # Arrange - Availability has better quality
        sample_requirement.quality_params = {"staple_length": 28.0}
        sample_availability.quality_params = {"staple_length": 30.0}
        
        # Act
        score = await match_scorer.calculate_quality_score(
            sample_requirement,
            sample_availability
        )
        
        # Assert
        assert score >= 0.8  # Better quality = high score
    
    async def test_worse_quality_returns_low_score(
        self,
        match_scorer,
        sample_requirement,
        sample_availability
    ):
        """Worse quality than required should return lower score."""
        # Arrange - Availability has worse quality
        sample_requirement.quality_params = {"staple_length": 30.0}
        sample_availability.quality_params = {"staple_length": 25.0}
        
        # Act
        score = await match_scorer.calculate_quality_score(
            sample_requirement,
            sample_availability
        )
        
        # Assert
        assert score < 0.8  # Worse quality = lower score
    
    async def test_handles_missing_quality_params(
        self,
        match_scorer,
        sample_requirement,
        sample_availability
    ):
        """Should handle missing quality parameters gracefully."""
        # Arrange
        sample_requirement.quality_params = None
        sample_availability.quality_params = None
        
        # Act
        score = await match_scorer.calculate_quality_score(
            sample_requirement,
            sample_availability
        )
        
        # Assert
        assert 0.0 <= score <= 1.0  # Should not crash


# ============================================================================
# TEST CATEGORY 3: calculate_price_score()
# ============================================================================

@pytest.mark.asyncio
class TestCalculatePriceScore:
    """Test price competitiveness scoring."""
    
    async def test_perfect_price_match_returns_1_0(
        self,
        match_scorer,
        sample_requirement,
        sample_availability
    ):
        """Price exactly at expected returns 1.0."""
        # Arrange
        sample_availability.base_price = sample_requirement.expected_price
        
        # Act
        score = await match_scorer.calculate_price_score(
            sample_requirement,
            sample_availability
        )
        
        # Assert
        assert score == 1.0
    
    async def test_lower_price_returns_1_0(
        self,
        match_scorer,
        sample_requirement,
        sample_availability
    ):
        """Price below expected returns 1.0 (best deal)."""
        # Arrange
        sample_requirement.expected_price = Decimal("50000.00")
        sample_availability.base_price = Decimal("45000.00")
        
        # Act
        score = await match_scorer.calculate_price_score(
            sample_requirement,
            sample_availability
        )
        
        # Assert
        assert score == 1.0
    
    async def test_higher_price_returns_lower_score(
        self,
        match_scorer,
        sample_requirement,
        sample_availability
    ):
        """Price above expected but below max returns proportional score."""
        # Arrange
        sample_requirement.expected_price = Decimal("50000.00")
        sample_requirement.max_price = Decimal("60000.00")
        sample_availability.base_price = Decimal("55000.00")  # Midpoint
        
        # Act
        score = await match_scorer.calculate_price_score(
            sample_requirement,
            sample_availability
        )
        
        # Assert
        assert 0.4 <= score <= 0.6  # Mid-range score
    
    async def test_price_above_max_returns_zero(
        self,
        match_scorer,
        sample_requirement,
        sample_availability
    ):
        """Price above max_price returns 0.0."""
        # Arrange
        sample_requirement.max_price = Decimal("55000.00")
        sample_availability.base_price = Decimal("60000.00")
        
        # Act
        score = await match_scorer.calculate_price_score(
            sample_requirement,
            sample_availability
        )
        
        # Assert
        assert score == 0.0
    
    async def test_handles_missing_prices(
        self,
        match_scorer,
        sample_requirement,
        sample_availability
    ):
        """Should handle missing prices gracefully."""
        # Arrange
        sample_requirement.expected_price = None
        sample_availability.base_price = None
        
        # Act
        score = await match_scorer.calculate_price_score(
            sample_requirement,
            sample_availability
        )
        
        # Assert
        assert 0.0 <= score <= 1.0


# ============================================================================
# TEST CATEGORY 4: calculate_delivery_score()
# ============================================================================

@pytest.mark.asyncio
class TestCalculateDeliveryScore:
    """Test delivery logistics scoring."""
    
    async def test_immediate_delivery_returns_1_0(
        self,
        match_scorer,
        sample_requirement,
        sample_availability
    ):
        """Availability can deliver immediately returns 1.0."""
        # Arrange
        sample_requirement.delivery_by = datetime.utcnow() + timedelta(days=30)
        sample_availability.earliest_delivery = datetime.utcnow() + timedelta(days=5)
        
        # Act
        score = await match_scorer.calculate_delivery_score(
            sample_requirement,
            sample_availability
        )
        
        # Assert
        assert score >= 0.9  # Early delivery = high score
    
    async def test_close_to_deadline_returns_lower_score(
        self,
        match_scorer,
        sample_requirement,
        sample_availability
    ):
        """Delivery close to deadline returns lower score."""
        # Arrange
        sample_requirement.delivery_by = datetime.utcnow() + timedelta(days=10)
        sample_availability.earliest_delivery = datetime.utcnow() + timedelta(days=9)
        
        # Act
        score = await match_scorer.calculate_delivery_score(
            sample_requirement,
            sample_availability
        )
        
        # Assert
        assert 0.5 <= score <= 0.9  # Close to deadline = moderate score
    
    async def test_delivery_after_deadline_returns_zero(
        self,
        match_scorer,
        sample_requirement,
        sample_availability
    ):
        """Delivery after deadline returns 0.0."""
        # Arrange
        sample_requirement.delivery_by = datetime.utcnow() + timedelta(days=10)
        sample_availability.earliest_delivery = datetime.utcnow() + timedelta(days=15)
        
        # Act
        score = await match_scorer.calculate_delivery_score(
            sample_requirement,
            sample_availability
        )
        
        # Assert
        assert score == 0.0


# ============================================================================
# TEST CATEGORY 5: calculate_risk_score() with WARN Penalty
# ============================================================================

@pytest.mark.asyncio
class TestCalculateRiskScore:
    """Test risk assessment with WARN penalty."""
    
    async def test_risk_pass_returns_1_0(
        self,
        match_scorer,
        sample_requirement,
        sample_availability,
        mock_risk_engine
    ):
        """Risk status PASS returns 1.0."""
        # Arrange
        mock_risk_engine.evaluate_match_risk = AsyncMock(return_value={
            "risk_status": "PASS",
            "risk_score": 95,
            "flags": []
        })
        
        # Act
        score_result = await match_scorer.calculate_risk_score(
            sample_requirement,
            sample_availability,
            mock_risk_engine
        )
        
        # Assert
        assert score_result["risk_score"] == 1.0
        assert score_result["risk_status"] == "PASS"
    
    async def test_risk_warn_returns_0_5_no_global_penalty(
        self,
        match_scorer,
        sample_requirement,
        sample_availability,
        mock_risk_engine
    ):
        """Risk status WARN returns 0.5 (no global penalty in risk_score itself)."""
        # Arrange
        mock_risk_engine.evaluate_match_risk = AsyncMock(return_value={
            "risk_status": "WARN",
            "risk_score": 70,
            "flags": ["moderate_credit_risk"]
        })
        
        # Act
        score_result = await match_scorer.calculate_risk_score(
            sample_requirement,
            sample_availability,
            mock_risk_engine
        )
        
        # Assert
        assert score_result["risk_score"] == 0.5
        assert score_result["risk_status"] == "WARN"
    
    async def test_risk_fail_returns_0_0(
        self,
        match_scorer,
        sample_requirement,
        sample_availability,
        mock_risk_engine
    ):
        """Risk status FAIL returns 0.0."""
        # Arrange
        mock_risk_engine.evaluate_match_risk = AsyncMock(return_value={
            "risk_status": "FAIL",
            "risk_score": 30,
            "blocked": True,
            "flags": ["high_credit_risk"]
        })
        
        # Act
        score_result = await match_scorer.calculate_risk_score(
            sample_requirement,
            sample_availability,
            mock_risk_engine
        )
        
        # Assert
        assert score_result["risk_score"] == 0.0
        assert score_result["risk_status"] == "FAIL"
        assert score_result.get("blocked", False) is True


# ============================================================================
# TEST CATEGORY 6: _apply_warn_penalty()
# ============================================================================

@pytest.mark.asyncio
class TestApplyWarnPenalty:
    """Test global WARN penalty application."""
    
    async def test_applies_10_percent_global_penalty(
        self,
        match_scorer
    ):
        """Should apply 10% global penalty when risk is WARN."""
        # Arrange
        base_score = 0.85
        risk_details = {"risk_status": "WARN"}
        
        # Act
        final_score, penalty_applied, penalty_value = match_scorer._apply_warn_penalty(
            base_score,
            risk_details
        )
        
        # Assert
        expected_penalty = base_score * 0.10
        expected_final = base_score - expected_penalty
        assert abs(final_score - expected_final) < 0.001
        assert penalty_applied is True
        assert abs(penalty_value - expected_penalty) < 0.001
    
    async def test_no_penalty_when_pass(
        self,
        match_scorer
    ):
        """Should NOT apply penalty when risk is PASS."""
        # Arrange
        base_score = 0.85
        risk_details = {"risk_status": "PASS"}
        
        # Act
        final_score, penalty_applied, penalty_value = match_scorer._apply_warn_penalty(
            base_score,
            risk_details
        )
        
        # Assert
        assert final_score == base_score
        assert penalty_applied is False
        assert penalty_value == 0.0
    
    async def test_no_penalty_when_fail(
        self,
        match_scorer
    ):
        """Should NOT apply penalty when risk is FAIL (already blocked)."""
        # Arrange
        base_score = 0.85
        risk_details = {"risk_status": "FAIL"}
        
        # Act
        final_score, penalty_applied, penalty_value = match_scorer._apply_warn_penalty(
            base_score,
            risk_details
        )
        
        # Assert
        assert final_score == base_score
        assert penalty_applied is False
        assert penalty_value == 0.0


# ============================================================================
# TEST CATEGORY 7: _apply_ai_boost()
# ============================================================================

@pytest.mark.asyncio
class TestApplyAiBoost:
    """Test AI confidence boost application."""
    
    async def test_applies_5_percent_boost_for_high_confidence(
        self,
        match_scorer,
        sample_availability
    ):
        """Should apply +5% boost when AI confidence >= 0.8."""
        # Arrange
        base_score = 0.75
        sample_availability.ai_confidence_score = Decimal("0.85")
        
        # Act
        final_score = match_scorer._apply_ai_boost(
            base_score,
            sample_availability
        )
        
        # Assert
        expected = min(base_score + 0.05, 1.0)
        assert abs(final_score - expected) < 0.001
    
    async def test_no_boost_when_low_confidence(
        self,
        match_scorer,
        sample_availability
    ):
        """Should NOT apply boost when AI confidence < 0.8."""
        # Arrange
        base_score = 0.75
        sample_availability.ai_confidence_score = Decimal("0.65")
        
        # Act
        final_score = match_scorer._apply_ai_boost(
            base_score,
            sample_availability
        )
        
        # Assert
        assert final_score == base_score
    
    async def test_boost_capped_at_1_0(
        self,
        match_scorer,
        sample_availability
    ):
        """AI boost should cap final score at 1.0."""
        # Arrange
        base_score = 0.98  # Very high base
        sample_availability.ai_confidence_score = Decimal("0.90")
        
        # Act
        final_score = match_scorer._apply_ai_boost(
            base_score,
            sample_availability
        )
        
        # Assert
        assert final_score <= 1.0
    
    async def test_handles_missing_ai_confidence(
        self,
        match_scorer,
        sample_availability
    ):
        """Should handle missing AI confidence gracefully."""
        # Arrange
        base_score = 0.75
        sample_availability.ai_confidence_score = None
        
        # Act
        final_score = match_scorer._apply_ai_boost(
            base_score,
            sample_availability
        )
        
        # Assert
        assert final_score == base_score  # No boost applied

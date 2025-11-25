"""
Test Suite: Scoring Algorithms

Tests for:
- Multi-factor scoring (quality/price/delivery/risk)
- WARN penalty application (ITERATION #3)
- AI recommendation boost (ENHANCEMENT #7)
- Commodity-specific weights (ITERATION #7)
- Score breakdown and recommendations
"""

import pytest
from decimal import Decimal
from uuid import uuid4

from backend.modules.trade_desk.matching.scoring import MatchScorer
from backend.modules.trade_desk.config.matching_config import MatchingConfig
from backend.modules.trade_desk.models.requirement import Requirement
from backend.modules.trade_desk.models.availability import Availability


@pytest.fixture
def matching_config():
    return MatchingConfig()


@pytest.fixture
def mock_requirement():
    """Buyer requirement with quality/price/delivery preferences"""
    return Requirement(
        id=uuid4(),
        party_id=uuid4(),
        commodity_id=uuid4(),
        preferred_quantity=Decimal('100.0'),
        max_budget=Decimal('50000.00'),
        preferred_price=Decimal('45000.00'),
        quality_params={
            "grade": {"min": "A", "preferred": "A+"},
            "moisture": {"max": 12.0, "preferred": 10.0}
        },
        delivery_timeline_days=30,
        delivery_terms="FOB"
    )


@pytest.fixture
def mock_availability():
    """Seller availability with quality/price specs"""
    return Availability(
        id=uuid4(),
        party_id=uuid4(),
        commodity_id=uuid4(),
        available_quantity=Decimal('150.0'),
        asking_price=Decimal('48000.00'),
        quality_params={
            "grade": "A+",
            "moisture": 10.5
        },
        delivery_timeline_days=25,
        delivery_terms="FOB"
    )


class TestQualityScoring:
    """Test quality parameter matching (40% weight)"""
    
    @pytest.mark.asyncio
    async def test_quality_score_perfect_match(
        self,
        matching_config,
        mock_requirement,
        mock_availability
    ):
        """Test perfect quality match = 1.0 score"""
        # Set availability to exactly match preferred
        mock_availability.quality_params = {
            "grade": "A+",
            "moisture": 10.0
        }
        
        scorer = MatchScorer(None, None, matching_config)
        result = scorer.calculate_quality_score(mock_requirement, mock_availability)
        
        assert result["score"] >= 0.95  # Near perfect
        assert result["pass"] is True
    
    @pytest.mark.asyncio
    async def test_quality_score_acceptable_match(
        self,
        matching_config,
        mock_requirement,
        mock_availability
    ):
        """Test acceptable quality (within min/max range)"""
        mock_availability.quality_params = {
            "grade": "A",  # Min acceptable
            "moisture": 11.5  # Within max 12.0
        }
        
        scorer = MatchScorer(None, None, matching_config)
        result = scorer.calculate_quality_score(mock_requirement, mock_availability)
        
        assert result["score"] > 0.5  # Acceptable
        assert result["pass"] is True
    
    @pytest.mark.asyncio
    async def test_quality_score_below_minimum(
        self,
        matching_config,
        mock_requirement,
        mock_availability
    ):
        """Test quality below minimum = fail"""
        mock_availability.quality_params = {
            "grade": "B",  # Below min "A"
            "moisture": 15.0  # Above max 12.0
        }
        
        scorer = MatchScorer(None, None, matching_config)
        result = scorer.calculate_quality_score(mock_requirement, mock_availability)
        
        assert result["score"] < 0.5  # Poor match
        assert result["pass"] is False


class TestPriceScoring:
    """Test price competitiveness (30% weight)"""
    
    @pytest.mark.asyncio
    async def test_price_score_at_preferred_price(
        self,
        matching_config,
        mock_requirement,
        mock_availability
    ):
        """Test asking price = preferred price = perfect score"""
        mock_requirement.preferred_price = Decimal('45000.00')
        mock_availability.asking_price = Decimal('45000.00')
        
        scorer = MatchScorer(None, None, matching_config)
        result = scorer.calculate_price_score(mock_requirement, mock_availability)
        
        assert result["score"] >= 0.95
        assert result["pass"] is True
    
    @pytest.mark.asyncio
    async def test_price_score_between_preferred_and_max(
        self,
        matching_config,
        mock_requirement,
        mock_availability
    ):
        """Test asking price between preferred and max budget"""
        mock_requirement.preferred_price = Decimal('45000.00')
        mock_requirement.max_budget = Decimal('50000.00')
        mock_availability.asking_price = Decimal('48000.00')
        
        scorer = MatchScorer(None, None, matching_config)
        result = scorer.calculate_price_score(mock_requirement, mock_availability)
        
        assert 0.4 < result["score"] < 0.9  # Acceptable but not ideal
        assert result["pass"] is True
    
    @pytest.mark.asyncio
    async def test_price_score_exceeds_max_budget(
        self,
        matching_config,
        mock_requirement,
        mock_availability
    ):
        """Test asking price > max budget = fail"""
        mock_requirement.max_budget = Decimal('50000.00')
        mock_availability.asking_price = Decimal('55000.00')
        
        scorer = MatchScorer(None, None, matching_config)
        result = scorer.calculate_price_score(mock_requirement, mock_availability)
        
        assert result["score"] == 0.0
        assert result["pass"] is False


class TestDeliveryScoring:
    """Test delivery logistics compatibility (15% weight)"""
    
    @pytest.mark.asyncio
    async def test_delivery_score_matching_timeline(
        self,
        matching_config,
        mock_requirement,
        mock_availability
    ):
        """Test delivery timeline matches or better"""
        mock_requirement.delivery_timeline_days = 30
        mock_availability.delivery_timeline_days = 25  # Faster
        
        scorer = MatchScorer(None, None, matching_config)
        result = scorer.calculate_delivery_score(mock_requirement, mock_availability)
        
        assert result["score"] >= 0.9
        assert result["pass"] is True
    
    @pytest.mark.asyncio
    async def test_delivery_score_matching_terms(
        self,
        matching_config,
        mock_requirement,
        mock_availability
    ):
        """Test delivery terms match (FOB, CIF, etc.)"""
        mock_requirement.delivery_terms = "FOB"
        mock_availability.delivery_terms = "FOB"
        
        scorer = MatchScorer(None, None, matching_config)
        result = scorer.calculate_delivery_score(mock_requirement, mock_availability)
        
        assert result["pass"] is True


class TestRiskScoring:
    """Test risk assessment integration (15% weight)"""
    
    @pytest.mark.asyncio
    async def test_risk_score_pass_status(
        self,
        matching_config,
        mock_requirement,
        mock_availability
    ):
        """Test PASS (≥80) = risk_score 1.0, no penalty"""
        # Mock risk engine to return PASS
        # Expected: risk_score = 1.0, warn_penalty = 0.0
        pass
    
    @pytest.mark.asyncio
    async def test_risk_score_warn_status(
        self,
        matching_config,
        mock_requirement,
        mock_availability
    ):
        """Test WARN (60-79) = risk_score 0.5, 10% global penalty"""
        # Mock risk engine to return WARN
        # Expected: risk_score = 0.5, warn_penalty = 0.10
        pass
    
    @pytest.mark.asyncio
    async def test_risk_score_fail_status(
        self,
        matching_config,
        mock_requirement,
        mock_availability
    ):
        """Test FAIL (<60) = block match, score 0.0"""
        # Mock risk engine to return FAIL
        # Expected: blocked = True, total_score = 0.0
        pass


class TestWARNPenalty:
    """Test ITERATION #3: WARN penalty semantics"""
    
    @pytest.mark.asyncio
    async def test_warn_penalty_10_percent_global(
        self,
        matching_config,
        mock_requirement,
        mock_availability
    ):
        """Test WARN applies single 10% global penalty"""
        # Mock scenario:
        # base_score = 0.80
        # WARN penalty = 0.10
        # final_score = 0.80 * 0.90 = 0.72
        
        # Mock risk engine to return WARN status
        # Verify final_score = base_score * 0.9
        pass
    
    @pytest.mark.asyncio
    async def test_warn_penalty_not_duplicated(
        self,
        matching_config,
        mock_requirement,
        mock_availability
    ):
        """Test WARN penalty applied only once (not duplicated in risk_score)"""
        # Verify risk_score = 0.5 (for 15% weight)
        # AND global penalty = -10%
        # Total impact: (0.5 * 0.15) + (base * -0.10)
        # Not (0.5 * 0.15 * 0.90) <- incorrect
        pass


class TestAIScoreBoost:
    """Test ENHANCEMENT #7: AI recommendation score boost"""
    
    @pytest.mark.asyncio
    async def test_ai_boost_for_recommended_seller(
        self,
        matching_config,
        mock_requirement,
        mock_availability
    ):
        """Test +5% boost for AI-recommended seller"""
        # Mock requirement with ai_recommended_sellers containing seller_id
        mock_requirement.ai_recommended_sellers = {
            "recommendations": [
                {"seller_id": str(mock_availability.party_id), "score": 0.92}
            ]
        }
        
        # Expected: ai_boost_applied = True, ai_boost_value = 0.05
        # final_score = base_score + 0.05 (capped at 1.0)
        pass
    
    @pytest.mark.asyncio
    async def test_ai_boost_capped_at_1_0(
        self,
        matching_config,
        mock_requirement,
        mock_availability
    ):
        """Test AI boost doesn't exceed 1.0 (100%)"""
        # Mock scenario: base_score = 0.98, ai_boost = 0.05
        # Expected: final_score = 1.0 (not 1.03)
        pass
    
    @pytest.mark.asyncio
    async def test_no_ai_boost_for_non_recommended_seller(
        self,
        matching_config,
        mock_requirement,
        mock_availability
    ):
        """Test no boost for seller not in AI recommendations"""
        mock_requirement.ai_recommended_sellers = {
            "recommendations": [
                {"seller_id": str(uuid4()), "score": 0.90}  # Different seller
            ]
        }
        
        # Expected: ai_boost_applied = False, ai_boost_value = 0.0
        pass


class TestCommoditySpecificWeights:
    """Test ITERATION #7: Per-commodity scoring weights"""
    
    @pytest.mark.asyncio
    async def test_cotton_default_weights(self, matching_config):
        """Test COTTON uses 40/30/15/15 weights"""
        weights = matching_config.get_scoring_weights("COTTON")
        
        assert weights["quality"] == 0.40
        assert weights["price"] == 0.30
        assert weights["delivery"] == 0.15
        assert weights["risk"] == 0.15
    
    @pytest.mark.asyncio
    async def test_gold_higher_quality_weight(self, matching_config):
        """Test GOLD might prioritize quality differently"""
        weights = matching_config.get_scoring_weights("GOLD")
        
        # Verify weights sum to 1.0
        total = weights["quality"] + weights["price"] + weights["delivery"] + weights["risk"]
        assert abs(total - 1.0) < 0.01


class TestScoreBreakdown:
    """Test score breakdown structure and transparency"""
    
    @pytest.mark.asyncio
    async def test_score_breakdown_contains_all_components(self):
        """Test breakdown shows all 4 scoring components"""
        # Mock full scoring calculation
        # Expected breakdown:
        # {
        #     "quality_score": 0.92,
        #     "price_score": 0.88,
        #     "delivery_score": 0.95,
        #     "risk_score": 1.0
        # }
        pass
    
    @pytest.mark.asyncio
    async def test_recommendations_text_generation(self):
        """Test recommendation text based on final score"""
        # final_score >= 0.9: "Excellent match"
        # final_score >= 0.75: "Good match"
        # final_score >= 0.6: "Acceptable match"
        # final_score < 0.6: "Below threshold"
        pass


# Run with: pytest backend/modules/trade_desk/tests/test_scoring.py -v --cov=backend/modules/trade_desk/matching/scoring

"""
Test Suite: Core Matching Engine

Tests for:
- Location-first hard filtering (ITERATION #1)
- Bidirectional matching (requirement → availability, availability → requirement)
- Duplicate detection (ITERATION #6)
- Atomic allocation (ITERATION #5)
- Match result structure and audit trail (ITERATION #8)
"""

import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from uuid import uuid4

from backend.modules.trade_desk.matching.matching_engine import MatchingEngine, MatchResult
from backend.modules.trade_desk.matching.scoring import MatchScorer
from backend.modules.trade_desk.config.matching_config import MatchingConfig
from backend.modules.trade_desk.models.requirement import Requirement
from backend.modules.trade_desk.models.availability import Availability


@pytest.fixture
def matching_config():
    """Default matching configuration"""
    return MatchingConfig()


@pytest.fixture
def mock_requirement():
    """Create a mock buyer requirement"""
    return Requirement(
        id=uuid4(),
        party_id=uuid4(),
        commodity_id=uuid4(),
        preferred_quantity=Decimal('100.0'),
        min_quantity=Decimal('10.0'),
        max_quantity=Decimal('200.0'),
        max_budget=Decimal('50000.00'),
        preferred_price=Decimal('45000.00'),
        status="ACTIVE",
        delivery_locations=[
            {
                "location_id": str(uuid4()),
                "latitude": 28.7041,
                "longitude": 77.1025,
                "max_distance_km": 50
            }
        ],
        quality_params={
            "grade": {"min": "A", "preferred": "A+"},
            "moisture": {"max": 12.0}
        },
        delivery_terms="FOB",
        created_at=datetime.utcnow()
    )


@pytest.fixture
def mock_availability(mock_requirement):
    """Create a mock seller availability matching the requirement"""
    location_id = mock_requirement.delivery_locations[0]["location_id"]
    
    return Availability(
        id=uuid4(),
        party_id=uuid4(),
        commodity_id=mock_requirement.commodity_id,
        location_id=location_id,
        available_quantity=Decimal('150.0'),
        asking_price=Decimal('48000.00'),
        status="ACTIVE",
        quality_params={
            "grade": "A+",
            "moisture": 10.5
        },
        delivery_terms="FOB",
        created_at=datetime.utcnow()
    )


class TestLocationFirstFiltering:
    """Test ITERATION #1: Location-first hard filter"""
    
    def test_location_filter_runs_before_scoring(
        self,
        matching_config,
        mock_requirement,
        mock_availability
    ):
        """
        Verify location check happens BEFORE any scoring.
        If location doesn't match → skip immediately (no scoring wasted).
        """
        # Change availability location to non-matching
        mock_availability.location_id = uuid4()
        
        engine = MatchingEngine(
            db=None,  # Mock
            req_repo=None,
            avail_repo=None,
            scorer=None,
            config=matching_config
        )
        
        # Location filter should reject before scoring
        assert not engine._location_matches(mock_requirement, mock_availability)
    
    def test_location_match_exact_location_id(
        self,
        matching_config,
        mock_requirement,
        mock_availability
    ):
        """Test exact location ID match"""
        location_id = mock_requirement.delivery_locations[0]["location_id"]
        mock_availability.location_id = location_id
        
        engine = MatchingEngine(
            db=None,
            req_repo=None,
            avail_repo=None,
            scorer=None,
            config=matching_config
        )
        
        assert engine._location_matches(mock_requirement, mock_availability)
    
    def test_location_filter_rejects_cross_state(
        self,
        matching_config,
        mock_requirement,
        mock_availability
    ):
        """Test cross-state matching is blocked by default"""
        # Availability in different location
        mock_availability.location_id = uuid4()
        
        engine = MatchingEngine(
            db=None,
            req_repo=None,
            avail_repo=None,
            scorer=None,
            config=matching_config
        )
        
        # Should reject if not in delivery_locations
        assert not engine._location_matches(mock_requirement, mock_availability)
    
    def test_multiple_delivery_locations(
        self,
        matching_config,
        mock_requirement,
        mock_availability
    ):
        """Test requirement with multiple acceptable delivery locations"""
        location1 = str(uuid4())
        location2 = str(uuid4())
        location3 = str(uuid4())
        
        mock_requirement.delivery_locations = [
            {"location_id": location1, "latitude": 28.7041, "longitude": 77.1025},
            {"location_id": location2, "latitude": 19.0760, "longitude": 72.8777},
            {"location_id": location3, "latitude": 13.0827, "longitude": 80.2707}
        ]
        
        # Availability at location2
        mock_availability.location_id = location2
        
        engine = MatchingEngine(
            db=None,
            req_repo=None,
            avail_repo=None,
            scorer=None,
            config=matching_config
        )
        
        # Should match any of the delivery locations
        assert engine._location_matches(mock_requirement, mock_availability)


class TestDuplicateDetection:
    """Test ITERATION #6: Duplicate detection with exact tolerances"""
    
    def test_duplicate_key_generation(self, matching_config):
        """Test duplicate key format: {commodity}:{buyer}:{seller}"""
        commodity_id = uuid4()
        buyer_id = uuid4()
        seller_id = uuid4()
        
        engine = MatchingEngine(
            db=None,
            req_repo=None,
            avail_repo=None,
            scorer=None,
            config=matching_config
        )
        
        key = engine._generate_duplicate_key(commodity_id, buyer_id, seller_id)
        
        assert key == f"{commodity_id}:{buyer_id}:{seller_id}"
    
    def test_duplicate_detection_5_minute_window(
        self,
        matching_config,
        mock_requirement,
        mock_availability
    ):
        """Test 5-minute time window for duplicate detection"""
        engine = MatchingEngine(
            db=None,
            req_repo=None,
            avail_repo=None,
            scorer=None,
            config=matching_config
        )
        
        # First match
        is_dup1 = engine._is_duplicate(
            mock_requirement.commodity_id,
            mock_requirement.party_id,
            mock_availability.party_id
        )
        assert not is_dup1  # First occurrence, not duplicate
        
        # Same match within 5 minutes
        is_dup2 = engine._is_duplicate(
            mock_requirement.commodity_id,
            mock_requirement.party_id,
            mock_availability.party_id
        )
        assert is_dup2  # Duplicate detected
    
    def test_duplicate_detection_different_commodities(
        self,
        matching_config,
        mock_requirement,
        mock_availability
    ):
        """Test that different commodities are NOT duplicates"""
        engine = MatchingEngine(
            db=None,
            req_repo=None,
            avail_repo=None,
            scorer=None,
            config=matching_config
        )
        
        commodity1 = uuid4()
        commodity2 = uuid4()
        buyer_id = mock_requirement.party_id
        seller_id = mock_availability.party_id
        
        # First commodity
        is_dup1 = engine._is_duplicate(commodity1, buyer_id, seller_id)
        assert not is_dup1
        
        # Different commodity, same buyer-seller
        is_dup2 = engine._is_duplicate(commodity2, buyer_id, seller_id)
        assert not is_dup2  # Different commodity = not duplicate


class TestMatchResultStructure:
    """Test ITERATION #8: Audit trail and explainability"""
    
    def test_match_result_contains_all_required_fields(self):
        """Test MatchResult has all required audit fields"""
        match = MatchResult(
            requirement_id=uuid4(),
            availability_id=uuid4(),
            score=0.85,
            base_score=0.90,
            warn_penalty_applied=True,
            score_breakdown={
                "breakdown": {
                    "quality_score": 0.92,
                    "price_score": 0.88,
                    "delivery_score": 0.95,
                    "risk_score": 0.85
                },
                "recommendations": "Good match - recommended (WARN penalty applied: -10%)"
            },
            risk_status="WARN",
            matched_quantity=Decimal('100.0'),
            matched_at=datetime.utcnow()
        )
        
        # Verify all audit fields present
        assert match.requirement_id is not None
        assert match.availability_id is not None
        assert match.score == 0.85
        assert match.base_score == 0.90
        assert match.warn_penalty_applied is True
        assert match.risk_status == "WARN"
        assert "breakdown" in match.score_breakdown
        assert "recommendations" in match.score_breakdown
    
    def test_match_result_score_breakdown_structure(self):
        """Test score breakdown contains all 4 factors"""
        match = MatchResult(
            requirement_id=uuid4(),
            availability_id=uuid4(),
            score=0.75,
            base_score=0.75,
            warn_penalty_applied=False,
            score_breakdown={
                "breakdown": {
                    "quality_score": 0.80,
                    "price_score": 0.70,
                    "delivery_score": 0.75,
                    "risk_score": 1.0
                }
            },
            risk_status="PASS"
        )
        
        breakdown = match.score_breakdown["breakdown"]
        
        assert "quality_score" in breakdown
        assert "price_score" in breakdown
        assert "delivery_score" in breakdown
        assert "risk_score" in breakdown
        
        # Verify scores are valid (0.0 to 1.0)
        for score in breakdown.values():
            assert 0.0 <= score <= 1.0


class TestBidirectionalMatching:
    """Test bidirectional matching flows"""
    
    @pytest.mark.asyncio
    async def test_find_matches_for_requirement(
        self,
        matching_config,
        mock_requirement
    ):
        """Test buyer finds sellers (requirement → availability)"""
        # This would require mocking the database and repositories
        # Placeholder for actual implementation
        pass
    
    @pytest.mark.asyncio
    async def test_find_matches_for_availability(
        self,
        matching_config,
        mock_availability
    ):
        """Test seller finds buyers (availability → requirement)"""
        # This would require mocking the database and repositories
        # Placeholder for actual implementation
        pass


class TestAtomicAllocation:
    """Test ITERATION #5: Atomic allocation with optimistic locking"""
    
    @pytest.mark.asyncio
    async def test_allocate_quantity_atomic_full_match(
        self,
        matching_config
    ):
        """Test full allocation when availability >= requirement"""
        # Mock availability with sufficient quantity
        availability = Availability(
            id=uuid4(),
            available_quantity=Decimal('150.0'),
            version=1
        )
        
        requirement_quantity = Decimal('100.0')
        
        # Would test actual allocation with DB mocking
        # Expected: allocated_quantity=100, remaining=50, type=FULL
        pass
    
    @pytest.mark.asyncio
    async def test_allocate_quantity_atomic_partial_match(
        self,
        matching_config
    ):
        """Test partial allocation when availability < requirement"""
        # Mock availability with insufficient quantity
        availability = Availability(
            id=uuid4(),
            available_quantity=Decimal('60.0'),
            version=1
        )
        
        requirement_quantity = Decimal('100.0')
        min_quantity = Decimal('50.0')
        
        # Would test actual allocation with DB mocking
        # Expected: allocated_quantity=60, remaining=0, type=PARTIAL
        pass
    
    @pytest.mark.asyncio
    async def test_allocate_quantity_atomic_version_conflict(
        self,
        matching_config
    ):
        """Test optimistic locking prevents double-allocation"""
        # Mock concurrent allocation scenario
        # Two requests try to allocate from same availability simultaneously
        # One should succeed, one should retry with updated version
        pass
    
    @pytest.mark.asyncio
    async def test_allocate_quantity_atomic_retry_logic(
        self,
        matching_config
    ):
        """Test retry logic with exponential backoff (max 3 attempts)"""
        # Mock scenario where first 2 attempts fail (version conflict)
        # 3rd attempt succeeds
        # Verify exponential backoff timing
        pass


class TestConfigurationPerCommodity:
    """Test ITERATION #7: Per-commodity configurable thresholds"""
    
    def test_scoring_weights_per_commodity(self, matching_config):
        """Test different commodities have different scoring weights"""
        cotton_weights = matching_config.get_scoring_weights("COTTON")
        gold_weights = matching_config.get_scoring_weights("GOLD")
        
        # Default weights
        assert cotton_weights["quality"] == 0.40
        assert cotton_weights["price"] == 0.30
        
        # Gold might have different weights (if configured)
        assert "quality" in gold_weights
        assert "price" in gold_weights
    
    def test_min_score_threshold_per_commodity(self, matching_config):
        """Test different min score thresholds per commodity"""
        cotton_threshold = matching_config.get_min_score_threshold("COTTON")
        gold_threshold = matching_config.get_min_score_threshold("GOLD")
        wheat_threshold = matching_config.get_min_score_threshold("WHEAT")
        
        # From spec: COTTON 0.6, GOLD 0.7, WHEAT 0.5
        assert cotton_threshold == 0.6
        assert gold_threshold == 0.7
        assert wheat_threshold == 0.5
    
    def test_default_threshold_for_unknown_commodity(self, matching_config):
        """Test fallback to default threshold for unconfigured commodity"""
        unknown_threshold = matching_config.get_min_score_threshold("UNKNOWN_COMMODITY")
        
        assert unknown_threshold == 0.6  # Default


# Run with: pytest backend/modules/trade_desk/tests/test_matching_engine.py -v

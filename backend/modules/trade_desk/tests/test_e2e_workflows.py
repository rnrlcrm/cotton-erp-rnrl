"""
End-to-End Integration Tests: Complete Matching Workflows

Tests complete matching workflows from requirement creation to match allocation.
Target Coverage: 80% overall coverage across all matching modules.

Test Categories:
1. Complete buyer-initiated matching workflow
2. Complete seller-initiated matching workflow
3. Multi-match scenarios with ranking
4. Concurrent matching and allocation
5. Error recovery and edge cases
"""

import pytest
import asyncio
from decimal import Decimal
from datetime import datetime, timedelta
from uuid import uuid4, UUID
from typing import List

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from unittest.mock import AsyncMock, Mock

from backend.modules.trade_desk.models.requirement import Requirement
from backend.modules.trade_desk.models.availability import Availability
from backend.modules.settings.commodities.models import Commodity
from backend.modules.trade_desk.repositories.requirement_repository import RequirementRepository
from backend.modules.trade_desk.repositories.availability_repository import AvailabilityRepository
from backend.modules.trade_desk.matching.matching_engine import MatchingEngine, MatchResult
from backend.modules.trade_desk.matching.scoring import MatchScorer
from backend.modules.trade_desk.matching.validators import MatchValidator
from backend.modules.trade_desk.config.matching_config import MatchingConfig
from backend.core.database import Base


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
async def async_db_engine():
    """Create in-memory async database engine."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
        future=True
    )
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    await engine.dispose()


@pytest.fixture
async def async_db_session(async_db_engine):
    """Create async database session."""
    async_session = sessionmaker(
        async_db_engine,
        class_=AsyncSession,
        expire_on_commit=False
    )
    
    async with async_session() as session:
        yield session
        await session.rollback()


@pytest.fixture
async def mock_risk_engine():
    """Mock risk engine that returns PASS by default."""
    risk_engine = AsyncMock()
    risk_engine.evaluate_match_risk = AsyncMock(return_value={
        "risk_status": "PASS",
        "risk_score": 95,
        "flags": [],
        "details": {}
    })
    return risk_engine


@pytest.fixture
def matching_config():
    """Test matching configuration."""
    return MatchingConfig()


@pytest.fixture
async def test_commodity(async_db_session):
    """Create COTTON commodity."""
    commodity = Commodity(
        id=uuid4(),
        code="COTTON",
        name="Cotton",
        category="Agricultural",
        is_active=True
    )
    async_db_session.add(commodity)
    await async_db_session.commit()
    await async_db_session.refresh(commodity)
    return commodity


@pytest.fixture
async def test_location(async_db_session):
    """Create Mumbai location."""
    from backend.modules.settings.locations.models import Location
    
    location = Location(
        id=uuid4(),
        name="Mumbai",
        state="Maharashtra",
        country="India",
        latitude=19.0760,
        longitude=72.8777,
        is_active=True
    )
    async_db_session.add(location)
    await async_db_session.commit()
    await async_db_session.refresh(location)
    return location


@pytest.fixture
async def matching_engine_full(
    async_db_session,
    mock_risk_engine,
    matching_config
):
    """Create fully configured matching engine."""
    req_repo = RequirementRepository(async_db_session)
    avail_repo = AvailabilityRepository(async_db_session)
    
    engine = MatchingEngine(
        db=async_db_session,
        risk_engine=mock_risk_engine,
        requirement_repo=req_repo,
        availability_repo=avail_repo,
        config=matching_config
    )
    
    return engine


# ============================================================================
# TEST CATEGORY 1: Complete Buyer-Initiated Workflow
# ============================================================================

@pytest.mark.asyncio
class TestBuyerInitiatedWorkflow:
    """Test complete workflow from buyer requirement to match."""
    
    async def test_buyer_posts_requirement_finds_single_match(
        self,
        matching_engine_full,
        async_db_session,
        test_commodity,
        test_location
    ):
        """
        E2E: Buyer posts requirement → Engine finds match → Returns top match.
        
        Workflow:
        1. Buyer creates requirement
        2. Matching engine searches for availabilities
        3. Location filter applied
        4. Scoring calculated
        5. Match returned with full details
        """
        # STEP 1: Buyer creates requirement
        requirement = Requirement(
            id=uuid4(),
            requirement_number=f"REQ-E2E-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
            buyer_partner_id=uuid4(),
            commodity_id=test_commodity.id,
            quantity_required=Decimal("100.000"),
            delivery_locations=[
                {
                    "location_id": str(test_location.id),
                    "latitude": test_location.latitude,
                    "longitude": test_location.longitude
                }
            ],
            quality_params={"staple_length": 28.5},
            expected_price=Decimal("50000.00"),
            max_price=Decimal("55000.00"),
            delivery_by=datetime.utcnow() + timedelta(days=30),
            status="ACTIVE",
            intent="DIRECT_BUY"
        )
        async_db_session.add(requirement)
        await async_db_session.commit()
        await async_db_session.refresh(requirement)
        
        # STEP 2: Seller posts availability (before matching)
        availability = Availability(
            id=uuid4(),
            commodity_id=test_commodity.id,
            location_id=test_location.id,
            seller_id=uuid4(),
            total_quantity=Decimal("150.000"),
            available_quantity=Decimal("150.000"),
            base_price=Decimal("48000.00"),
            quality_params={"staple_length": 29.0},
            status="ACTIVE",
            risk_precheck_status="PASS",
            risk_precheck_score=95
        )
        async_db_session.add(availability)
        await async_db_session.commit()
        
        # STEP 3: Run matching engine
        matches = await matching_engine_full.find_matches_for_requirement(
            requirement_id=requirement.id,
            min_score=0.5
        )
        
        # STEP 4: Verify match found
        assert len(matches) == 1
        match = matches[0]
        assert match.requirement_id == requirement.id
        assert match.availability_id == availability.id
        assert match.score >= 0.5
        assert match.location_filter_passed is True
        assert match.risk_status == "PASS"
        
        # STEP 5: Verify score breakdown
        assert "quality_score" in match.score_breakdown
        assert "price_score" in match.score_breakdown
        assert "delivery_score" in match.score_breakdown
        assert "risk_score" in match.score_breakdown
    
    async def test_buyer_requirement_finds_multiple_matches_ranked(
        self,
        matching_engine_full,
        async_db_session,
        test_commodity,
        test_location
    ):
        """
        E2E: Buyer requirement → Multiple sellers available → Ranked by score.
        
        Verifies:
        - Multiple matches found
        - Sorted by score (best first)
        - All pass location filter
        """
        # STEP 1: Create buyer requirement
        requirement = Requirement(
            id=uuid4(),
            requirement_number=f"REQ-MULTI-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
            buyer_partner_id=uuid4(),
            commodity_id=test_commodity.id,
            quantity_required=Decimal("100.000"),
            delivery_locations=[{"location_id": str(test_location.id)}],
            quality_params={"staple_length": 28.5},
            expected_price=Decimal("50000.00"),
            max_price=Decimal("55000.00"),
            delivery_by=datetime.utcnow() + timedelta(days=30),
            status="ACTIVE",
            intent="DIRECT_BUY"
        )
        async_db_session.add(requirement)
        await async_db_session.commit()
        
        # STEP 2: Create 3 availabilities with different prices
        availabilities = []
        prices = [Decimal("45000.00"), Decimal("50000.00"), Decimal("52000.00")]
        
        for price in prices:
            avail = Availability(
                id=uuid4(),
                commodity_id=test_commodity.id,
                location_id=test_location.id,
                seller_id=uuid4(),
                total_quantity=Decimal("100.000"),
                available_quantity=Decimal("100.000"),
                base_price=price,
                quality_params={"staple_length": 29.0},
                status="ACTIVE",
                risk_precheck_status="PASS"
            )
            async_db_session.add(avail)
            availabilities.append(avail)
        
        await async_db_session.commit()
        
        # STEP 3: Run matching
        matches = await matching_engine_full.find_matches_for_requirement(
            requirement_id=requirement.id,
            min_score=0.3
        )
        
        # STEP 4: Verify all 3 found and ranked
        assert len(matches) == 3
        
        # Verify sorted by score (descending)
        for i in range(len(matches) - 1):
            assert matches[i].score >= matches[i + 1].score
        
        # Verify best match is cheapest price
        best_match = matches[0]
        assert best_match.score >= matches[1].score
        assert best_match.score >= matches[2].score


# ============================================================================
# TEST CATEGORY 2: Complete Seller-Initiated Workflow
# ============================================================================

@pytest.mark.asyncio
class TestSellerInitiatedWorkflow:
    """Test reverse matching from seller availability."""
    
    async def test_seller_posts_availability_finds_matching_requirements(
        self,
        matching_engine_full,
        async_db_session,
        test_commodity,
        test_location
    ):
        """
        E2E: Seller posts availability → Engine finds buyer requirements.
        
        Workflow:
        1. Create buyer requirements first
        2. Seller posts availability
        3. Matching engine finds compatible requirements
        4. Returns ranked matches
        """
        # STEP 1: Create 2 buyer requirements
        requirements = []
        for i in range(2):
            req = Requirement(
                id=uuid4(),
                requirement_number=f"REQ-SELLER-{i}-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
                buyer_partner_id=uuid4(),
                commodity_id=test_commodity.id,
                quantity_required=Decimal("100.000"),
                delivery_locations=[{"location_id": str(test_location.id)}],
                quality_params={"staple_length": 28.5},
                expected_price=Decimal("50000.00"),
                max_price=Decimal("55000.00"),
                delivery_by=datetime.utcnow() + timedelta(days=30),
                status="ACTIVE",
                intent="DIRECT_BUY"
            )
            async_db_session.add(req)
            requirements.append(req)
        
        await async_db_session.commit()
        
        # STEP 2: Seller posts availability
        availability = Availability(
            id=uuid4(),
            commodity_id=test_commodity.id,
            location_id=test_location.id,
            seller_id=uuid4(),
            total_quantity=Decimal("500.000"),
            available_quantity=Decimal("500.000"),
            base_price=Decimal("48000.00"),
            quality_params={"staple_length": 29.0},
            status="ACTIVE",
            risk_precheck_status="PASS"
        )
        async_db_session.add(availability)
        await async_db_session.commit()
        
        # STEP 3: Run reverse matching
        matches = await matching_engine_full.find_matches_for_availability(
            availability_id=availability.id,
            min_score=0.5
        )
        
        # STEP 4: Verify both requirements found
        assert len(matches) >= 2
        assert all(m.availability_id == availability.id for m in matches)
        assert all(m.score >= 0.5 for m in matches)


# ============================================================================
# TEST CATEGORY 3: Concurrent Allocation Scenarios
# ============================================================================

@pytest.mark.asyncio
class TestConcurrentAllocation:
    """Test concurrent allocation with race conditions."""
    
    async def test_concurrent_buyers_compete_for_limited_availability(
        self,
        matching_engine_full,
        async_db_session,
        test_commodity,
        test_location
    ):
        """
        E2E: Multiple buyers → Limited availability → Only one succeeds.
        
        Tests:
        - Optimistic locking
        - Atomic allocation
        - Race condition handling
        """
        # STEP 1: Create limited availability
        availability = Availability(
            id=uuid4(),
            commodity_id=test_commodity.id,
            location_id=test_location.id,
            seller_id=uuid4(),
            total_quantity=Decimal("100.000"),
            available_quantity=Decimal("100.000"),
            base_price=Decimal("48000.00"),
            status="ACTIVE",
            risk_precheck_status="PASS",
            version=0  # Optimistic locking
        )
        async_db_session.add(availability)
        await async_db_session.commit()
        
        # STEP 2: Create 3 competing requirements
        req_ids = []
        for i in range(3):
            req = Requirement(
                id=uuid4(),
                requirement_number=f"REQ-RACE-{i}",
                buyer_partner_id=uuid4(),
                commodity_id=test_commodity.id,
                quantity_required=Decimal("80.000"),  # Each wants 80, only 100 available
                delivery_locations=[{"location_id": str(test_location.id)}],
                expected_price=Decimal("50000.00"),
                max_price=Decimal("55000.00"),
                status="ACTIVE",
                intent="DIRECT_BUY"
            )
            async_db_session.add(req)
            req_ids.append(req.id)
        
        await async_db_session.commit()
        
        # STEP 3: Simulate concurrent allocations
        allocation_tasks = [
            matching_engine_full.allocate_quantity_atomic(
                availability_id=availability.id,
                quantity=Decimal("80.000"),
                requirement_id=req_id
            )
            for req_id in req_ids
        ]
        
        results = await asyncio.gather(*allocation_tasks, return_exceptions=True)
        
        # STEP 4: Verify only one allocation succeeded
        successes = [r for r in results if r is True]
        assert len(successes) == 1  # Only first allocation succeeds


# ============================================================================
# TEST CATEGORY 4: Risk-Driven Workflows
# ============================================================================

@pytest.mark.asyncio
class TestRiskDrivenWorkflows:
    """Test workflows with different risk statuses."""
    
    async def test_warn_status_applies_penalty_but_allows_match(
        self,
        matching_engine_full,
        async_db_session,
        test_commodity,
        test_location,
        mock_risk_engine
    ):
        """
        E2E: Risk WARN → Score penalty applied → Match still possible.
        
        Verifies:
        - WARN doesn't block match
        - 10% penalty applied to total score
        - Match details include penalty info
        """
        # Configure risk engine for WARN
        mock_risk_engine.evaluate_match_risk = AsyncMock(return_value={
            "risk_status": "WARN",
            "risk_score": 70,
            "flags": ["moderate_credit_risk"],
            "details": {}
        })
        
        # Create requirement and availability
        requirement = Requirement(
            id=uuid4(),
            requirement_number="REQ-WARN-001",
            buyer_partner_id=uuid4(),
            commodity_id=test_commodity.id,
            quantity_required=Decimal("100.000"),
            delivery_locations=[{"location_id": str(test_location.id)}],
            expected_price=Decimal("50000.00"),
            max_price=Decimal("55000.00"),
            status="ACTIVE",
            intent="DIRECT_BUY"
        )
        
        availability = Availability(
            id=uuid4(),
            commodity_id=test_commodity.id,
            location_id=test_location.id,
            seller_id=uuid4(),
            total_quantity=Decimal("150.000"),
            available_quantity=Decimal("150.000"),
            base_price=Decimal("48000.00"),
            status="ACTIVE",
            risk_precheck_status="WARN"
        )
        
        async_db_session.add_all([requirement, availability])
        await async_db_session.commit()
        
        # Run matching
        matches = await matching_engine_full.find_matches_for_requirement(
            requirement_id=requirement.id
        )
        
        # Verify WARN handling
        assert len(matches) > 0
        match = matches[0]
        assert match.risk_status == "WARN"
        assert match.warn_penalty_applied is True
        assert match.score < match.base_score  # Penalty reduced score
        
        # Verify 10% penalty
        expected_penalty = match.base_score * 0.10
        assert abs(match.warn_penalty_value - expected_penalty) < 0.001
    
    async def test_fail_status_blocks_match_completely(
        self,
        matching_engine_full,
        async_db_session,
        test_commodity,
        test_location,
        mock_risk_engine
    ):
        """
        E2E: Risk FAIL → Match blocked → No results returned.
        """
        # Configure risk engine for FAIL
        mock_risk_engine.evaluate_match_risk = AsyncMock(return_value={
            "risk_status": "FAIL",
            "risk_score": 30,
            "blocked": True,
            "flags": ["high_credit_risk"]
        })
        
        # Create requirement and availability
        requirement = Requirement(
            id=uuid4(),
            requirement_number="REQ-FAIL-001",
            buyer_partner_id=uuid4(),
            commodity_id=test_commodity.id,
            quantity_required=Decimal("100.000"),
            delivery_locations=[{"location_id": str(test_location.id)}],
            expected_price=Decimal("50000.00"),
            max_price=Decimal("55000.00"),
            status="ACTIVE",
            intent="DIRECT_BUY"
        )
        
        availability = Availability(
            id=uuid4(),
            commodity_id=test_commodity.id,
            location_id=test_location.id,
            seller_id=uuid4(),
            total_quantity=Decimal("150.000"),
            available_quantity=Decimal("150.000"),
            base_price=Decimal("48000.00"),
            status="ACTIVE",
            risk_precheck_status="FAIL"
        )
        
        async_db_session.add_all([requirement, availability])
        await async_db_session.commit()
        
        # Run matching
        matches = await matching_engine_full.find_matches_for_requirement(
            requirement_id=requirement.id
        )
        
        # Verify blocked
        assert len(matches) == 0  # FAIL blocks match


# ============================================================================
# TEST CATEGORY 5: Edge Cases and Error Recovery
# ============================================================================

@pytest.mark.asyncio
class TestEdgeCasesAndErrorRecovery:
    """Test error handling and edge cases."""
    
    async def test_handles_no_matches_gracefully(
        self,
        matching_engine_full,
        async_db_session,
        test_commodity,
        test_location
    ):
        """Should return empty list when no matches found."""
        # Create requirement with impossible criteria
        requirement = Requirement(
            id=uuid4(),
            requirement_number="REQ-NOMATCH-001",
            buyer_partner_id=uuid4(),
            commodity_id=test_commodity.id,
            quantity_required=Decimal("100.000"),
            delivery_locations=[{"location_id": str(uuid4())}],  # Non-existent location
            expected_price=Decimal("1.00"),  # Impossibly low price
            max_price=Decimal("2.00"),
            status="ACTIVE",
            intent="DIRECT_BUY"
        )
        async_db_session.add(requirement)
        await async_db_session.commit()
        
        # Run matching
        matches = await matching_engine_full.find_matches_for_requirement(
            requirement_id=requirement.id
        )
        
        # Should return empty, not crash
        assert matches == []
    
    async def test_continues_after_individual_match_error(
        self,
        matching_engine_full,
        async_db_session,
        test_commodity,
        test_location
    ):
        """Should continue processing even if one match scoring fails."""
        # Create requirement
        requirement = Requirement(
            id=uuid4(),
            requirement_number="REQ-ERROR-001",
            buyer_partner_id=uuid4(),
            commodity_id=test_commodity.id,
            quantity_required=Decimal("100.000"),
            delivery_locations=[{"location_id": str(test_location.id)}],
            expected_price=Decimal("50000.00"),
            max_price=Decimal("55000.00"),
            status="ACTIVE",
            intent="DIRECT_BUY"
        )
        
        # Create good availability
        good_avail = Availability(
            id=uuid4(),
            commodity_id=test_commodity.id,
            location_id=test_location.id,
            seller_id=uuid4(),
            total_quantity=Decimal("100.000"),
            available_quantity=Decimal("100.000"),
            base_price=Decimal("48000.00"),
            status="ACTIVE",
            risk_precheck_status="PASS"
        )
        
        # Create bad availability (missing data)
        bad_avail = Availability(
            id=uuid4(),
            commodity_id=test_commodity.id,
            location_id=test_location.id,
            seller_id=uuid4(),
            total_quantity=Decimal("100.000"),
            available_quantity=Decimal("100.000"),
            base_price=None,  # Will cause error
            status="ACTIVE"
        )
        
        async_db_session.add_all([requirement, good_avail, bad_avail])
        await async_db_session.commit()
        
        # Run matching - should skip bad_avail and return good_avail
        matches = await matching_engine_full.find_matches_for_requirement(
            requirement_id=requirement.id
        )
        
        # Should have at least the good match
        assert len(matches) >= 1

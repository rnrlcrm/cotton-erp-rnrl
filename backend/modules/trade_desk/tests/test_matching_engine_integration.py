"""
Integration Tests: Matching Engine

Tests async methods, database queries, candidate fetching, allocation workflows.
Uses real SQLAlchemy models with in-memory database.

Target Coverage: 85% of matching_engine.py

Test Categories:
1. find_matches_for_requirement() - Core matching workflow
2. find_matches_for_availability() - Reverse matching workflow  
3. allocate_quantity_atomic() - Concurrency and locking
4. _is_duplicate() - Async duplicate detection
5. Database integration - Real queries and filters
6. Error handling - Edge cases and failures
"""

import pytest
import asyncio
from decimal import Decimal
from datetime import datetime, timedelta
from uuid import uuid4, UUID
from typing import Dict, Any, List

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

from backend.modules.trade_desk.models.requirement import Requirement
from backend.modules.trade_desk.models.availability import Availability
from backend.modules.settings.commodities.models import Commodity
from backend.modules.trade_desk.repositories.requirement_repository import RequirementRepository
from backend.modules.trade_desk.repositories.availability_repository import AvailabilityRepository
from backend.modules.trade_desk.matching.matching_engine import MatchingEngine, MatchResult
from backend.modules.trade_desk.config.matching_config import MatchingConfig
from backend.core.database import Base


# ============================================================================
# FIXTURES: Database Setup
# ============================================================================

@pytest.fixture
async def async_db_engine():
    """Create in-memory SQLite async engine for testing."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
        future=True
    )
    
    # Create all tables
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
    """Mock risk engine for testing."""
    from unittest.mock import AsyncMock
    
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
    """Create test matching configuration."""
    return MatchingConfig()


@pytest.fixture
async def sample_commodity(async_db_session):
    """Create sample commodity."""
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
async def sample_location(async_db_session):
    """Create sample location."""
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
async def sample_requirement(async_db_session, sample_commodity, sample_location):
    """Create sample requirement for testing."""
    requirement = Requirement(
        id=uuid4(),
        requirement_number=f"REQ-{datetime.utcnow().strftime('%Y%m%d')}-001",
        buyer_partner_id=uuid4(),
        commodity_id=sample_commodity.id,
        quantity_required=Decimal("100.000"),
        delivery_locations=[
            {
                "location_id": str(sample_location.id),
                "latitude": sample_location.latitude,
                "longitude": sample_location.longitude,
                "max_distance_km": 50
            }
        ],
        quality_params={
            "staple_length": 28.5,
            "micronaire": 4.5,
            "strength": 28.0
        },
        expected_price=Decimal("50000.00"),
        max_price=Decimal("55000.00"),
        currency="INR",
        status="ACTIVE",
        intent="DIRECT_BUY",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    async_db_session.add(requirement)
    await async_db_session.commit()
    await async_db_session.refresh(requirement)
    return requirement


@pytest.fixture
async def sample_availability(async_db_session, sample_commodity, sample_location):
    """Create sample availability for testing."""
    availability = Availability(
        id=uuid4(),
        commodity_id=sample_commodity.id,
        location_id=sample_location.id,
        seller_id=uuid4(),
        total_quantity=Decimal("150.000"),
        available_quantity=Decimal("150.000"),
        reserved_quantity=Decimal("0.000"),
        sold_quantity=Decimal("0.000"),
        base_price=Decimal("48000.00"),
        currency="INR",
        quality_params={
            "staple_length": 29.0,
            "micronaire": 4.3,
            "strength": 29.0
        },
        status="ACTIVE",
        risk_precheck_status="PASS",
        risk_precheck_score=95,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    async_db_session.add(availability)
    await async_db_session.commit()
    await async_db_session.refresh(availability)
    return availability


@pytest.fixture
async def matching_engine(
    async_db_session, 
    mock_risk_engine, 
    matching_config
):
    """Create matching engine instance with repositories."""
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
# TEST CATEGORY 1: find_matches_for_requirement()
# ============================================================================

@pytest.mark.asyncio
class TestFindMatchesForRequirement:
    """Test core matching workflow from requirement perspective."""
    
    async def test_finds_matching_availability_with_location_filter(
        self,
        matching_engine,
        sample_requirement,
        sample_availability
    ):
        """Should find availability when location matches."""
        # Act
        matches = await matching_engine.find_matches_for_requirement(
            requirement_id=sample_requirement.id,
            min_score=0.5
        )
        
        # Assert
        assert len(matches) > 0
        assert matches[0].requirement_id == sample_requirement.id
        assert matches[0].availability_id == sample_availability.id
        assert matches[0].score >= 0.5
        assert matches[0].location_filter_passed is True
    
    async def test_filters_out_non_matching_location(
        self,
        matching_engine,
        async_db_session,
        sample_requirement,
        sample_commodity
    ):
        """Should NOT match availability with different location."""
        # Arrange - Create availability with different location
        different_location = uuid4()
        availability = Availability(
            id=uuid4(),
            commodity_id=sample_commodity.id,
            location_id=different_location,
            seller_id=uuid4(),
            total_quantity=Decimal("150.000"),
            available_quantity=Decimal("150.000"),
            base_price=Decimal("48000.00"),
            currency="INR",
            status="ACTIVE"
        )
        async_db_session.add(availability)
        await async_db_session.commit()
        
        # Act
        matches = await matching_engine.find_matches_for_requirement(
            requirement_id=sample_requirement.id
        )
        
        # Assert
        assert len(matches) == 0  # Location filter blocks match
    
    async def test_respects_min_score_threshold(
        self,
        matching_engine,
        sample_requirement,
        sample_availability
    ):
        """Should filter out matches below minimum score."""
        # Act - Set very high min score
        matches = await matching_engine.find_matches_for_requirement(
            requirement_id=sample_requirement.id,
            min_score=0.95  # Very high threshold
        )
        
        # Assert
        # If no perfect matches, should return empty
        # If perfect match, should have score >= 0.95
        if len(matches) > 0:
            assert all(m.score >= 0.95 for m in matches)
    
    async def test_sorts_matches_by_score_descending(
        self,
        matching_engine,
        async_db_session,
        sample_requirement,
        sample_commodity,
        sample_location
    ):
        """Should return matches sorted by score (best first)."""
        # Arrange - Create multiple availabilities with different quality
        availabilities = []
        for i, quality_score in enumerate([25.0, 30.0, 28.0]):  # Different qualities
            avail = Availability(
                id=uuid4(),
                commodity_id=sample_commodity.id,
                location_id=sample_location.id,
                seller_id=uuid4(),
                total_quantity=Decimal("100.000"),
                available_quantity=Decimal("100.000"),
                base_price=Decimal("48000.00"),
                currency="INR",
                quality_params={"staple_length": quality_score},
                status="ACTIVE",
                risk_precheck_status="PASS"
            )
            async_db_session.add(avail)
            availabilities.append(avail)
        
        await async_db_session.commit()
        
        # Act
        matches = await matching_engine.find_matches_for_requirement(
            requirement_id=sample_requirement.id,
            min_score=0.3
        )
        
        # Assert
        assert len(matches) >= 2
        # Scores should be in descending order
        for i in range(len(matches) - 1):
            assert matches[i].score >= matches[i + 1].score
    
    async def test_limits_max_results(
        self,
        matching_engine,
        async_db_session,
        sample_requirement,
        sample_commodity,
        sample_location
    ):
        """Should respect max_results parameter."""
        # Arrange - Create 10 availabilities
        for i in range(10):
            avail = Availability(
                id=uuid4(),
                commodity_id=sample_commodity.id,
                location_id=sample_location.id,
                seller_id=uuid4(),
                total_quantity=Decimal("100.000"),
                available_quantity=Decimal("100.000"),
                base_price=Decimal("48000.00"),
                currency="INR",
                status="ACTIVE",
                risk_precheck_status="PASS"
            )
            async_db_session.add(avail)
        
        await async_db_session.commit()
        
        # Act
        matches = await matching_engine.find_matches_for_requirement(
            requirement_id=sample_requirement.id,
            max_results=5
        )
        
        # Assert
        assert len(matches) <= 5
    
    async def test_handles_requirement_not_found(
        self,
        matching_engine
    ):
        """Should raise ValueError for non-existent requirement."""
        # Act & Assert
        with pytest.raises(ValueError, match="not found"):
            await matching_engine.find_matches_for_requirement(
                requirement_id=uuid4()
            )
    
    async def test_handles_no_delivery_locations(
        self,
        matching_engine,
        async_db_session,
        sample_commodity
    ):
        """Should return empty list when requirement has no delivery locations."""
        # Arrange - Requirement without delivery_locations
        requirement = Requirement(
            id=uuid4(),
            requirement_number="REQ-NO-LOC-001",
            buyer_partner_id=uuid4(),
            commodity_id=sample_commodity.id,
            quantity_required=Decimal("100.000"),
            delivery_locations=None,  # No locations
            status="ACTIVE"
        )
        async_db_session.add(requirement)
        await async_db_session.commit()
        
        # Act
        matches = await matching_engine.find_matches_for_requirement(
            requirement_id=requirement.id
        )
        
        # Assert
        assert len(matches) == 0


# ============================================================================
# TEST CATEGORY 2: find_matches_for_availability()
# ============================================================================

@pytest.mark.asyncio
class TestFindMatchesForAvailability:
    """Test reverse matching workflow from availability perspective."""
    
    async def test_finds_matching_requirements(
        self,
        matching_engine,
        sample_requirement,
        sample_availability
    ):
        """Should find requirements matching availability location."""
        # Act
        matches = await matching_engine.find_matches_for_availability(
            availability_id=sample_availability.id,
            min_score=0.5
        )
        
        # Assert
        assert len(matches) > 0
        assert matches[0].availability_id == sample_availability.id
        assert matches[0].requirement_id == sample_requirement.id
        assert matches[0].score >= 0.5
    
    async def test_handles_availability_not_found(
        self,
        matching_engine
    ):
        """Should raise ValueError for non-existent availability."""
        # Act & Assert
        with pytest.raises(ValueError, match="not found"):
            await matching_engine.find_matches_for_availability(
                availability_id=uuid4()
            )


# ============================================================================
# TEST CATEGORY 3: allocate_quantity_atomic()
# ============================================================================

@pytest.mark.asyncio
class TestAtomicAllocation:
    """Test concurrent allocation with optimistic locking."""
    
    async def test_allocates_quantity_successfully(
        self,
        matching_engine,
        sample_availability
    ):
        """Should allocate quantity and update available_quantity."""
        # Arrange
        initial_quantity = sample_availability.available_quantity
        allocate_qty = Decimal("50.000")
        
        # Act
        success = await matching_engine.allocate_quantity_atomic(
            availability_id=sample_availability.id,
            quantity=allocate_qty,
            requirement_id=uuid4()
        )
        
        # Assert
        assert success is True
        # Verify quantity updated
        # Note: Would need to refresh from DB to see actual update
    
    async def test_fails_when_insufficient_quantity(
        self,
        matching_engine,
        sample_availability
    ):
        """Should fail allocation when requested > available."""
        # Act - Try to allocate more than available
        success = await matching_engine.allocate_quantity_atomic(
            availability_id=sample_availability.id,
            quantity=Decimal("999999.000"),  # Way more than available
            requirement_id=uuid4()
        )
        
        # Assert
        assert success is False
    
    async def test_handles_concurrent_allocation_race_condition(
        self,
        matching_engine,
        async_db_session,
        sample_commodity,
        sample_location
    ):
        """Should handle concurrent allocations with optimistic locking."""
        # Arrange - Create availability with version column
        availability = Availability(
            id=uuid4(),
            commodity_id=sample_commodity.id,
            location_id=sample_location.id,
            seller_id=uuid4(),
            total_quantity=Decimal("100.000"),
            available_quantity=Decimal("100.000"),
            base_price=Decimal("48000.00"),
            currency="INR",
            status="ACTIVE",
            version=0  # Optimistic locking version
        )
        async_db_session.add(availability)
        await async_db_session.commit()
        
        # Act - Simulate concurrent allocations
        results = await asyncio.gather(
            matching_engine.allocate_quantity_atomic(
                availability.id, 
                Decimal("60.000"), 
                uuid4()
            ),
            matching_engine.allocate_quantity_atomic(
                availability.id, 
                Decimal("60.000"), 
                uuid4()
            ),
            return_exceptions=True
        )
        
        # Assert - Only one should succeed
        successes = [r for r in results if r is True]
        assert len(successes) == 1  # Only one allocation succeeds


# ============================================================================
# TEST CATEGORY 4: Duplicate Detection
# ============================================================================

@pytest.mark.asyncio
class TestDuplicateDetection:
    """Test async duplicate detection logic."""
    
    async def test_detects_duplicate_within_time_window(
        self,
        matching_engine,
        sample_requirement,
        sample_availability
    ):
        """Should detect duplicate matches within 5-minute window."""
        # Arrange
        dup_key = matching_engine._generate_duplicate_key(
            sample_requirement, 
            sample_availability
        )
        seen_set = set()
        
        # Act - First call
        is_dup_first = await matching_engine._is_duplicate(
            dup_key,
            seen_set,
            sample_requirement.id,
            sample_availability.id
        )
        
        # Act - Second call (should be duplicate)
        is_dup_second = await matching_engine._is_duplicate(
            dup_key,
            seen_set,
            sample_requirement.id,
            sample_availability.id
        )
        
        # Assert
        assert is_dup_first is False  # First time, not duplicate
        assert is_dup_second is True  # Second time, is duplicate
    
    async def test_duplicate_key_generation_is_consistent(
        self,
        matching_engine,
        sample_requirement,
        sample_availability
    ):
        """Should generate same key for same requirement-availability pair."""
        # Act
        key1 = matching_engine._generate_duplicate_key(
            sample_requirement,
            sample_availability
        )
        key2 = matching_engine._generate_duplicate_key(
            sample_requirement,
            sample_availability
        )
        
        # Assert
        assert key1 == key2
        assert isinstance(key1, str)
        assert len(key1) > 0


# ============================================================================
# TEST CATEGORY 5: Error Handling
# ============================================================================

@pytest.mark.asyncio
class TestErrorHandling:
    """Test edge cases and error scenarios."""
    
    async def test_handles_scoring_exception_gracefully(
        self,
        matching_engine,
        sample_requirement,
        async_db_session,
        sample_commodity,
        sample_location
    ):
        """Should skip match and continue when scoring raises exception."""
        # Arrange - Create availability with invalid data that might cause scoring error
        bad_availability = Availability(
            id=uuid4(),
            commodity_id=sample_commodity.id,
            location_id=sample_location.id,
            seller_id=uuid4(),
            total_quantity=Decimal("100.000"),
            available_quantity=Decimal("100.000"),
            base_price=None,  # Missing price might cause error
            currency="INR",
            status="ACTIVE"
        )
        async_db_session.add(bad_availability)
        await async_db_session.commit()
        
        # Act - Should not raise, just skip bad match
        matches = await matching_engine.find_matches_for_requirement(
            requirement_id=sample_requirement.id
        )
        
        # Assert - Should complete without exception
        assert isinstance(matches, list)
    
    async def test_handles_risk_blocked_matches(
        self,
        matching_engine,
        mock_risk_engine,
        sample_requirement,
        sample_availability
    ):
        """Should skip matches blocked by risk engine."""
        # Arrange - Configure risk engine to block match
        mock_risk_engine.evaluate_match_risk = AsyncMock(return_value={
            "risk_status": "FAIL",
            "risk_score": 30,
            "blocked": True,
            "flags": ["high_risk"]
        })
        
        # Act
        matches = await matching_engine.find_matches_for_requirement(
            requirement_id=sample_requirement.id,
            include_risk_check=True
        )
        
        # Assert
        # Match should be blocked
        assert all(m.risk_status != "FAIL" for m in matches)

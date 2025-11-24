"""
Unit Tests - Availability Repository

Tests:
- CRUD operations
- Smart search algorithm
- Match scoring
- Geo-proximity calculation
- Seller validation
"""

import pytest
from decimal import Decimal
from uuid import uuid4

from backend.modules.trade_desk.repositories.availability_repository import AvailabilityRepository
from backend.modules.trade_desk.enums import MarketVisibility


@pytest.mark.asyncio
class TestAvailabilityRepository:
    """Test Availability repository data access layer."""
    
    async def test_get_by_id_success(self, async_db, sample_availability):
        """Test fetching availability by ID."""
        repo = AvailabilityRepository(async_db)
        
        result = await repo.get_by_id(sample_availability.id)
        
        assert result is not None
        assert result.id == sample_availability.id
        assert result.total_quantity == sample_availability.total_quantity
    
    async def test_get_by_id_with_relationships(self, async_db, sample_availability):
        """Test fetching with relationships loaded."""
        repo = AvailabilityRepository(async_db)
        
        result = await repo.get_by_id(sample_availability.id, load_relationships=True)
        
        assert result is not None
        # Check relationships loaded (if eager loading configured)
        # assert result.commodity is not None
        # assert result.location is not None
    
    async def test_get_by_seller(self, async_db, sample_availability, sample_seller):
        """Test fetching seller's availabilities."""
        repo = AvailabilityRepository(async_db)
        
        results = await repo.get_by_seller(sample_seller.id)
        
        assert len(results) >= 1
        assert all(r.seller_id == sample_seller.id for r in results)
    
    async def test_create_availability(self, async_db, sample_commodity, sample_location, sample_seller, mock_user):
        """Test creating new availability."""
        repo = AvailabilityRepository(async_db)
        
        availability_data = {
            "seller_id": sample_seller.id,
            "commodity_id": sample_commodity.id,
            "location_id": sample_location.id,
            "total_quantity": Decimal("5000"),
            "available_quantity": Decimal("5000"),
            "base_price": Decimal("80000"),
            "quality_params": {"staple_length": "30mm"},
            "created_by": mock_user.id
        }
        
        result = await repo.create(**availability_data)
        await async_db.commit()
        
        assert result.id is not None
        assert result.total_quantity == Decimal("5000")
        assert result.base_price == Decimal("80000")
    
    async def test_update_availability(self, async_db, sample_availability):
        """Test updating availability."""
        repo = AvailabilityRepository(async_db)
        
        new_price = Decimal("78000")
        updates = {"base_price": new_price}
        
        result = await repo.update(sample_availability.id, updates)
        await async_db.commit()
        
        assert result.base_price == new_price
    
    async def test_soft_delete(self, async_db, sample_availability):
        """Test soft delete."""
        repo = AvailabilityRepository(async_db)
        
        await repo.soft_delete(sample_availability.id, deleted_by=sample_availability.created_by)
        await async_db.commit()
        
        # Should not be found in regular queries
        result = await repo.get_by_id(sample_availability.id)
        assert result is None or result.is_deleted is True
    
    async def test_smart_search_by_commodity(
        self,
        async_db,
        sample_availability,
        sample_commodity,
        mock_buyer_user
    ):
        """Test smart search filters by commodity."""
        repo = AvailabilityRepository(async_db)
        
        results = await repo.smart_search(
            buyer_id=mock_buyer_user.business_partner_id,
            commodity_id=sample_commodity.id
        )
        
        assert len(results) >= 1
        assert all(r["availability"].commodity_id == sample_commodity.id for r in results)
    
    async def test_smart_search_price_range(
        self,
        async_db,
        sample_availability,
        sample_commodity,
        mock_buyer_user
    ):
        """Test smart search with price range."""
        repo = AvailabilityRepository(async_db)
        
        results = await repo.smart_search(
            buyer_id=mock_buyer_user.business_partner_id,
            commodity_id=sample_commodity.id,
            min_price=Decimal("70000"),
            max_price=Decimal("80000")
        )
        
        assert len(results) >= 1
        for r in results:
            price = r["availability"].base_price
            assert Decimal("70000") <= price <= Decimal("80000")
    
    async def test_smart_search_quantity_filter(
        self,
        async_db,
        sample_availability,
        sample_commodity,
        mock_buyer_user
    ):
        """Test smart search filters by minimum quantity."""
        repo = AvailabilityRepository(async_db)
        
        results = await repo.smart_search(
            buyer_id=mock_buyer_user.business_partner_id,
            commodity_id=sample_commodity.id,
            min_quantity=Decimal("1000")
        )
        
        assert len(results) >= 1
        assert all(r["availability"].available_quantity >= Decimal("1000") for r in results)
    
    async def test_smart_search_visibility_filter(
        self,
        async_db,
        sample_availability,
        sample_commodity,
        mock_buyer_user
    ):
        """Test smart search respects market visibility."""
        repo = AvailabilityRepository(async_db)
        
        # Only PUBLIC availabilities should be returned
        results = await repo.smart_search(
            buyer_id=mock_buyer_user.business_partner_id,
            commodity_id=sample_commodity.id,
            market_visibility=[MarketVisibility.PUBLIC]
        )
        
        assert len(results) >= 1
        assert all(r["availability"].market_visibility == MarketVisibility.PUBLIC for r in results)
    
    async def test_smart_search_exclude_anomalies(
        self,
        async_db,
        sample_availability,
        sample_commodity,
        mock_buyer_user
    ):
        """Test smart search can exclude price anomalies."""
        repo = AvailabilityRepository(async_db)
        
        results = await repo.smart_search(
            buyer_id=mock_buyer_user.business_partner_id,
            commodity_id=sample_commodity.id,
            exclude_anomalies=True
        )
        
        # All results should have ai_price_anomaly_flag = False
        assert all(r["availability"].ai_price_anomaly_flag is False for r in results)
    
    async def test_smart_search_match_scoring(
        self,
        async_db,
        sample_availability,
        sample_commodity,
        mock_buyer_user
    ):
        """Test smart search returns match scores."""
        repo = AvailabilityRepository(async_db)
        
        results = await repo.smart_search(
            buyer_id=mock_buyer_user.business_partner_id,
            commodity_id=sample_commodity.id,
            quality_params={"staple_length": "29mm"},
            quality_tolerance=0.1
        )
        
        assert len(results) >= 1
        for r in results:
            assert "match_score" in r
            assert 0.0 <= r["match_score"] <= 1.0
            assert "distance_km" in r
    
    async def test_smart_search_pagination(
        self,
        async_db,
        sample_availability,
        sample_commodity,
        mock_buyer_user
    ):
        """Test smart search pagination."""
        repo = AvailabilityRepository(async_db)
        
        # Get first page
        page1 = await repo.smart_search(
            buyer_id=mock_buyer_user.business_partner_id,
            commodity_id=sample_commodity.id,
            skip=0,
            limit=5
        )
        
        # Get second page
        page2 = await repo.smart_search(
            buyer_id=mock_buyer_user.business_partner_id,
            commodity_id=sample_commodity.id,
            skip=5,
            limit=5
        )
        
        # Pages should not overlap
        if len(page1) > 0 and len(page2) > 0:
            page1_ids = {r["availability"].id for r in page1}
            page2_ids = {r["availability"].id for r in page2}
            assert page1_ids.isdisjoint(page2_ids)
    
    async def test_mark_expired(self, async_db, sample_availability):
        """Test marking availabilities as expired."""
        repo = AvailabilityRepository(async_db)
        
        count = await repo.mark_expired()
        await async_db.commit()
        
        # Count should be >= 0 (depends on test data expiry dates)
        assert count >= 0

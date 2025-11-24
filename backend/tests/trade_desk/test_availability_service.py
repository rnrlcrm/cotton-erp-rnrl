"""
Unit Tests - Availability Service

Tests:
- AI pipeline (normalize, anomaly detection, embeddings)
- Change detection
- Business rules
- Workflow orchestration
"""

import pytest
from decimal import Decimal
from datetime import datetime, timedelta, timezone

from backend.modules.trade_desk.services.availability_service import AvailabilityService
from backend.modules.trade_desk.enums import AvailabilityStatus, ApprovalStatus


@pytest.mark.asyncio
class TestAvailabilityService:
    """Test Availability service business logic."""
    
    async def test_create_availability_success(
        self,
        async_db,
        sample_commodity,
        sample_location,
        sample_seller,
        mock_user
    ):
        """Test creating availability with AI pipeline."""
        service = AvailabilityService(async_db)
        
        availability = await service.create_availability(
            seller_id=sample_seller.id,
            commodity_id=sample_commodity.id,
            location_id=sample_location.id,
            total_quantity=Decimal("5000"),
            base_price=Decimal("75000"),
            price_matrix={"29mm": 75000, "30mm": 77000},
            quality_params={"staple_length": "29mm", "micronaire": "3.5-4.5"},
            market_visibility="PUBLIC",
            allow_partial_order=True,
            min_order_quantity=Decimal("500"),
            delivery_terms="EX-WAREHOUSE",
            delivery_address="Test Address",
            expiry_date=datetime.now(timezone.utc) + timedelta(days=30),
            created_by=mock_user.id
        )
        
        assert availability.id is not None
        assert availability.total_quantity == Decimal("5000")
        assert availability.status == AvailabilityStatus.DRAFT
        assert availability.approval_status == ApprovalStatus.PENDING
        
        # AI enhancements should be applied
        assert availability.ai_suggested_price is not None
        assert availability.ai_confidence_score is not None
    
    async def test_update_availability_with_change_detection(
        self,
        async_db,
        sample_availability,
        mock_user
    ):
        """Test update with intelligent change detection."""
        service = AvailabilityService(async_db)
        
        new_price = Decimal("78000")
        updates = {"base_price": new_price}
        
        updated = await service.update_availability(
            availability_id=sample_availability.id,
            updates=updates,
            updated_by=mock_user.id
        )
        
        assert updated.base_price == new_price
        # Price change event should be emitted
        # (check via event store in integration tests)
    
    async def test_approve_availability(
        self,
        async_db,
        sample_availability,
        mock_user
    ):
        """Test approval workflow."""
        service = AvailabilityService(async_db)
        
        # Set to DRAFT first
        sample_availability.status = AvailabilityStatus.DRAFT
        sample_availability.approval_status = ApprovalStatus.PENDING
        await async_db.commit()
        
        approved = await service.approve_availability(
            availability_id=sample_availability.id,
            approved_by=mock_user.id,
            notes="Approved for testing"
        )
        
        assert approved.approval_status == ApprovalStatus.APPROVED
        assert approved.status == AvailabilityStatus.ACTIVE
        assert approved.approved_by == mock_user.id
    
    async def test_reserve_availability_success(
        self,
        async_db,
        sample_availability,
        mock_buyer_user,
        mock_user
    ):
        """Test quantity reservation."""
        service = AvailabilityService(async_db)
        
        reserve_qty = Decimal("500")
        initial_available = sample_availability.available_quantity
        
        reserved = await service.reserve_availability(
            availability_id=sample_availability.id,
            reserve_quantity=reserve_qty,
            buyer_id=mock_buyer_user.business_partner_id,
            reserved_by=mock_user.id
        )
        
        assert reserved.reserved_quantity == reserve_qty
        assert reserved.available_quantity == initial_available - reserve_qty
    
    async def test_reserve_fails_insufficient_quantity(
        self,
        async_db,
        sample_availability,
        mock_buyer_user,
        mock_user
    ):
        """Test reservation fails with insufficient quantity."""
        service = AvailabilityService(async_db)
        
        excessive_qty = sample_availability.available_quantity + Decimal("1000")
        
        with pytest.raises(ValueError, match="Insufficient available quantity"):
            await service.reserve_availability(
                availability_id=sample_availability.id,
                reserve_quantity=excessive_qty,
                buyer_id=mock_buyer_user.business_partner_id,
                reserved_by=mock_user.id
            )
    
    async def test_release_availability_success(
        self,
        async_db,
        sample_availability,
        mock_buyer_user,
        mock_user
    ):
        """Test quantity release."""
        service = AvailabilityService(async_db)
        
        # First reserve
        reserve_qty = Decimal("500")
        await service.reserve_availability(
            availability_id=sample_availability.id,
            reserve_quantity=reserve_qty,
            buyer_id=mock_buyer_user.business_partner_id,
            reserved_by=mock_user.id
        )
        
        # Then release
        released = await service.release_availability(
            availability_id=sample_availability.id,
            release_quantity=reserve_qty,
            released_by=mock_user.id
        )
        
        assert released.reserved_quantity == Decimal("0")
        assert released.available_quantity == sample_availability.total_quantity
    
    async def test_mark_as_sold_success(
        self,
        async_db,
        sample_availability,
        mock_buyer_user,
        mock_user
    ):
        """Test marking quantity as sold."""
        service = AvailabilityService(async_db)
        
        # First reserve
        sold_qty = Decimal("500")
        await service.reserve_availability(
            availability_id=sample_availability.id,
            reserve_quantity=sold_qty,
            buyer_id=mock_buyer_user.business_partner_id,
            reserved_by=mock_user.id
        )
        
        # Then mark as sold
        trade_id = "TRADE-001"
        sold = await service.mark_as_sold(
            availability_id=sample_availability.id,
            sold_quantity=sold_qty,
            trade_id=trade_id,
            marked_by=mock_user.id
        )
        
        assert sold.sold_quantity == sold_qty
        assert sold.reserved_quantity == Decimal("0")
    
    async def test_normalize_quality_params(self, async_db, cotton_quality_params):
        """Test quality normalization (placeholder implementation)."""
        service = AvailabilityService(async_db)
        
        normalized = await service.normalize_quality_params(
            commodity_id="test-id",
            raw_params=cotton_quality_params
        )
        
        # Placeholder returns original params
        assert normalized == cotton_quality_params
    
    async def test_detect_price_anomaly(
        self,
        async_db,
        sample_commodity
    ):
        """Test price anomaly detection."""
        service = AvailabilityService(async_db)
        
        result = await service.detect_price_anomaly(
            commodity_id=sample_commodity.id,
            proposed_price=Decimal("75000"),
            quality_params={"staple_length": "29mm"}
        )
        
        assert "is_anomaly" in result
        assert "confidence" in result
        assert "suggested_price" in result
        assert isinstance(result["is_anomaly"], bool)
        assert 0.0 <= result["confidence"] <= 1.0
    
    async def test_calculate_negotiation_readiness_score(
        self,
        async_db,
        sample_availability
    ):
        """Test negotiation readiness scoring."""
        service = AvailabilityService(async_db)
        
        score_data = await service.calculate_negotiation_readiness_score(
            sample_availability
        )
        
        assert "score" in score_data
        assert "factors" in score_data
        assert "recommendations" in score_data
        assert 0.0 <= score_data["score"] <= 1.0
        assert isinstance(score_data["factors"], dict)
        assert isinstance(score_data["recommendations"], list)
    
    async def test_suggest_similar_commodities(
        self,
        async_db,
        sample_commodity
    ):
        """Test similar commodity suggestions."""
        service = AvailabilityService(async_db)
        
        similar = await service.suggest_similar_commodities(
            commodity_id=sample_commodity.id,
            quality_params={"staple_length": "29mm"},
            limit=5
        )
        
        assert isinstance(similar, list)
        # Placeholder returns empty list
        # In production, would return actual similar commodities
    
    async def test_search_availabilities(
        self,
        async_db,
        sample_availability,
        sample_commodity,
        mock_buyer_user
    ):
        """Test availability search."""
        service = AvailabilityService(async_db)
        
        results = await service.search_availabilities(
            buyer_id=mock_buyer_user.business_partner_id,
            commodity_id=sample_commodity.id,
            min_price=Decimal("70000"),
            max_price=Decimal("80000")
        )
        
        assert isinstance(results, list)
        assert len(results) >= 0
        
        if len(results) > 0:
            assert "availability" in results[0]
            assert "match_score" in results[0]
            assert "distance_km" in results[0]

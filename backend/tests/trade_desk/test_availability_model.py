"""
Unit Tests - Availability Model

Tests:
- Event emission (created, updated, reserved, released, sold)
- Business logic (reserve, release, mark_sold)
- Status transitions
- Validation rules
"""

import pytest
from decimal import Decimal
from datetime import datetime, timezone

from backend.modules.trade_desk.models.availability import Availability
from backend.modules.trade_desk.enums import AvailabilityStatus
from backend.modules.trade_desk.events.availability_events import (
    AvailabilityCreatedEvent,
    AvailabilityReservedEvent,
    AvailabilityReleasedEvent,
    AvailabilitySoldEvent
)


@pytest.mark.asyncio
class TestAvailabilityModel:
    """Test Availability domain model."""
    
    async def test_create_availability_emits_event(self, async_db, sample_commodity, sample_location, sample_seller, mock_user):
        """Test that creating availability emits AvailabilityCreatedEvent."""
        availability = Availability(
            seller_id=sample_seller.id,
            commodity_id=sample_commodity.id,
            location_id=sample_location.id,
            total_quantity=Decimal("1000"),
            available_quantity=Decimal("1000"),
            base_price=Decimal("75000"),
            quality_params={"staple_length": "29mm"},
            created_by=mock_user.id
        )
        
        # Trigger event emission
        availability.emit_created_event()
        
        # Verify event in pending_events
        assert len(availability.pending_events) == 1
        event = availability.pending_events[0]
        assert isinstance(event, AvailabilityCreatedEvent)
        assert event.availability_id == availability.id
        assert event.seller_id == sample_seller.id
        assert event.total_quantity == Decimal("1000")
    
    async def test_reserve_quantity_success(self, sample_availability, mock_buyer_user):
        """Test successful quantity reservation."""
        initial_available = sample_availability.available_quantity
        reserve_qty = Decimal("500")
        
        # Reserve quantity
        sample_availability.reserve(
            quantity=reserve_qty,
            buyer_id=mock_buyer_user.business_partner_id
        )
        
        # Verify quantities updated
        assert sample_availability.available_quantity == initial_available - reserve_qty
        assert sample_availability.reserved_quantity == reserve_qty
        
        # Verify event emitted
        assert len(sample_availability.pending_events) >= 1
        reserved_events = [e for e in sample_availability.pending_events if isinstance(e, AvailabilityReservedEvent)]
        assert len(reserved_events) == 1
        assert reserved_events[0].reserved_quantity == reserve_qty
    
    async def test_reserve_quantity_insufficient(self, sample_availability, mock_buyer_user):
        """Test reservation fails when insufficient quantity."""
        excessive_qty = sample_availability.available_quantity + Decimal("1000")
        
        with pytest.raises(ValueError, match="Insufficient available quantity"):
            sample_availability.reserve(
                quantity=excessive_qty,
                buyer_id=mock_buyer_user.business_partner_id
            )
    
    async def test_release_quantity_success(self, sample_availability, mock_buyer_user):
        """Test successful quantity release."""
        # First reserve
        reserve_qty = Decimal("500")
        sample_availability.reserve(reserve_qty, mock_buyer_user.business_partner_id)
        sample_availability.pending_events.clear()  # Clear reserve event
        
        initial_available = sample_availability.available_quantity
        
        # Then release
        sample_availability.release(quantity=reserve_qty)
        
        # Verify quantities updated
        assert sample_availability.available_quantity == initial_available + reserve_qty
        assert sample_availability.reserved_quantity == Decimal("0")
        
        # Verify event emitted
        release_events = [e for e in sample_availability.pending_events if isinstance(e, AvailabilityReleasedEvent)]
        assert len(release_events) == 1
        assert release_events[0].released_quantity == reserve_qty
    
    async def test_mark_sold_success(self, sample_availability):
        """Test successfully marking quantity as sold."""
        # First reserve
        sold_qty = Decimal("500")
        sample_availability.reserve(sold_qty, sample_availability.seller_id)
        sample_availability.pending_events.clear()
        
        initial_available = sample_availability.available_quantity
        initial_reserved = sample_availability.reserved_quantity
        
        # Mark as sold
        trade_id = "TRADE-001"
        sample_availability.mark_sold(quantity=sold_qty, trade_id=trade_id)
        
        # Verify quantities updated
        assert sample_availability.sold_quantity == sold_qty
        assert sample_availability.reserved_quantity == initial_reserved - sold_qty
        
        # Verify event emitted
        sold_events = [e for e in sample_availability.pending_events if isinstance(e, AvailabilitySoldEvent)]
        assert len(sold_events) == 1
        assert sold_events[0].sold_quantity == sold_qty
        assert sold_events[0].trade_id == trade_id
    
    async def test_status_transition_to_sold_out(self, sample_availability):
        """Test status automatically changes to SOLD_OUT when fully sold."""
        # Reserve and sell entire quantity
        total_qty = sample_availability.total_quantity
        sample_availability.reserve(total_qty, sample_availability.seller_id)
        sample_availability.mark_sold(total_qty, "TRADE-001")
        
        # Status should be SOLD_OUT
        assert sample_availability.status == AvailabilityStatus.SOLD_OUT
        assert sample_availability.available_quantity == Decimal("0")
        assert sample_availability.sold_quantity == total_qty
    
    async def test_partial_orders_allowed(self, sample_availability):
        """Test partial order logic."""
        assert sample_availability.allow_partial_order is True
        assert sample_availability.min_order_quantity == Decimal("500")
        
        # Reserving below minimum should be validated by service layer
        # Model just tracks quantities
    
    async def test_price_matrix_storage(self, sample_availability):
        """Test JSONB price_matrix storage."""
        price_matrix = sample_availability.price_matrix
        
        assert isinstance(price_matrix, dict)
        assert "29mm" in price_matrix
        assert price_matrix["29mm"] == 75000
        assert price_matrix["30mm"] == 77000
    
    async def test_quality_params_storage(self, sample_availability):
        """Test JSONB quality_params storage."""
        quality_params = sample_availability.quality_params
        
        assert isinstance(quality_params, dict)
        assert "staple_length" in quality_params
        assert quality_params["staple_length"] == "29mm"
        assert "micronaire" in quality_params

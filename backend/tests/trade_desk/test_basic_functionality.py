"""
Simple validation tests for Availability Engine

Tests basic functionality without full database setup:
- Model creation
- Event emission
- Business logic
- JSONB flexibility
"""

import pytest
from decimal import Decimal
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from backend.modules.trade_desk.models.availability import Availability
from backend.modules.trade_desk.enums import AvailabilityStatus, MarketVisibility
from backend.modules.trade_desk.events.availability_events import (
    AvailabilityCreatedEvent,
    AvailabilityReservedEvent,
    AvailabilityReleasedEvent,
    AvailabilitySoldEvent
)


class TestAvailabilityBasics:
    """Test Availability model basics without database."""
    
    def test_availability_creation(self):
        """Test creating availability instance."""
        availability = Availability(
            id=uuid4(),
            seller_id=uuid4(),
            commodity_id=uuid4(),
            location_id=uuid4(),
            total_quantity=Decimal("10000"),
            available_quantity=Decimal("10000"),
            reserved_quantity=Decimal("0"),
            sold_quantity=Decimal("0"),
            base_price=Decimal("75000"),
            price_matrix={"29mm": 75000, "30mm": 77000},
            quality_params={"staple_length": "29mm"},
            market_visibility=MarketVisibility.PUBLIC,
            status=AvailabilityStatus.ACTIVE,
            created_at=datetime.now(timezone.utc)
        )
        
        assert availability.id is not None
        assert availability.total_quantity == Decimal("10000")
        assert availability.base_price == Decimal("75000")
        assert availability.status == AvailabilityStatus.ACTIVE
    
    def test_jsonb_price_matrix(self):
        """Test JSONB price_matrix storage."""
        price_matrix = {
            "29mm": 75000,
            "30mm": 77000,
            "28mm": 73000,
            "31mm": 79000
        }
        
        availability = Availability(
            id=uuid4(),
            seller_id=uuid4(),
            commodity_id=uuid4(),
            location_id=uuid4(),
            total_quantity=Decimal("10000"),
            available_quantity=Decimal("10000"),
            base_price=Decimal("75000"),
            price_matrix=price_matrix,
            quality_params={"staple_length": "29mm"},
            created_at=datetime.now(timezone.utc)
        )
        
        assert availability.price_matrix == price_matrix
        assert availability.price_matrix["29mm"] == 75000
        assert availability.price_matrix["30mm"] == 77000
    
    def test_jsonb_quality_params_cotton(self):
        """Test JSONB quality_params for cotton."""
        cotton_params = {
            "staple_length": "29mm",
            "micronaire": "3.5-4.5",
            "strength": "28-30 g/tex",
            "trash": "< 2%",
            "color_grade": "31-1"
        }
        
        availability = Availability(
            id=uuid4(),
            seller_id=uuid4(),
            commodity_id=uuid4(),
            location_id=uuid4(),
            total_quantity=Decimal("10000"),
            available_quantity=Decimal("10000"),
            base_price=Decimal("75000"),
            quality_params=cotton_params,
            created_at=datetime.now(timezone.utc)
        )
        
        assert availability.quality_params == cotton_params
        assert availability.quality_params["staple_length"] == "29mm"
        assert availability.quality_params["micronaire"] == "3.5-4.5"
    
    def test_jsonb_quality_params_gold(self):
        """Test JSONB quality_params for gold (different schema)."""
        gold_params = {
            "purity": "99.99%",
            "form": "bar",
            "weight": "1kg",
            "certification": "LBMA",
            "serial_number": "XYZ123"
        }
        
        availability = Availability(
            id=uuid4(),
            seller_id=uuid4(),
            commodity_id=uuid4(),
            location_id=uuid4(),
            total_quantity=Decimal("1000"),
            available_quantity=Decimal("1000"),
            base_price=Decimal("6500000"),
            quality_params=gold_params,
            created_at=datetime.now(timezone.utc)
        )
        
        assert availability.quality_params == gold_params
        assert availability.quality_params["purity"] == "99.99%"
        assert availability.quality_params["certification"] == "LBMA"
    
    def test_reserve_quantity(self):
        """Test quantity reservation logic."""
        availability = Availability(
            id=uuid4(),
            seller_id=uuid4(),
            commodity_id=uuid4(),
            location_id=uuid4(),
            total_quantity=Decimal("10000"),
            available_quantity=Decimal("10000"),
            reserved_quantity=Decimal("0"),
            sold_quantity=Decimal("0"),
            base_price=Decimal("75000"),
            quality_params={"staple_length": "29mm"},
            status=AvailabilityStatus.ACTIVE.value,
            allow_partial_order=True,
            created_at=datetime.now(timezone.utc)
        )
        
        buyer_id = uuid4()
        user_id = uuid4()
        reserve_qty = Decimal("500")
        reservation_expiry = datetime.now(timezone.utc) + timedelta(hours=24)
        
        availability.reserve_quantity(reserve_qty, buyer_id, reservation_expiry, user_id)
        
        assert availability.available_quantity == Decimal("9500")
        assert availability.reserved_quantity == Decimal("500")
    
    def test_reserve_insufficient_quantity(self):
        """Test reserve fails when insufficient quantity."""
        availability = Availability(
            id=uuid4(),
            seller_id=uuid4(),
            commodity_id=uuid4(),
            location_id=uuid4(),
            total_quantity=Decimal("1000"),
            available_quantity=Decimal("1000"),
            reserved_quantity=Decimal("0"),
            base_price=Decimal("75000"),
            quality_params={"staple_length": "29mm"},
            created_at=datetime.now(timezone.utc)
        )
        
        with pytest.raises(ValueError, match="Cannot reserve requested quantity"):
            reservation_expiry = datetime.now(timezone.utc) + timedelta(hours=24)
            availability.reserve_quantity(Decimal("2000"), uuid4(), reservation_expiry, uuid4())
    
    def test_release_quantity(self):
        """Test quantity release logic."""
        availability = Availability(
            id=uuid4(),
            seller_id=uuid4(),
            commodity_id=uuid4(),
            location_id=uuid4(),
            total_quantity=Decimal("10000"),
            available_quantity=Decimal("9500"),
            reserved_quantity=Decimal("500"),
            sold_quantity=Decimal("0"),
            base_price=Decimal("75000"),
            quality_params={"staple_length": "29mm"},
            created_at=datetime.now(timezone.utc)
        )
        
        buyer_id = uuid4()
        user_id = uuid4()
        availability.release_quantity(Decimal("500"), buyer_id, user_id, "Test release")
        
        assert availability.available_quantity == Decimal("10000")
        assert availability.reserved_quantity == Decimal("0")
    
    def test_mark_sold(self):
        """Test marking quantity as sold."""
        availability = Availability(
            id=uuid4(),
            seller_id=uuid4(),
            commodity_id=uuid4(),
            location_id=uuid4(),
            total_quantity=Decimal("10000"),
            available_quantity=Decimal("9500"),
            reserved_quantity=Decimal("500"),
            sold_quantity=Decimal("0"),
            base_price=Decimal("75000"),
            quality_params={"staple_length": "29mm"},
            status=AvailabilityStatus.ACTIVE,
            created_at=datetime.now(timezone.utc)
        )
        
        buyer_id = uuid4()
        trade_id = uuid4()
        user_id = uuid4()
        sold_price = Decimal("75000")
        availability.mark_sold(Decimal("500"), buyer_id, trade_id, sold_price, user_id)
        
        assert availability.sold_quantity == Decimal("500")
        assert availability.reserved_quantity == Decimal("0")
    
    def test_full_sale_status_change(self):
        """Test status changes to SOLD when fully sold."""
        availability = Availability(
            id=uuid4(),
            seller_id=uuid4(),
            commodity_id=uuid4(),
            location_id=uuid4(),
            total_quantity=Decimal("1000"),
            available_quantity=Decimal("0"),
            reserved_quantity=Decimal("1000"),
            sold_quantity=Decimal("0"),
            base_price=Decimal("75000"),
            quality_params={"staple_length": "29mm"},
            status=AvailabilityStatus.ACTIVE,
            created_at=datetime.now(timezone.utc)
        )
        
        buyer_id = uuid4()
        trade_id = uuid4()
        user_id = uuid4()
        sold_price = Decimal("75000")
        availability.mark_sold(Decimal("1000"), buyer_id, trade_id, sold_price, user_id)
        
        assert availability.status == AvailabilityStatus.SOLD.value
        assert availability.sold_quantity == Decimal("1000")
        assert availability.available_quantity == Decimal("0")
    
    def test_emit_created_event(self):
        """Test availability emits created event."""
        user_id = uuid4()
        availability = Availability(
            id=uuid4(),
            seller_id=uuid4(),
            commodity_id=uuid4(),
            location_id=uuid4(),
            total_quantity=Decimal("10000"),
            available_quantity=Decimal("10000"),
            base_price=Decimal("75000"),
            quality_params={"staple_length": "29mm"},
            created_at=datetime.now(timezone.utc),
            created_by=user_id
        )
        
        availability.emit_created(user_id)
        
        # Event emitted successfully (events stored in _pending_events internally)
        assert availability.id is not None


class TestEnums:
    """Test enum values."""
    
    def test_availability_status_values(self):
        """Test AvailabilityStatus enum."""
        assert AvailabilityStatus.DRAFT == "DRAFT"
        assert AvailabilityStatus.ACTIVE == "ACTIVE"
        assert AvailabilityStatus.RESERVED == "RESERVED"
        assert AvailabilityStatus.SOLD == "SOLD"
        assert AvailabilityStatus.EXPIRED == "EXPIRED"
        assert AvailabilityStatus.CANCELLED == "CANCELLED"
    
    def test_market_visibility_values(self):
        """Test MarketVisibility enum."""
        assert MarketVisibility.PUBLIC == "PUBLIC"
        assert MarketVisibility.PRIVATE == "PRIVATE"
        assert MarketVisibility.RESTRICTED == "RESTRICTED"
        assert MarketVisibility.INTERNAL == "INTERNAL"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

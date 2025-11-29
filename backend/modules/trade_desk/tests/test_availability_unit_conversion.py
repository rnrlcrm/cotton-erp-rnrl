"""
Test Suite: Availability Engine Unit Conversion Integration

Tests the integration between:
1. Commodity Master unit conversion (CANDY = 355.6222 KG)
2. Availability Engine quantity_unit field
3. Auto-conversion to base_unit for matching

Critical Tests:
- Create availability with CANDY unit → auto-converts to KG
- Create availability with BALE unit → auto-converts to KG
- Quality parameter validation (min/max checking)
- Mandatory parameter enforcement
- Test report URL storage
- Media URL storage
- Location validation (ANY location allowed)
"""

import pytest
from decimal import Decimal
from uuid import uuid4

from backend.modules.trade_desk.services.availability_service import AvailabilityService
from backend.modules.commodity_master.services.unit_converter import UnitConverter


@pytest.mark.asyncio
class TestAvailabilityUnitConversion:
    """Test unit conversion integration with Commodity Master"""
    
    async def test_create_availability_with_candy_unit_converts_to_kg(
        self,
        db_session,
        sample_commodity,
        sample_seller,
        sample_location
    ):
        """
        Test: Create availability with CANDY unit → auto-converts to KG
        
        Given: Commodity with base_unit=KG, seller, location
        When: Create availability with quantity=100 CANDY
        Then: quantity_in_base_unit = 100 * 355.6222 = 35562.22 KG
        """
        service = AvailabilityService(db_session)
        
        # Create availability with CANDY unit
        availability = await service.create_availability(
            seller_id=sample_seller.id,
            commodity_id=sample_commodity.id,
            location_id=sample_location.id,
            total_quantity=Decimal("100.0"),
            quantity_unit="CANDY",
            base_price=Decimal("8000.0"),
            price_unit="per CANDY",
            quality_params={"length": 29.0, "strength": 26.0},
            created_by=uuid4(),
            auto_approve=True
        )
        
        # Verify unit conversion
        assert availability.quantity_unit == "CANDY"
        assert availability.quantity_in_base_unit is not None
        
        # Verify conversion: 100 CANDY * 355.6222 = 35562.22 KG
        expected = Decimal("100.0") * Decimal("355.6222")
        assert abs(availability.quantity_in_base_unit - expected) < Decimal("0.01")
        
        # Verify price conversion
        assert availability.price_unit == "per CANDY"
        assert availability.price_per_base_unit is not None
        
        # Verify price conversion: ₹8000 per CANDY / 355.6222 = ₹22.50 per KG
        expected_price = Decimal("8000.0") / Decimal("355.6222")
        assert abs(availability.price_per_base_unit - expected_price) < Decimal("0.01")
    
    async def test_create_availability_with_bale_unit_converts_to_kg(
        self,
        db_session,
        sample_commodity,
        sample_seller,
        sample_location
    ):
        """
        Test: Create availability with BALE unit → auto-converts to KG
        
        Given: Commodity with base_unit=KG
        When: Create availability with quantity=50 BALE
        Then: quantity_in_base_unit = 50 * 170 = 8500 KG (assuming BALE=170 KG)
        """
        service = AvailabilityService(db_session)
        
        availability = await service.create_availability(
            seller_id=sample_seller.id,
            commodity_id=sample_commodity.id,
            location_id=sample_location.id,
            total_quantity=Decimal("50.0"),
            quantity_unit="BALE",
            base_price=Decimal("12000.0"),
            price_unit="per BALE",
            quality_params={"length": 29.0, "strength": 26.0},
            created_by=uuid4(),
            auto_approve=True
        )
        
        assert availability.quantity_unit == "BALE"
        assert availability.quantity_in_base_unit is not None
        
        # Verify conversion (BALE varies by region, check actual conversion)
        conversion_factor = UnitConverter.get_conversion_factor("BALE", "KG")
        expected = Decimal("50.0") * Decimal(str(conversion_factor))
        assert abs(availability.quantity_in_base_unit - expected) < Decimal("0.01")
    
    async def test_quality_parameter_validation_min_max(
        self,
        db_session,
        sample_commodity_with_parameters,
        sample_seller,
        sample_location
    ):
        """
        Test: Quality parameter validation against min/max constraints
        
        Given: Commodity with parameter constraints (length: 27-32mm)
        When: Create availability with length=25mm (below min)
        Then: Raise ValueError
        """
        service = AvailabilityService(db_session)
        
        # Test: Value below minimum
        with pytest.raises(ValueError, match="below minimum"):
            await service.create_availability(
                seller_id=sample_seller.id,
                commodity_id=sample_commodity_with_parameters.id,
                location_id=sample_location.id,
                total_quantity=Decimal("100.0"),
                quantity_unit="CANDY",
                quality_params={"length": 25.0},  # Below min=27
                created_by=uuid4()
            )
        
        # Test: Value above maximum
        with pytest.raises(ValueError, match="exceeds maximum"):
            await service.create_availability(
                seller_id=sample_seller.id,
                commodity_id=sample_commodity_with_parameters.id,
                location_id=sample_location.id,
                total_quantity=Decimal("100.0"),
                quantity_unit="CANDY",
                quality_params={"length": 35.0},  # Above max=32
                created_by=uuid4()
            )
        
        # Test: Valid value
        availability = await service.create_availability(
            seller_id=sample_seller.id,
            commodity_id=sample_commodity_with_parameters.id,
            location_id=sample_location.id,
            total_quantity=Decimal("100.0"),
            quantity_unit="CANDY",
            quality_params={"length": 29.0},  # Within 27-32 range
            created_by=uuid4(),
            auto_approve=True
        )
        
        assert availability.quality_params["length"] == 29.0
    
    async def test_mandatory_parameter_enforcement(
        self,
        db_session,
        sample_commodity_with_mandatory_params,
        sample_seller,
        sample_location
    ):
        """
        Test: Mandatory parameter enforcement
        
        Given: Commodity with mandatory parameters (length, strength)
        When: Create availability without mandatory parameters
        Then: Raise ValueError with parameter list
        """
        service = AvailabilityService(db_session)
        
        # Test: Missing mandatory parameters
        with pytest.raises(ValueError, match="Mandatory parameter"):
            await service.create_availability(
                seller_id=sample_seller.id,
                commodity_id=sample_commodity_with_mandatory_params.id,
                location_id=sample_location.id,
                total_quantity=Decimal("100.0"),
                quantity_unit="CANDY",
                quality_params=None,  # Missing mandatory params
                created_by=uuid4()
            )
        
        # Test: Partial mandatory parameters
        with pytest.raises(ValueError, match="Mandatory parameter"):
            await service.create_availability(
                seller_id=sample_seller.id,
                commodity_id=sample_commodity_with_mandatory_params.id,
                location_id=sample_location.id,
                total_quantity=Decimal("100.0"),
                quantity_unit="CANDY",
                quality_params={"length": 29.0},  # Missing 'strength'
                created_by=uuid4()
            )
        
        # Test: All mandatory parameters provided
        availability = await service.create_availability(
            seller_id=sample_seller.id,
            commodity_id=sample_commodity_with_mandatory_params.id,
            location_id=sample_location.id,
            total_quantity=Decimal("100.0"),
            quantity_unit="CANDY",
            quality_params={
                "length": 29.0,
                "strength": 26.0
            },
            created_by=uuid4(),
            auto_approve=True
        )
        
        assert availability.quality_params["length"] == 29.0
        assert availability.quality_params["strength"] == 26.0
    
    async def test_test_report_url_storage(
        self,
        db_session,
        sample_commodity,
        sample_seller,
        sample_location
    ):
        """
        Test: Test report URL storage
        
        Given: Valid test report URL
        When: Create availability with test_report_url
        Then: URL stored, test_report_verified=False, test_report_data placeholder
        """
        service = AvailabilityService(db_session)
        
        availability = await service.create_availability(
            seller_id=sample_seller.id,
            commodity_id=sample_commodity.id,
            location_id=sample_location.id,
            total_quantity=Decimal("100.0"),
            quantity_unit="CANDY",
            quality_params={"length": 29.0},
            test_report_url="https://storage.example.com/test-reports/abc123.pdf",
            created_by=uuid4(),
            auto_approve=True
        )
        
        assert availability.test_report_url == "https://storage.example.com/test-reports/abc123.pdf"
        assert availability.test_report_verified is False
        assert availability.test_report_data is not None
        assert "source" in availability.test_report_data
    
    async def test_media_url_storage(
        self,
        db_session,
        sample_commodity,
        sample_seller,
        sample_location
    ):
        """
        Test: Media URL storage (photos/videos)
        
        Given: Photo and video URLs
        When: Create availability with media_urls
        Then: URLs stored, ai_detected_params placeholder
        """
        service = AvailabilityService(db_session)
        
        media_urls = {
            "photos": [
                "https://storage.example.com/photos/cotton1.jpg",
                "https://storage.example.com/photos/cotton2.jpg"
            ],
            "videos": [
                "https://storage.example.com/videos/cotton_demo.mp4"
            ]
        }
        
        availability = await service.create_availability(
            seller_id=sample_seller.id,
            commodity_id=sample_commodity.id,
            location_id=sample_location.id,
            total_quantity=Decimal("100.0"),
            quantity_unit="CANDY",
            quality_params={"length": 29.0},
            media_urls=media_urls,
            created_by=uuid4(),
            auto_approve=True
        )
        
        assert availability.media_urls == media_urls
        assert len(availability.media_urls["photos"]) == 2
        assert len(availability.media_urls["videos"]) == 1
        assert availability.ai_detected_params is not None
        assert "source" in availability.ai_detected_params
    
    async def test_seller_can_sell_from_any_location(
        self,
        db_session,
        sample_commodity,
        sample_seller,
        sample_location
    ):
        """
        Test: Seller can sell from ANY location (no restriction)
        
        Given: Seller not registered at location
        When: Create availability at any location
        Then: Success (location exists check only)
        """
        service = AvailabilityService(db_session)
        
        # Create availability at ANY location (no ownership check)
        availability = await service.create_availability(
            seller_id=sample_seller.id,
            commodity_id=sample_commodity.id,
            location_id=sample_location.id,  # Any location
            total_quantity=Decimal("100.0"),
            quantity_unit="CANDY",
            quality_params={"length": 29.0},
            created_by=uuid4(),
            auto_approve=True
        )
        
        assert availability.location_id == sample_location.id
        assert availability.seller_id == sample_seller.id
    
    async def test_invalid_location_raises_error(
        self,
        db_session,
        sample_commodity,
        sample_seller
    ):
        """
        Test: Invalid location raises error
        
        Given: Non-existent location_id
        When: Create availability
        Then: Raise ValueError (location does not exist)
        """
        service = AvailabilityService(db_session)
        
        fake_location_id = uuid4()
        
        with pytest.raises(ValueError, match="does not exist"):
            await service.create_availability(
                seller_id=sample_seller.id,
                commodity_id=sample_commodity.id,
                location_id=fake_location_id,  # Non-existent
                total_quantity=Decimal("100.0"),
                quantity_unit="CANDY",
                quality_params={"length": 29.0},
                created_by=uuid4()
            )


# ========================
# Fixtures
# ========================

@pytest.fixture
async def sample_commodity_with_parameters(db_session):
    """Create commodity with parameter constraints"""
    from backend.modules.commodity_master.models import Commodity, CommodityParameter
    
    commodity = Commodity(
        id=uuid4(),
        name="Cotton 29mm",
        base_unit="KG",
        trade_unit="CANDY",
        rate_unit="CANDY"
    )
    db_session.add(commodity)
    
    # Add parameter constraints
    param_length = CommodityParameter(
        commodity_id=commodity.id,
        parameter_name="length",
        min_value=Decimal("27.0"),
        max_value=Decimal("32.0"),
        is_mandatory=False
    )
    db_session.add(param_length)
    
    await db_session.commit()
    return commodity


@pytest.fixture
async def sample_commodity_with_mandatory_params(db_session):
    """Create commodity with mandatory parameters"""
    from backend.modules.commodity_master.models import Commodity, CommodityParameter
    
    commodity = Commodity(
        id=uuid4(),
        name="Cotton Premium",
        base_unit="KG",
        trade_unit="CANDY",
        rate_unit="CANDY"
    )
    db_session.add(commodity)
    
    # Mandatory length
    param_length = CommodityParameter(
        commodity_id=commodity.id,
        parameter_name="length",
        min_value=Decimal("27.0"),
        max_value=Decimal("32.0"),
        is_mandatory=True
    )
    db_session.add(param_length)
    
    # Mandatory strength
    param_strength = CommodityParameter(
        commodity_id=commodity.id,
        parameter_name="strength",
        min_value=Decimal("24.0"),
        max_value=Decimal("30.0"),
        is_mandatory=True
    )
    db_session.add(param_strength)
    
    await db_session.commit()
    return commodity

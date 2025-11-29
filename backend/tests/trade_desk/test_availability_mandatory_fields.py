"""
Integration Tests: Availability Engine Mandatory Field Validation

Tests that MANDATORY fields are enforced:
1. quantity + quantity_unit + location_id (REQUIRED)
2. quality_params (REQUIRED and non-empty)
3. Validates quality_params against CommodityParameter (min/max/mandatory)
4. price and price_unit are OPTIONAL

Business Rule: "AVAILABILITY ENGINE MANDATORY IS (QTY, PARAMETER, LOCATION) PRICE AND OTHER THINGS OPTIONAL"

Test Scenarios:
- ✅ Allow: All mandatory fields provided + price (full data)
- ✅ Allow: All mandatory fields provided + NO price (negotiable/on-request)
- ❌ Block: Missing quantity_unit
- ❌ Block: Missing quality_params
- ❌ Block: Empty quality_params {}
- ❌ Block: quality_params missing mandatory commodity parameter
- ❌ Block: quality_params value outside min/max range
- ✅ Allow: Price provided WITH price_unit
- ❌ Block: Price provided WITHOUT price_unit
"""

import pytest
from decimal import Decimal
from uuid import UUID, uuid4
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import ValidationError

from backend.modules.trade_desk.services.availability_service import AvailabilityService
from backend.modules.trade_desk.schemas import AvailabilityCreateRequest
from backend.modules.partners.models import BusinessPartner
from backend.modules.settings.models import Location
from backend.modules.commodity_master.models import Commodity, CommodityParameter


@pytest.fixture
async def setup_mandatory_test_data(db_session: AsyncSession):
    """Create test data for mandatory field validation."""
    
    # Create location
    location = Location(
        id=uuid4(),
        name="Test Location",
        state="Gujarat",
        country="India",
        latitude=Decimal("23.0225"),
        longitude=Decimal("72.5714"),
        region="WEST"
    )
    db_session.add(location)
    
    # Create commodity
    commodity = Commodity(
        id=uuid4(),
        name="Cotton 29mm",
        category="cotton",
        base_unit="KG",
        trade_unit="CANDY",
        rate_unit="CANDY"
    )
    db_session.add(commodity)
    
    # Create commodity parameters (min/max/mandatory constraints)
    param1 = CommodityParameter(
        id=uuid4(),
        commodity_id=commodity.id,
        parameter_name="length",
        min_value=Decimal("26.0"),
        max_value=Decimal("32.0"),
        is_mandatory=True,  # REQUIRED parameter
        parameter_type="numeric",
        unit="mm"
    )
    db_session.add(param1)
    
    param2 = CommodityParameter(
        id=uuid4(),
        commodity_id=commodity.id,
        parameter_name="strength",
        min_value=Decimal("24.0"),
        max_value=Decimal("30.0"),
        is_mandatory=True,  # REQUIRED parameter
        parameter_type="numeric",
        unit="g/tex"
    )
    db_session.add(param2)
    
    param3 = CommodityParameter(
        id=uuid4(),
        commodity_id=commodity.id,
        parameter_name="micronaire",
        min_value=Decimal("3.5"),
        max_value=Decimal("5.0"),
        is_mandatory=False,  # OPTIONAL parameter
        parameter_type="numeric",
        unit=""
    )
    db_session.add(param3)
    
    # Create seller
    seller = BusinessPartner(
        id=uuid4(),
        legal_name="Test Seller Ltd",
        country="India",
        entity_class="business_entity",
        capabilities={
            "domestic_buy_india": False,
            "domestic_sell_india": True
        }
    )
    db_session.add(seller)
    
    await db_session.commit()
    await db_session.refresh(location)
    await db_session.refresh(commodity)
    await db_session.refresh(seller)
    
    return {
        "location": location,
        "commodity": commodity,
        "seller": seller
    }


@pytest.mark.asyncio
async def test_create_with_all_mandatory_fields_and_price(db_session: AsyncSession, setup_mandatory_test_data):
    """Test successful creation with all mandatory fields + price."""
    
    data = await setup_mandatory_test_data
    service = AvailabilityService(db_session)
    
    availability = await service.create_availability(
        seller_id=data["seller"].id,
        commodity_id=data["commodity"].id,
        location_id=data["location"].id,
        total_quantity=Decimal("100.0"),  # MANDATORY
        quantity_unit="CANDY",  # MANDATORY
        quality_params={"length": 29.0, "strength": 26.0},  # MANDATORY
        base_price=Decimal("8000.0"),  # OPTIONAL
        price_unit="per CANDY",  # Required if base_price provided
        created_by=uuid4(),
        auto_approve=True
    )
    
    assert availability.total_quantity == Decimal("100.0")
    assert availability.quantity_unit == "CANDY"
    assert availability.quality_params == {"length": 29.0, "strength": 26.0}
    assert availability.base_price == Decimal("8000.0")
    assert availability.price_unit == "per CANDY"


@pytest.mark.asyncio
async def test_create_without_price_is_allowed(db_session: AsyncSession, setup_mandatory_test_data):
    """Test successful creation WITHOUT price (negotiable/on-request)."""
    
    data = await setup_mandatory_test_data
    service = AvailabilityService(db_session)
    
    availability = await service.create_availability(
        seller_id=data["seller"].id,
        commodity_id=data["commodity"].id,
        location_id=data["location"].id,
        total_quantity=Decimal("100.0"),
        quantity_unit="CANDY",
        quality_params={"length": 29.0, "strength": 26.0},
        # NO base_price - negotiable/on-request
        created_by=uuid4(),
        auto_approve=True
    )
    
    assert availability.base_price is None
    assert availability.price_unit is None
    # Still valid - price is OPTIONAL


@pytest.mark.asyncio
async def test_schema_rejects_missing_quantity_unit(setup_mandatory_test_data):
    """Test that schema validation rejects missing quantity_unit."""
    
    data = await setup_mandatory_test_data
    
    with pytest.raises(ValidationError) as exc_info:
        AvailabilityCreateRequest(
            commodity_id=data["commodity"].id,
            location_id=data["location"].id,
            total_quantity=Decimal("100.0"),
            # quantity_unit MISSING - should fail
            quality_params={"length": 29.0, "strength": 26.0}
        )
    
    errors = exc_info.value.errors()
    assert any(e["loc"] == ("quantity_unit",) for e in errors)


@pytest.mark.asyncio
async def test_schema_rejects_missing_quality_params(setup_mandatory_test_data):
    """Test that schema validation rejects missing quality_params."""
    
    data = await setup_mandatory_test_data
    
    with pytest.raises(ValidationError) as exc_info:
        AvailabilityCreateRequest(
            commodity_id=data["commodity"].id,
            location_id=data["location"].id,
            total_quantity=Decimal("100.0"),
            quantity_unit="CANDY",
            # quality_params MISSING - should fail
        )
    
    errors = exc_info.value.errors()
    assert any(e["loc"] == ("quality_params",) for e in errors)


@pytest.mark.asyncio
async def test_schema_rejects_empty_quality_params(setup_mandatory_test_data):
    """Test that schema validation rejects empty quality_params {}."""
    
    data = await setup_mandatory_test_data
    
    with pytest.raises(ValidationError) as exc_info:
        AvailabilityCreateRequest(
            commodity_id=data["commodity"].id,
            location_id=data["location"].id,
            total_quantity=Decimal("100.0"),
            quantity_unit="CANDY",
            quality_params={}  # Empty - should fail
        )
    
    errors = exc_info.value.errors()
    # Check for "quality_params cannot be empty" error
    assert any("empty" in str(e["msg"]).lower() for e in errors)


@pytest.mark.asyncio
async def test_service_rejects_missing_mandatory_commodity_parameter(db_session: AsyncSession, setup_mandatory_test_data):
    """Test that service validates mandatory commodity parameters."""
    
    data = await setup_mandatory_test_data
    service = AvailabilityService(db_session)
    
    with pytest.raises(ValueError) as exc_info:
        await service.create_availability(
            seller_id=data["seller"].id,
            commodity_id=data["commodity"].id,
            location_id=data["location"].id,
            total_quantity=Decimal("100.0"),
            quantity_unit="CANDY",
            quality_params={"length": 29.0},  # Missing "strength" (mandatory)
            created_by=uuid4(),
            auto_approve=True
        )
    
    assert "mandatory parameter 'strength' is missing" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_service_rejects_parameter_below_min_value(db_session: AsyncSession, setup_mandatory_test_data):
    """Test that service validates min_value constraint."""
    
    data = await setup_mandatory_test_data
    service = AvailabilityService(db_session)
    
    with pytest.raises(ValueError) as exc_info:
        await service.create_availability(
            seller_id=data["seller"].id,
            commodity_id=data["commodity"].id,
            location_id=data["location"].id,
            total_quantity=Decimal("100.0"),
            quantity_unit="CANDY",
            quality_params={
                "length": 25.0,  # Below min_value of 26.0
                "strength": 26.0
            },
            created_by=uuid4(),
            auto_approve=True
        )
    
    assert "below minimum" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_service_rejects_parameter_above_max_value(db_session: AsyncSession, setup_mandatory_test_data):
    """Test that service validates max_value constraint."""
    
    data = await setup_mandatory_test_data
    service = AvailabilityService(db_session)
    
    with pytest.raises(ValueError) as exc_info:
        await service.create_availability(
            seller_id=data["seller"].id,
            commodity_id=data["commodity"].id,
            location_id=data["location"].id,
            total_quantity=Decimal("100.0"),
            quantity_unit="CANDY",
            quality_params={
                "length": 29.0,
                "strength": 35.0  # Above max_value of 30.0
            },
            created_by=uuid4(),
            auto_approve=True
        )
    
    assert "exceeds maximum" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_service_allows_optional_parameters_missing(db_session: AsyncSession, setup_mandatory_test_data):
    """Test that optional parameters can be omitted."""
    
    data = await setup_mandatory_test_data
    service = AvailabilityService(db_session)
    
    # micronaire is OPTIONAL (is_mandatory=False)
    availability = await service.create_availability(
        seller_id=data["seller"].id,
        commodity_id=data["commodity"].id,
        location_id=data["location"].id,
        total_quantity=Decimal("100.0"),
        quantity_unit="CANDY",
        quality_params={
            "length": 29.0,
            "strength": 26.0
            # micronaire OMITTED - OK because optional
        },
        created_by=uuid4(),
        auto_approve=True
    )
    
    assert availability.quality_params == {"length": 29.0, "strength": 26.0}


@pytest.mark.asyncio
async def test_schema_rejects_price_without_price_unit(setup_mandatory_test_data):
    """Test that if base_price provided, price_unit is required."""
    
    data = await setup_mandatory_test_data
    
    with pytest.raises(ValidationError) as exc_info:
        AvailabilityCreateRequest(
            commodity_id=data["commodity"].id,
            location_id=data["location"].id,
            total_quantity=Decimal("100.0"),
            quantity_unit="CANDY",
            quality_params={"length": 29.0, "strength": 26.0},
            base_price=Decimal("8000.0"),
            # price_unit MISSING - should fail
        )
    
    errors = exc_info.value.errors()
    assert any("price_unit is required when base_price is provided" in str(e["msg"]) for e in errors)


@pytest.mark.asyncio
async def test_seller_can_sell_from_any_location(db_session: AsyncSession, setup_mandatory_test_data):
    """Test that seller can create availability from ANY location (no restriction)."""
    
    data = await setup_mandatory_test_data
    service = AvailabilityService(db_session)
    
    # Create DIFFERENT location (not in seller's registered locations)
    new_location = Location(
        id=uuid4(),
        name="Different Location",
        state="Maharashtra",
        country="India",
        latitude=Decimal("19.0760"),
        longitude=Decimal("72.8777"),
        region="WEST"
    )
    db_session.add(new_location)
    await db_session.commit()
    await db_session.refresh(new_location)
    
    # Seller creates availability from DIFFERENT location (should succeed)
    availability = await service.create_availability(
        seller_id=data["seller"].id,
        commodity_id=data["commodity"].id,
        location_id=new_location.id,  # Different location
        total_quantity=Decimal("100.0"),
        quantity_unit="CANDY",
        quality_params={"length": 29.0, "strength": 26.0},
        created_by=uuid4(),
        auto_approve=True
    )
    
    assert availability.location_id == new_location.id
    # No error - seller CAN sell from ANY location

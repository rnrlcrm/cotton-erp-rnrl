"""
Test fixtures for Trade Desk module.

Provides:
- Database fixtures (commodities, locations, business partners)
- Authentication mocks
- Sample availabilities
"""

import pytest
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from backend.db.session import Base
from backend.modules.settings.commodities.models import Commodity
from backend.modules.settings.locations.models import Location
from backend.modules.partners.models import BusinessPartner
from backend.modules.trade_desk.models.availability import Availability
from backend.modules.trade_desk.enums import AvailabilityStatus, MarketVisibility


# Test database engine (in-memory SQLite for speed)
TEST_DATABASE_URL = "sqlite:///:memory:"

test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)

TestSessionLocal = sessionmaker(
    bind=test_engine,
    autocommit=False,
    autoflush=False
)


@pytest.fixture(scope="function")
def db_session():
    """
    Create sync database session for each test.
    """
    Base.metadata.create_all(bind=test_engine)
    
    session = TestSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def mock_user():
    """Mock authenticated user."""
    class MockUser:
        id = uuid4()
        user_type = "EXTERNAL"
        business_partner_id = uuid4()
        organization_id = None
        is_active = True
        email = "seller@test.com"
    
    return MockUser()


@pytest.fixture
def mock_buyer_user():
    """Mock buyer user."""
    class MockBuyerUser:
        id = uuid4()
        user_type = "EXTERNAL"
        business_partner_id = uuid4()
        organization_id = None
        is_active = True
        email = "buyer@test.com"
    
    return MockBuyerUser()


@pytest.fixture
def sample_commodity(db_session: Session):
    """Create sample cotton commodity."""
    commodity = Commodity(
        id=uuid4(),
        name="Cotton",
        hsn_code="520100",
        category="FIBER",
        subcategory="NATURAL_FIBER",
        unit_of_measure="KG",
        is_active=True,
        created_at=datetime.now(timezone.utc)
    )
    db_session.add(commodity)
    db_session.commit()
    db_session.refresh(commodity)
    return commodity


@pytest.fixture
def sample_gold_commodity(db_session: Session):
    """Create sample gold commodity."""
    commodity = Commodity(
        id=uuid4(),
        name="Gold",
        hsn_code="710812",
        category="PRECIOUS_METAL",
        subcategory="GOLD",
        unit_of_measure="GM",
        is_active=True,
        created_at=datetime.now(timezone.utc)
    )
    db_session.add(commodity)
    db_session.commit()
    db_session.refresh(commodity)
    return commodity


@pytest.fixture
def sample_wheat_commodity(db_session: Session):
    """Create sample wheat commodity."""
    commodity = Commodity(
        id=uuid4(),
        name="Wheat",
        hsn_code="100190",
        category="GRAIN",
        subcategory="CEREAL",
        unit_of_measure="KG",
        is_active=True,
        created_at=datetime.now(timezone.utc)
    )
    db_session.add(commodity)
    db_session.commit()
    db_session.refresh(commodity)
    return commodity


@pytest.fixture
def sample_location(db_session: Session):
    """Create sample location (warehouse in Gujarat)."""
    location = Location(
        id=uuid4(),
        name="Gujarat Warehouse",
        location_type="WAREHOUSE",
        address_line1="Plot 123, GIDC",
        city="Ahmedabad",
        state="Gujarat",
        country="India",
        postal_code="380001",
        latitude=Decimal("23.0225"),
        longitude=Decimal("72.5714"),
        is_active=True,
        created_at=datetime.now(timezone.utc)
    )
    db_session.add(location)
    db_session.commit()
    db_session.refresh(location)
    return location


@pytest.fixture
def sample_seller(db_session: Session, mock_user):
    """Create sample seller business partner."""
    seller = BusinessPartner(
        id=mock_user.business_partner_id,
        name="Test Cotton Trader",
        partner_type="SELLER",
        is_active=True,
        created_at=datetime.now(timezone.utc)
    )
    db_session.add(seller)
    db_session.commit()
    db_session.refresh(seller)
    return seller


@pytest.fixture
def sample_buyer(db_session: Session, mock_buyer_user):
    """Create sample buyer business partner."""
    buyer = BusinessPartner(
        id=mock_buyer_user.business_partner_id,
        name="Test Cotton Mill",
        partner_type="BUYER",
        is_active=True,
        created_at=datetime.now(timezone.utc)
    )
    db_session.add(buyer)
    db_session.commit()
    db_session.refresh(buyer)
    return buyer


@pytest.fixture
def sample_availability(
    db_session: Session,
    sample_commodity,
    sample_location,
    sample_seller,
    mock_user
):
    """Create sample availability."""
    availability = Availability(
        id=uuid4(),
        seller_id=sample_seller.id,
        commodity_id=sample_commodity.id,
        location_id=sample_location.id,
        total_quantity=Decimal("10000"),
        available_quantity=Decimal("10000"),
        reserved_quantity=Decimal("0"),
        sold_quantity=Decimal("0"),
        base_price=Decimal("75000"),
        price_matrix={"29mm": 75000, "30mm": 77000, "28mm": 73000},
        quality_params={
            "staple_length": "29mm",
            "micronaire": "3.5-4.5",
            "strength": "28-30 g/tex",
            "trash": "< 2%"
        },
        market_visibility=MarketVisibility.PUBLIC,
        allow_partial_order=True,
        min_order_quantity=Decimal("500"),
        delivery_terms="EX-WAREHOUSE",
        delivery_address="Gujarat Warehouse, Ahmedabad",
        delivery_latitude=Decimal("23.0225"),
        delivery_longitude=Decimal("72.5714"),
        expiry_date=datetime.now(timezone.utc) + timedelta(days=30),
        status=AvailabilityStatus.ACTIVE,
        approval_status="APPROVED",
        ai_suggested_price=Decimal("75500"),
        ai_confidence_score=Decimal("0.85"),
        ai_price_anomaly_flag=False,
        created_at=datetime.now(timezone.utc),
        created_by=mock_user.id
    )
    db_session.add(availability)
    db_session.commit()
    db_session.refresh(availability)
    return availability


@pytest.fixture
def cotton_quality_params():
    """Standard cotton quality parameters."""
    return {
        "staple_length": "29mm",
        "micronaire": "3.5-4.5",
        "strength": "28-30 g/tex",
        "trash": "< 2%",
        "color_grade": "31-1",
        "leaf_grade": "3"
    }


@pytest.fixture
def gold_quality_params():
    """Standard gold quality parameters."""
    return {
        "purity": "99.99%",
        "form": "bar",
        "weight": "1kg",
        "certification": "LBMA"
    }


@pytest.fixture
def wheat_quality_params():
    """Standard wheat quality parameters."""
    return {
        "variety": "PBW 343",
        "moisture": "12%",
        "foreign_matter": "< 1%",
        "broken_grains": "< 2%",
        "test_weight": "78 kg/hl"
    }

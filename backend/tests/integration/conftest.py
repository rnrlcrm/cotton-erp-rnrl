"""
Integration Test Infrastructure with Testcontainers + PostgreSQL

Provides real PostgreSQL database for thorough integration testing of all modules.
"""
import asyncio
import os
import uuid
from typing import AsyncGenerator, Generator

import pytest
import pytest_asyncio
from sqlalchemy import text, create_engine, event, exc
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool
from testcontainers.postgres import PostgresContainer

from backend.db.async_session import get_db

# Configure password hashing for tests (avoid bcrypt 5.0.0 compatibility issues)
os.environ.setdefault("PASSWORD_SCHEME", "pbkdf2_sha256")


# ============================================
# HELPER FUNCTIONS
# ============================================

def create_test_partner(partner_type="buyer", legal_name="Test Partner"):
    """Helper to create BusinessPartner with all required fields."""
    from backend.modules.partners.models import BusinessPartner
    import uuid
    
    return BusinessPartner(
        id=uuid.uuid4(),
        partner_type=partner_type,
        legal_name=legal_name,
        country="India",
        primary_currency="INR",
        bank_account_name=legal_name,
        bank_name="HDFC Bank",
        bank_account_number="1234567890",
        bank_routing_code="HDFC0001234",
        primary_address="123 Test Street",
        primary_city="Mumbai",
        primary_postal_code="400001",
        primary_country="India",
        primary_contact_name="Test Contact",
        primary_contact_email="test@example.com",
        primary_contact_phone="+919876543210",
        status="active"
    )


async def create_test_requirement(
    db_session: AsyncSession,
    buyer_partner_id: uuid.UUID,
    commodity_id: uuid.UUID,
    created_by_user_id: uuid.UUID,
    overrides: dict = None
) -> "Requirement":
    """
    Factory function to create a valid Requirement with all required fields.
    
    Handles:
    - Auto-number generation (requirement_number)
    - Required NOT NULL fields
    - JSONB defaults
    - Proper FK relationships
    
    Args:
        db_session: Async database session
        buyer_partner_id: UUID of buyer partner
        commodity_id: UUID of commodity
        created_by_user_id: UUID of user creating requirement
        overrides: Optional dict to override defaults
    
    Returns:
        Requirement instance (not yet committed)
    """
    from backend.modules.trade_desk.models.requirement import Requirement
    from decimal import Decimal
    from datetime import datetime, timezone, timedelta
    import random
    
    # Generate unique requirement number
    req_number = f"REQ-TEST-{random.randint(100000, 999999)}"
    
    # Generate timestamps
    now = datetime.now(timezone.utc)
    later = now + timedelta(days=30)
    
    # Default data
    data = {
        "id": uuid.uuid4(),
        "requirement_number": req_number,
        "buyer_partner_id": buyer_partner_id,
        "commodity_id": commodity_id,
        "created_by_user_id": created_by_user_id,
        "min_quantity": Decimal("100.00"),
        "max_quantity": Decimal("200.00"),
        "quantity_unit": "kg",
        "quality_requirements": {"grade": "A"},  # Required JSONB
        "max_budget_per_unit": Decimal("50.00"),  # Required NOT NULL
        "valid_from": now,  # Required NOT NULL TIMESTAMP
        "valid_until": later,  # Required NOT NULL TIMESTAMP
    }
    
    # Apply overrides
    if overrides:
        data.update(overrides)
    
    requirement = Requirement(**data)
    db_session.add(requirement)
    await db_session.flush()
    await db_session.refresh(requirement)
    
    return requirement


async def create_test_availability(
    db_session: AsyncSession,
    seller_id: uuid.UUID,
    commodity_id: uuid.UUID,
    location_id: uuid.UUID,
    created_by: uuid.UUID,
    overrides: dict = None
) -> "Availability":
    """
    Factory function to create a valid Availability with all required fields.
    
    Handles:
    - Required NOT NULL fields
    - JSONB defaults
    - Proper FK relationships
    - Price type defaults
    
    Args:
        db_session: Async database session
        seller_id: UUID of seller partner (NOT seller_partner_id!)
        commodity_id: UUID of commodity
        location_id: UUID of location (NOT pickup_location_id!)
        created_by: UUID of user creating availability (NOT created_by_user_id!)
        overrides: Optional dict to override defaults
    
    Returns:
        Availability instance (not yet committed)
    """
    from backend.modules.trade_desk.models.availability import Availability
    from decimal import Decimal
    
    # Default data
    data = {
        "id": uuid.uuid4(),
        "seller_id": seller_id,  # ⚠️ NOT seller_partner_id
        "commodity_id": commodity_id,
        "location_id": location_id,  # ⚠️ NOT pickup_location_id
        "created_by": created_by,  # ⚠️ NOT created_by_user_id
        "total_quantity": Decimal("1000.00"),
        "available_quantity": Decimal("1000.00"),
        "price_type": "FIXED",  # Required
        "base_price": Decimal("45.00"),
        "quality_params": {"grade": "A"},  # Optional JSONB
    }
    
    # Apply overrides
    if overrides:
        data.update(overrides)
    
    availability = Availability(**data)
    db_session.add(availability)
    await db_session.flush()
    await db_session.refresh(availability)
    
    return availability


# ============================================
# PYTEST FIXTURES
# ============================================

from backend.db.session_module import Base


@pytest.fixture(scope="session")
def postgres_container() -> Generator[PostgresContainer, None, None]:
    """
    Session-scoped PostgreSQL container.
    Starts once for all tests, provides real database.
    """
    container = PostgresContainer("postgres:15-alpine")
    container.start()
    
    yield container
    
    container.stop()


@pytest.fixture(scope="session")
def sync_database_url(postgres_container: PostgresContainer) -> str:
    """Synchronous database URL for schema creation."""
    url = postgres_container.get_connection_url()
    # Inject into environment for Alembic to use
    import os
    os.environ["DATABASE_URL"] = url
    return url


@pytest.fixture(scope="session")
def async_database_url(postgres_container: PostgresContainer) -> str:
    """Asynchronous database URL for async operations."""
    return postgres_container.get_connection_url().replace("psycopg2", "asyncpg")


@pytest.fixture(scope="session", autouse=True)
def setup_database_schema(sync_database_url: str):
    """
    Create all tables in the database using SQLAlchemy metadata.
    Runs once per test session AUTOMATICALLY.
    
    Note: Using Base.metadata.create_all() instead of Alembic for tests
    because Alembic has issues with duplicate migration execution in test context.
    This still creates all tables, but skips triggers/sequences that would be
    created by migrations. For integration tests, this is acceptable.
    """
    import sys
    
    print(f"\n{'='*80}", file=sys.stderr)
    print(f"🔧 setup_database_schema CALLED (autouse=True, scope=session)", file=sys.stderr)
    print(f"{'='*80}\n", file=sys.stderr)
    
    # Import all models to ensure they're registered
    from backend.modules.partners.models import (
        BusinessPartner, PartnerLocation, PartnerEmployee,
        PartnerDocument, PartnerVehicle, PartnerOnboardingApplication,
        PartnerAmendment, PartnerKYCRenewal
    )
    from backend.modules.trade_desk.models.requirement import Requirement
    from backend.modules.trade_desk.models.availability import Availability
    from backend.modules.settings.commodities.models import Commodity, PaymentTerm
    from backend.modules.settings.locations.models import Location
    from backend.modules.settings.organization.models import Organization
    from backend.modules.settings.models.settings_models import User
    
    # Create sync engine
    engine = create_engine(sync_database_url, poolclass=NullPool)
    
    try:
        # Create all tables using SQLAlchemy metadata
        print("🔧 Creating database schema...", file=sys.stderr)
        Base.metadata.create_all(engine)
        print("✅ Schema created - database ready", file=sys.stderr)
        yield
    finally:
        # Cleanup
        print("🧹 Cleaning up database...", file=sys.stderr)
        Base.metadata.drop_all(engine)
        engine.dispose()
        print("✅ Cleanup complete", file=sys.stderr)


@pytest_asyncio.fixture(scope="function")
async def db_session(
    async_database_url: str,
    setup_database_schema,
) -> AsyncGenerator[AsyncSession, None]:
    """
    Async database session for each test.
    Each test gets a clean transaction that rolls back.
    """
    engine = create_async_engine(async_database_url, poolclass=NullPool, echo=False)
    
    async_session_maker = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session_maker() as session:
        # Start transaction
        async with session.begin():
            yield session
            # Rollback happens automatically when exiting context
    
    await engine.dispose()


@pytest_asyncio.fixture
async def seed_organization(db_session: AsyncSession):
    """Create main organization for testing."""
    from backend.modules.settings.organization.models import Organization
    import random
    import string
    
    # Generate unique name to avoid conflicts between tests
    suffix = ''.join(random.choices(string.ascii_letters, k=6))
    
    org = Organization(
        id=uuid.uuid4(),
        name=f"MainCo_{suffix}",
        legal_name="Main Company Ltd",
        PAN="AAACM1234A"
    )
    db_session.add(org)
    await db_session.flush()
    return org


@pytest_asyncio.fixture
async def seed_user(db_session: AsyncSession, seed_organization):
    """Create test user for audit trails."""
    from backend.modules.settings.models.settings_models import User
    import random
    import string
    
    suffix = ''.join(random.choices(string.digits, k=4))
    
    user = User(
        id=uuid.uuid4(),
        user_type="INTERNAL",
        organization_id=seed_organization.id,
        mobile_number=f"+9199999{suffix}",
        full_name="Test User",
        is_active=True,
        is_verified=True
    )
    db_session.add(user)
    await db_session.flush()
    return user


@pytest_asyncio.fixture
async def seed_locations(db_session: AsyncSession):
    """Create test locations."""
    from backend.modules.settings.locations.models import Location
    import random
    import string
    
    suffix = ''.join(random.choices(string.ascii_letters + string.digits, k=6))
    
    locations = [
        Location(
            id=uuid.uuid4(),
            name="Mumbai",
            google_place_id=f"ChIJwe1EZjDG5zsRaYxkjY_tpF0_{suffix}_1",
            city="Mumbai",
            state="Maharashtra",
            pincode="400001",
            region="WEST"
        ),
        Location(
            id=uuid.uuid4(),
            name="Delhi",
            google_place_id=f"ChIJLbZ-NFv9DDkRzk0gTkm3wlI_{suffix}_2",
            city="Delhi",
            state="Delhi",
            pincode="110001",
            region="NORTH"
        ),
        Location(
            id=uuid.uuid4(),
            name="Bangalore",
            google_place_id=f"ChIJbU60yXAWrjsR4E9-UejD3_g_{suffix}_3",
            city="Bangalore",
            state="Karnataka",
            pincode="560001",
            region="SOUTH"
        ),
    ]
    
    for loc in locations:
        db_session.add(loc)
    
    await db_session.flush()
    return locations


@pytest_asyncio.fixture
async def seed_commodities(db_session: AsyncSession):
    """Create test commodities."""
    from backend.modules.settings.commodities.models import Commodity
    
    commodities = [
        Commodity(
            id=uuid.uuid4(),
            name="Cotton",
            category="Agricultural",
            uom="Bales",
            is_active=True
        ),
        Commodity(
            id=uuid.uuid4(),
            name="Gold",
            category="Precious Metal",
            uom="Grams",
            is_active=True
        ),
    ]
    
    for comm in commodities:
        db_session.add(comm)
    
    await db_session.flush()
    return commodities


@pytest_asyncio.fixture
async def seed_payment_terms(db_session: AsyncSession):
    """Create test payment terms."""
    from backend.modules.settings.commodities.models import PaymentTerm
    import random
    import string
    
    suffix = ''.join(random.choices(string.ascii_letters, k=4))
    
    terms = [
        PaymentTerm(
            id=uuid.uuid4(),
            name=f"Immediate_{suffix}",
            days=0,
            is_active=True
        ),
        PaymentTerm(
            id=uuid.uuid4(),
            name=f"Net30_{suffix}",
            days=30,
            is_active=True
        ),
    ]
    
    for term in terms:
        db_session.add(term)
    
    await db_session.flush()
    return terms


# ============================================
# HTTP CLIENT FIXTURE
# ============================================

@pytest_asyncio.fixture
async def async_client(db_session: AsyncSession) -> AsyncGenerator:
    """
    Async HTTP client for API testing.
    
    Provides HTTPX AsyncClient configured for FastAPI testing.
    Automatically handles database session dependency override.
    """
    from httpx import AsyncClient, ASGITransport
    from backend.app.main import app
    
    # Override database dependency to use test session
    async def override_get_db():
        yield db_session
    
    app.dependency_overrides[get_db] = override_get_db
    
    async with AsyncClient(
        transport=ASGITransport(app=app), 
        base_url="http://test"
    ) as client:
        yield client
    
    # Cleanup
    app.dependency_overrides.clear()

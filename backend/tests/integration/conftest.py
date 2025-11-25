"""
Integration Test Infrastructure with Testcontainers + PostgreSQL

Provides real PostgreSQL database for thorough integration testing of all modules.
"""
import asyncio
import uuid
from typing import AsyncGenerator, Generator

import pytest
import pytest_asyncio
from sqlalchemy import text, create_engine, event, exc
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool
from testcontainers.postgres import PostgresContainer


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
    return postgres_container.get_connection_url()


@pytest.fixture(scope="session")
def async_database_url(postgres_container: PostgresContainer) -> str:
    """Asynchronous database URL for async operations."""
    return postgres_container.get_connection_url().replace("psycopg2", "asyncpg")


@pytest.fixture(scope="session")
def setup_database_schema(sync_database_url: str):
    """
    Create all tables in the database using SQLAlchemy models.
    Runs once per test session.
    """
    # Import all models to register them with Base
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
        # Create all tables
        Base.metadata.create_all(engine)
        yield
    finally:
        # Cleanup
        Base.metadata.drop_all(engine)
        engine.dispose()


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

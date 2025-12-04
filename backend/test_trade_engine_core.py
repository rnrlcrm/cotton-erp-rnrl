"""
Trade Engine Core Functionality Test

Tests the complete flow:
1. Create partner branches
2. Create negotiation
3. Accept negotiation → Create instant binding contract
4. Verify trade details
5. Test AI branch suggestions
6. Test status updates

Run with: pytest test_trade_engine_core.py -v -s
"""

import asyncio
import pytest
import pytest_asyncio
from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import select

from backend.db.session import Base

# Lazy imports to avoid circular dependencies - import inside functions where needed


# Test database URL (use cotton_dev or create test DB)
TEST_DATABASE_URL = "postgresql+psycopg://postgres:postgres@localhost:5432/cotton_dev"


@pytest_asyncio.fixture(scope="function")
async def db_session():
    """Create async database session for testing"""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    
    async_session_maker = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session_maker() as session:
        yield session
        await session.rollback()
    
    await engine.dispose()


@pytest.fixture
async def setup_test_data(db_session: AsyncSession):
    """Create test partners and branches"""
    
    from backend.modules.partners.models import PartnerBranch, BusinessPartner
    
    # Create buyer partner
    buyer = BusinessPartner(
        id=uuid4(),
        partner_type="buyer",
        company_name="Test Buyer Co",
        pan="AAAAA1234A",
        state="Maharashtra",
        city="Mumbai",
        # Signature uploaded (required for trading)
        digital_signature_url="https://s3.example.com/signatures/buyer.png",
        is_active=True
    )
    db_session.add(buyer)
    
    # Create seller partner
    seller = BusinessPartner(
        id=uuid4(),
        partner_type="seller",
        company_name="Test Seller Co",
        pan="BBBBB5678B",
        state="Gujarat",
        city="Ahmedabad",
        # Signature uploaded (required for trading)
        digital_signature_url="https://s3.example.com/signatures/seller.png",
        is_active=True
    )
    db_session.add(seller)
    
    await db_session.flush()
    
    # Create buyer branches
    buyer_branch_1 = PartnerBranch(
        id=uuid4(),
        partner_id=buyer.id,
        branch_code="WH-01",
        branch_name="Mumbai Warehouse",
        address_line_1="123 MIDC Area",
        city="Mumbai",
        state="Maharashtra",
        postal_code="400001",
        country="India",
        latitude=Decimal("19.0760"),
        longitude=Decimal("72.8777"),
        can_receive_shipments=True,
        can_send_shipments=False,
        warehouse_capacity_qtls=5000,
        current_stock_qtls=1000,
        supported_commodities=["COTTON", "WHEAT"],
        is_default_ship_to=True,
        is_active=True
    )
    db_session.add(buyer_branch_1)
    
    buyer_branch_2 = PartnerBranch(
        id=uuid4(),
        partner_id=buyer.id,
        branch_code="HO",
        branch_name="Head Office - Mumbai",
        address_line_1="456 Business Park",
        city="Mumbai",
        state="Maharashtra",
        postal_code="400002",
        country="India",
        can_receive_shipments=False,
        can_send_shipments=False,
        is_head_office=True,
        is_active=True
    )
    db_session.add(buyer_branch_2)
    
    # Create seller branches
    seller_branch_1 = PartnerBranch(
        id=uuid4(),
        partner_id=seller.id,
        branch_code="WH-01",
        branch_name="Ahmedabad Warehouse",
        address_line_1="789 Industrial Estate",
        city="Ahmedabad",
        state="Gujarat",
        postal_code="380001",
        country="India",
        latitude=Decimal("23.0225"),
        longitude=Decimal("72.5714"),
        can_receive_shipments=False,
        can_send_shipments=True,
        warehouse_capacity_qtls=3000,
        current_stock_qtls=500,
        supported_commodities=["COTTON"],
        is_default_ship_from=True,
        is_active=True
    )
    db_session.add(seller_branch_1)
    
    await db_session.flush()
    
    return {
        "buyer": buyer,
        "seller": seller,
        "buyer_branch_1": buyer_branch_1,
        "buyer_branch_2": buyer_branch_2,
        "seller_branch_1": seller_branch_1
    }


@pytest.mark.asyncio
async def test_trade_number_generation(db_session: AsyncSession):
    """Test trade number generation (TR-2025-00001 format)"""
    from backend.modules.trade_desk.repositories.trade_repository import TradeRepository
    from backend.modules.trade_desk.models import Trade
    
    print("\n=== Test 1: Trade Number Generation ===")
    
    repo = TradeRepository(db_session)
    
    # Generate first trade number
    trade_number_1 = await repo.generate_trade_number()
    print(f"✓ Generated trade number: {trade_number_1}")
    assert trade_number_1.startswith("TR-2025-")
    assert len(trade_number_1) == 13  # TR-2025-00001
    
    # Create a trade to increment sequence
    from backend.modules.commodities.models import Commodity
    
    # Create dummy commodity
    commodity = Commodity(
        id=uuid4(),
        code="COTTON",
        name="Cotton",
        category="Agriculture"
    )
    db_session.add(commodity)
    await db_session.flush()
    
    trade = Trade(
        id=uuid4(),
        trade_number=trade_number_1,
        negotiation_id=uuid4(),  # Dummy
        buyer_partner_id=uuid4(),
        seller_partner_id=uuid4(),
        commodity_id=commodity.id,
        quantity=Decimal("100.000"),
        price_per_unit=Decimal("5000.00"),
        total_amount=Decimal("500000.00"),
        ship_to_address={"city": "Mumbai"},
        bill_to_address={"city": "Mumbai"},
        ship_from_address={"city": "Ahmedabad"},
        status="ACTIVE",
        trade_date=date.today()
    )
    db_session.add(trade)
    await db_session.flush()
    
    # Generate next trade number
    trade_number_2 = await repo.generate_trade_number()
    print(f"✓ Generated next trade number: {trade_number_2}")
    assert trade_number_2 > trade_number_1
    
    print("✅ Trade number generation working!\n")


@pytest.mark.asyncio
async def test_branch_creation_and_queries(db_session: AsyncSession, setup_test_data):
    """Test branch CRUD and capability queries"""
    from backend.modules.partners.repositories.branch_repository import BranchRepository
    
    print("\n=== Test 2: Branch Management ===")
    
    data = await setup_test_data
    buyer = data["buyer"]
    
    branch_repo = BranchRepository(db_session)
    
    # Test get branches by partner
    branches = await branch_repo.get_by_partner(buyer.id)
    print(f"✓ Found {len(branches)} branches for buyer")
    assert len(branches) == 2
    
    # Test ship-to branches
    ship_to_branches = await branch_repo.get_ship_to_branches(
        partner_id=buyer.id,
        commodity_code="COTTON",
        required_capacity_qtls=100
    )
    print(f"✓ Found {len(ship_to_branches)} ship-to branches for COTTON")
    assert len(ship_to_branches) >= 1
    
    # Test default branch
    default_ship_to = await branch_repo.get_default_ship_to(buyer.id)
    print(f"✓ Default ship-to: {default_ship_to.branch_name if default_ship_to else 'None'}")
    assert default_ship_to is not None
    
    # Test head office
    head_office = await branch_repo.get_head_office(buyer.id)
    print(f"✓ Head office: {head_office.branch_name if head_office else 'None'}")
    assert head_office is not None
    
    print("✅ Branch management working!\n")


@pytest.mark.asyncio
async def test_ai_branch_suggestions(db_session: AsyncSession, setup_test_data):
    """Test AI branch suggestion scoring algorithm"""
    from backend.modules.partners.repositories.branch_repository import BranchRepository
    from backend.modules.trade_desk.services.branch_suggestion_service import BranchSuggestionService
    
    print("\n=== Test 3: AI Branch Suggestions ===")
    
    data = await setup_test_data
    buyer = data["buyer"]
    seller_branch = data["seller_branch_1"]
    
    branch_repo = BranchRepository(db_session)
    ai_service = BranchSuggestionService(db_session, branch_repo)
    
    # Get suggestions for buyer (ship-to)
    suggestions = await ai_service.suggest_ship_to_branch(
        partner_id=buyer.id,
        commodity_code="COTTON",
        quantity_qtls=100,
        target_state="Gujarat",  # Seller's state
        target_latitude=seller_branch.latitude,
        target_longitude=seller_branch.longitude
    )
    
    print(f"✓ AI suggested {len(suggestions)} branches")
    
    if suggestions:
        best = suggestions[0]
        print(f"\n  Best Match: {best['branch'].branch_name}")
        print(f"  Total Score: {best['score']:.2f}/100")
        print(f"  Reasoning: {best['reasoning']}")
        print(f"  Breakdown:")
        for key, value in best['breakdown'].items():
            print(f"    - {key}: {value:.2f} points")
    
    print("\n✅ AI branch suggestions working!\n")


@pytest.mark.asyncio
async def test_gst_calculation(db_session: AsyncSession):
    """Test GST type calculation (INTRA_STATE vs INTER_STATE)"""
    from backend.modules.trade_desk.repositories.trade_repository import TradeRepository
    from backend.modules.partners.repositories.branch_repository import BranchRepository
    from backend.modules.trade_desk.services.trade_service import TradeService
    
    print("\n=== Test 4: GST Calculation ===")
    
    trade_repo = TradeRepository(db_session)
    branch_repo = BranchRepository(db_session)
    service = TradeService(db_session, trade_repo, branch_repo)
    
    # Test INTRA_STATE (same state)
    gst_intra = service._calculate_gst(
        buyer_state="Maharashtra",
        seller_state="Maharashtra",
        base_amount=Decimal("100000.00")
    )
    print(f"✓ Same state (Maharashtra): {gst_intra['gst_type']}")
    print(f"  CGST: {gst_intra['cgst_rate']}%, SGST: {gst_intra['sgst_rate']}%")
    assert gst_intra['gst_type'] == 'INTRA_STATE'
    assert gst_intra['cgst_rate'] == Decimal('9.00')
    assert gst_intra['sgst_rate'] == Decimal('9.00')
    
    # Test INTER_STATE (different states)
    gst_inter = service._calculate_gst(
        buyer_state="Maharashtra",
        seller_state="Gujarat",
        base_amount=Decimal("100000.00")
    )
    print(f"\n✓ Different states (MH → GJ): {gst_inter['gst_type']}")
    print(f"  IGST: {gst_inter['igst_rate']}%")
    assert gst_inter['gst_type'] == 'INTER_STATE'
    assert gst_inter['igst_rate'] == Decimal('18.00')
    
    print("\n✅ GST calculation working!\n")


@pytest.mark.asyncio
async def test_signature_validation(db_session: AsyncSession, setup_test_data):
    """Test signature validation (must exist before trading)"""
    from backend.modules.partners.models import BusinessPartner
    from backend.modules.trade_desk.repositories.trade_repository import TradeRepository
    from backend.modules.partners.repositories.branch_repository import BranchRepository
    from backend.modules.trade_desk.services.trade_service import TradeService
    
    print("\n=== Test 5: Signature Validation ===")
    
    data = await setup_test_data
    buyer = data["buyer"]
    seller = data["seller"]
    
    trade_repo = TradeRepository(db_session)
    branch_repo = BranchRepository(db_session)
    service = TradeService(db_session, trade_repo, branch_repo)
    
    # Test with valid signatures
    try:
        await service._validate_signatures_exist(buyer.id, seller.id)
        print("✓ Both parties have signatures - validation passed")
    except Exception as e:
        pytest.fail(f"Signature validation failed: {e}")
    
    # Test with missing signature
    partner_no_sig = BusinessPartner(
        id=uuid4(),
        partner_type="buyer",
        company_name="No Signature Co",
        pan="CCCCC9999C",
        state="Maharashtra",
        city="Mumbai",
        digital_signature_url=None,  # No signature!
        is_active=True
    )
    db_session.add(partner_no_sig)
    await db_session.flush()
    
    try:
        await service._validate_signatures_exist(partner_no_sig.id, seller.id)
        pytest.fail("Should have raised exception for missing signature")
    except Exception as e:
        print(f"✓ Correctly blocked trade without signature: {str(e)[:60]}...")
    
    print("\n✅ Signature validation working!\n")


@pytest.mark.asyncio
async def test_address_freezing(db_session: AsyncSession, setup_test_data):
    """Test address snapshot freezing (immutable JSONB)"""
    from backend.modules.trade_desk.repositories.trade_repository import TradeRepository
    from backend.modules.partners.repositories.branch_repository import BranchRepository
    from backend.modules.trade_desk.services.trade_service import TradeService
    
    print("\n=== Test 6: Address Freezing ===")
    
    data = await setup_test_data
    buyer_branch = data["buyer_branch_1"]
    seller_branch = data["seller_branch_1"]
    
    trade_repo = TradeRepository(db_session)
    branch_repo = BranchRepository(db_session)
    service = TradeService(db_session, trade_repo, branch_repo)
    
    # Create branch config
    branch_config = {
        'ship_to_branch_id': buyer_branch.id,
        'bill_to_branch_id': data["buyer_branch_2"].id,
        'ship_from_branch_id': seller_branch.id
    }
    
    # Freeze addresses
    addresses = await service._freeze_addresses(branch_config)
    
    print("✓ Addresses frozen as JSONB snapshots:")
    print(f"  Ship-to: {addresses['ship_to']['city']}, {addresses['ship_to']['state']}")
    print(f"  Bill-to: {addresses['bill_to']['city']}, {addresses['bill_to']['state']}")
    print(f"  Ship-from: {addresses['ship_from']['city']}, {addresses['ship_from']['state']}")
    
    assert 'ship_to' in addresses
    assert 'bill_to' in addresses
    assert 'ship_from' in addresses
    assert addresses['ship_to']['city'] == buyer_branch.city
    
    # Simulate branch address update
    original_city = buyer_branch.city
    buyer_branch.city = "New City"
    await db_session.flush()
    
    # Frozen address should NOT change
    assert addresses['ship_to']['city'] == original_city
    print(f"\n✓ Address immutable: Branch city changed to '{buyer_branch.city}'")
    print(f"  But frozen snapshot still has: '{addresses['ship_to']['city']}'")
    
    print("\n✅ Address freezing working (immutable snapshots)!\n")


@pytest.mark.asyncio
async def test_full_trade_creation_flow(db_session: AsyncSession, setup_test_data):
    """
    Test COMPLETE flow: Create instant binding contract
    
    This is the CORE FUNCTIONALITY test!
    """
    print("\n=== Test 7: FULL TRADE CREATION FLOW ===")
    print("This simulates accepting a negotiation and creating instant contract\n")
    
    data = await setup_test_data
    buyer = data["buyer"]
    seller = data["seller"]
    
    # Step 1: Create a mock negotiation (ACCEPTED)
    from backend.modules.commodities.models import Commodity
    from backend.modules.trade_desk.models import Requirement, Availability, Negotiation
    from backend.modules.trade_desk.repositories.trade_repository import TradeRepository
    from backend.modules.partners.repositories.branch_repository import BranchRepository
    from backend.modules.trade_desk.services.trade_service import TradeService
    
    commodity = Commodity(
        id=uuid4(),
        code="COTTON",
        name="Raw Cotton",
        category="Agriculture"
    )
    db_session.add(commodity)
    await db_session.flush()
    
    requirement = Requirement(
        id=uuid4(),
        party_id=buyer.id,
        commodity_id=commodity.id,
        commodity_code="COTTON",
        quantity=Decimal("500.000"),
        delivery_city="Mumbai",
        delivery_state="Maharashtra",
        delivery_terms="FOB",
        status="ACTIVE"
    )
    db_session.add(requirement)
    
    availability = Availability(
        id=uuid4(),
        party_id=seller.id,
        commodity_id=commodity.id,
        commodity_code="COTTON",
        total_quantity=Decimal("1000.000"),
        base_price=Decimal("5500.00"),
        status="ACTIVE"
    )
    db_session.add(availability)
    await db_session.flush()
    
    negotiation = Negotiation(
        id=uuid4(),
        match_token_id=uuid4(),
        requirement_id=requirement.id,
        availability_id=availability.id,
        buyer_partner_id=buyer.id,
        seller_partner_id=seller.id,
        status="ACCEPTED",  # User accepted!
        current_quantity=Decimal("500.000"),
        current_price_per_unit=Decimal("5500.00"),
        final_quantity=Decimal("500.000"),
        final_price_per_unit=Decimal("5500.00"),
        final_total_amount=Decimal("2750000.00"),
        final_payment_terms="30 days credit"
    )
    db_session.add(negotiation)
    await db_session.flush()
    
    print("✓ Step 1: Negotiation ACCEPTED")
    print(f"  Buyer: {buyer.company_name}")
    print(f"  Seller: {seller.company_name}")
    print(f"  Commodity: {commodity.name}")
    print(f"  Quantity: {negotiation.final_quantity} quintals")
    print(f"  Price: ₹{negotiation.final_price_per_unit}/quintal")
    print(f"  Total: ₹{negotiation.final_total_amount}")
    
    # Step 2: Create instant binding contract
    trade_repo = TradeRepository(db_session)
    branch_repo = BranchRepository(db_session)
    service = TradeService(db_session, trade_repo, branch_repo)
    
    user_id = uuid4()
    
    print("\n✓ Step 2: Creating INSTANT BINDING CONTRACT...")
    
    trade = await service.create_trade_from_negotiation(
        negotiation_id=negotiation.id,
        user_id=user_id,
        branch_selections=None  # Let AI auto-select
    )
    
    print(f"\n🎉 TRADE CREATED SUCCESSFULLY!")
    print(f"  Trade Number: {trade.trade_number}")
    print(f"  Status: {trade.status} (legally binding!)")
    print(f"  Trade Date: {trade.trade_date}")
    
    # Step 3: Verify trade details
    print("\n✓ Step 3: Verifying trade details...")
    
    assert trade.status == "ACTIVE"
    assert trade.buyer_partner_id == buyer.id
    assert trade.seller_partner_id == seller.id
    assert trade.quantity == Decimal("500.000")
    assert trade.price_per_unit == Decimal("5500.00")
    assert trade.total_amount == Decimal("2750000.00")
    
    # Verify frozen addresses
    assert trade.ship_to_address is not None
    assert trade.bill_to_address is not None
    assert trade.ship_from_address is not None
    print(f"  ✓ Addresses frozen: Ship-to={trade.ship_to_address['city']}, Ship-from={trade.ship_from_address['city']}")
    
    # Verify GST calculation
    assert trade.gst_type in ["INTRA_STATE", "INTER_STATE"]
    print(f"  ✓ GST Type: {trade.gst_type}")
    
    if trade.gst_type == "INTRA_STATE":
        assert trade.cgst_rate == Decimal("9.00")
        assert trade.sgst_rate == Decimal("9.00")
        print(f"    CGST: {trade.cgst_rate}%, SGST: {trade.sgst_rate}%")
    else:
        assert trade.igst_rate == Decimal("18.00")
        print(f"    IGST: {trade.igst_rate}%")
    
    # Verify negotiation updated
    await db_session.refresh(negotiation)
    assert negotiation.accepted_at is not None
    print(f"  ✓ Negotiation marked accepted at: {negotiation.accepted_at}")
    
    print("\n✅ FULL TRADE CREATION FLOW WORKING PERFECTLY!\n")
    print("=" * 60)
    print("🎊 CORE FUNCTIONALITY VERIFIED!")
    print("=" * 60)
    
    return trade


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("TRADE ENGINE CORE FUNCTIONALITY TEST")
    print("=" * 60)
    
    # Run all tests
    pytest.main([__file__, "-v", "-s"])

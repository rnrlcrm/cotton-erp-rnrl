"""
Integration Tests for Trade Desk Module with Testcontainers + PostgreSQL

Tests FK fixes:
1. Requirement.buyer_partner_id → business_partners.id (not partners.id)
2. Requirement.buyer_branch_id → partner_locations.id (not branches.id)
3. Availability.seller_branch_id → partner_locations.id (not branches.id)
4. Complete CRUD operations
5. FK integrity checks
"""
import uuid
from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.modules.trade_desk.models.requirement import Requirement
from backend.modules.trade_desk.models.availability import Availability
from backend.modules.partners.models import BusinessPartner, PartnerLocation
from .conftest import create_test_partner


class TestRequirementFKFixes:
    """Test Requirement model FK fixes."""
    
    @pytest.mark.asyncio
    async def test_create_requirement_with_correct_buyer_partner_fk(
        self, db_session: AsyncSession, seed_commodities, seed_payment_terms, seed_locations
    ):
        """✅ Test: Requirement.buyer_partner_id correctly references business_partners.id."""
        # Create buyer partner
        buyer = create_test_partner("buyer", "Cotton Buyer Ltd")
        db_session.add(buyer)
        await db_session.flush()
        
        # Create requirement with buyer_partner_id
        requirement = Requirement(
            id=uuid.uuid4(),
            buyer_partner_id=buyer.id,  # FK to business_partners.id ✅
            commodity_id=seed_commodities[0].id,
            quantity_required=Decimal("1000.00"),
            unit="kg",
            delivery_location_id=seed_locations[0].id,
            payment_term_id=seed_payment_terms[0].id,
            status="open"
        )
        
        db_session.add(requirement)
        await db_session.flush()
        
        # Verify FK integrity
        result = await db_session.execute(
            select(Requirement).where(Requirement.id == requirement.id)
        )
        created_req = result.scalar_one()
        
        assert created_req.buyer_partner_id == buyer.id
        # Verify FK relationship works
        assert created_req.buyer_partner.legal_name == "Buyer Corp"
    
    @pytest.mark.asyncio
    async def test_create_requirement_with_correct_buyer_branch_fk(
        self, db_session: AsyncSession, seed_commodities, seed_payment_terms, seed_locations
    ):
        """✅ Test: Requirement.buyer_branch_id correctly references partner_locations.id."""
        # Create buyer partner
        buyer = create_test_partner("buyer", "Multi-Branch Buyer")
        db_session.add(buyer)
        await db_session.flush()
        
        # Create buyer branch
        buyer_branch = PartnerLocation(
            id=uuid.uuid4(),
            partner_id=buyer.id,
            location_type="branch_different_state",
            location_name="Mumbai Branch",
            address="123 Street",
            city="Mumbai",
            state="Maharashtra",
            postal_code="400001",
            country="India"
        )
        db_session.add(buyer_branch)
        await db_session.flush()
        
        # Create requirement with buyer_branch_id
        requirement = Requirement(
            id=uuid.uuid4(),
            buyer_partner_id=buyer.id,
            buyer_branch_id=buyer_branch.id,  # FK to partner_locations.id ✅
            commodity_id=seed_commodities[0].id,
            quantity_required=Decimal("500.00"),
            unit="kg",
            delivery_location_id=seed_locations[0].id,
            payment_term_id=seed_payment_terms[0].id,
            status="open"
        )
        
        db_session.add(requirement)
        await db_session.flush()
        
        # Verify FK integrity
        result = await db_session.execute(
            select(Requirement).where(Requirement.id == requirement.id)
        )
        created_req = result.scalar_one()
        
        assert created_req.buyer_branch_id == buyer_branch.id
        # Verify FK relationship works
        assert created_req.buyer_branch.location_name == "Mumbai Branch"
    
    @pytest.mark.asyncio
    async def test_requirement_fk_cascade_on_partner_delete(
        self, db_session: AsyncSession, seed_commodities, seed_payment_terms, seed_locations
    ):
        """✅ Test: Deleting BusinessPartner handles requirement FK correctly."""
        # Create buyer
        buyer = create_test_partner("buyer", "Temporary Buyer")
        db_session.add(buyer)
        await db_session.flush()
        
        # Create requirement
        requirement = Requirement(
            id=uuid.uuid4(),
            buyer_partner_id=buyer.id,
            commodity_id=seed_commodities[0].id,
            quantity_required=Decimal("100.00"),
            unit="kg",
            delivery_location_id=seed_locations[0].id,
            payment_term_id=seed_payment_terms[0].id,
            status="open"
        )
        db_session.add(requirement)
        await db_session.flush()
        
        # Delete buyer (FK should handle this - SET NULL or RESTRICT based on schema)
        await db_session.delete(buyer)
        await db_session.flush()
        
        # Verify requirement still exists or deleted based on FK constraint
        result = await db_session.execute(
            select(Requirement).where(Requirement.id == requirement.id)
        )
        req_after_delete = result.scalar_one_or_none()
        
        # Should either be deleted (CASCADE) or have buyer_partner_id=NULL (SET NULL)
        if req_after_delete:
            assert req_after_delete.buyer_partner_id is None


class TestAvailabilityFKFixes:
    """Test Availability model FK fixes."""
    
    @pytest.mark.asyncio
    async def test_create_availability_with_correct_seller_branch_fk(
        self, db_session: AsyncSession, seed_commodities, seed_payment_terms, seed_locations
    ):
        """✅ Test: Availability.seller_branch_id correctly references partner_locations.id."""
        # Create seller partner
        seller = create_test_partner("seller", "Multi-Branch Seller")
        db_session.add(seller)
        await db_session.flush()
        
        # Create seller branch
        seller_branch = PartnerLocation(
            id=uuid.uuid4(),
            partner_id=seller.id,
            location_type="warehouse",
            location_name="Delhi Warehouse",
            address="456 Road",
            city="Delhi",
            state="Delhi",
            postal_code="110001",
            country="India"
        )
        db_session.add(seller_branch)
        await db_session.flush()
        
        # Create availability with seller_branch_id
        availability = Availability(
            id=uuid.uuid4(),
            seller_partner_id=seller.id,
            seller_branch_id=seller_branch.id,  # FK to partner_locations.id ✅
            commodity_id=seed_commodities[0].id,
            quantity_available=Decimal("2000.00"),
            unit="kg",
            price_per_unit=Decimal("50.00"),
            pickup_location_id=seed_locations[1].id,
            payment_term_id=seed_payment_terms[0].id,
            status="available"
        )
        
        db_session.add(availability)
        await db_session.flush()
        
        # Verify FK integrity
        result = await db_session.execute(
            select(Availability).where(Availability.id == availability.id)
        )
        created_avail = result.scalar_one()
        
        assert created_avail.seller_branch_id == seller_branch.id
        # Verify FK relationship works
        assert created_avail.seller_branch.location_name == "Delhi Warehouse"
    
    @pytest.mark.asyncio
    async def test_availability_fk_cascade_on_branch_delete(
        self, db_session: AsyncSession, seed_commodities, seed_payment_terms, seed_locations
    ):
        """✅ Test: Deleting PartnerLocation handles availability FK correctly."""
        # Create seller
        seller = create_test_partner("seller", "Seller With Branch")
        db_session.add(seller)
        await db_session.flush()
        
        # Create seller branch
        seller_branch = PartnerLocation(
            id=uuid.uuid4(),
            partner_id=seller.id,
            location_type="branch_different_state",
            location_name="Temporary Branch",
            address="Temp Address",
            city="Bangalore",
            state="Karnataka",
            postal_code="560001",
            country="India"
        )
        db_session.add(seller_branch)
        await db_session.flush()
        
        # Create availability
        availability = Availability(
            id=uuid.uuid4(),
            seller_partner_id=seller.id,
            seller_branch_id=seller_branch.id,
            commodity_id=seed_commodities[0].id,
            quantity_available=Decimal("500.00"),
            unit="kg",
            price_per_unit=Decimal("45.00"),
            pickup_location_id=seed_locations[2].id,
            payment_term_id=seed_payment_terms[0].id,
            status="available"
        )
        db_session.add(availability)
        await db_session.flush()
        
        # Delete branch
        await db_session.delete(seller_branch)
        await db_session.flush()
        
        # Verify availability updated (FK SET NULL or CASCADE)
        result = await db_session.execute(
            select(Availability).where(Availability.id == availability.id)
        )
        avail_after_delete = result.scalar_one_or_none()
        
        if avail_after_delete:
            assert avail_after_delete.seller_branch_id is None


class TestTradeDeskCompleteWorkflow:
    """Test complete trade desk workflow with fixed FKs."""
    
    @pytest.mark.asyncio
    async def test_complete_buyer_seller_workflow(
        self, db_session: AsyncSession, seed_commodities, seed_payment_terms, seed_locations
    ):
        """✅ Test: Complete workflow - buyer requirement + seller availability with correct FKs."""
        # Create buyer
        buyer = create_test_partner("buyer", "Cotton Buyer Ltd")
        db_session.add(buyer)
        
        # Create buyer branch
        buyer_branch = PartnerLocation(
            id=uuid.uuid4(),
            partner_id=buyer.id,
            location_type="principal",
            location_name="Buyer HQ",
            address="Buyer Address",
            city="Mumbai",
            postal_code="400001",
            country="India"
        )
        db_session.add(buyer_branch)
        
        # Create seller
        seller = create_test_partner("seller", "Cotton Seller Corp")
        db_session.add(seller)
        
        # Create seller branch
        seller_branch = PartnerLocation(
            id=uuid.uuid4(),
            partner_id=seller.id,
            location_type="warehouse",
            location_name="Seller Warehouse",
            address="Seller Address",
            city="Mumbai",
            postal_code="400002",
            country="India"
        )
        db_session.add(seller_branch)
        
        await db_session.flush()
        
        # Create buyer requirement
        requirement = Requirement(
            id=uuid.uuid4(),
            buyer_partner_id=buyer.id,  # ✅ Correct FK
            buyer_branch_id=buyer_branch.id,  # ✅ Correct FK
            commodity_id=seed_commodities[0].id,
            quantity_required=Decimal("1000.00"),
            unit="kg",
            max_price_per_unit=Decimal("55.00"),
            delivery_location_id=seed_locations[0].id,
            payment_term_id=seed_payment_terms[0].id,
            status="open"
        )
        db_session.add(requirement)
        
        # Create seller availability
        availability = Availability(
            id=uuid.uuid4(),
            seller_partner_id=seller.id,  # ✅ Correct FK
            seller_branch_id=seller_branch.id,  # ✅ Correct FK
            commodity_id=seed_commodities[0].id,
            quantity_available=Decimal("2000.00"),
            unit="kg",
            price_per_unit=Decimal("50.00"),
            pickup_location_id=seed_locations[0].id,
            payment_term_id=seed_payment_terms[0].id,
            status="available"
        )
        db_session.add(availability)
        
        await db_session.flush()
        
        # Verify all FKs work correctly
        req_result = await db_session.execute(
            select(Requirement).where(Requirement.id == requirement.id)
        )
        created_req = req_result.scalar_one()
        
        avail_result = await db_session.execute(
            select(Availability).where(Availability.id == availability.id)
        )
        created_avail = avail_result.scalar_one()
        
        # Verify buyer relationships
        assert created_req.buyer_partner_id == buyer.id
        assert created_req.buyer_branch_id == buyer_branch.id
        assert created_req.buyer_partner.legal_name == "Cotton Buyer Ltd"
        assert created_req.buyer_branch.location_name == "Buyer HQ"
        
        # Verify seller relationships
        assert created_avail.seller_partner_id == seller.id
        assert created_avail.seller_branch_id == seller_branch.id
        assert created_avail.seller_partner.legal_name == "Cotton Seller Corp"
        assert created_avail.seller_branch.location_name == "Seller Warehouse"
        
        # Verify matching criteria (location, commodity, price)
        assert created_req.delivery_location_id == created_avail.pickup_location_id
        assert created_req.commodity_id == created_avail.commodity_id
        assert created_avail.price_per_unit <= created_req.max_price_per_unit

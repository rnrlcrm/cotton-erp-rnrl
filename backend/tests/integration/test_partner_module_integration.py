"""
Integration Tests for Partner Module with Testcontainers + PostgreSQL

Tests:
1. BusinessPartner CRUD without organization_id
2. PartnerLocation CRUD (belongs to partner only)
3. PartnerEmployee CRUD (no organization_id)
4. PartnerDocument CRUD (no organization_id)
5. PartnerVehicle CRUD (no organization_id)
6. PartnerOnboardingApplication with nullable organization_id
7. FK integrity checks
"""
import uuid
from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.modules.partners.models import (
    BusinessPartner,
    PartnerLocation,
    PartnerEmployee,
    PartnerDocument,
    PartnerVehicle,
    PartnerOnboardingApplication,
)
from .conftest import create_test_partner


class TestBusinessPartnerCRUD:
    """Test BusinessPartner without organization_id."""
    
    @pytest.mark.asyncio
    async def test_create_business_partner_without_organization_id(
        self, db_session: AsyncSession
    ):
        """✅ Test: Create BusinessPartner WITHOUT organization_id (external entity)."""
        partner = create_test_partner("buyer", "External Buyer Corp")
        
        db_session.add(partner)
        await db_session.flush()
        
        # Verify created
        result = await db_session.execute(
            select(BusinessPartner).where(BusinessPartner.id == partner.id)
        )
        created_partner = result.scalar_one()
        
        assert created_partner.legal_name == "External Buyer Corp"
        assert created_partner.partner_type == "buyer"
        assert created_partner.bank_account_name == "External Buyer Corp"
        # Verify NO organization_id attribute
        assert not hasattr(created_partner, 'organization_id')
    
    @pytest.mark.asyncio
    async def test_update_business_partner(
        self, db_session: AsyncSession
    ):
        """✅ Test: Update BusinessPartner."""
        partner = create_test_partner("seller", "Seller Corp")
        partner.status = "pending"
        
        db_session.add(partner)
        await db_session.flush()
        
        # Update status
        partner.status = "active"
        partner.trade_name = "Seller Trading Co"
        await db_session.flush()
        
        # Verify updated
        result = await db_session.execute(
            select(BusinessPartner).where(BusinessPartner.id == partner.id)
        )
        updated_partner = result.scalar_one()
        
        assert updated_partner.status == "active"
        assert updated_partner.trade_name == "Seller Trading Co"
    
    @pytest.mark.asyncio
    async def test_delete_business_partner_cascades_to_locations(
        self, db_session: AsyncSession
    ):
        """✅ Test: Deleting BusinessPartner cascades to PartnerLocations."""
        partner = create_test_partner("buyer", "Test Partner")
        db_session.add(partner)
        await db_session.flush()
        
        # Add location
        location = PartnerLocation(
            id=uuid.uuid4(),
            partner_id=partner.id,
            location_type="principal",
            location_name="Main Office",
            address="123 Street",
            city="Mumbai",
            postal_code="400001",
            country="India"
        )
        db_session.add(location)
        await db_session.flush()
        
        # Delete partner
        await db_session.delete(partner)
        await db_session.flush()
        
        # Verify location also deleted (CASCADE)
        result = await db_session.execute(
            select(PartnerLocation).where(PartnerLocation.id == location.id)
        )
        assert result.scalar_one_or_none() is None


class TestPartnerLocationCRUD:
    """Test PartnerLocation belongs to partner only (no organization_id)."""
    
    @pytest.mark.asyncio
    async def test_create_partner_location_without_organization_id(
        self, db_session: AsyncSession
    ):
        """✅ Test: Create PartnerLocation WITHOUT organization_id."""
        partner = create_test_partner("seller", "Seller With Branches")
        db_session.add(partner)
        await db_session.flush()
        
        location = PartnerLocation(
            id=uuid.uuid4(),
            partner_id=partner.id,
            location_type="branch_different_state",
            location_name="Gujarat Branch",
            address="456 Road",
            city="Ahmedabad",
            state="Gujarat",
            postal_code="380001",
            country="India",
            gstin_for_location="24AAAAA0000A1Z5"
        )
        
        db_session.add(location)
        await db_session.flush()
        
        # Verify created
        result = await db_session.execute(
            select(PartnerLocation).where(PartnerLocation.id == location.id)
        )
        created_location = result.scalar_one()
        
        assert created_location.location_name == "Gujarat Branch"
        assert created_location.partner_id == partner.id
        # Verify NO organization_id
        assert not hasattr(created_location, 'organization_id')
    
    @pytest.mark.asyncio
    async def test_partner_with_multiple_locations(
        self, db_session: AsyncSession
    ):
        """✅ Test: Partner can have multiple locations."""
        partner = create_test_partner("transporter", "Multi-Location Transporter")
        db_session.add(partner)
        await db_session.flush()
        
        locations = [
            PartnerLocation(
                id=uuid.uuid4(),
                partner_id=partner.id,
                location_type="principal",
                location_name="HQ Mumbai",
                address="HQ Address",
                city="Mumbai",
                postal_code="400001",
                country="India"
            ),
            PartnerLocation(
                id=uuid.uuid4(),
                partner_id=partner.id,
                location_type="warehouse",
                location_name="Warehouse Delhi",
                address="Warehouse Address",
                city="Delhi",
                postal_code="110001",
                country="India"
            ),
        ]
        
        for loc in locations:
            db_session.add(loc)
        await db_session.flush()
        
        # Verify all locations belong to partner
        result = await db_session.execute(
            select(PartnerLocation).where(PartnerLocation.partner_id == partner.id)
        )
        partner_locations = result.scalars().all()
        
        assert len(partner_locations) == 2
        assert all(loc.partner_id == partner.id for loc in partner_locations)


class TestPartnerEmployeeCRUD:
    """Test PartnerEmployee without organization_id."""
    
    @pytest.mark.asyncio
    async def test_create_partner_employee_without_organization_id(
        self, db_session: AsyncSession, seed_organization
    ):
        """✅ Test: Create PartnerEmployee WITHOUT organization_id."""
        from backend.modules.settings.models.settings_models import User
        
        # Create partner
        partner = create_test_partner("buyer", "Buyer With Employees")
        db_session.add(partner)
        await db_session.flush()
        
        # Create user (EXTERNAL type - belongs to partner)
        user = User(
            id=uuid.uuid4(),
            user_type="EXTERNAL",
            business_partner_id=partner.id,
            mobile_number="+919876543210",
            full_name="Partner Employee",
            is_active=True,
            is_verified=True
        )
        db_session.add(user)
        await db_session.flush()
        
        # Create employee
        employee = PartnerEmployee(
            id=uuid.uuid4(),
            partner_id=partner.id,
            user_id=user.id,
            employee_name="John Doe",
            employee_email="john@partner.com",
            employee_phone="+919876543210",
            role="employee"
        )
        
        db_session.add(employee)
        await db_session.flush()
        
        # Verify created
        result = await db_session.execute(
            select(PartnerEmployee).where(PartnerEmployee.id == employee.id)
        )
        created_employee = result.scalar_one()
        
        assert created_employee.employee_name == "John Doe"
        assert created_employee.partner_id == partner.id
        # Verify NO organization_id
        assert not hasattr(created_employee, 'organization_id')


class TestPartnerDocumentCRUD:
    """Test PartnerDocument without organization_id."""
    
    @pytest.mark.asyncio
    async def test_create_partner_document_without_organization_id(
        self, db_session: AsyncSession
    ):
        """✅ Test: Create PartnerDocument WITHOUT organization_id."""
        partner = create_test_partner("seller", "Seller With Documents")
        db_session.add(partner)
        await db_session.flush()
        
        document = PartnerDocument(
            id=uuid.uuid4(),
            partner_id=partner.id,
            document_type="gst_certificate",
            country="India",
            file_url="https://storage.example.com/gst.pdf",
            file_name="gst_certificate.pdf",
            verified=False
        )
        
        db_session.add(document)
        await db_session.flush()
        
        # Verify created
        result = await db_session.execute(
            select(PartnerDocument).where(PartnerDocument.id == document.id)
        )
        created_doc = result.scalar_one()
        
        assert created_doc.document_type == "gst_certificate"
        assert created_doc.partner_id == partner.id
        # Verify NO organization_id
        assert not hasattr(created_doc, 'organization_id')


class TestPartnerVehicleCRUD:
    """Test PartnerVehicle without organization_id."""
    
    @pytest.mark.asyncio
    async def test_create_partner_vehicle_without_organization_id(
        self, db_session: AsyncSession
    ):
        """✅ Test: Create PartnerVehicle WITHOUT organization_id."""
        partner = create_test_partner("transporter", "Transporter With Fleet")
        db_session.add(partner)
        await db_session.flush()
        
        vehicle = PartnerVehicle(
            id=uuid.uuid4(),
            partner_id=partner.id,
            vehicle_number="MH01AB1234",
            vehicle_type="truck",
            capacity_tons=Decimal("10.00"),
            status="active"
        )
        
        db_session.add(vehicle)
        await db_session.flush()
        
        # Verify created
        result = await db_session.execute(
            select(PartnerVehicle).where(PartnerVehicle.id == vehicle.id)
        )
        created_vehicle = result.scalar_one()
        
        assert created_vehicle.vehicle_number == "MH01AB1234"
        assert created_vehicle.partner_id == partner.id
        # Verify NO organization_id
        assert not hasattr(created_vehicle, 'organization_id')


class TestPartnerOnboardingApplication:
    """Test PartnerOnboardingApplication with nullable organization_id."""
    
    @pytest.mark.asyncio
    async def test_create_onboarding_application_without_organization_id(
        self, db_session: AsyncSession, seed_organization
    ):
        """✅ Test: Create onboarding application with NULL organization_id (auto-defaults to main)."""
        from backend.modules.settings.models.settings_models import User
        
        # Create user (INTERNAL type - pre-signup user applying for partner status)
        user = User(
            id=uuid.uuid4(),
            user_type="INTERNAL",
            organization_id=seed_organization.id,
            mobile_number="+919999999999",
            full_name="New Applicant",
            is_active=True,
            is_verified=False
        )
        db_session.add(user)
        await db_session.flush()
        
        # Create onboarding application WITHOUT organization_id
        application = PartnerOnboardingApplication(
            id=uuid.uuid4(),
            user_id=user.id,
            # organization_id=None,  # NULL - will auto-default to main company
            partner_type="buyer",
            legal_name="New Buyer Application",
            country="India",
            bank_account_name="New Buyer",
            bank_name="HDFC Bank",
            bank_account_number="1234567890",
            bank_routing_code="HDFC0001234",
            primary_address="Application Address",
            primary_city="Mumbai",
            primary_postal_code="400001",
            primary_country="India",
            primary_contact_name="Contact Person",
            primary_contact_email="contact@newbuyer.com",
            primary_contact_phone="+919999999999",
            primary_currency="INR",
            status="pending"
        )
        
        db_session.add(application)
        await db_session.flush()
        
        # Verify created with NULL organization_id
        result = await db_session.execute(
            select(PartnerOnboardingApplication).where(
                PartnerOnboardingApplication.id == application.id
            )
        )
        created_app = result.scalar_one()
        
        assert created_app.legal_name == "New Buyer Application"
        assert created_app.organization_id is None  # NULL allowed
    
    @pytest.mark.asyncio
    async def test_create_onboarding_application_with_organization_id(
        self, db_session: AsyncSession, seed_organization
    ):
        """✅ Test: Create onboarding application WITH organization_id (tracks which company processed it)."""
        from backend.modules.settings.models.settings_models import User
        
        # Create user (INTERNAL type - pre-signup user applying for partner status)
        user = User(
            id=uuid.uuid4(),
            user_type="INTERNAL",
            organization_id=seed_organization.id,
            mobile_number="+918888888888",
            full_name="Another Applicant",
            is_active=True,
            is_verified=False
        )
        db_session.add(user)
        await db_session.flush()
        
        # Create onboarding application WITH organization_id
        application = PartnerOnboardingApplication(
            id=uuid.uuid4(),
            user_id=user.id,
            organization_id=seed_organization.id,  # Explicitly set to main company
            partner_type="seller",
            legal_name="New Seller Application",
            country="India",
            bank_account_name="New Seller",
            bank_name="ICICI Bank",
            bank_account_number="0987654321",
            bank_routing_code="ICIC0004321",
            primary_address="Seller Address",
            primary_city="Delhi",
            primary_postal_code="110001",
            primary_country="India",
            primary_contact_name="Seller Contact",
            primary_contact_email="contact@newseller.com",
            primary_contact_phone="+918888888888",
            primary_currency="INR",
            status="pending"
        )
        
        db_session.add(application)
        await db_session.flush()
        
        # Verify created with organization_id
        result = await db_session.execute(
            select(PartnerOnboardingApplication).where(
                PartnerOnboardingApplication.id == application.id
            )
        )
        created_app = result.scalar_one()
        
        assert created_app.organization_id == seed_organization.id

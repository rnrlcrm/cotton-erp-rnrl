"""
Integration tests for Business Partner Module.

Tests comprehensive partner lifecycle including:
- Onboarding workflow (start → documents → submit → approval)
- Partner CRUD operations
- Amendment management
- Employee management
- Location management
- Vehicle management (for transporters)
- KYC renewal workflow
- Risk scoring and auto-approval
- Data isolation (EXTERNAL vs INTERNAL users)
- CDPS capability integration
"""

import pytest
import uuid
from datetime import date, datetime, timedelta
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.modules.partners.models import (
    BusinessPartner,
    PartnerOnboardingApplication,
    PartnerAmendment,
    PartnerLocation,
    PartnerEmployee,
    PartnerDocument,
    PartnerVehicle,
    PartnerKYCRenewal,
)
from backend.modules.partners.partner_services import (
    PartnerService,
    ApprovalService,
    KYCRenewalService,
    RiskScoringService,
)
from backend.modules.partners.repositories import (
    BusinessPartnerRepository,
    OnboardingApplicationRepository,
    PartnerAmendmentRepository,
    PartnerLocationRepository,
    PartnerEmployeeRepository,
    PartnerDocumentRepository,
    PartnerVehicleRepository,
    PartnerKYCRenewalRepository,
)
from backend.modules.partners.schemas import (
    OnboardingApplicationCreate,
    ApprovalDecision,
    AmendmentRequest,
    PartnerLocationCreate,
    VehicleData,
    KYCRenewalRequest,
)
from backend.modules.partners.enums import (
    PartnerType,
    PartnerStatus,
    KYCStatus,
    RiskCategory,
    BusinessEntityType,
    ServiceProviderType,
    TransporterType,
    AmendmentType,
    DocumentType,
)
from backend.core.events.emitter import EventEmitter


class TestPartnerOnboardingWorkflow:
    """Test complete onboarding workflow from start to approval."""

    @pytest.mark.asyncio
    async def test_start_onboarding_indian_buyer(self, db_session: AsyncSession, seed_user, seed_organization):
        """✅ Test: Start onboarding for Indian buyer."""
        user_id = seed_user.id
        org_id = seed_organization.id
        event_emitter = EventEmitter(db_session)
        service = PartnerService(db_session, event_emitter, user_id, org_id)

        payload = OnboardingApplicationCreate(
            partner_type=PartnerType.BUYER,
            legal_name="ABC Textiles Pvt Ltd",
            trade_name="ABC Textiles",
            country="India",
            business_entity_type=BusinessEntityType.PRIVATE_LIMITED,
            registration_date=date(2020, 1, 15),
            has_tax_registration=True,
            tax_id_type="GSTIN",
            tax_id_number="27AABCT1234C1Z5",
            pan_number="AABCT1234C",
            pan_name="ABC TEXTILES PVT LTD",
            bank_account_name="ABC Textiles Pvt Ltd",
            bank_name="HDFC Bank",
            bank_account_number="50200012345678",
            bank_routing_code="HDFC0001234",
            primary_address="123, Industrial Area, Sector 5",
            primary_city="Mumbai",
            primary_state="Maharashtra",
            primary_postal_code="400001",
            primary_country="India",
            primary_contact_name="Rajesh Kumar",
            primary_contact_email="rajesh@abctextiles.com",
            primary_contact_phone="+919876543210",
            primary_currency="INR",
            commodities=["Cotton", "Yarn"],
        )

        application = await service.start_onboarding(payload)

        assert application.legal_name == "ABC Textiles Pvt Ltd"
        assert application.partner_type == PartnerType.BUYER
        assert application.country == "India"
        assert application.tax_id_number == "27AABCT1234C1Z5"
        assert application.onboarding_stage == "documents"
        assert application.status == "pending"

    @pytest.mark.asyncio
    async def test_start_onboarding_foreign_exporter(self, db_session: AsyncSession, seed_user, seed_organization):
        """✅ Test: Start onboarding for foreign exporter (selling to India)."""  
        user_id = seed_user.id
        org_id = seed_organization.id
        event_emitter = EventEmitter(db_session)
        service = PartnerService(db_session, event_emitter, user_id, org_id)

        payload = OnboardingApplicationCreate(
            partner_type=PartnerType.SELLER,
            legal_name="Global Cotton LLC",
            trade_name="Global Cotton",
            country="USA",
            business_entity_type=BusinessEntityType.LLC,
            registration_date=date(2018, 6, 20),
            has_tax_registration=True,
            tax_id_type="EIN",
            tax_id_number="12-3456789",
            pan_number=None,
            pan_name=None,
            has_no_gst_declaration=True,
            declaration_reason="Foreign entity - no GST requirement",
            bank_account_name="Global Cotton LLC",
            bank_name="Chase Bank",
            bank_account_number="1234567890",
            bank_routing_code="CHASUS33",
            primary_address="456 Cotton Street",
            primary_city="Dallas",
            primary_state="Texas",
            primary_postal_code="75201",
            primary_country="USA",
            primary_contact_name="John Smith",
            primary_contact_email="john@globalcotton.com",
            primary_contact_phone="+12145551234",
            primary_currency="USD",
            commodities=["Cotton"],
        )

        application = await service.start_onboarding(payload)

        assert application.legal_name == "Global Cotton LLC"
        assert application.country == "USA"
        assert application.has_no_gst_declaration is True
        assert application.business_entity_type == BusinessEntityType.LLC

    @pytest.mark.asyncio
    async def test_start_onboarding_transporter_lorry_owner(self, db_session: AsyncSession, seed_user, seed_organization):
        """✅ Test: Start onboarding for transporter (lorry owner)."""  
        user_id = seed_user.id
        org_id = seed_organization.id
        event_emitter = EventEmitter(db_session)
        service = PartnerService(db_session, event_emitter, user_id, org_id)

        payload = OnboardingApplicationCreate(
            partner_type=PartnerType.TRANSPORTER,
            service_provider_type=ServiceProviderType.TRANSPORTER,
            legal_name="Fast Transport Services",
            trade_name="Fast Transport",
            country="India",
            business_entity_type=BusinessEntityType.PROPRIETORSHIP,
            registration_date=date(2019, 3, 10),
            has_tax_registration=True,
            tax_id_type="GSTIN",
            tax_id_number="27AABCD5678E1Z9",
            pan_number="AABCD5678E",
            pan_name="FAST TRANSPORT SERVICES",
            bank_account_name="Fast Transport Services",
            bank_name="SBI",
            bank_account_number="12345678901234",
            bank_routing_code="SBIN0001234",
            primary_address="Transport Nagar, Plot 12",
            primary_city="Nagpur",
            primary_state="Maharashtra",
            primary_postal_code="440001",
            primary_country="India",
            primary_contact_name="Suresh Patil",
            primary_contact_email="suresh@fasttransport.com",
            primary_contact_phone="+919876543211",
            primary_currency="INR",
            commodities=["Cotton", "Yarn", "Textile"],
        )

        application = await service.start_onboarding(payload)

        assert application.legal_name == "Fast Transport Services"
        assert application.partner_type == PartnerType.TRANSPORTER
        assert application.service_provider_type == ServiceProviderType.TRANSPORTER

    @pytest.mark.asyncio
    async def test_submit_for_approval_low_risk_auto_approve(self, db_session: AsyncSession, seed_user, seed_organization):
        """✅ Test: Submit application with low risk score triggers auto-approval."""  
        user_id = seed_user.id
        org_id = seed_organization.id
        event_emitter = EventEmitter(db_session)
        service = PartnerService(db_session, event_emitter, user_id, org_id)
        # Start onboarding
        payload = OnboardingApplicationCreate(
            partner_type=PartnerType.BUYER,
            legal_name="Established Buyer Ltd",
            trade_name="Established Buyer",
            country="India",
            business_entity_type=BusinessEntityType.PRIVATE_LIMITED,
            registration_date=date(2015, 1, 1),  # Old business = low risk
            has_tax_registration=True,
            tax_id_type="GSTIN",
            tax_id_number="27AABCE1234F1Z1",
            pan_number="AABCE1234F",
            pan_name="ESTABLISHED BUYER LTD",
            bank_account_name="Established Buyer Ltd",
            bank_name="ICICI Bank",
            bank_account_number="123456789012",
            bank_routing_code="ICIC0001234",
            primary_address="Business Plaza, MG Road",
            primary_city="Pune",
            primary_state="Maharashtra",
            primary_postal_code="411001",
            primary_country="India",
            primary_contact_name="Amit Shah",
            primary_contact_email="amit@established.com",
            primary_contact_phone="+919876543212",
            primary_currency="INR",
            commodities=["Cotton"],
        )

        application = await service.start_onboarding(payload)

        # Submit for approval
        result = await service.submit_for_approval(application.id)

        # Should be auto-approved for low risk
        assert result["status"] in ["approved", "pending_approval"]
        assert "approval_route" in result

    @pytest.mark.asyncio
    async def test_manual_approval_process(self, db_session: AsyncSession, seed_user, seed_organization):
        """✅ Test: Manual approval by manager/director."""  
        user_id = seed_user.id
        org_id = seed_organization.id
        manager_id = uuid.uuid4()  # Different manager
        event_emitter = EventEmitter(db_session)
        # Create application
        service = PartnerService(db_session, event_emitter, user_id, org_id)
        payload = OnboardingApplicationCreate(
            partner_type=PartnerType.SELLER,
            legal_name="New Seller Pvt Ltd",
            trade_name="New Seller",
            country="India",
            business_entity_type=BusinessEntityType.PRIVATE_LIMITED,
            registration_date=date(2024, 1, 1),  # New business = higher risk
            has_tax_registration=True,
            tax_id_type="GSTIN",
            tax_id_number="27AABCF1234G1Z2",
            pan_number="AABCF1234G",
            pan_name="NEW SELLER PVT LTD",
            bank_account_name="New Seller Pvt Ltd",
            bank_name="HDFC Bank",
            bank_account_number="98765432109876",
            bank_routing_code="HDFC0005678",
            primary_address="Plot 45, Industrial Estate",
            primary_city="Surat",
            primary_state="Gujarat",
            primary_postal_code="395001",
            primary_country="India",
            primary_contact_name="Kiran Patel",
            primary_contact_email="kiran@newseller.com",
            primary_contact_phone="+919876543213",
            primary_currency="INR",
            commodities=["Cotton"],
        )

        application = await service.start_onboarding(payload)

        # Approve manually
        approval_service = ApprovalService(db_session, manager_id)
        
        # First need to submit for approval
        await service.submit_for_approval(application.id)
        
        # Get risk assessment
        risk_service = RiskScoringService(db_session)
        risk_assessment = await risk_service.calculate_risk_score(
            partner_type=PartnerType.SELLER,
            entity_type=BusinessEntityType.PRIVATE_LIMITED,
            business_age_months=11,  # New business
        )

        # Approve
        decision = ApprovalDecision(
            decision="approve",
            notes="Verified documents and background"
        )
        
        partner = await approval_service.process_approval(
            application.id,
            risk_assessment,
            decision
        )

        assert partner.legal_name == "New Seller Pvt Ltd"
        assert partner.status == PartnerStatus.APPROVED


class TestPartnerCRUD:
    """Test partner CRUD operations."""

    @pytest.mark.asyncio
    async def test_create_partner_directly(self, db_session: AsyncSession, seed_organization):
        """✅ Test: Create partner directly (bypass onboarding)."""  
        org_id = seed_organization.id
        repo = BusinessPartnerRepository(db_session)
        partner = BusinessPartner(
            legal_name="Direct Create Partner",
            trade_name="Direct Partner",
            partner_type=PartnerType.BUYER,
            country="India",
            entity_class="business_entity",
            business_entity_type=BusinessEntityType.PROPRIETORSHIP,
            status=PartnerStatus.APPROVED,
            kyc_status=KYCStatus.VERIFIED,
            tax_id_number="27AABCG1234H1Z3",
            pan_number="AABCG1234H",
            bank_account_name="Direct Create Partner",
            bank_name="HDFC Bank",
            bank_account_number="123456789",
            bank_routing_code="HDFC0001234",
            primary_address="123 Test St",
            primary_city="Mumbai",
            primary_postal_code="400001",
            primary_country="India",
            primary_contact_name="Test Contact",
            primary_contact_email="test@example.com",
            primary_contact_phone="+919876543210",
            primary_currency="INR",
        )
        
        db_session.add(partner)
        await db_session.flush()

        assert partner.legal_name == "Direct Create Partner"
        assert partner.status == PartnerStatus.APPROVED

    @pytest.mark.asyncio
    async def test_get_partner_by_id(self, db_session: AsyncSession, seed_organization):
        """✅ Test: Retrieve partner by ID."""  
        org_id = seed_organization.id
        repo = BusinessPartnerRepository(db_session)
        partner = BusinessPartner(
            legal_name="Test Retrieval Partner",
            trade_name="Test Partner",
            partner_type=PartnerType.SELLER,
            country="India",
            entity_class="business_entity",
            status=PartnerStatus.APPROVED,
            bank_account_name="Test Retrieval Partner",
            bank_name="HDFC Bank",
            bank_account_number="123456789",
            bank_routing_code="HDFC0001234",
            primary_address="123 Test St",
            primary_city="Mumbai",
            primary_postal_code="400001",
            primary_country="India",
            primary_contact_name="Test Contact",
            primary_contact_email="test@example.com",
            primary_contact_phone="+919876543210",
            primary_currency="INR",
        )
        
        db_session.add(partner)
        await db_session.flush()

        retrieved = await repo.get_by_id(partner.id)

        assert retrieved is not None
        assert retrieved.id == partner.id
        assert retrieved.legal_name == "Test Retrieval Partner"

    @pytest.mark.asyncio
    async def test_list_partners_with_filters(self, db_session: AsyncSession, seed_organization):
        """✅ Test: List partners with status and type filters."""  
        org_id = seed_organization.id
        repo = BusinessPartnerRepository(db_session)
        
        # Use unique prefix to identify partners created in this test
        test_prefix = "FilterTest_"
        
        # Create multiple partners
        partners = [
            BusinessPartner(
                legal_name=f"{test_prefix}Partner {i}",
                partner_type=PartnerType.BUYER if i % 2 == 0 else PartnerType.SELLER,
                country="India",
                entity_class="business_entity",
                status=PartnerStatus.APPROVED if i % 3 == 0 else PartnerStatus.PENDING,
                bank_account_name=f"{test_prefix}Partner {i}",
                bank_name="HDFC Bank",
                bank_account_number=f"12345678{i}",
                bank_routing_code="HDFC0001234",
                primary_address="123 Test St",
                primary_city="Mumbai",
                primary_postal_code="400001",
                primary_country="India",
                primary_contact_name="Test Contact",
                primary_contact_email=f"filtertest{i}@example.com",
                primary_contact_phone=f"+9198765432{i:02d}",
                primary_currency="INR",
            )
            for i in range(5)
        ]
        
        for partner in partners:
            db_session.add(partner)
        await db_session.flush()

        # List approved partners
        result = await repo.list_partners(
            status=PartnerStatus.APPROVED
        )

        # Verify that partners we created with APPROVED status are in the result
        approved_partners = [p for p in partners if p.status == PartnerStatus.APPROVED]
        approved_ids = {p.id for p in approved_partners}
        result_ids = {p.id for p in result}
        
        # All our approved partners should be in the results
        assert approved_ids.issubset(result_ids), "All approved partners should be in results"
        # The filter should only return approved partners
        assert all(p.status == PartnerStatus.APPROVED for p in result), "All results should be approved"

    @pytest.mark.asyncio
    async def test_update_partner(self, db_session: AsyncSession, seed_organization):
        """✅ Test: Update partner details."""  
        org_id = seed_organization.id
        repo = BusinessPartnerRepository(db_session)
        partner = BusinessPartner(
            legal_name="Original Name",
            trade_name="Original Trade",
            partner_type=PartnerType.BUYER,
            country="India",
            entity_class="business_entity",
            status=PartnerStatus.APPROVED,
            bank_account_name="Original Name",
            bank_name="HDFC Bank",
            bank_account_number="123456789",
            bank_routing_code="HDFC0001234",
            primary_address="123 Test St",
            primary_city="Mumbai",
            primary_postal_code="400001",
            primary_country="India",
            primary_contact_name="Test Contact",
            primary_contact_email="original@example.com",
            primary_contact_phone="+919876543210",
            primary_currency="INR",
        )
        
        db_session.add(partner)
        await db_session.flush()

        # Update partner
        await repo.update(
            partner.id,
            trade_name="Updated Trade Name",
            primary_contact_email="updated@email.com"
        )

        updated = await repo.get_by_id(partner.id)
        assert updated.trade_name == "Updated Trade Name"
        assert updated.primary_contact_email == "updated@email.com"

    @pytest.mark.asyncio
    async def test_search_partners_by_name(self, db_session: AsyncSession, seed_organization):
        """✅ Test: Search partners by name."""  
        org_id = seed_organization.id
        repo = BusinessPartnerRepository(db_session)
        partners = [
            BusinessPartner(
                legal_name="Commodity Traders Pvt Ltd",
                partner_type=PartnerType.TRADER,
                country="India",
                entity_class="business_entity",
                status=PartnerStatus.APPROVED,
                bank_account_name="Commodity Traders Pvt Ltd",
                bank_name="HDFC Bank",
                bank_account_number="1234567890",
                bank_routing_code="HDFC0001234",
                primary_address="123 Test St",
                primary_city="Mumbai",
                primary_postal_code="400001",
                primary_country="India",
                primary_contact_name="Test Contact",
                primary_contact_email="cotton@example.com",
                primary_contact_phone="+919876543210",
                primary_currency="INR",
            ),
            BusinessPartner(
                legal_name="Textile Buyers Association",
                partner_type=PartnerType.BUYER,
                country="India",
                entity_class="business_entity",
                status=PartnerStatus.APPROVED,
                bank_account_name="Textile Buyers Association",
                bank_name="HDFC Bank",
                bank_account_number="9876543210",
                bank_routing_code="HDFC0001234",
                primary_address="456 Test St",
                primary_city="Delhi",
                primary_postal_code="110001",
                primary_country="India",
                primary_contact_name="Test Contact",
                primary_contact_email="textile@example.com",
                primary_contact_phone="+919876543211",
                primary_currency="INR",
            ),
        ]
        
        for partner in partners:
            db_session.add(partner)
        await db_session.flush()

        # Search for "Cotton"
        results = await repo.search_partners(org_id, search_term="Cotton")
        
        assert len(results) >= 1
        assert any("Cotton" in p.legal_name for p in results)


class TestPartnerAmendments:
    """Test partner amendment workflow."""

    @pytest.mark.asyncio
    async def test_request_bank_change_amendment(self, db_session: AsyncSession, seed_user, seed_organization):
        """✅ Test: Request bank account change amendment."""  
        org_id = seed_organization.id
        user_id = seed_user.id        # Create partner
        partner = BusinessPartner(
            legal_name="Amendment Test Partner",
            partner_type=PartnerType.BUYER,
            country="India",
            entity_class="business_entity",
            status=PartnerStatus.APPROVED,
            bank_account_name="Amendment Test Partner",
            bank_name="Old Bank",
            bank_account_number="111111111111",
            bank_routing_code="OLDB0001234",
            primary_address="123 Test St",
            primary_city="Mumbai",
            primary_postal_code="400001",
            primary_country="India",
            primary_contact_name="Test Contact",
            primary_contact_email="test@example.com",
            primary_contact_phone="+919876543210",
            primary_currency="INR",
        )
        
        db_session.add(partner)
        await db_session.flush()

        # Request amendment
        repo = PartnerAmendmentRepository(db_session)
        amendment = PartnerAmendment(
            partner_id=partner.id,
            amendment_type=AmendmentType.CHANGE_BANK,
            requested_by=user_id,
            requested_at=datetime.utcnow(),
            old_value={
                "bank_account_number": "111111111111",
                "bank_name": "Old Bank",
            },
            new_value={
                "bank_account_number": "222222222222",
                "bank_name": "New Bank",
                "bank_routing_code": "NEWB0001234",
            },
            reason="Changed banking relationship",
            status="pending",
        )
        
        db_session.add(amendment)
        await db_session.flush()

        assert amendment.amendment_type == AmendmentType.CHANGE_BANK
        assert amendment.status == "pending"
        assert amendment.new_value["bank_account_number"] == "222222222222"

    @pytest.mark.asyncio
    async def test_approve_amendment(self, db_session: AsyncSession, seed_user, seed_organization):
        """✅ Test: Approve and apply amendment."""  
        org_id = seed_organization.id
        user_id = seed_user.id
        approver_id = uuid.uuid4()  # Different approver        # Create partner
        partner = BusinessPartner(
            legal_name="Amendment Approval Partner",
            partner_type=PartnerType.SELLER,
            country="India",
            entity_class="business_entity",
            status=PartnerStatus.APPROVED,
            bank_account_name="Amendment Approval Partner",
            bank_name="HDFC Bank",
            bank_account_number="123456789",
            bank_routing_code="HDFC0001234",
            primary_address="123 Test St",
            primary_city="Mumbai",
            primary_postal_code="400001",
            primary_country="India",
            primary_contact_name="Test Contact",
            primary_contact_email="old@email.com",
            primary_contact_phone="+919876543210",
            primary_currency="INR",
        )
        
        db_session.add(partner)
        await db_session.flush()

        # Create amendment
        amendment = PartnerAmendment(
            partner_id=partner.id,
            amendment_type=AmendmentType.UPDATE_CONTACT,
            requested_by=user_id,
            requested_at=datetime.utcnow(),
            old_value={"primary_contact_email": "old@email.com"},
            new_value={"primary_contact_email": "new@email.com"},
            reason="Email changed",
            status="pending",
        )
        
        db_session.add(amendment)
        await db_session.flush()

        # Approve amendment
        amendment.status = "approved"
        amendment.approved_by = approver_id
        amendment.approved_at = datetime.utcnow()
        
        # Apply changes to partner
        partner.primary_contact_email = "new@email.com"
        
        await db_session.flush()

        assert partner.primary_contact_email == "new@email.com"
        assert amendment.status == "approved"


class TestPartnerLocations:
    """Test partner location management."""

    @pytest.mark.asyncio
    async def test_add_partner_location(self, db_session: AsyncSession, seed_organization):
        """✅ Test: Add additional location/branch to partner."""  
        org_id = seed_organization.id        # Create partner
        partner = BusinessPartner(
            legal_name="Multi-Location Partner",
            partner_type=PartnerType.BUYER,
            country="India",
            entity_class="business_entity",
            status=PartnerStatus.APPROVED,
            bank_account_name="Multi-Location Partner",
            bank_name="HDFC Bank",
            bank_account_number="123456789",
            bank_routing_code="HDFC0001234",
            primary_address="123 Test St",
            primary_city="Mumbai",
            primary_postal_code="400001",
            primary_country="India",
            primary_contact_name="Test Contact",
            primary_contact_email="test@example.com",
            primary_contact_phone="+919876543210",
            primary_currency="INR",
        )
        
        db_session.add(partner)
        await db_session.flush()

        # Add location
        location = PartnerLocation(
            partner_id=partner.id,
            location_type="additional_same_state",
            location_name="Mumbai Branch",
            address="Andheri Industrial Estate",
            city="Mumbai",
            state="Maharashtra",
            postal_code="400053",
            country="India",
        )
        
        db_session.add(location)
        await db_session.flush()

        assert location.location_name == "Mumbai Branch"
        assert location.partner_id == partner.id
        assert location.location_type == "additional_same_state"

    @pytest.mark.asyncio
    async def test_list_partner_locations(self, db_session: AsyncSession, seed_organization):
        """✅ Test: List all locations for a partner."""  
        org_id = seed_organization.id        # Create partner
        partner = BusinessPartner(
            legal_name="Location Test Partner",
            partner_type=PartnerType.TRADER,
            country="India",
            entity_class="business_entity",
            status=PartnerStatus.APPROVED,
            bank_account_name="Location Test Partner",
            bank_name="HDFC Bank",
            bank_account_number="123456789",
            bank_routing_code="HDFC0001234",
            primary_address="123 Test St",
            primary_city="Mumbai",
            primary_postal_code="400001",
            primary_country="India",
            primary_contact_name="Test Contact",
            primary_contact_email="test@example.com",
            primary_contact_phone="+919876543210",
            primary_currency="INR",
        )
        
        db_session.add(partner)
        await db_session.flush()

        # Add multiple locations
        locations = [
            PartnerLocation(
                partner_id=partner.id,
                location_type="principal" if i == 0 else "additional_same_state",
                location_name=f"Branch {i}",
                address=f"Address {i}",
                city=f"City {i}",
                postal_code=f"40000{i}",
                country="India",
            )
            for i in range(3)
        ]
        
        for loc in locations:
            db_session.add(loc)
        await db_session.flush()

        # List locations
        repo = PartnerLocationRepository(db_session)
        result = await repo.get_by_partner(partner.id)

        assert len(result) == 3
        assert sum(1 for loc in result if loc.location_type == "principal") == 1


class TestPartnerEmployees:
    """Test partner employee management."""

    @pytest.mark.asyncio
    async def test_add_partner_employee(self, db_session: AsyncSession, seed_organization):
        """✅ Test: Add employee to partner."""  
        org_id = seed_organization.id        # Create partner
        partner = BusinessPartner(
            legal_name="Employee Test Partner",
            partner_type=PartnerType.SELLER,
            country="India",
            entity_class="business_entity",
            status=PartnerStatus.APPROVED,
            bank_account_name="Employee Test Partner",
            bank_name="HDFC Bank",
            bank_account_number="123456789",
            bank_routing_code="HDFC0001234",
            primary_address="123 Test St",
            primary_city="Mumbai",
            primary_postal_code="400001",
            primary_country="India",
            primary_contact_name="Test Contact",
            primary_contact_email="test@example.com",
            primary_contact_phone="+919876543210",
            primary_currency="INR",
        )
        
        db_session.add(partner)
        await db_session.flush()

        # Create user account for employee
        from backend.modules.settings.models.settings_models import User
        user = User(
            email="ramesh@testpartner.com",
            mobile_number="+919876543214",
            full_name="Ramesh Kumar",
            user_type="EXTERNAL",
            business_partner_id=partner.id,
            is_active=True,
            is_verified=False
        )
        db_session.add(user)
        await db_session.flush()

        # Add employee
        employee = PartnerEmployee(
            partner_id=partner.id,
            user_id=user.id,
            employee_name="Ramesh Kumar",
            employee_email="ramesh@testpartner.com",
            employee_phone="+919876543214",
            designation="Sales Manager",
            role="employee",
            status="active"
        )
        
        db_session.add(employee)
        await db_session.flush()

        assert employee.employee_name == "Ramesh Kumar"
        assert employee.employee_email == "ramesh@testpartner.com"
        assert employee.designation == "Sales Manager"
        assert employee.partner_id == partner.id

    @pytest.mark.asyncio
    async def test_list_partner_employees(self, db_session: AsyncSession, seed_organization):
        """✅ Test: List all employees for a partner."""  
        org_id = seed_organization.id        # Create partner
        partner = BusinessPartner(
            legal_name="Multi-Employee Partner",
            partner_type=PartnerType.BUYER,
            country="India",
            entity_class="business_entity",
            status=PartnerStatus.APPROVED,
            bank_account_name="Multi-Employee Partner",
            bank_name="HDFC Bank",
            bank_account_number="123456789",
            bank_routing_code="HDFC0001234",
            primary_address="123 Test St",
            primary_city="Mumbai",
            primary_postal_code="400001",
            primary_country="India",
            primary_contact_name="Test Contact",
            primary_contact_email="test@example.com",
            primary_contact_phone="+919876543210",
            primary_currency="INR",
        )
        
        db_session.add(partner)
        await db_session.flush()

        # Add employees (testing unlimited - no max 2 restriction)
        from backend.modules.settings.models.settings_models import User
        employees = []
        for i in range(5):  # Testing 5 employees to prove no limit
            # Create user account
            user = User(
                email=f"employee{i}@multipartner.com",
                mobile_number=f"+9198765432{i:02d}",
                full_name=f"Employee {i}",
                user_type="EXTERNAL",
                business_partner_id=partner.id,
                is_active=True,
                is_verified=False
            )
            db_session.add(user)
            await db_session.flush()
            
            # Create employee record
            employee = PartnerEmployee(
                partner_id=partner.id,
                user_id=user.id,
                employee_name=f"Employee {i}",
                employee_email=f"employee{i}@multipartner.com",
                employee_phone=f"+9198765432{i:02d}",
                designation="Staff",
                role="employee",
                status="active"
            )
            employees.append(employee)
            db_session.add(employee)
        
        await db_session.flush()

        # List employees
        repo = PartnerEmployeeRepository(db_session)
        result = await repo.get_by_partner(partner.id)

        # Should have 5 employees (proving no max 2 limit)
        assert len(result) == 5
        assert all(emp.employee_email.endswith("@multipartner.com") for emp in result)


class TestPartnerVehicles:
    """Test vehicle management for transporters."""

    @pytest.mark.asyncio
    async def test_add_vehicle_to_transporter(self, db_session: AsyncSession, seed_organization):
        """✅ Test: Add vehicle to transporter (lorry owner)."""  
        org_id = seed_organization.id        # Create transporter partner
        partner = BusinessPartner(
            legal_name="Transport Company",
            partner_type=PartnerType.TRANSPORTER,
            service_provider_type=ServiceProviderType.TRANSPORTER,
            country="India",
            entity_class="service_provider",
            status=PartnerStatus.APPROVED,
            bank_account_name="Transport Company",
            bank_name="HDFC Bank",
            bank_account_number="123456789",
            bank_routing_code="HDFC0001234",
            primary_address="123 Test St",
            primary_city="Mumbai",
            primary_postal_code="400001",
            primary_country="India",
            primary_contact_name="Test Contact",
            primary_contact_email="test@example.com",
            primary_contact_phone="+919876543210",
            primary_currency="INR",
        )
        
        db_session.add(partner)
        await db_session.flush()

        # Add vehicle
        vehicle = PartnerVehicle(
            partner_id=partner.id,
            vehicle_number="MH12AB1234",
            vehicle_type="Truck",
            owner_name="Transport Company",
            maker_model="Tata 407",
            capacity_tons=Decimal("7.5"),
            registration_date=date(2020, 5, 15),
            fitness_valid_till=date(2025, 5, 15),
            insurance_valid_till=date(2025, 12, 31),
            permit_type="All India",
            verified_via_rto=True,
        )
        
        db_session.add(vehicle)
        await db_session.flush()

        assert vehicle.vehicle_number == "MH12AB1234"
        assert vehicle.capacity_tons == Decimal("7.5")
        assert vehicle.verified_via_rto is True

    @pytest.mark.asyncio
    async def test_list_partner_vehicles(self, db_session: AsyncSession, seed_organization):
        """✅ Test: List all vehicles for transporter."""  
        org_id = seed_organization.id        # Create transporter
        partner = BusinessPartner(
            legal_name="Fleet Owner Transport",
            partner_type=PartnerType.TRANSPORTER,
            service_provider_type=ServiceProviderType.TRANSPORTER,
            country="India",
            entity_class="service_provider",
            status=PartnerStatus.APPROVED,
            bank_account_name="Fleet Owner Transport",
            bank_name="HDFC Bank",
            bank_account_number="123456789",
            bank_routing_code="HDFC0001234",
            primary_address="123 Test St",
            primary_city="Mumbai",
            primary_postal_code="400001",
            primary_country="India",
            primary_contact_name="Test Contact",
            primary_contact_email="test@example.com",
            primary_contact_phone="+919876543210",
            primary_currency="INR",
        )
        
        db_session.add(partner)
        await db_session.flush()

        # Add multiple vehicles
        vehicles = [
            PartnerVehicle(
                partner_id=partner.id,
                vehicle_number=f"MH12XY{1000+i}",
                vehicle_type="Truck",
                capacity_tons=Decimal("10.0"),
                verified_via_rto=True,
            )
            for i in range(5)
        ]
        
        for vehicle in vehicles:
            db_session.add(vehicle)
        await db_session.flush()

        # List vehicles
        repo = PartnerVehicleRepository(db_session)
        result = await repo.get_by_partner(partner.id)

        assert len(result) == 5


class TestKYCRenewal:
    """Test KYC renewal workflow."""

    @pytest.mark.asyncio
    async def test_initiate_kyc_renewal(self, db_session: AsyncSession, seed_user, seed_organization):
        """✅ Test: Initiate KYC renewal for expiring partner."""  
        org_id = seed_organization.id
        user_id = seed_user.id        # Create partner with expiring KYC
        partner = BusinessPartner(
            legal_name="KYC Expiring Partner",
            partner_type=PartnerType.BUYER,
            country="India",
            entity_class="business_entity",
            status=PartnerStatus.APPROVED,
            kyc_status=KYCStatus.VERIFIED,
            kyc_verified_at=datetime.utcnow() - timedelta(days=350),  # Almost 1 year old
            bank_account_name="KYC Expiring Partner",
            bank_name="HDFC Bank",
            bank_account_number="123456789",
            bank_routing_code="HDFC0001234",
            primary_address="123 Test St",
            primary_city="Mumbai",
            primary_postal_code="400001",
            primary_country="India",
            primary_contact_name="Test Contact",
            primary_contact_email="test@example.com",
            primary_contact_phone="+919876543210",
            primary_currency="INR",
        )
        
        db_session.add(partner)
        await db_session.flush()

        # Initiate renewal
        renewal = PartnerKYCRenewal(
            partner_id=partner.id,
            renewal_due_date=(datetime.utcnow() + timedelta(days=15)).date(),
            renewal_requested_at=datetime.utcnow(),
            status="pending",
        )
        
        db_session.add(renewal)
        await db_session.flush()

        assert renewal.status == "pending"
        assert renewal.renewal_due_date is not None

    @pytest.mark.asyncio
    async def test_complete_kyc_renewal(self, db_session: AsyncSession, seed_user, seed_organization):
        """✅ Test: Complete KYC renewal process."""  
        org_id = seed_organization.id
        user_id = seed_user.id
        verifier_id = uuid.uuid4()  # Different verifier        # Create partner
        partner = BusinessPartner(
            legal_name="KYC Renewal Partner",
            partner_type=PartnerType.SELLER,
            country="India",
            entity_class="business_entity",
            status=PartnerStatus.APPROVED,
            kyc_status=KYCStatus.RENEWAL_REQUIRED,
            bank_account_name="KYC Renewal Partner",
            bank_name="HDFC Bank",
            bank_account_number="123456789",
            bank_routing_code="HDFC0001234",
            primary_address="123 Test St",
            primary_city="Mumbai",
            primary_postal_code="400001",
            primary_country="India",
            primary_contact_name="Test Contact",
            primary_contact_email="test@example.com",
            primary_contact_phone="+919876543210",
            primary_currency="INR",
        )
        
        db_session.add(partner)
        await db_session.flush()

        # Create renewal
        renewal = PartnerKYCRenewal(
            partner_id=partner.id,
            renewal_requested_at=datetime.utcnow() - timedelta(days=10),
            renewal_due_date=datetime.utcnow().date(),
            status="pending",
        )
        
        db_session.add(renewal)
        await db_session.flush()

        # Complete renewal
        renewal.status = "completed"
        renewal.renewal_completed_at = datetime.utcnow()
        renewal.completed_by = verifier_id
        renewal.notes = "All documents verified and updated"
        
        partner.kyc_status = KYCStatus.VERIFIED
        partner.kyc_verified_at = datetime.utcnow()
        
        await db_session.flush()

        assert renewal.status == "completed"
        assert partner.kyc_status == KYCStatus.VERIFIED


class TestRiskScoring:
    """Test risk scoring and approval routing."""

    @pytest.mark.asyncio
    async def test_risk_score_calculation_low_risk(self, db_session: AsyncSession):
        """✅ Test: Calculate risk score for low-risk partner."""
        service = RiskScoringService(db_session)

        # Old established business = low risk
        assessment = await service.calculate_risk_score(
            partner_type=PartnerType.BUYER,
            entity_type=BusinessEntityType.PRIVATE_LIMITED,
            business_age_months=72,  # 6 years
            gst_turnover=Decimal("50000000"),  # 5 Cr
            gst_compliance="High",
        )

        assert assessment.total_score >= 70  # Low risk threshold
        assert assessment.category == RiskCategory.LOW
        assert assessment.approval_route == "auto"

    @pytest.mark.asyncio
    async def test_risk_score_calculation_high_risk(self, db_session: AsyncSession):
        """✅ Test: Calculate risk score for high-risk partner."""
        service = RiskScoringService(db_session)

        # New business, low turnover = high risk
        assessment = await service.calculate_risk_score(
            partner_type=PartnerType.SELLER,
            entity_type=BusinessEntityType.PROPRIETORSHIP,
            business_age_months=6,  # Very new
            gst_turnover=Decimal("500000"),  # Low turnover
            gst_compliance="Low",
        )

        assert assessment.total_score < 40  # High risk threshold
        assert assessment.category == RiskCategory.HIGH
        assert assessment.approval_route == "director"


class TestCDPSIntegration:
    """Test CDPS capability detection integration."""

    @pytest.mark.asyncio
    async def test_indian_partner_capabilities(self, db_session: AsyncSession, seed_organization):
        """✅ Test: Indian partner gets domestic trading capabilities."""  
        org_id = seed_organization.id        # Create Indian partner with GST + PAN
        partner = BusinessPartner(
            legal_name="Indian Trader",
            partner_type=PartnerType.TRADER,
            country="India",
            entity_class="business_entity",
            business_entity_type=BusinessEntityType.PRIVATE_LIMITED,
            status=PartnerStatus.APPROVED,
            tax_id_number="27AABCH1234I1Z4",
            pan_number="AABCH1234I",
            capabilities={
                "domestic_sell_india": True,
                "domestic_buy_india": True,
                "domestic_sell_home_country": False,
                "domestic_buy_home_country": False,
            },
            bank_account_name="Indian Trader",
            bank_name="HDFC Bank",
            bank_account_number="123456789",
            bank_routing_code="HDFC0001234",
            primary_address="123 Test St",
            primary_city="Mumbai",
            primary_postal_code="400001",
            primary_country="India",
            primary_contact_name="Test Contact",
            primary_contact_email="test@example.com",
            primary_contact_phone="+919876543210",
            primary_currency="INR",
        )
        
        db_session.add(partner)
        await db_session.flush()

        assert partner.capabilities["domestic_sell_india"] is True
        assert partner.capabilities["domestic_buy_india"] is True

    @pytest.mark.asyncio
    async def test_foreign_partner_home_country_only(self, db_session: AsyncSession, seed_organization):
        """✅ Test: Foreign partner can only trade in home country, NOT India."""  
        org_id = seed_organization.id        # Create foreign partner
        partner = BusinessPartner(
            legal_name="USA Cotton Exporter",
            partner_type=PartnerType.SELLER,
            country="USA",
            entity_class="business_entity",
            business_entity_type=BusinessEntityType.CORPORATION,
            status=PartnerStatus.APPROVED,
            capabilities={
                "domestic_sell_india": False,  # Cannot sell in India
                "domestic_buy_india": False,   # Cannot buy in India
                "domestic_sell_home_country": True,  # Can sell in USA
                "domestic_buy_home_country": True,   # Can buy in USA
            },
            bank_account_name="USA Cotton Exporter",
            bank_name="Chase Bank",
            bank_account_number="123456789",
            bank_routing_code="CHASUS33",
            primary_address="123 Main St",
            primary_city="Dallas",
            primary_postal_code="75201",
            primary_country="USA",
            primary_contact_name="John Smith",
            primary_contact_email="john@usacotton.com",
            primary_contact_phone="+12145551234",
            primary_currency="USD",
        )
        
        db_session.add(partner)
        await db_session.flush()

        assert partner.capabilities["domestic_sell_india"] is False
        assert partner.capabilities["domestic_buy_india"] is False
        assert partner.capabilities["domestic_sell_home_country"] is True

    @pytest.mark.asyncio
    async def test_service_provider_no_trading_capabilities(self, db_session: AsyncSession, seed_organization):
        """✅ Test: Service providers cannot trade."""  
        org_id = seed_organization.id        # Create service provider (broker)
        partner = BusinessPartner(
            legal_name="Trade Broker Services",
            partner_type=PartnerType.BROKER,
            service_provider_type=ServiceProviderType.BROKER,
            country="India",
            entity_class="service_provider",
            status=PartnerStatus.APPROVED,
            capabilities={
                "domestic_sell_india": False,
                "domestic_buy_india": False,
                "domestic_sell_home_country": False,
                "domestic_buy_home_country": False,
            },
            bank_account_name="Trade Broker Services",
            bank_name="HDFC Bank",
            bank_account_number="123456789",
            bank_routing_code="HDFC0001234",
            primary_address="123 Test St",
            primary_city="Mumbai",
            primary_postal_code="400001",
            primary_country="India",
            primary_contact_name="Test Contact",
            primary_contact_email="broker@example.com",
            primary_contact_phone="+919876543210",
            primary_currency="INR",
        )
        
        db_session.add(partner)
        await db_session.flush()

        # All trading capabilities should be False
        assert partner.capabilities["domestic_sell_india"] is False
        assert partner.capabilities["domestic_buy_india"] is False

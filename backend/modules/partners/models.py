"""
Business Partner Onboarding Models

Complete business partner management with:
- All partner types (Seller, Buyer, Trader, Broker, Sub-Broker, Transporter, Controller, Importer, Exporter)
- Data isolation via organization_id (NO business_partner_id - this IS the business partner table)
- Yearly KYC renewal
- Multi-location support
- GST/Tax auto-fetch
- Risk assessment

Compliance:
- GDPR Article 32: Security of Processing
- IT Act 2000 Section 43A: Data Protection
- Income Tax Act 1961: 7-year retention
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import relationship

from backend.db.session import Base


class BusinessPartner(Base):
    """
    Business Partner - Complete model for all partner types
    
    Partner Types:
    - seller: Sells commodities
    - buyer: Buys commodities
    - trader: Both buy and sell
    - broker: Licensed commodity broker
    - sub_broker: Agent of broker
    - transporter: Logistics provider
    - controller: Quality inspector (CCI/Private)
    - financer: Banks/NBFCs
    - shipping_agent: Port/shipping services
    - importer: Foreign entity buying from India
    - exporter: Foreign entity selling to India
    
    Data Isolation:
    - Uses organization_id for isolation (settings tables don't have business_partner_id)
    - External users link to this via User.business_partner_id FK
    - BaseRepository applies organization_id filter for EXTERNAL users
    """
    
    __tablename__ = "business_partners"
    
    # ============================================
    # PRIMARY KEY
    # ============================================
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # ============================================
    # DATA ISOLATION - Uses organization_id
    # (NOT business_partner_id - this IS the BP table)
    # ============================================
    organization_id = Column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        comment="Organization this partner belongs to (for data isolation)"
    )
    
    # ============================================
    # PARTNER CLASSIFICATION
    # ============================================
    partner_code = Column(
        String(50),
        unique=True,
        nullable=True,
        comment="Auto-generated: BP-IND-SEL-0001"
    )
    
    partner_type = Column(
        String(20),
        nullable=False,
        index=True,
        comment="seller, buyer, trader, broker, sub_broker, transporter, controller, financer, shipping_agent, importer, exporter"
    )
    
    service_provider_type = Column(
        String(50),
        nullable=True,
        comment="For service providers: broker, sub_broker, transporter, controller, financer, shipping_agent"
    )
    
    trade_classification = Column(
        String(20),
        nullable=True,
        comment="domestic, exporter (foreign selling to India), importer (foreign buying from India)"
    )
    
    # ============================================
    # BUSINESS IDENTITY
    # ============================================
    legal_name = Column(String(500), nullable=False, index=True)
    trade_name = Column(String(500), nullable=True)
    
    country = Column(String(100), nullable=False, index=True)
    business_entity_type = Column(
        String(100),
        nullable=True,
        comment="proprietorship, partnership, llp, private_limited, public_limited, corporation"
    )
    registration_date = Column(Date, nullable=True, comment="From tax registration")
    
    # ============================================
    # TAX REGISTRATION
    # ============================================
    has_tax_registration = Column(Boolean, default=False)
    tax_id_type = Column(String(20), nullable=True, comment="GST, EIN, TRN, VAT, etc.")
    tax_id_number = Column(String(50), nullable=True, unique=True, index=True)
    
    # Complete GST/Tax details (JSON for flexibility)
    tax_details = Column(
        JSON,
        nullable=True,
        comment="GST: {gstin, legal_name, trade_name, status, state, directors, additional_places, other_state_gstins}"
    )
    
    tax_verified = Column(Boolean, default=False)
    tax_verified_at = Column(DateTime(timezone=True), nullable=True)
    
    # ============================================
    # PAN (MANDATORY FOR INDIA)
    # ============================================
    pan_number = Column(String(10), nullable=True, index=True)
    pan_name = Column(String(500), nullable=True)
    pan_verified = Column(Boolean, default=False)
    
    # ============================================
    # NO GST DECLARATION (Service Providers)
    # ============================================
    has_no_gst_declaration = Column(Boolean, default=False)
    no_gst_declaration_url = Column(String(1000), nullable=True)
    declaration_reason = Column(
        String(200),
        nullable=True,
        comment="commission_agent, turnover_below_threshold, exempted_category"
    )
    
    # ============================================
    # BANK ACCOUNT
    # ============================================
    bank_account_name = Column(String(200), nullable=False)
    bank_name = Column(String(200), nullable=False)
    bank_account_number = Column(String(100), nullable=False)
    bank_routing_code = Column(
        String(50),
        nullable=False,
        comment="IFSC (India), Routing (USA), SWIFT/IBAN (International)"
    )
    bank_verified = Column(Boolean, default=False)
    
    # ============================================
    # PRIMARY LOCATION (HEAD OFFICE)
    # ============================================
    primary_address = Column(Text, nullable=False)
    primary_city = Column(String(100), nullable=False)
    primary_state = Column(String(100), nullable=True)
    primary_postal_code = Column(String(20), nullable=False)
    primary_country = Column(String(100), nullable=False)
    
    # Auto-verified geocoding (NO user confirmation if confidence >90%)
    primary_latitude = Column(Numeric(10, 7), nullable=True)
    primary_longitude = Column(Numeric(10, 7), nullable=True)
    location_geocoded = Column(Boolean, default=False)
    location_confidence = Column(
        Numeric(5, 2),
        nullable=True,
        comment="Google Maps geocoding confidence 0-100"
    )
    
    # ============================================
    # PRIMARY CONTACT
    # ============================================
    primary_contact_name = Column(String(200), nullable=False)
    primary_contact_email = Column(String(200), nullable=False)
    primary_contact_phone = Column(String(20), nullable=False)
    
    # ============================================
    # CURRENCY
    # ============================================
    primary_currency = Column(String(3), nullable=False, default="INR")
    
    # ============================================
    # COMMODITIES (for buyers/sellers/traders)
    # ============================================
    commodities = Column(
        JSON,
        nullable=True,
        comment='["cotton", "cotton_yarn", "textiles"]'
    )
    
    # ============================================
    # BUYER-SPECIFIC FIELDS
    # ============================================
    credit_limit = Column(Numeric(20, 2), nullable=True)
    credit_utilized = Column(Numeric(20, 2), default=0)
    payment_terms_days = Column(Integer, nullable=True, comment="0=advance, 15, 30, 45")
    monthly_purchase_volume = Column(String(100), nullable=True)
    
    # ============================================
    # SELLER-SPECIFIC FIELDS
    # ============================================
    production_capacity = Column(String(200), nullable=True)
    can_arrange_transport = Column(Boolean, default=False)
    has_quality_lab = Column(Boolean, default=False)
    
    # ============================================
    # SERVICE PROVIDER DETAILS (JSON)
    # ============================================
    service_details = Column(
        JSON,
        nullable=True,
        comment="Transporter: {fleet_size, routes, vehicle_types, has_own_vehicles, transport_license}, Broker: {license_number, exchange, commission_structure}"
    )
    
    # ============================================
    # RISK ASSESSMENT (AUTO-CALCULATED)
    # ============================================
    risk_score = Column(Integer, nullable=True, comment="0-100")
    risk_category = Column(String(20), nullable=True, comment="low, medium, high, critical")
    risk_assessment = Column(
        JSON,
        nullable=True,
        comment="Detailed scoring breakdown and flags"
    )
    last_risk_assessment_at = Column(DateTime(timezone=True), nullable=True)
    
    # ============================================
    # KYC RENEWAL (YEARLY)
    # ============================================
    kyc_verified_at = Column(
        DateTime(timezone=True),
        nullable=True,
        comment="Initial KYC verification date (approval date)"
    )
    kyc_expiry_date = Column(
        Date,
        nullable=True,
        comment="1 year from approval - triggers renewal"
    )
    kyc_status = Column(
        String(20),
        default="pending",
        comment="pending, verified, expired, renewal_required"
    )
    last_kyc_renewal_at = Column(DateTime(timezone=True), nullable=True)
    
    # ============================================
    # STATUS & APPROVAL
    # ============================================
    status = Column(
        String(20),
        default="pending",
        nullable=False,
        comment="pending, approved, rejected, suspended, inactive"
    )
    approved_by = Column(UUID(as_uuid=True), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    rejection_reason = Column(Text, nullable=True)
    
    # ============================================
    # EMPLOYEE MANAGEMENT
    # ============================================
    max_employees_allowed = Column(Integer, default=2)
    current_employee_count = Column(Integer, default=0)
    
    # ============================================
    # SOFT DELETE (GDPR 7-year retention)
    # ============================================
    is_deleted = Column(Boolean, default=False, nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    deleted_by = Column(UUID(as_uuid=True), nullable=True)
    
    # ============================================
    # AUDIT TRAIL
    # ============================================
    created_by = Column(UUID(as_uuid=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=text("NOW()"), nullable=False)
    updated_by = Column(UUID(as_uuid=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), onupdate=datetime.utcnow, nullable=True)
    
    # ============================================
    # RELATIONSHIPS
    # ============================================
    organization = relationship("Organization", foreign_keys=[organization_id])
    locations = relationship("PartnerLocation", back_populates="partner", cascade="all, delete-orphan")
    employees = relationship("PartnerEmployee", back_populates="partner", cascade="all, delete-orphan")
    documents = relationship("PartnerDocument", back_populates="partner", cascade="all, delete-orphan")
    vehicles = relationship("PartnerVehicle", back_populates="partner", cascade="all, delete-orphan")


class PartnerLocation(Base):
    """
    Additional locations (branches/warehouses/factories)
    
    Locations can be:
    - Same state (shares GSTIN with principal place)
    - Different state (different GSTIN)
    - Non-business (ship-to, bill-to - no GST required)
    """
    
    __tablename__ = "partner_locations"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    partner_id = Column(UUID(as_uuid=True), ForeignKey("business_partners.id", ondelete="CASCADE"), nullable=False)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False, index=True)
    
    location_type = Column(
        String(50),
        nullable=False,
        comment="principal, additional_same_state, branch_different_state, warehouse, factory, ship_to, bill_to"
    )
    location_name = Column(String(200), nullable=False)
    
    # GST for this location (if applicable)
    is_from_gst = Column(Boolean, default=False, comment="Auto-fetched from GST API")
    gstin_for_location = Column(String(15), nullable=True, comment="Different GSTIN if different state")
    requires_gst = Column(Boolean, default=True)
    
    # Address
    address = Column(Text, nullable=False)
    city = Column(String(100), nullable=False)
    state = Column(String(100), nullable=True)
    postal_code = Column(String(20), nullable=False)
    country = Column(String(100), nullable=False)
    
    # Auto-verified geocoding (NO confirmation if confidence >90%)
    latitude = Column(Numeric(10, 7), nullable=True)
    longitude = Column(Numeric(10, 7), nullable=True)
    geocoded = Column(Boolean, default=False)
    geocode_confidence = Column(Numeric(5, 2), nullable=True)
    
    # Contact
    contact_person = Column(String(200), nullable=True)
    contact_phone = Column(String(20), nullable=True)
    
    status = Column(String(20), default="active")
    is_deleted = Column(Boolean, default=False)
    
    created_at = Column(DateTime(timezone=True), server_default=text("NOW()"))
    updated_at = Column(DateTime(timezone=True), onupdate=datetime.utcnow)
    
    partner = relationship("BusinessPartner", back_populates="locations")
    organization = relationship("Organization", foreign_keys=[organization_id])


class PartnerEmployee(Base):
    """
    Employees under a partner (max 2 additional users)
    
    Partner owner becomes 'admin' with full access
    Employees get limited permissions
    """
    
    __tablename__ = "partner_employees"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    partner_id = Column(UUID(as_uuid=True), ForeignKey("business_partners.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False, index=True)
    
    employee_name = Column(String(200), nullable=False)
    employee_email = Column(String(200), nullable=False)
    employee_phone = Column(String(20), nullable=False)
    designation = Column(String(100), nullable=True)
    
    role = Column(String(20), default="employee", comment="admin (partner owner), employee")
    
    # Permissions
    permissions = Column(
        JSON,
        nullable=True,
        comment='{"create_orders": true, "view_reports": true, "approve_contracts": false}'
    )
    
    status = Column(String(20), default="active")
    invited_at = Column(DateTime(timezone=True), server_default=text("NOW()"))
    activated_at = Column(DateTime(timezone=True), nullable=True)
    
    partner = relationship("BusinessPartner", back_populates="employees")
    organization = relationship("Organization", foreign_keys=[organization_id])


class PartnerDocument(Base):
    """
    Documents uploaded by partner
    """
    
    __tablename__ = "partner_documents"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    partner_id = Column(UUID(as_uuid=True), ForeignKey("business_partners.id", ondelete="CASCADE"), nullable=False)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False, index=True)
    
    document_type = Column(
        String(100),
        nullable=False,
        comment="gst_certificate, pan_card, bank_proof, transport_license, vehicle_rc, etc."
    )
    document_subtype = Column(String(100), nullable=True)
    country = Column(String(100), nullable=False)
    
    file_url = Column(String(1000), nullable=False)
    file_name = Column(String(500))
    file_size = Column(Integer)
    mime_type = Column(String(100))
    
    # OCR extracted data
    ocr_extracted_data = Column(JSON, nullable=True)
    extraction_confidence = Column(Numeric(5, 2), nullable=True)
    
    # Validity
    issue_date = Column(Date, nullable=True)
    expiry_date = Column(Date, nullable=True)
    is_expired = Column(Boolean, default=False)
    
    # Verification
    verified = Column(Boolean, default=False)
    verified_by = Column(UUID(as_uuid=True), nullable=True)
    verified_at = Column(DateTime(timezone=True), nullable=True)
    
    uploaded_at = Column(DateTime(timezone=True), server_default=text("NOW()"))
    
    partner = relationship("BusinessPartner", back_populates="documents")
    organization = relationship("Organization", foreign_keys=[organization_id])


class PartnerVehicle(Base):
    """
    Vehicles for transporters (lorry owners)
    """
    
    __tablename__ = "partner_vehicles"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    partner_id = Column(UUID(as_uuid=True), ForeignKey("business_partners.id", ondelete="CASCADE"), nullable=False)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False, index=True)
    
    vehicle_number = Column(String(20), nullable=False, unique=True, index=True)
    vehicle_type = Column(String(50), nullable=False, comment="truck, trailer, container, etc.")
    
    # From RTO API or manual upload
    owner_name = Column(String(200), nullable=True)
    maker_model = Column(String(200), nullable=True)
    capacity_tons = Column(Numeric(10, 2), nullable=True)
    registration_date = Column(Date, nullable=True)
    
    # Documents
    rc_document_url = Column(String(1000), nullable=True)
    insurance_valid_till = Column(Date, nullable=True)
    fitness_valid_till = Column(Date, nullable=True)
    permit_type = Column(String(100), nullable=True)
    
    # Verification
    verified_via_rto = Column(Boolean, default=False)
    rto_data = Column(JSON, nullable=True, comment="Data from Parivahan/Vahan API")
    
    status = Column(String(20), default="active")
    created_at = Column(DateTime(timezone=True), server_default=text("NOW()"))
    
    partner = relationship("BusinessPartner", back_populates="vehicles")
    organization = relationship("Organization", foreign_keys=[organization_id])


class PartnerOnboardingApplication(Base):
    """
    Temporary table for onboarding applications
    Converted to BusinessPartner upon approval
    """
    
    __tablename__ = "partner_onboarding_applications"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False, index=True)
    
    # Same fields as BusinessPartner (copy-paste for simplicity)
    partner_type = Column(String(20), nullable=False)
    service_provider_type = Column(String(50), nullable=True)
    trade_classification = Column(String(20), nullable=True)
    
    legal_name = Column(String(500), nullable=False)
    trade_name = Column(String(500), nullable=True)
    country = Column(String(100), nullable=False)
    business_entity_type = Column(String(100), nullable=True)
    registration_date = Column(Date, nullable=True)
    
    has_tax_registration = Column(Boolean, default=False)
    tax_id_type = Column(String(20), nullable=True)
    tax_id_number = Column(String(50), nullable=True)
    tax_details = Column(JSON, nullable=True)
    tax_verified = Column(Boolean, default=False)
    
    pan_number = Column(String(10), nullable=True)
    pan_name = Column(String(500), nullable=True)
    pan_verified = Column(Boolean, default=False)
    
    has_no_gst_declaration = Column(Boolean, default=False)
    no_gst_declaration_url = Column(String(1000), nullable=True)
    declaration_reason = Column(String(200), nullable=True)
    
    bank_account_name = Column(String(200), nullable=False)
    bank_name = Column(String(200), nullable=False)
    bank_account_number = Column(String(100), nullable=False)
    bank_routing_code = Column(String(50), nullable=False)
    
    primary_address = Column(Text, nullable=False)
    primary_city = Column(String(100), nullable=False)
    primary_state = Column(String(100), nullable=True)
    primary_postal_code = Column(String(20), nullable=False)
    primary_country = Column(String(100), nullable=False)
    primary_latitude = Column(Numeric(10, 7), nullable=True)
    primary_longitude = Column(Numeric(10, 7), nullable=True)
    
    primary_contact_name = Column(String(200), nullable=False)
    primary_contact_email = Column(String(200), nullable=False)
    primary_contact_phone = Column(String(20), nullable=False)
    
    primary_currency = Column(String(3), nullable=False)
    commodities = Column(JSON, nullable=True)
    service_details = Column(JSON, nullable=True)
    
    # Onboarding specific
    onboarding_stage = Column(
        String(50),
        default="documents",
        comment="documents, verification, approval"
    )
    chat_transcript = Column(JSON, nullable=True)
    verification_results = Column(JSON, nullable=True)
    
    risk_score = Column(Integer, nullable=True)
    risk_category = Column(String(20), nullable=True)
    risk_assessment = Column(JSON, nullable=True)
    
    status = Column(String(20), default="pending")
    rejection_reason = Column(Text, nullable=True)
    
    # Converted to partner
    converted_to_partner_id = Column(UUID(as_uuid=True), nullable=True)
    converted_at = Column(DateTime(timezone=True), nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=text("NOW()"))
    updated_at = Column(DateTime(timezone=True), onupdate=datetime.utcnow)


class PartnerAmendment(Base):
    """
    Track all changes to partner data post-approval
    """
    
    __tablename__ = "partner_amendments"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    partner_id = Column(UUID(as_uuid=True), ForeignKey("business_partners.id"), nullable=False)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False, index=True)
    
    amendment_type = Column(
        String(50),
        nullable=False,
        comment="add_location, change_bank, update_gst, increase_credit_limit, add_employee"
    )
    
    field_changed = Column(String(100))
    old_value = Column(JSON)
    new_value = Column(JSON)
    
    reason = Column(Text)
    supporting_documents = Column(JSON, comment="Document IDs")
    
    status = Column(String(20), default="pending", comment="pending, approved, rejected")
    
    requested_by = Column(UUID(as_uuid=True), nullable=False)
    approved_by = Column(UUID(as_uuid=True), nullable=True)
    
    requested_at = Column(DateTime(timezone=True), server_default=text("NOW()"))
    approved_at = Column(DateTime(timezone=True), nullable=True)
    
    chat_transcript = Column(JSON, nullable=True)
    
    organization = relationship("Organization", foreign_keys=[organization_id])


class PartnerKYCRenewal(Base):
    """
    Track yearly KYC renewals
    """
    
    __tablename__ = "partner_kyc_renewals"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    partner_id = Column(UUID(as_uuid=True), ForeignKey("business_partners.id"), nullable=False)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False, index=True)
    
    renewal_type = Column(String(20), default="annual", comment="annual, adhoc")
    renewal_due_date = Column(Date, nullable=False)
    renewal_requested_at = Column(DateTime(timezone=True), nullable=True)
    renewal_completed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Documents re-verified
    documents_verified = Column(JSON, nullable=True, comment="List of document IDs verified")
    
    # Re-verification results
    tax_re_verified = Column(Boolean, default=False)
    bank_re_verified = Column(Boolean, default=False)
    risk_re_assessed = Column(Boolean, default=False)
    new_risk_score = Column(Integer, nullable=True)
    
    status = Column(
        String(20),
        default="pending",
        comment="pending, in_progress, completed, expired"
    )
    
    completed_by = Column(UUID(as_uuid=True), nullable=True)
    notes = Column(Text, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=text("NOW()"))
    
    organization = relationship("Organization", foreign_keys=[organization_id])

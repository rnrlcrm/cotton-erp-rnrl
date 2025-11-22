"""
Business Partner Schemas

Pydantic models for request/response validation
Following the existing pattern from commodities and locations modules
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, validator

from backend.modules.partners.enums import (
    AmendmentType,
    BusinessEntityType,
    DocumentType,
    KYCStatus,
    LocationType,
    PartnerStatus,
    PartnerType,
    RiskCategory,
    ServiceProviderType,
    TradeClassification,
)


# ============================================
# ONBOARDING SCHEMAS
# ============================================

class OnboardingStart(BaseModel):
    """Start onboarding - just partner type and country"""
    partner_type: PartnerType
    country: str = Field(..., min_length=2, max_length=100)


class DocumentUpload(BaseModel):
    """Document upload response"""
    document_id: UUID
    document_type: DocumentType
    extracted_data: Optional[Dict[str, Any]] = None
    extraction_confidence: Optional[Decimal] = None
    verification_result: Optional[Dict[str, Any]] = None


class GSTVerificationResult(BaseModel):
    """GST verification from government API"""
    gstin: str
    legal_name: str
    trade_name: Optional[str] = None
    status: str  # Active, Cancelled
    registration_date: Optional[date] = None
    business_type: Optional[str] = None
    state: str
    principal_place: Dict[str, Any]
    additional_places: List[Dict[str, Any]] = []
    directors: List[Dict[str, str]] = []
    other_state_gstins: List[Dict[str, Any]] = []  # Found by PAN search
    verified: bool = True


class LocationData(BaseModel):
    """Location with geocoding"""
    address: str
    city: str
    state: Optional[str] = None
    postal_code: str
    country: str
    latitude: Optional[Decimal] = None
    longitude: Optional[Decimal] = None
    geocoded: bool = False
    geocode_confidence: Optional[Decimal] = None


class ContactInfo(BaseModel):
    """Primary contact information"""
    name: str = Field(..., min_length=2, max_length=200)
    email: EmailStr
    phone: str = Field(..., min_length=10, max_length=20)


class BuyerSpecificData(BaseModel):
    """Additional data for buyers"""
    credit_limit_requested: Optional[Decimal] = None
    payment_terms_preference: Optional[str] = None  # advance, 15_days, 30_days
    monthly_volume_estimate: Optional[str] = None


class SellerSpecificData(BaseModel):
    """Additional data for sellers"""
    production_capacity: Optional[str] = None
    can_arrange_transport: bool = False
    has_quality_lab: bool = False


class TransporterData(BaseModel):
    """Data for transporters"""
    operates_from_city: str
    operates_from_state: str
    commodities_transported: List[str] = []
    routes: List[str] = []
    is_lorry_owner: bool = False
    is_commission_agent: bool = False
    fleet_size: Optional[int] = None
    vehicle_types: List[str] = []
    transport_license_number: Optional[str] = None


class VehicleData(BaseModel):
    """Vehicle details for lorry owners"""
    vehicle_number: str
    vehicle_type: str
    owner_name: Optional[str] = None
    maker_model: Optional[str] = None
    capacity_tons: Optional[Decimal] = None
    registration_date: Optional[date] = None
    fitness_valid_till: Optional[date] = None
    insurance_valid_till: Optional[date] = None
    permit_type: Optional[str] = None
    verified_via_rto: bool = False
    rto_data: Optional[Dict[str, Any]] = None


class BrokerData(BaseModel):
    """Data for brokers"""
    broker_license_number: str
    exchange: str  # MCX, NCDEX
    license_valid_till: Optional[date] = None
    specialization: List[str] = []  # cotton, yarn
    commission_buyer_side: Optional[Decimal] = None
    commission_seller_side: Optional[Decimal] = None


class OnboardingApplicationCreate(BaseModel):
    """Complete onboarding application"""
    partner_type: PartnerType
    service_provider_type: Optional[ServiceProviderType] = None
    trade_classification: Optional[TradeClassification] = None
    
    # Business details (auto-filled from GST or manual)
    legal_name: str
    trade_name: Optional[str] = None
    country: str
    business_entity_type: Optional[BusinessEntityType] = None
    registration_date: Optional[date] = None
    
    # Tax
    has_tax_registration: bool = False
    tax_id_type: Optional[str] = None
    tax_id_number: Optional[str] = None
    tax_details: Optional[Dict[str, Any]] = None
    
    # PAN
    pan_number: Optional[str] = None
    pan_name: Optional[str] = None
    
    # No GST declaration
    has_no_gst_declaration: bool = False
    declaration_reason: Optional[str] = None
    
    # Bank
    bank_account_name: str
    bank_name: str
    bank_account_number: str
    bank_routing_code: str
    
    # Address
    primary_address: str
    primary_city: str
    primary_state: Optional[str] = None
    primary_postal_code: str
    primary_country: str
    primary_latitude: Optional[Decimal] = None
    primary_longitude: Optional[Decimal] = None
    
    # Contact
    primary_contact_name: str
    primary_contact_email: EmailStr
    primary_contact_phone: str
    
    # Currency
    primary_currency: str = "INR"
    
    # Commodities
    commodities: Optional[List[str]] = None
    
    # Type-specific data
    buyer_data: Optional[BuyerSpecificData] = None
    seller_data: Optional[SellerSpecificData] = None
    transporter_data: Optional[TransporterData] = None
    broker_data: Optional[BrokerData] = None


# ============================================
# VERIFICATION & RISK ASSESSMENT
# ============================================

class VerificationResult(BaseModel):
    """Verification results"""
    tax_verified: bool = False
    pan_verified: bool = False
    bank_verified: bool = False
    names_match: bool = False
    documents_clear: bool = False
    is_duplicate: bool = False
    location_geocoded: bool = False
    details: Dict[str, Any] = {}


class RiskAssessment(BaseModel):
    """Risk scoring result"""
    total_score: int = Field(..., ge=0, le=100)
    category: RiskCategory
    business_age_score: int
    entity_type_score: int
    tax_compliance_score: int
    documentation_score: int
    verification_score: int
    flags: List[str] = []
    recommendation: str


# ============================================
# BUSINESS PARTNER RESPONSES
# ============================================

class PartnerLocationResponse(BaseModel):
    """Location response"""
    id: UUID
    location_type: LocationType
    location_name: str
    gstin_for_location: Optional[str] = None
    address: str
    city: str
    state: Optional[str] = None
    postal_code: str
    country: str
    latitude: Optional[Decimal] = None
    longitude: Optional[Decimal] = None
    geocoded: bool
    status: str
    
    class Config:
        from_attributes = True


class PartnerEmployeeResponse(BaseModel):
    """Employee response"""
    id: UUID
    employee_name: str
    employee_email: EmailStr
    employee_phone: str
    designation: Optional[str] = None
    role: str
    status: str
    invited_at: datetime
    activated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class PartnerDocumentResponse(BaseModel):
    """Document response"""
    id: UUID
    document_type: DocumentType
    file_name: Optional[str] = None
    file_size: Optional[int] = None
    extraction_confidence: Optional[Decimal] = None
    verified: bool
    verified_at: Optional[datetime] = None
    expiry_date: Optional[date] = None
    is_expired: bool
    uploaded_at: datetime
    
    class Config:
        from_attributes = True


class PartnerVehicleResponse(BaseModel):
    """Vehicle response"""
    id: UUID
    vehicle_number: str
    vehicle_type: str
    owner_name: Optional[str] = None
    maker_model: Optional[str] = None
    capacity_tons: Optional[Decimal] = None
    insurance_valid_till: Optional[date] = None
    fitness_valid_till: Optional[date] = None
    verified_via_rto: bool
    status: str
    
    class Config:
        from_attributes = True


class BusinessPartnerResponse(BaseModel):
    """Complete partner response"""
    id: UUID
    partner_code: Optional[str] = None
    partner_type: PartnerType
    service_provider_type: Optional[ServiceProviderType] = None
    trade_classification: Optional[TradeClassification] = None
    
    legal_name: str
    trade_name: Optional[str] = None
    country: str
    business_entity_type: Optional[BusinessEntityType] = None
    registration_date: Optional[date] = None
    
    has_tax_registration: bool
    tax_id_type: Optional[str] = None
    tax_id_number: Optional[str] = None
    tax_verified: bool
    
    pan_number: Optional[str] = None
    pan_verified: bool
    
    has_no_gst_declaration: bool
    
    bank_account_name: str
    bank_name: str
    bank_verified: bool
    
    primary_address: str
    primary_city: str
    primary_state: Optional[str] = None
    primary_postal_code: str
    primary_country: str
    primary_latitude: Optional[Decimal] = None
    primary_longitude: Optional[Decimal] = None
    location_geocoded: bool
    
    primary_contact_name: str
    primary_contact_email: EmailStr
    primary_contact_phone: str
    
    primary_currency: str
    commodities: Optional[List[str]] = None
    
    # Buyer fields
    credit_limit: Optional[Decimal] = None
    credit_utilized: Optional[Decimal] = None
    payment_terms_days: Optional[int] = None
    
    # Seller fields
    production_capacity: Optional[str] = None
    can_arrange_transport: bool = False
    has_quality_lab: bool = False
    
    # Service details
    service_details: Optional[Dict[str, Any]] = None
    
    # Risk
    risk_score: Optional[int] = None
    risk_category: Optional[RiskCategory] = None
    
    # KYC
    kyc_status: KYCStatus
    kyc_verified_at: Optional[datetime] = None
    kyc_expiry_date: Optional[date] = None
    
    # Status
    status: PartnerStatus
    approved_at: Optional[datetime] = None
    
    # Employees
    max_employees_allowed: int
    current_employee_count: int
    
    # Relationships
    locations: List[PartnerLocationResponse] = []
    employees: List[PartnerEmployeeResponse] = []
    documents: List[PartnerDocumentResponse] = []
    vehicles: List[PartnerVehicleResponse] = []
    
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class BusinessPartnerListResponse(BaseModel):
    """List response"""
    id: UUID
    partner_code: Optional[str] = None
    partner_type: PartnerType
    legal_name: str
    country: str
    status: PartnerStatus
    risk_score: Optional[int] = None
    risk_category: Optional[RiskCategory] = None
    kyc_status: KYCStatus
    created_at: datetime
    
    class Config:
        from_attributes = True


# ============================================
# APPROVAL SCHEMAS
# ============================================

class ApprovalDecision(BaseModel):
    """Manager approval decision"""
    decision: str = Field(..., regex="^(approve|reject|request_info)$")
    notes: Optional[str] = None
    credit_limit: Optional[Decimal] = None  # For buyers
    payment_terms_days: Optional[int] = None


# ============================================
# AMENDMENT SCHEMAS
# ============================================

class AmendmentRequest(BaseModel):
    """Request to amend partner data"""
    amendment_type: AmendmentType
    reason: str
    new_value: Dict[str, Any]
    supporting_documents: Optional[List[UUID]] = None


class AmendmentResponse(BaseModel):
    """Amendment status"""
    id: UUID
    partner_id: UUID
    amendment_type: AmendmentType
    field_changed: Optional[str] = None
    old_value: Optional[Dict[str, Any]] = None
    new_value: Optional[Dict[str, Any]] = None
    reason: Optional[str] = None
    status: str
    requested_at: datetime
    approved_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


# ============================================
# KYC RENEWAL SCHEMAS
# ============================================

class KYCRenewalRequest(BaseModel):
    """Initiate KYC renewal"""
    partner_id: UUID


class KYCRenewalResponse(BaseModel):
    """KYC renewal status"""
    id: UUID
    partner_id: UUID
    renewal_due_date: date
    renewal_completed_at: Optional[datetime] = None
    tax_re_verified: bool
    bank_re_verified: bool
    risk_re_assessed: bool
    new_risk_score: Optional[int] = None
    status: str
    
    class Config:
        from_attributes = True


# ============================================
# EMPLOYEE MANAGEMENT SCHEMAS
# ============================================

class EmployeeInvite(BaseModel):
    """Invite employee"""
    employee_name: str
    employee_email: EmailStr
    employee_phone: str
    designation: Optional[str] = None
    permissions: Optional[Dict[str, bool]] = None


class EmployeeResponse(BaseModel):
    """Employee with user details"""
    id: UUID
    partner_id: UUID
    user_id: UUID
    employee_name: str
    employee_email: EmailStr
    employee_phone: str
    designation: Optional[str] = None
    role: str
    permissions: Optional[Dict[str, bool]] = None
    status: str
    invited_at: datetime
    activated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

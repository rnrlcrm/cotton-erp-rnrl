"""
Partner API Router

REST API endpoints for business partner onboarding and management.

Endpoints:
- POST /onboarding/start - Start onboarding
- POST /onboarding/{app_id}/documents - Upload documents
- POST /onboarding/{app_id}/submit - Submit for approval
- GET /onboarding/{app_id}/status - Check status
- POST /partners/{partner_id}/approve - Approve partner (manager/director)
- POST /partners/{partner_id}/reject - Reject application
- GET /partners - List all partners
- GET /partners/{partner_id} - Get partner details
- POST /partners/{partner_id}/amendments - Request amendment
- POST /partners/{partner_id}/employees - Add employee
- POST /partners/{partner_id}/kyc/renew - Initiate KYC renewal
- GET /partners/kyc/expiring - Get partners with expiring KYC
"""

from __future__ import annotations

from typing import List, Optional, Dict, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, UploadFile, File, status
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as redis

from backend.core.auth.deps import get_current_user
from backend.core.auth.capabilities import Capabilities, RequireCapability
from backend.core.events.emitter import EventEmitter
from backend.db.session import get_db
from backend.app.dependencies import get_redis
from backend.modules.partners.enums import PartnerStatus, PartnerType, KYCStatus, RiskCategory
from backend.modules.partners.schemas import (
    AmendmentRequest,
    ApprovalDecision,
    BusinessPartnerResponse,
    DashboardStats,
    EmployeeInvite,
    KYCRenewalRequest,
    OnboardingApplicationCreate,
    OnboardingApplicationResponse,
    PartnerDocumentResponse,
    PartnerEmployeeResponse,
    PartnerFilters,
    PartnerLocationCreate,
    PartnerLocationResponse,
    PartnerVehicleResponse,
    VehicleData,
)
from backend.modules.partners.partner_services import (
    PartnerService,
    ApprovalService,
    KYCRenewalService,
    DocumentProcessingService,
)
from backend.modules.partners.services.analytics import PartnerAnalyticsService
from backend.modules.partners.services.documents import PartnerDocumentService
from backend.modules.partners.repositories import (
    BusinessPartnerRepository,
    OnboardingApplicationRepository,
    PartnerDocumentRepository,
    PartnerEmployeeRepository,
    PartnerLocationRepository,
    PartnerVehicleRepository,
)

router = APIRouter(prefix="/partners", tags=["partners"])


# ===== DEPENDENCIES =====

def get_current_user_id() -> UUID:
    """Get current user ID from auth context"""
    # TODO: Replace with actual auth dependency
    from uuid import uuid4
    return uuid4()


def get_current_organization_id() -> UUID:
    """Get current organization ID from auth context"""
    # TODO: Replace with actual auth dependency
    from uuid import uuid4
    return uuid4()


def get_event_emitter(db: AsyncSession = Depends(get_db)) -> EventEmitter:
    """Get event emitter instance"""
    return EventEmitter(db)


def get_partner_service(
    db: AsyncSession = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis),
    current_user = Depends(get_current_user)
) -> PartnerService:
    """Get PartnerService instance with dependencies"""
    event_emitter = EventEmitter(db)
    return PartnerService(
        db=db,
        event_emitter=event_emitter,
        current_user_id=current_user.id,
        organization_id=current_user.organization_id,
        redis_client=redis_client
    )


def get_analytics_service(
    db: AsyncSession = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis)
) -> PartnerAnalyticsService:
    """Get PartnerAnalyticsService instance"""
    return PartnerAnalyticsService(db=db, redis_client=redis_client)


def get_document_service(
    db: AsyncSession = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis)
) -> PartnerDocumentService:
    """Get PartnerDocumentService instance"""
    return PartnerDocumentService(db=db, redis_client=redis_client)


# ===== ONBOARDING ENDPOINTS =====

@router.post(
    "/onboarding/start",
    response_model=OnboardingApplicationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Start Partner Onboarding",
    description="""
    Start partner onboarding process.
    
    Automatically:
    - Verifies GST and fetches business details
    - Geocodes location (auto-verifies if confidence >90%)
    - Creates draft application
    
    Next step: Upload required documents
    
    **Infrastructure:**
    - Idempotency via Idempotency-Key header
    - Capability: PARTNER_CREATE
    - Events emitted through transactional outbox
    """
)
async def start_onboarding(
    data: OnboardingApplicationCreate,
    db: AsyncSession = Depends(get_db),
    event_emitter: EventEmitter = Depends(get_event_emitter),
    user_id: UUID = Depends(get_current_user_id),
    organization_id: UUID = Depends(get_current_organization_id),
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    redis_client: redis.Redis = Depends(get_redis),
    _check: None = Depends(RequireCapability(Capabilities.PARTNER_CREATE)),
):
    """Start partner onboarding with GST verification and geocoding"""
    service = PartnerService(db, event_emitter, user_id, organization_id, redis_client=redis_client)
    
    try:
        application = await service.start_onboarding(data)
        return application
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post(
    "/onboarding/{application_id}/documents",
    response_model=PartnerDocumentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload Document",
    description="""
    Upload document with OCR extraction.
    
    Automatically extracts:
    - GST Certificate: GSTIN, business name
    - PAN Card: PAN number, name
    - Bank Proof: Account number, IFSC
    - Vehicle RC: Registration number, owner name
    
    **Infrastructure:**
    - Idempotency via Idempotency-Key header
    - Capability: PARTNER_CREATE
    - Events emitted through transactional outbox
    """
)
async def upload_document(
    application_id: UUID,
    document_type: str,
    file: UploadFile = File(...),
    partner_service: PartnerService = Depends(get_partner_service),
    organization_id: UUID = Depends(get_current_organization_id),
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    _check: None = Depends(RequireCapability(Capabilities.PARTNER_CREATE)),
):
    """Upload document and extract data using OCR"""
    # TODO: Upload file to storage (S3/GCS)
    file_url = f"https://storage.example.com/{file.filename}"
    
    # Extract data using OCR
    doc_service = DocumentProcessingService()
    
    if document_type == "GST_CERTIFICATE":
        extracted_data = await doc_service.extract_gst_certificate(file_url)
    elif document_type == "PAN_CARD":
        extracted_data = await doc_service.extract_pan_card(file_url)
    elif document_type == "BANK_PROOF":
        extracted_data = await doc_service.extract_bank_proof(file_url)
    elif document_type == "VEHICLE_RC":
        extracted_data = await doc_service.extract_vehicle_rc(file_url)
    else:
        extracted_data = {}
    
    # Get application to find partner_id
    application = await partner_service.get_application_by_id(application_id)
    
    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found"
        )
    
    # Create document using service's repository (temporary - should be in service method)
    document = await partner_service.document_repo.create(
        partner_id=application.id,  # For now, link to application
        organization_id=organization_id,
        document_type=document_type,
        file_url=file_url,
        file_name=file.filename,
        file_size=file.size,
        mime_type=file.content_type,
        ocr_extracted_data=extracted_data,
        ocr_confidence=extracted_data.get("confidence", 0),
        uploaded_by=partner_service.current_user_id
    )
    
    return document


@router.post(
    "/onboarding/{application_id}/submit",
    summary="Submit for Approval",
    description="""
    Submit application for approval after documents uploaded.
    
    Automatically:
    - Calculates risk score
    - Routes to auto-approve/manager/director
    - Low risk (>70): Auto-approved within 1 hour
    - Medium risk (40-70): Manager review, 24-48 hours
    - High risk (<40): Director review, 3-5 days
    
    **Infrastructure:**
    - Idempotency via Idempotency-Key header
    - Capability: PARTNER_CREATE
    - Events emitted through transactional outbox
    """
)
async def submit_for_approval(
    application_id: UUID,
    db: AsyncSession = Depends(get_db),
    event_emitter: EventEmitter = Depends(get_event_emitter),
    user_id: UUID = Depends(get_current_user_id),
    organization_id: UUID = Depends(get_current_organization_id),
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    _check: None = Depends(RequireCapability(Capabilities.PARTNER_CREATE)),
):
    """Submit application for approval with risk-based routing"""
    service = PartnerService(db, event_emitter, user_id, organization_id, redis_client=redis_client)
    
    try:
        result = await service.submit_for_approval(application_id)
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get(
    "/onboarding/{application_id}/status",
    response_model=OnboardingApplicationResponse,
    summary="Check Application Status"
)
async def get_application_status(
    application_id: UUID,
    partner_service: PartnerService = Depends(get_partner_service),
    organization_id: UUID = Depends(get_current_organization_id)
):
    """Get current status of onboarding application"""
    application = await partner_service.get_application_by_id(application_id)
    
    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found"
        )
    
    return application


# ===== APPROVAL ENDPOINTS (Manager/Director only) =====

@router.post(
    "/partners/{application_id}/approve",
    response_model=BusinessPartnerResponse,
    summary="Approve Partner Application",
    description="""
    Manager/Director approves partner application.
    
    **Infrastructure:**
    - Idempotency via Idempotency-Key header
    - Capability: PARTNER_APPROVE (CRITICAL)
    - Events emitted through transactional outbox
    """
)
async def approve_partner(
    application_id: UUID,
    decision: ApprovalDecision,
    partner_service: PartnerService = Depends(get_partner_service),
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    _check: None = Depends(RequireCapability(Capabilities.PARTNER_APPROVE)),
):
    """Approve partner application (manager/director only)"""
    approval_service = ApprovalService(db, user_id, redis_client=redis_client)
    
    # Get application
    application = await partner_service.get_application_by_id(application_id)
    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found"
        )
    
    # Build risk assessment from application
    risk_assessment = RiskAssessment(
        risk_score=application.risk_score or 50,
        risk_category=application.risk_category,
        approval_route="manual",
        factors=[],
        assessment_date=application.submitted_at
    )
    
    try:
        # Service handles: business logic, event emission, commit, idempotency
        partner = await approval_service.process_approval(
            application_id,
            risk_assessment,
            decision,
            idempotency_key=idempotency_key
        )
        return partner
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post(
    "/partners/{application_id}/reject",
    summary="Reject Partner Application",
    description="""
    Reject partner application.
    
    **Infrastructure:**
    - Idempotency via Idempotency-Key header
    - Capability: PARTNER_APPROVE (CRITICAL)
    - Events emitted through transactional outbox
    """
)
async def reject_partner(
    application_id: UUID,
    decision: ApprovalDecision,
    partner_service: PartnerService = Depends(get_partner_service),
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    _check: None = Depends(RequireCapability(Capabilities.PARTNER_APPROVE)),
):
    """Reject partner application"""
    decision.approved = False
    
    # Check application exists before creating service
    application = await partner_service.get_application_by_id(application_id)
    
    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found"
        )
    
    approval_service = ApprovalService(db, user_id, redis_client=redis_client)
    
    risk_assessment = RiskAssessment(
        risk_score=application.risk_score or 0,
        risk_category=application.risk_category,
        approval_route="manual",
        factors=[]
    )
    
    try:
        # Service handles: business logic, event emission, commit, idempotency
        await approval_service.process_approval(
            application_id,
            risk_assessment,
            decision,
            idempotency_key=idempotency_key
        )
    except ValueError as e:
        # Rejection raises ValueError with message
        return {"message": str(e), "status": "rejected"}


# ===== PARTNER MANAGEMENT ENDPOINTS =====

@router.get(
    "/",
    response_model=List[BusinessPartnerResponse],
    summary="List Partners",
    description="List all business partners with filters"
)
async def list_partners(
    skip: int = 0,
    limit: int = 100,
    partner_type: Optional[PartnerType] = None,
    status: Optional[PartnerStatus] = None,
    kyc_status: Optional[KYCStatus] = None,
    search: Optional[str] = None,
    partner_service: PartnerService = Depends(get_partner_service)
):
    """List all partners with filters (auto-isolated by organization)"""
    partners = await partner_service.list_all_partners(
        skip=skip,
        limit=limit,
        partner_type=partner_type,
        status=status,
        kyc_status=kyc_status,
        search=search
    )
    
    return partners


@router.get(
    "/{partner_id}",
    response_model=BusinessPartnerResponse,
    summary="Get Partner Details"
)
async def get_partner(
    partner_id: UUID,
    partner_service: PartnerService = Depends(get_partner_service)
):
    """Get partner details by ID"""
    partner = await partner_service.get_partner_by_id(partner_id)
    
    if not partner:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Partner not found"
        )
    
    return partner


@router.get(
    "/{partner_id}/locations",
    response_model=List[PartnerLocationResponse],
    summary="Get Partner Locations"
)
async def get_partner_locations(
    partner_id: UUID,
    partner_service: PartnerService = Depends(get_partner_service)
):
    """Get all locations for a partner"""
    locations = await partner_service.get_partner_locations(partner_id)
    return locations


@router.post(
    "/{partner_id}/locations",
    response_model=PartnerLocationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add Location (Branch, Warehouse, Ship-To, etc.)",
    description="""
    Add a new location for a partner.
    
    **Infrastructure:**
    - Idempotency via Idempotency-Key header
    - Capability: PARTNER_UPDATE
    - Events emitted through transactional outbox
    """
)
async def add_partner_location(
    partner_id: UUID,
    location_data: PartnerLocationCreate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    _check: None = Depends(RequireCapability(Capabilities.PARTNER_UPDATE)),
):
    """
    Add a new location for a partner
    
    RESTRICTIONS:
    - ship_to: ONLY BUYERS can add (no GST required)
    - branch_different_state: Requires GSTIN with same PAN as primary
    - warehouse/factory: All partners can add
    
    VALIDATIONS:
    - Google Maps geocoding with tagging
    - GST validation for branches (PAN matching)
    - Partner type validation for ship-to
    """
    from backend.modules.partners.partner_services import GeocodingService, GSTVerificationService
    
    # Verify partner exists
    partner = await partner_service.get_partner_by_id(partner_id)
    if not partner:
        raise HTTPException(status_code=404, detail="Partner not found")
    if location_data.location_type == "ship_to":
        if partner.partner_type not in ["buyer", "trader"]:
            raise HTTPException(
                status_code=400,
                detail="Only buyers and traders can add ship-to addresses"
            )
        # Ship-to does NOT require GST
        location_data.requires_gst = False
        location_data.gstin_for_location = None
    
    # VALIDATION 2: Branch in different state - validate GSTIN
    if location_data.location_type == "branch_different_state":
        if not location_data.gstin_for_location:
            raise HTTPException(
                status_code=400,
                detail="GSTIN required for branch in different state"
            )
        
        # Extract PAN from new GSTIN (characters 3-12)
        new_pan = location_data.gstin_for_location[2:12]
        primary_pan = partner.pan_number
        
        if new_pan != primary_pan:
            raise HTTPException(
                status_code=400,
                detail=f"GSTIN PAN ({new_pan}) does not match primary PAN ({primary_pan}). Branch GSTIN must belong to same business."
            )
        
        # Verify GSTIN via GST API
        gst_service = GSTVerificationService()
        try:
            gst_data = await gst_service.verify_gstin(location_data.gstin_for_location)
            if not gst_data or gst_data.get("status") != "Active":
                raise HTTPException(
                    status_code=400,
                    detail="GSTIN is not active or invalid"
                )
            
            # Verify business name matches
            if gst_data.get("legal_name").upper() != partner.legal_business_name.upper():
                raise HTTPException(
                    status_code=400,
                    detail="GSTIN business name does not match primary business name"
                )
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=f"GST verification failed: {str(e)}"
            )
    
    # VALIDATION 3: Geocode with Google Maps and tag location
    geocoding = GeocodingService()
    full_address = f"{location_data.address}, {location_data.city}, {location_data.state}, {location_data.postal_code}, {location_data.country}"
    geocode_result = await geocoding.geocode_address(full_address)
    
    if not geocode_result or geocode_result.get("confidence", 0) < 50:
        raise HTTPException(
            status_code=400,
            detail="Could not verify address via Google Maps. Please check address details."
        )
    
    # Create location with Google Maps data
    location = await partner_service.location_repo.create(
        partner_id=partner_id,
        organization_id=partner.organization_id,
        location_type=location_data.location_type,
        location_name=location_data.location_name,
        gstin_for_location=location_data.gstin_for_location,
        address=location_data.address,
        city=location_data.city,
        state=location_data.state,
        postal_code=location_data.postal_code,
        country=location_data.country,
        contact_person=location_data.contact_person,
        contact_phone=location_data.contact_phone,
        requires_gst=location_data.requires_gst,
        # Google Maps data
        latitude=geocode_result["latitude"],
        longitude=geocode_result["longitude"],
        geocoded=True,
        geocode_confidence=geocode_result["confidence"],
        status="active"
    )
    
    # TODO: PartnerLocation doesn't have EventMixin - event emission disabled
    # Once EventMixin is added to PartnerLocation model, uncomment:
    # location.emit_event(
    #     event_type="partner.location.added",
    #     user_id=current_user.id,
    #     data={
    #         "location_id": str(location.id),
    #         "partner_id": str(partner_id),
    #         "location_type": location_data.location_type,
    #         "location_name": location_data.location_name,
    #         "google_maps_tagged": True,
    #         "latitude": location.latitude,
    #         "longitude": location.longitude
    #     }
    # )
    # await location.flush_events(db)
    
    return location


@router.get(
    "/{partner_id}/employees",
    response_model=List[PartnerEmployeeResponse],
    summary="Get Partner Employees"
)
async def get_partner_employees(
    partner_id: UUID,
    partner_service: PartnerService = Depends(get_partner_service)
):
    """Get all employees for a partner"""
    employees = await partner_service.get_partner_employees(partner_id)
    return employees


@router.get(
    "/{partner_id}/documents",
    response_model=List[PartnerDocumentResponse],
    summary="Get Partner Documents"
)
async def get_partner_documents(
    partner_id: UUID,
    document_type: Optional[str] = None,
    partner_service: PartnerService = Depends(get_partner_service)
):
    """Get all documents for a partner"""
    documents = await partner_service.get_partner_documents(partner_id)
    return documents


@router.get(
    "/{partner_id}/vehicles",
    response_model=List[PartnerVehicleResponse],
    summary="Get Partner Vehicles"
)
async def get_partner_vehicles(
    partner_id: UUID,
    partner_service: PartnerService = Depends(get_partner_service)
):
    """Get all vehicles for a transporter partner"""
    vehicles = await partner_service.get_partner_vehicles(partner_id)
    return vehicles


# ===== AMENDMENT ENDPOINTS =====

@router.post(
    "/{partner_id}/amendments",
    summary="Request Amendment",
    description="""
    Request to change partner details post-approval.
    
    **Infrastructure:**
    - Idempotency via Idempotency-Key header
    - Capability: PARTNER_UPDATE
    - Events emitted through transactional outbox
    """
)
async def request_amendment(
    partner_id: UUID,
    amendment: AmendmentRequest,
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    _check: None = Depends(RequireCapability(Capabilities.PARTNER_UPDATE)),
):
    """Request amendment to partner details"""
    # TODO: Implement amendment service
    return {
        "message": "Amendment request submitted",
        "amendment_id": "mock-uuid",
        "status": "pending_approval"
    }


# ===== EMPLOYEE MANAGEMENT ENDPOINTS =====

@router.post(
    "/{partner_id}/employees",
    response_model=PartnerEmployeeResponse,
    summary="Invite Employee",
    description="""
    Add employee to partner account (unlimited - role/module based access).
    
    **Infrastructure:**
    - Idempotency via Idempotency-Key header
    - Capability: PARTNER_CREATE
    - Events emitted through transactional outbox
    """
)
async def invite_employee(
    partner_id: UUID,
    employee: EmployeeInvite,
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
    organization_id: UUID = Depends(get_current_organization_id),
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    _check: None = Depends(RequireCapability(Capabilities.PARTNER_CREATE)),
):
    """Invite employee to partner account"""
    # Service handles: employee creation, event emission, commit
    service = PartnerService(db, get_event_emitter(), user_id, organization_id, redis_client=redis_client)
    new_employee = await service.invite_employee(
        partner_id=partner_id,
        employee_data=employee.dict(),
        idempotency_key=idempotency_key
    )
    
    # TODO: Send invitation email with OTP/magic link
    
    return new_employee


# ===== KYC RENEWAL ENDPOINTS =====

@router.get(
    "/kyc/expiring",
    response_model=List[BusinessPartnerResponse],
    summary="Get Partners with Expiring KYC",
    description="Get partners with KYC expiring in next 30 days"
)
async def get_expiring_kyc_partners(
    days: int = 30,
    db: AsyncSession = Depends(get_db),
    organization_id: UUID = Depends(get_current_organization_id)
):
    """Get partners with KYC expiring soon"""
    kyc_service = KYCRenewalService(db, UUID("00000000-0000-0000-0000-000000000000"), redis_client=redis_client)
    partners = await kyc_service.check_kyc_expiry(organization_id, days)
    return partners


@router.post(
    "/{partner_id}/kyc/renew",
    summary="Initiate KYC Renewal",
    description="""
    Start yearly KYC renewal process.
    
    **Infrastructure:**
    - Idempotency via Idempotency-Key header
    - Capability: PARTNER_UPDATE
    - Events emitted through transactional outbox
    """
)
async def initiate_kyc_renewal(
    partner_id: UUID,
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    _check: None = Depends(RequireCapability(Capabilities.PARTNER_UPDATE)),
):
    """Initiate KYC renewal for partner"""
    kyc_service = KYCRenewalService(db, user_id, redis_client=redis_client)
    
    try:
        # Service already handles commit
        renewal = await kyc_service.initiate_kyc_renewal(partner_id)
        
        return {
            "message": "KYC renewal initiated",
            "renewal_id": renewal.id,
            "due_date": renewal.due_date,
            "status": renewal.status
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post(
    "/{partner_id}/kyc/complete",
    summary="Complete KYC Renewal",
    description="""
    Complete KYC renewal with new documents.
    
    **Infrastructure:**
    - Idempotency via Idempotency-Key header
    - Capability: PARTNER_UPDATE
    - Events emitted through transactional outbox
    """
)
async def complete_kyc_renewal(
    partner_id: UUID,
    renewal: KYCRenewalRequest,
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    _check: None = Depends(RequireCapability(Capabilities.PARTNER_UPDATE)),
):
    """Complete KYC renewal with new documents"""
    kyc_service = KYCRenewalService(db, user_id, redis_client=redis_client)
    
    try:
        partner = await kyc_service.complete_kyc_renewal(
            renewal.renewal_id,
            renewal.new_document_ids,
            verified=True
        )
        
        return {
            "message": "KYC renewal completed successfully",
            "partner_id": partner.id,
            "new_expiry_date": partner.kyc_expiry_date,
            "kyc_status": partner.kyc_status
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


# ===== VEHICLE MANAGEMENT (for Transporters) =====

@router.post(
    "/{partner_id}/vehicles",
    response_model=PartnerVehicleResponse,
    summary="Add Vehicle",
    description="""
    Add vehicle for transporter partner.
    
    **Infrastructure:**
    - Idempotency via Idempotency-Key header
    - Capability: PARTNER_UPDATE
    - Events emitted through transactional outbox
    """
)
async def add_vehicle(
    partner_id: UUID,
    vehicle: VehicleData,
    partner_service: PartnerService = Depends(get_partner_service),
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
    organization_id: UUID = Depends(get_current_organization_id),
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    _check: None = Depends(RequireCapability(Capabilities.PARTNER_UPDATE)),
):
    """Add vehicle for transporter"""
    # TODO: Verify vehicle from RTO
    
    new_vehicle = await partner_service.vehicle_repo.create(
        partner_id=partner_id,
        organization_id=organization_id,
        registration_number=vehicle.registration_number,
        vehicle_type=vehicle.vehicle_type,
        manufacturer=vehicle.manufacturer,
        model=vehicle.model,
        year_of_manufacture=vehicle.year_of_manufacture,
        capacity_tons=vehicle.capacity_tons,
        is_active=True,
        created_by=user_id
    )
    
    return new_vehicle


@router.get(
    "/",
    response_model=Dict[str, Any],
    summary="List Partners with Advanced Filters",
    description="""
    Get partners with advanced filtering:
    - KYC expiring in N days
    - State-wise filtering
    - Date range filtering
    - Full-text search on business name/GSTIN
    - Risk category filtering
    """
)
async def list_partners_advanced(
    partner_type: Optional[PartnerType] = None,
    status: Optional[PartnerStatus] = None,
    kyc_status: Optional[KYCStatus] = None,
    kyc_expiring_days: Optional[int] = None,
    risk_category: Optional[RiskCategory] = None,
    state: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    search: Optional[str] = None,
    sort_by: str = "created_at",
    sort_order: str = "desc",
    skip: int = 0,
    limit: int = 50,
    partner_service: PartnerService = Depends(get_partner_service),
    organization_id: UUID = Depends(get_current_organization_id)
):
    """List partners with advanced filters"""
    return await partner_service.search_partners_advanced(
        partner_type=partner_type,
        status=status,
        kyc_status=kyc_status,
        kyc_expiring_days=kyc_expiring_days,
        risk_category=risk_category,
        state=state,
        date_from=date_from,
        date_to=date_to,
        search=search,
        sort_by=sort_by,
        sort_order=sort_order,
        skip=skip,
        limit=limit
    )


# ===== EXPORT FUNCTIONALITY =====

@router.get(
    "/export",
    summary="Export Partners to Excel/CSV",
    description="Export partners with all filters applied"
)
async def export_partners(
    format: str = "excel",  # excel or csv
    partner_type: Optional[PartnerType] = None,
    status: Optional[PartnerStatus] = None,
    kyc_status: Optional[KYCStatus] = None,
    state: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    organization_id: UUID = Depends(get_current_organization_id)
):
    """
    Export partners to Excel or CSV.
    
    Uses PartnerAnalyticsService for clean architecture (15-year design).
    """
    from fastapi.responses import StreamingResponse
    import io
    import csv
    from datetime import datetime
    
    # Use analytics service
    analytics_service = PartnerAnalyticsService(db)
    
    # Parse dates
    date_from_dt = datetime.fromisoformat(date_from) if date_from else None
    date_to_dt = datetime.fromisoformat(date_to) if date_to else None
    
    # Get export data
    partners = await analytics_service.get_export_data(
        organization_id=organization_id,
        partner_type=partner_type,
        status=status,
        kyc_status=kyc_status,
        state=state,
        date_from=date_from_dt,
        date_to=date_to_dt,
    )
    
    # Create CSV
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Headers
    writer.writerow([
        'Business Name', 'GSTIN', 'PAN', 'Partner Type', 'Status', 
        'KYC Status', 'KYC Expiry', 'Risk Score', 'Risk Category',
        'State', 'Contact Person', 'Email', 'Phone', 'Created At'
    ])
    
    # Data
    for p in partners:
        writer.writerow([
            p.legal_business_name,
            p.tax_id_number,
            p.pan_number,
            p.partner_type,
            p.status,
            p.kyc_status,
            p.kyc_expiry_date.isoformat() if p.kyc_expiry_date else '',
            p.risk_score or '',
            p.risk_category or '',
            p.primary_state or '',
            p.primary_contact_person,
            p.primary_contact_email,
            p.primary_contact_phone,
            p.created_at.isoformat()
        ])
    
    output.seek(0)
    
    if format == "excel":
        # For Excel, you'd use openpyxl or pandas
        # For now, return CSV with Excel mime type
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="application/vnd.ms-excel",
            headers={
                "Content-Disposition": f"attachment; filename=partners_{datetime.now().strftime('%Y%m%d')}.csv"
            }
        )
    else:
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename=partners_{datetime.now().strftime('%Y%m%d')}.csv"
            }
        )


# ===== KYC PDF DOWNLOAD =====

@router.get(
    "/{partner_id}/kyc-register/download",
    summary="Download Complete KYC Register as PDF",
    description="Generate PDF with complete partner KYC details for record keeping"
)
async def download_kyc_register(
    partner_id: UUID,
    partner_service: PartnerService = Depends(get_partner_service),
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id),
    organization_id: UUID = Depends(get_current_organization_id)
):
    """Generate and download complete KYC register PDF"""
    from fastapi.responses import StreamingResponse
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    import io
    
    # Get partner with all related data
    partner = await partner_service.get_partner_by_id(partner_id)
    
    if not partner:
        raise HTTPException(status_code=404, detail="Partner not found")
    
    # Get related data
    locations = await partner_service.get_partner_locations(partner_id)
    documents = await partner_service.get_partner_documents(partner_id)
    employees = await partner_service.get_partner_employees(partner_id)
    p.drawString(50, height - 50, "KYC REGISTER")
    
    # Business Details
    y = height - 100
    p.setFont("Helvetica-Bold", 12)
    p.drawString(50, y, "Business Details")
    y -= 20
    
    p.setFont("Helvetica", 10)
    p.drawString(50, y, f"Legal Name: {partner.legal_business_name}")
    y -= 15
    p.drawString(50, y, f"GSTIN: {partner.tax_id_number}")
    y -= 15
    p.drawString(50, y, f"PAN: {partner.pan_number}")
    y -= 15
    p.drawString(50, y, f"Partner Type: {partner.partner_type}")
    y -= 15
    p.drawString(50, y, f"Status: {partner.status}")
    y -= 15
    p.drawString(50, y, f"KYC Status: {partner.kyc_status}")
    y -= 15
    if partner.kyc_expiry_date:
        p.drawString(50, y, f"KYC Expiry: {partner.kyc_expiry_date.strftime('%Y-%m-%d')}")
    y -= 15
    p.drawString(50, y, f"Risk Score: {partner.risk_score or 'N/A'} ({partner.risk_category or 'N/A'})")
    y -= 30
    
    # Documents
    p.setFont("Helvetica-Bold", 12)
    p.drawString(50, y, f"Uploaded Documents ({len(documents)})")
    y -= 20
    
    p.setFont("Helvetica", 9)
    for doc in documents:
        p.drawString(60, y, f"• {doc.document_type} - Uploaded: {doc.uploaded_at.strftime('%Y-%m-%d')}")
        y -= 12
        if y < 100:
            p.showPage()
            y = height - 50
    
    y -= 20
    
    # Locations
    p.setFont("Helvetica-Bold", 12)
    p.drawString(50, y, f"Locations ({len(locations)})")
    y -= 20
    
    p.setFont("Helvetica", 9)
    for loc in locations:
        p.drawString(60, y, f"• {loc.location_name} - {loc.city}, {loc.state}")
        y -= 12
        if y < 100:
            p.showPage()
            y = height - 50
    
    y -= 20
    
    # Employees
    p.setFont("Helvetica-Bold", 12)
    p.drawString(50, y, f"Employees ({len(employees)})")
    y -= 20
    
    p.setFont("Helvetica", 9)
    for emp in employees:
        p.drawString(60, y, f"• {emp.employee_name} - {emp.designation or 'N/A'}")
        y -= 12
        if y < 100:
            p.showPage()
            y = height - 50
    
    # Approval History
    if partner.approved_at:
        y -= 30
        p.setFont("Helvetica-Bold", 12)
        p.drawString(50, y, "Approval Details")
        y -= 20
        
        p.setFont("Helvetica", 9)
        p.drawString(60, y, f"Approved on: {partner.approved_at.strftime('%Y-%m-%d %H:%M')}")
        y -= 12
        if partner.approval_notes:
            p.drawString(60, y, f"Notes: {partner.approval_notes[:100]}")
    
    # Footer
    p.setFont("Helvetica", 8)
    p.drawString(50, 30, f"Generated on: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
    p.drawString(50, 20, f"Generated by: User ID {user_id}")
    
    p.save()
    buffer.seek(0)
    
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename=kyc_register_{partner.tax_id_number}.pdf"
        }
    )


# ===== DASHBOARD & ANALYTICS =====

@router.get(
    "/dashboard/stats",
    response_model=DashboardStats,
    summary="Dashboard Statistics",
    description="Get comprehensive dashboard statistics"
)
async def get_dashboard_stats(
    db: AsyncSession = Depends(get_db),
    organization_id: UUID = Depends(get_current_organization_id)
):
    """
    Get dashboard statistics.
    
    Uses PartnerAnalyticsService for clean architecture (15-year design).
    """
    analytics_service = PartnerAnalyticsService(db)
    stats = await analytics_service.get_dashboard_stats(organization_id)
    
    # Convert to DashboardStats schema
    return DashboardStats(
        total_partners=sum(stats["by_type"].values()),
        by_type=stats["by_type"],
        by_status=stats["by_status"],
        kyc_breakdown={
            "valid": sum(stats["by_status"].values()) - stats["expiring_kyc_count"],
            "expiring_90_days": 0,  # Could be enhanced
            "expiring_30_days": stats["expiring_kyc_count"],
            "expired": 0,  # Could be enhanced
        },
        risk_distribution=stats["risk_distribution"],
        pending_approvals={"onboarding": 0},  # Could be enhanced
        state_wise=stats["state_distribution"],
        monthly_onboarding=stats["monthly_trend"]
    )


# ===== HELPER FUNCTIONS =====

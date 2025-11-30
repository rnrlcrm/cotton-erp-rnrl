"""
Partner Services

Business logic for partner onboarding and management.

Services:
- GSTVerificationService: Auto-fetch GST details from GSTN API
- GeocodingService: Google Maps location verification
- RTOVerificationService: Vehicle RC verification from Parivahan
- DocumentProcessingService: OCR extraction and verification
- RiskScoringService: Calculate 0-100 risk score
- ApprovalService: Route to auto/manager/director based on risk
- KYCRenewalService: Track and trigger yearly KYC renewals
- PartnerService: Orchestrates complete onboarding workflow
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as redis

from backend.core.events.emitter import EventEmitter
from backend.core.resilience.circuit_breaker import api_circuit_breaker
from backend.core.outbox import OutboxRepository
from backend.modules.partners.enums import (
    AmendmentType,
    BusinessEntityType,
    DocumentType,
    KYCStatus,
    PartnerStatus,
    PartnerType,
    RiskCategory,
)
from backend.modules.partners.models import (
    BusinessPartner,
    PartnerAmendment,
    PartnerDocument,
    PartnerEmployee,
    PartnerKYCRenewal,
    PartnerLocation,
    PartnerOnboardingApplication,
    PartnerVehicle,
)
from backend.modules.partners.repositories import (
    BusinessPartnerRepository,
    OnboardingApplicationRepository,
    PartnerAmendmentRepository,
    PartnerDocumentRepository,
    PartnerEmployeeRepository,
    PartnerKYCRenewalRepository,
    PartnerLocationRepository,
    PartnerVehicleRepository,
)
from backend.modules.partners.schemas import (
    ApprovalDecision,
    GSTVerificationResult,
    OnboardingApplicationCreate,
    RiskAssessment,
    VerificationResult,
)


class GSTVerificationService:
    """
    GST verification and data fetching service.
    
    Auto-fetches business details from GSTN API to minimize user data entry.
    """
    
    def __init__(self):
        pass
    
    @api_circuit_breaker  # 3 retries, 60s timeout, exponential backoff
    async def verify_gstin(self, gstin: str) -> GSTVerificationResult:
        """
        Verify GSTIN and fetch business details from GSTN API.
        
        **Circuit Breaker**: Auto-retry on failure (3 attempts, exponential backoff).
        If GSTN API is down, fail fast after 3 retries to prevent cascade failures.
        
        Args:
            gstin: 15-character GSTIN
        
        Returns:
            GSTVerificationResult with business details
        
        Note: In production, this calls actual GSTN API
        """
        # Validate GSTIN format
        if not gstin or len(gstin) != 15:
            return GSTVerificationResult(
                verified=False,
                gstin=gstin,
                error="Invalid GSTIN format. Must be 15 characters."
            )
        
        # TODO: Call actual GSTN API
        # For now, mock response
        # In production: requests.post('https://gstapi.gov.in/verify', ...)
        
        # Mock verified response
        return GSTVerificationResult(
            verified=True,
            gstin=gstin,
            legal_name="Sample Business Pvt Ltd",
            trade_name="Sample Traders",
            gst_status="Active",
            registration_date=datetime(2020, 1, 15).date(),
            entity_type=BusinessEntityType.PRIVATE_LIMITED,
            principal_place={
                "address": "123 Business Park, Industrial Area",
                "city": "Mumbai",
                "state": "Maharashtra",
                "postal_code": "400001",
                "state_code": "27"
            },
            additional_places=[
                {
                    "gstin": gstin[:2] + "AAAA1234B2Z5",
                    "address": "Branch Office, Ahmedabad",
                    "city": "Ahmedabad",
                    "state": "Gujarat"
                }
            ],
            business_activities=["Trading", "Manufacturing"],
            annual_turnover=Decimal("50000000.00"),
            last_return_filed=datetime(2024, 10, 1).date(),
            compliance_rating="Good"
        )
    
    @api_circuit_breaker  # 3 retries, 60s timeout, exponential backoff
    async def search_other_gstins(self, pan: str) -> List[str]:
        """
        Search for other GSTINs registered under same PAN.
        
        **Circuit Breaker**: Auto-retry on failure to prevent cascade failures.
        
        Useful for businesses with multiple state registrations.
        
        Args:
            pan: 10-character PAN
        
        Returns:
            List of GSTINs
        """
        # TODO: Call GSTN API to search by PAN
        # For now, mock
        
        return [
            "27AAAPB1234C1Z5",  # Maharashtra
            "24AAAPB1234C1Z3",  # Gujarat
            "29AAAPB1234C1Z7",  # Karnataka
        ]


class GeocodingService:
    """
    Location verification using Google Maps Geocoding API.
    
    Auto-verifies locations without user confirmation if confidence >90%.
    """
    
    def __init__(self):
        self.api_key = None  # TODO: Load from settings
    
    async def geocode_address(self, address: str, city: str, state: str, postal_code: str) -> Dict:
        """
        Geocode address and verify location.
        
        Args:
            address: Street address
            city: City name
            state: State name
            postal_code: PIN code
        
        Returns:
            Dict with latitude, longitude, confidence, formatted_address
        """
        # Construct full address
        full_address = f"{address}, {city}, {state} {postal_code}, India"
        
        # TODO: Call Google Maps Geocoding API
        # For now, mock response
        # In production: googlemaps.Client(key=self.api_key).geocode(full_address)
        
        # Mock high-confidence result
        return {
            "latitude": 19.0760,
            "longitude": 72.8777,
            "confidence": 0.95,  # >90% = auto-verify
            "formatted_address": f"{address}, {city}, {state} {postal_code}, India",
            "location_type": "ROOFTOP",  # ROOFTOP = high accuracy
            "place_id": "ChIJwe1EZjDEDzkRvAu-v2bAuGw"
        }
    
    async def reverse_geocode(self, latitude: float, longitude: float) -> Dict:
        """
        Reverse geocode coordinates to address.
        
        Args:
            latitude: Latitude
            longitude: Longitude
        
        Returns:
            Dict with address components
        """
        # TODO: Call Google Maps Reverse Geocoding API
        
        return {
            "formatted_address": "123 Business Park, Mumbai, Maharashtra 400001",
            "city": "Mumbai",
            "state": "Maharashtra",
            "postal_code": "400001",
            "country": "India"
        }


class RTOVerificationService:
    """
    Vehicle RC verification from Parivahan/Vahan API.
    
    For transporters adding vehicle details.
    """
    
    def __init__(self):
        pass
    
    async def verify_vehicle_rc(self, registration_number: str) -> Dict:
        """
        Verify vehicle RC from Parivahan database.
        
        Args:
            registration_number: Vehicle registration number (e.g., MH01AB1234)
        
        Returns:
            Dict with vehicle details
        """
        # TODO: Call Parivahan/Vahan API
        # For now, mock
        
        return {
            "verified": True,
            "registration_number": registration_number,
            "owner_name": "Sample Transport Pvt Ltd",
            "vehicle_class": "Light Goods Vehicle",
            "vehicle_type": "Open Body",
            "manufacturer": "Tata Motors",
            "model": "407 Pickup",
            "registration_date": datetime(2019, 5, 15).date(),
            "fitness_valid_until": datetime(2025, 5, 15).date(),
            "insurance_valid_until": datetime(2025, 12, 31).date(),
            "permit_type": "All India Permit",
            "fuel_type": "Diesel",
            "seating_capacity": 2,
            "unladen_weight": "1500 kg",
            "gross_weight": "3500 kg"
        }


class DocumentProcessingService:
    """
    OCR extraction and document verification.
    
    Auto-extracts data from uploaded documents to minimize user typing.
    """
    
    def __init__(self):
        pass
    
    async def extract_gst_certificate(self, file_url: str) -> Dict:
        """
        Extract GSTIN and business name from GST certificate using OCR.
        
        Args:
            file_url: URL to uploaded GST certificate
        
        Returns:
            Dict with extracted data
        """
        # TODO: Call OCR service (Tesseract, AWS Textract, Google Vision)
        # For now, mock
        
        return {
            "gstin": "27AAAPB1234C1Z5",
            "legal_name": "Sample Business Pvt Ltd",
            "trade_name": "Sample Traders",
            "registration_date": "15/01/2020",
            "principal_address": "123 Business Park, Mumbai",
            "confidence": 0.92
        }
    
    async def extract_pan_card(self, file_url: str) -> Dict:
        """
        Extract PAN from PAN card using OCR.
        
        Args:
            file_url: URL to uploaded PAN card
        
        Returns:
            Dict with extracted data
        """
        # TODO: Call OCR service
        
        return {
            "pan": "AAAPB1234C",
            "name": "SAMPLE BUSINESS PVT LTD",
            "confidence": 0.95
        }
    
    async def extract_bank_proof(self, file_url: str) -> Dict:
        """
        Extract account details from cancelled cheque/bank statement.
        
        Args:
            file_url: URL to uploaded bank proof
        
        Returns:
            Dict with extracted data
        """
        # TODO: Call OCR service
        
        return {
            "account_number": "1234567890",
            "ifsc_code": "HDFC0001234",
            "account_holder_name": "Sample Business Pvt Ltd",
            "bank_name": "HDFC Bank",
            "branch": "Mumbai Branch",
            "confidence": 0.88
        }
    
    async def extract_vehicle_rc(self, file_url: str) -> Dict:
        """
        Extract vehicle details from RC book.
        
        Args:
            file_url: URL to uploaded RC book
        
        Returns:
            Dict with extracted data
        """
        # TODO: Call OCR service
        
        return {
            "registration_number": "MH01AB1234",
            "owner_name": "Sample Transport Pvt Ltd",
            "vehicle_class": "Light Goods Vehicle",
            "manufacturer": "Tata Motors",
            "model": "407 Pickup",
            "confidence": 0.90
        }


class RiskScoringService:
    """
    Calculate risk score (0-100) based on business profile.
    
    Used for approval routing:
    - Low risk (>70): Auto-approved
    - Medium risk (40-70): Manager approval
    - High risk (<40): Director approval
    """
    
    def __init__(self):
        pass
    
    async def calculate_risk_score(
        self,
        partner_type: PartnerType,
        entity_type: BusinessEntityType,
        business_age_months: int,
        gst_turnover: Optional[Decimal] = None,
        gst_compliance: Optional[str] = None,
        has_quality_lab: bool = False,
        can_arrange_transport: bool = False,
        production_capacity: Optional[str] = None
    ) -> RiskAssessment:
        """
        Calculate comprehensive risk score.
        
        Args:
            partner_type: Type of partner
            entity_type: Business entity type
            business_age_months: Age in months
            gst_turnover: Annual GST turnover
            gst_compliance: GST compliance rating
            has_quality_lab: Has quality testing lab
            can_arrange_transport: Can arrange own transport
            production_capacity: Production capacity (for sellers)
        
        Returns:
            RiskAssessment with score, category, and factors
        """
        score = 50  # Base score
        factors = []
        
        # Track individual component scores
        business_age_score = 0
        entity_type_score = 0
        tax_compliance_score = 0
        documentation_score = 0
        verification_score = 0
        
        # === Business Age ===
        if business_age_months >= 60:  # 5+ years
            business_age_score = 20
            score += 20
            factors.append({
                "factor": "Business Age",
                "impact": "Positive",
                "detail": "Established business (5+ years)",
                "points": 20
            })
        elif business_age_months >= 24:  # 2+ years
            business_age_score = 10
            score += 10
            factors.append({
                "factor": "Business Age",
                "impact": "Positive",
                "detail": "Mature business (2+ years)",
                "points": 10
            })
        elif business_age_months < 12:  # <1 year
            business_age_score = -15
            score -= 15
            factors.append({
                "factor": "Business Age",
                "impact": "Negative",
                "detail": "New business (<1 year)",
                "points": -15
            })
        
        # === Entity Type ===
        if entity_type in [BusinessEntityType.PRIVATE_LIMITED, BusinessEntityType.PUBLIC_LIMITED]:
            entity_type_score = 15
            score += 15
            factors.append({
                "factor": "Entity Type",
                "impact": "Positive",
                "detail": "Limited company (lower personal liability risk)",
                "points": 15
            })
        elif entity_type == BusinessEntityType.PARTNERSHIP:
            entity_type_score = 5
            score += 5
            factors.append({
                "factor": "Entity Type",
                "impact": "Neutral",
                "detail": "Partnership (moderate risk)",
                "points": 5
            })
        elif entity_type == BusinessEntityType.PROPRIETORSHIP:
            entity_type_score = -5
            score -= 5
            factors.append({
                "factor": "Entity Type",
                "impact": "Negative",
                "detail": "Proprietorship (higher personal risk)",
                "points": -5
            })
        
        # === GST Turnover ===
        if gst_turnover:
            if gst_turnover >= Decimal("10000000"):  # 1 Crore+
                score += 15
                factors.append({
                    "factor": "Annual Turnover",
                    "impact": "Positive",
                    "detail": f"High turnover (₹{gst_turnover:,.0f})",
                    "points": 15
                })
            elif gst_turnover >= Decimal("5000000"):  # 50 Lakhs+
                score += 10
                factors.append({
                    "factor": "Annual Turnover",
                    "impact": "Positive",
                    "detail": f"Good turnover (₹{gst_turnover:,.0f})",
                    "points": 10
                })
            elif gst_turnover >= Decimal("1000000"):  # 10 Lakhs+
                score += 5
                factors.append({
                    "factor": "Annual Turnover",
                    "impact": "Neutral",
                    "detail": f"Moderate turnover (₹{gst_turnover:,.0f})",
                    "points": 5
                })
        
        # === GST Compliance ===
        if gst_compliance == "Excellent":
            tax_compliance_score = 15
            score += 15
            factors.append({
                "factor": "Tax Compliance",
                "impact": "Positive",
                "detail": "Excellent GST compliance history",
                "points": 15
            })
        elif gst_compliance == "Good":
            tax_compliance_score = 10
            score += 10
            factors.append({
                "factor": "Tax Compliance",
                "impact": "Positive",
                "detail": "Good GST compliance",
                "points": 10
            })
        elif gst_compliance == "Poor":
            tax_compliance_score = -25
            score -= 25
            factors.append({
                "factor": "Tax Compliance",
                "impact": "Negative",
                "detail": "Poor GST compliance (missed returns, penalties)",
                "points": -25
            })
        
        # === Quality Infrastructure (for sellers) ===
        if partner_type == PartnerType.SELLER and has_quality_lab:
            score += 10
            factors.append({
                "factor": "Quality Infrastructure",
                "impact": "Positive",
                "detail": "Has in-house quality testing lab",
                "points": 10
            })
        
        # === Logistics Capability (for sellers) ===
        if partner_type == PartnerType.SELLER and can_arrange_transport:
            score += 5
            factors.append({
                "factor": "Logistics",
                "impact": "Positive",
                "detail": "Can arrange own transport",
                "points": 5
            })
        
        # Clamp score to 0-100
        score = max(0, min(100, score))
        
        # Determine category
        if score >= 70:
            category = RiskCategory.LOW
            approval_route = "auto"
        elif score >= 40:
            category = RiskCategory.MEDIUM
            approval_route = "manager"
        elif score >= 20:
            category = RiskCategory.HIGH
            approval_route = "director"
        else:
            category = RiskCategory.CRITICAL
            approval_route = "director_with_checks"
        
        # Extract flag strings from factors
        flag_strings = [f"{f['factor']}: {f['detail']}" for f in factors]
        
        return RiskAssessment(
            total_score=score,
            category=category,
            business_age_score=business_age_score,
            entity_type_score=entity_type_score,
            tax_compliance_score=tax_compliance_score,
            documentation_score=documentation_score,
            verification_score=verification_score,
            flags=flag_strings,
            recommendation=f"{category.value} risk - {approval_route}",
            approval_route=approval_route,
            recommended_credit_limit=self._calculate_credit_limit(score, gst_turnover)
        )
    
    def _calculate_credit_limit(
        self,
        risk_score: int,
        gst_turnover: Optional[Decimal]
    ) -> Optional[Decimal]:
        """
        Calculate recommended credit limit based on risk and turnover.
        
        Args:
            risk_score: Risk score (0-100)
            gst_turnover: Annual GST turnover
        
        Returns:
            Recommended credit limit
        """
        if not gst_turnover:
            return None
        
        # Base: 10% of annual turnover
        base_limit = gst_turnover * Decimal("0.10")
        
        # Adjust by risk
        if risk_score >= 70:
            # Low risk: 15% of turnover
            return gst_turnover * Decimal("0.15")
        elif risk_score >= 40:
            # Medium risk: 10% of turnover
            return base_limit
        else:
            # High risk: 5% of turnover
            return gst_turnover * Decimal("0.05")


class ApprovalService:
    """
    Route approvals based on risk score.
    
    Auto-approve low risk, route to manager/director for higher risk.
    """
    
    def __init__(self, db: AsyncSession, current_user_id: UUID, redis_client: Optional[redis.Redis] = None):
        self.db = db
        self.current_user_id = current_user_id
        self.redis = redis_client
        self.bp_repo = BusinessPartnerRepository(db)
        self.app_repo = OnboardingApplicationRepository(db)
        self.outbox_repo = OutboxRepository(db)
    
    async def process_approval(
        self,
        application_id: UUID,
        risk_assessment: RiskAssessment,
        decision: ApprovalDecision,
        idempotency_key: Optional[str] = None
    ) -> BusinessPartner:
        """
        Process approval decision.
        
        Args:
            application_id: Application ID
            risk_assessment: Risk assessment result
            decision: Approval decision
            idempotency_key: Idempotency key for deduplication
        
        Returns:
            Approved BusinessPartner
        """
        # Check idempotency
        if idempotency_key and self.redis:
            cached = await self.redis.get(f"idempotency:{idempotency_key}")
            if cached:
                return json.loads(cached)
        
        # Get application
        application = await self.app_repo.get_by_id(application_id)
        if not application:
            raise ValueError("Application not found")
        
        if decision.decision == "approve":
            # Use provided credit limit or default from risk assessment
            credit_limit = decision.credit_limit or risk_assessment.recommended_credit_limit
            
            # Create BusinessPartner record
            partner = await self.bp_repo.create(
                partner_type=application.partner_type,
                legal_name=application.legal_name,
                trade_name=application.trade_name,
                country=application.primary_country,
                tax_id_number=application.tax_id_number,
                pan_number=application.pan_number,
                business_entity_type=application.business_entity_type,
                registration_date=application.registration_date,
                bank_account_name=application.bank_account_name,
                bank_name=application.bank_name,
                bank_account_number=application.bank_account_number,
                bank_routing_code=application.bank_routing_code,
                primary_address=application.primary_address,
                primary_city=application.primary_city,
                primary_state=application.primary_state,
                primary_postal_code=application.primary_postal_code,
                primary_country=application.primary_country,
                primary_latitude=getattr(application, 'primary_latitude', None),
                primary_longitude=getattr(application, 'primary_longitude', None),
                location_geocoded=getattr(application, 'location_geocoded', False),
                location_confidence=getattr(application, 'location_confidence', None),
                primary_contact_name=application.primary_contact_name,
                primary_contact_email=application.primary_contact_email,
                primary_contact_phone=application.primary_contact_phone,
                primary_currency=application.primary_currency,
                risk_score=risk_assessment.total_score,
                risk_category=risk_assessment.category,
                risk_assessment={"flags": risk_assessment.flags},
                credit_limit=credit_limit,
                status=PartnerStatus.APPROVED,
                kyc_status=KYCStatus.VERIFIED,
                kyc_verified_at=datetime.utcnow(),
                kyc_expiry_date=datetime.utcnow() + timedelta(days=365),  # 1 year
                approved_by=self.current_user_id,
                approved_at=datetime.utcnow(),
                created_by=self.current_user_id
            )
            
            # Update application status
            await self.app_repo.update(
                application_id,
                status="approved",
                approved_at=datetime.utcnow(),
                approved_by=self.current_user_id
            )
            
            # Emit event through outbox (transactional)
            await self.outbox_repo.add_event(
                aggregate_id=partner.id,
                aggregate_type="Partner",
                event_type="PartnerApproved",
                payload={
                    "partner_id": str(partner.id),
                    "partner_type": partner.partner_type,
                    "legal_name": partner.legal_name,
                    "credit_limit": float(partner.credit_limit),
                    "approved_by": str(self.current_user_id),
                    "approved_at": partner.approved_at.isoformat()
                },
                topic_name="partner-events",
                metadata={"user_id": str(self.current_user_id)},
                idempotency_key=idempotency_key
            )
            
            # Commit transaction
            await self.db.commit()
            
            # Cache result for idempotency
            if idempotency_key and self.redis:
                partner_dict = {
                    "id": str(partner.id),
                    "legal_name": partner.legal_name,
                    "status": partner.status
                }
                await self.redis.setex(
                    f"idempotency:{idempotency_key}",
                    86400,
                    json.dumps(partner_dict)
                )
            
            return partner
        elif decision.decision == "reject":
            # Rejection
            await self.app_repo.update(
                application_id,
                status="rejected",
                rejected_at=datetime.utcnow(),
                rejected_by=self.current_user_id,
                rejection_reason=decision.notes
            )
            
            # Emit rejection event
            await self.outbox_repo.add_event(
                aggregate_id=application_id,
                aggregate_type="PartnerApplication",
                event_type="PartnerApplicationRejected",
                payload={
                    "application_id": str(application_id),
                    "reason": decision.notes,
                    "rejected_by": str(self.current_user_id),
                    "rejected_at": datetime.utcnow().isoformat()
                },
                topic_name="partner-events",
                metadata={"user_id": str(self.current_user_id)},
                idempotency_key=idempotency_key
            )
            
            await self.db.commit()
            
            raise ValueError(f"Application rejected: {decision.notes}")
        else:
            # Request more info
            await self.app_repo.update(
                application_id,
                status="info_requested",
                notes=decision.notes
            )
            raise ValueError(f"More information requested: {decision.notes}")


class KYCRenewalService:
    """
    Track and trigger yearly KYC renewals.
    
    KYC expires 1 year from approval date.
    """
    
    def __init__(self, db: AsyncSession, current_user_id: UUID):
        self.db = db
        self.current_user_id = current_user_id
        self.bp_repo = BusinessPartnerRepository(db)
        self.kyc_repo = PartnerKYCRenewalRepository(db)
    
    async def check_kyc_expiry(self, organization_id: UUID, days_threshold: int = 30) -> List[BusinessPartner]:
        """
        Get partners with KYC expiring soon.
        
        Args:
            organization_id: Organization ID
            days_threshold: Days before expiry
        
        Returns:
            List of partners needing renewal
        """
        return await self.bp_repo.get_expiring_kyc(organization_id, days_threshold)
    
    async def initiate_kyc_renewal(self, partner_id: UUID) -> PartnerKYCRenewal:
        """
        Initiate KYC renewal process.
        
        Args:
            partner_id: Partner ID
        
        Returns:
            KYCRenewal record
        """
        renewal = await self.kyc_repo.create(
            business_partner_id=partner_id,
            initiated_at=datetime.utcnow(),
            initiated_by=self.current_user_id,
            status="pending",
            due_date=datetime.utcnow() + timedelta(days=30)  # 30 days to complete
        )
        
        return renewal
    
    async def complete_kyc_renewal(
        self,
        renewal_id: UUID,
        new_documents: List[UUID],
        verified: bool = True
    ) -> BusinessPartner:
        """
        Complete KYC renewal and extend expiry date.
        
        Args:
            renewal_id: Renewal ID
            new_documents: List of new document IDs uploaded
            verified: Verification passed
        
        Returns:
            Updated BusinessPartner
        """
        renewal = await self.kyc_repo.get_by_id(renewal_id)
        if not renewal:
            raise ValueError("Renewal not found")
        
        if verified:
            # Update partner KYC
            partner = await self.bp_repo.update(
                renewal.business_partner_id,
                kyc_status=KYCStatus.VERIFIED,
                kyc_verified_at=datetime.utcnow(),
                kyc_expiry_date=datetime.utcnow() + timedelta(days=365),  # Extend 1 year
                updated_by=self.current_user_id
            )
            
            # Update renewal record
            await self.kyc_repo.update(
                renewal_id,
                status="completed",
                completed_at=datetime.utcnow(),
                completed_by=self.current_user_id,
                verification_passed=True
            )
            
            return partner
        else:
            # Failed verification
            await self.kyc_repo.update(
                renewal_id,
                status="failed",
                completed_at=datetime.utcnow(),
                completed_by=self.current_user_id,
                verification_passed=False
            )
            
            # Suspend partner
            await self.bp_repo.update(
                renewal.business_partner_id,
                kyc_status=KYCStatus.EXPIRED,
                status=PartnerStatus.SUSPENDED,
                updated_by=self.current_user_id
            )
            
            raise ValueError("KYC verification failed")


class PartnerService:
    """
    Main orchestration service for complete partner onboarding workflow.
    
    Coordinates:
    - GST verification
    - Location geocoding
    - Document processing
    - Risk scoring
    - Approval routing
    """
    
    def __init__(
        self,
        db: AsyncSession,
        event_emitter: EventEmitter,
        current_user_id: UUID,
        organization_id: UUID
    ):
        self.db = db
        self.event_emitter = event_emitter
        self.current_user_id = current_user_id
        self.organization_id = organization_id
        
        # Initialize repositories
        self.bp_repo = BusinessPartnerRepository(db)
        self.app_repo = OnboardingApplicationRepository(db)
        self.location_repo = PartnerLocationRepository(db)
        self.employee_repo = PartnerEmployeeRepository(db)
        self.document_repo = PartnerDocumentRepository(db)
        self.vehicle_repo = PartnerVehicleRepository(db)
        
        # Initialize services
        self.gst_service = GSTVerificationService()
        self.geocoding_service = GeocodingService()
        self.rto_service = RTOVerificationService()
        self.doc_service = DocumentProcessingService()
        self.risk_service = RiskScoringService()
        self.approval_service = ApprovalService(db, current_user_id)
        self.kyc_service = KYCRenewalService(db, current_user_id)
    
    async def start_onboarding(
        self,
        data: OnboardingApplicationCreate
    ) -> PartnerOnboardingApplication:
        """
        Start onboarding process.
        
        Steps:
        1. Create draft application
        2. Verify GST (auto-fetch details)
        3. Geocode location (auto-verify if confidence >90%)
        4. Return application for document upload
        
        Args:
            data: Onboarding application data
        
        Returns:
            OnboardingApplication
        """
        # Step 1: Verify GST if tax_id_number provided
        gst_verified = False
        gst_verification_data = None
        legal_name = data.legal_name
        trade_name = data.trade_name
        entity_type = data.business_entity_type
        registration_date = data.registration_date
        
        if data.tax_id_number:
            try:
                gst_result = await self.gst_service.verify_gstin(data.tax_id_number)
                if gst_result.verified:
                    gst_verified = True
                    legal_name = gst_result.legal_name
                    trade_name = gst_result.trade_name or data.trade_name
                    entity_type = gst_result.entity_type
                    registration_date = gst_result.registration_date
                    gst_verification_data = gst_result.dict()
            except Exception as e:
                # Continue with manual data if GST verification fails
                pass
        
        # Step 2: Geocode location (auto-verify if confidence >90%)
        location_verified = False
        latitude = data.primary_latitude
        longitude = data.primary_longitude
        
        try:
            location_result = await self.geocoding_service.geocode_address(
                data.primary_address,
                data.primary_city,
                data.primary_state,
                data.primary_postal_code
            )
            location_verified = location_result.get("confidence", 0) > 0.90
            latitude = location_result.get("latitude")
            longitude = location_result.get("longitude")
        except Exception as e:
            # Continue with manual coordinates if geocoding fails
            pass
        
        # Step 3: Create application
        application = await self.app_repo.create(
            user_id=self.current_user_id,
            organization_id=self.organization_id,
            partner_type=data.partner_type,
            service_provider_type=data.service_provider_type,
            trade_classification=data.trade_classification,
            legal_name=legal_name,
            trade_name=trade_name,
            country=data.country,
            business_entity_type=entity_type,
            registration_date=registration_date,
            has_tax_registration=data.has_tax_registration,
            tax_id_type=data.tax_id_type,
            tax_id_number=data.tax_id_number,
            tax_details=data.tax_details,
            tax_verified=gst_verified,
            pan_number=data.pan_number,
            pan_name=data.pan_name,
            pan_verified=False,
            has_no_gst_declaration=data.has_no_gst_declaration,
            declaration_reason=data.declaration_reason,
            bank_account_name=data.bank_account_name,
            bank_name=data.bank_name,
            bank_account_number=data.bank_account_number,
            bank_routing_code=data.bank_routing_code,
            primary_address=data.primary_address,
            primary_city=data.primary_city,
            primary_state=data.primary_state,
            primary_postal_code=data.primary_postal_code,
            primary_country=data.primary_country,
            primary_latitude=latitude,
            primary_longitude=longitude,
            primary_contact_name=data.primary_contact_name,
            primary_contact_email=data.primary_contact_email,
            primary_contact_phone=data.primary_contact_phone,
            primary_currency=data.primary_currency,
            commodities=data.commodities,
            onboarding_stage="documents",
            verification_results={
                "gst_verified": gst_verified,
                "location_verified": location_verified,
                "gst_data": gst_verification_data
            },
            status="pending"
        )
        
        # TODO: Emit event
        # await self.event_emitter.emit(OnboardingStartedEvent(...))
        
        return application
    
    async def submit_for_approval(self, application_id: UUID) -> Dict:
        """
        Submit application for approval after documents uploaded.
        
        Steps:
        1. Validate all required documents uploaded
        2. Calculate risk score
        3. Route to auto-approve/manager/director
        4. Return approval status
        
        Args:
            application_id: Application ID
        
        Returns:
            Dict with approval route and estimated time
        """
        # Get application
        application = await self.app_repo.get_by_id(application_id, self.organization_id)
        if not application:
            raise ValueError("Application not found")
        
        # Calculate risk score
        business_age_months = (
            (datetime.utcnow().date() - application.registration_date).days // 30
            if application.registration_date
            else 0
        )
        
        # Safely get GST verification data (may not exist in test fixtures)
        gst_data = getattr(application, 'gst_verification_data', None) or {}
        
        risk_assessment = await self.risk_service.calculate_risk_score(
            partner_type=application.partner_type,
            entity_type=application.business_entity_type,
            business_age_months=business_age_months,
            gst_turnover=gst_data.get("annual_turnover"),
            gst_compliance=gst_data.get("compliance_rating"),
            has_quality_lab=False,  # From partner-specific data
            can_arrange_transport=False
        )
        
        # Update application with risk score
        await self.app_repo.update(
            application_id,
            risk_score=risk_assessment.total_score,
            risk_category=risk_assessment.category,
            status="pending_approval",
            submitted_at=datetime.utcnow()
        )
        
        # Auto-approve if low risk
        if risk_assessment.approval_route == "auto":
            partner = await self.approval_service.process_approval(
                application_id,
                risk_assessment,
                ApprovalDecision(
                    decision="approve",
                    notes="Auto-approved based on low risk score"
                )
            )
            
            return {
                "status": "approved",
                "partner_id": partner.id,
                "approval_route": "auto",
                "message": "Congratulations! Your application is auto-approved."
            }
        else:
            return {
                "status": "pending_approval",
                "approval_route": risk_assessment.approval_route,
                "estimated_time": "24-48 hours" if risk_assessment.approval_route == "manager" else "3-5 business days",
                "message": f"Application submitted for {risk_assessment.approval_route} review."
            }

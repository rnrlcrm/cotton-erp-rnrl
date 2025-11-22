"""
Partner Assistant Tools

Helper tools for partner onboarding and management operations.
"""

from typing import Dict, List, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from backend.modules.partners.enums import PartnerType, DocumentType


class PartnerTools:
    """
    Tools for partner assistant operations.
    
    Provides data access and helper functions for the AI assistant.
    """
    
    def __init__(self, db: Optional[Session] = None):
        """
        Initialize partner tools.
        
        Args:
            db: Database session (optional, for data access)
        """
        self.db = db
    
    async def get_onboarding_requirements(self, partner_type: str) -> Dict:
        """
        Get onboarding requirements for partner type.
        
        Args:
            partner_type: Type of partner
        
        Returns:
            Dict with required fields and documents
        """
        # Common requirements for all partner types
        common_requirements = {
            "basic_info": [
                "Business name (as per GST)",
                "GST Number (15 characters)",
                "PAN Number (10 characters)",
                "Business entity type (Proprietorship/Partnership/Pvt Ltd/etc.)",
                "Contact person name",
                "Email address",
                "Phone number"
            ],
            "address": [
                "Registered business address",
                "City, State, PIN code",
                "Location will be auto-verified via Google Maps"
            ],
            "documents": [
                "GST Registration Certificate",
                "PAN Card",
                "Bank Account Proof (Cancelled Cheque)"
            ]
        }
        
        # Partner-type specific requirements
        type_specific = {}
        
        if partner_type == PartnerType.BUYER.value:
            type_specific = {
                "buyer_specific": [
                    "Monthly purchase volume estimate",
                    "Preferred payment terms (days)",
                    "Credit limit requested (optional)"
                ],
                "note": "Credit limit will be assigned based on risk assessment"
            }
        
        elif partner_type == PartnerType.SELLER.value:
            type_specific = {
                "seller_specific": [
                    "Production capacity per month",
                    "Can arrange transport? (Yes/No)",
                    "Has quality testing lab? (Yes/No)"
                ],
                "note": "Higher production capacity and quality lab increase trust score"
            }
        
        elif partner_type == PartnerType.TRANSPORTER.value:
            type_specific = {
                "transporter_specific": [
                    "Fleet size (number of vehicles)",
                    "Vehicle types (Open Body/Container/Tanker/etc.)",
                    "Service coverage areas (states/regions)"
                ],
                "vehicles": [
                    "Vehicle registration numbers",
                    "Vehicle RC book copy",
                    "Insurance certificate",
                    "Fitness certificate"
                ],
                "note": "Add vehicle details after account approval"
            }
        
        elif partner_type in [PartnerType.BROKER.value, PartnerType.SUB_BROKER.value]:
            type_specific = {
                "broker_specific": [
                    "Service coverage areas",
                    "Commodities handled",
                    "Years of experience in cotton trade"
                ],
                "commission": "Commission rates configured after approval",
                "note": "Sub-brokers must specify parent broker"
            }
        
        elif partner_type == PartnerType.TRADER.value:
            type_specific = {
                "trader_specific": [
                    "Trade classification (Domestic/Exporter/Importer)",
                    "Annual trading volume",
                    "Markets served"
                ],
                "note": "Can act as both buyer and seller"
            }
        
        elif partner_type == PartnerType.CONTROLLER.value:
            type_specific = {
                "controller_specific": [
                    "Service types offered",
                    "Coverage areas",
                    "Team size"
                ],
                "note": "Controllers manage quality inspections and logistics"
            }
        
        elif partner_type == PartnerType.FINANCER.value:
            type_specific = {
                "financer_specific": [
                    "Financing products offered",
                    "Interest rates",
                    "Maximum financing amount"
                ],
                "documents": [
                    "NBFC registration (if applicable)",
                    "RBI license (if applicable)"
                ],
                "note": "Additional regulatory compliance required"
            }
        
        elif partner_type in [PartnerType.IMPORTER.value, PartnerType.EXPORTER.value]:
            type_specific = {
                "import_export_specific": [
                    "IEC (Import Export Code)",
                    "Countries traded with",
                    "Annual import/export volume"
                ],
                "documents": [
                    "IEC certificate",
                    "DGFT registration"
                ],
                "note": "International trade compliance documents required"
            }
        
        # Combine all requirements
        return {
            **common_requirements,
            **type_specific,
            "partner_type": partner_type
        }
    
    async def get_verification_status(self, application_id: UUID) -> Dict:
        """
        Get verification status for onboarding application.
        
        Args:
            application_id: Application ID
        
        Returns:
            Current verification status
        """
        # If database session available, fetch real status
        if self.db:
            from backend.modules.partners.repositories import OnboardingApplicationRepository
            
            repo = OnboardingApplicationRepository(self.db)
            application = repo.get_by_id(application_id)
            
            if not application:
                return {"error": "Application not found"}
            
            return {
                "application_id": str(application.id),
                "stage": application.status.value,
                "gst_verified": application.gst_verified,
                "pan_verified": application.pan_verified,
                "documents_uploaded": application.documents_count > 0,
                "location_verified": application.location_verified,
                "risk_score": application.risk_score,
                "risk_category": application.risk_category.value if application.risk_category else None,
                "submitted_at": application.submitted_at.isoformat() if application.submitted_at else None,
                "verification_notes": application.verification_notes
            }
        
        # Mock response if no database
        return {
            "application_id": str(application_id),
            "stage": "verification_in_progress",
            "gst_verified": True,
            "pan_verified": True,
            "documents_uploaded": True,
            "location_verified": False,
            "risk_score": None,
            "risk_category": None
        }
    
    def get_document_checklist(self, partner_type: str) -> List[Dict]:
        """
        Get document checklist for partner type.
        
        Args:
            partner_type: Partner type
        
        Returns:
            List of required documents with details
        """
        # Common documents for all
        documents = [
            {
                "type": DocumentType.GST_CERTIFICATE.value,
                "name": "GST Registration Certificate",
                "mandatory": True,
                "format": "PDF or Image",
                "max_size": "5 MB",
                "ocr_enabled": True
            },
            {
                "type": DocumentType.PAN_CARD.value,
                "name": "PAN Card",
                "mandatory": True,
                "format": "PDF or Image",
                "max_size": "2 MB",
                "ocr_enabled": True
            },
            {
                "type": DocumentType.BANK_PROOF.value,
                "name": "Bank Account Proof",
                "mandatory": True,
                "format": "PDF or Image",
                "max_size": "5 MB",
                "ocr_enabled": True,
                "note": "Cancelled cheque or bank statement"
            }
        ]
        
        # Add partner-type specific documents
        if partner_type == PartnerType.TRANSPORTER.value:
            documents.extend([
                {
                    "type": DocumentType.VEHICLE_RC.value,
                    "name": "Vehicle RC Book",
                    "mandatory": False,
                    "format": "PDF or Image",
                    "max_size": "5 MB",
                    "ocr_enabled": True,
                    "note": "Required for each vehicle"
                },
                {
                    "type": DocumentType.INSURANCE.value,
                    "name": "Vehicle Insurance",
                    "mandatory": False,
                    "format": "PDF or Image",
                    "max_size": "5 MB",
                    "ocr_enabled": False,
                    "note": "Valid insurance certificate"
                }
            ])
        
        if partner_type in [PartnerType.IMPORTER.value, PartnerType.EXPORTER.value]:
            documents.append({
                "type": DocumentType.IEC.value,
                "name": "Import Export Code Certificate",
                "mandatory": True,
                "format": "PDF or Image",
                "max_size": "5 MB",
                "ocr_enabled": True
            })
        
        return documents
    
    def calculate_risk_factors(
        self,
        business_age_months: int,
        entity_type: str,
        gst_turnover: Optional[float] = None,
        has_quality_lab: bool = False,
        tax_compliant: bool = True
    ) -> Dict:
        """
        Calculate risk factors for explanation.
        
        Args:
            business_age_months: Age of business in months
            entity_type: Business entity type
            gst_turnover: Annual GST turnover
            has_quality_lab: Has quality testing lab
            tax_compliant: Tax compliance status
        
        Returns:
            Risk factors breakdown
        """
        factors = {
            "business_age_months": business_age_months,
            "entity_type": entity_type,
            "gst_turnover": gst_turnover,
            "has_quality_lab": has_quality_lab,
            "tax_compliant": tax_compliant
        }
        
        # Calculate score
        score = 50  # Base score
        
        # Business age impact
        if business_age_months >= 60:
            score += 20
        elif business_age_months >= 24:
            score += 10
        elif business_age_months < 12:
            score -= 15
        
        # Entity type impact
        if entity_type in ["private_limited", "public_limited"]:
            score += 15
        elif entity_type == "partnership":
            score += 5
        elif entity_type == "proprietorship":
            score -= 5
        
        # Turnover impact
        if gst_turnover:
            if gst_turnover >= 10000000:  # 1 Crore
                score += 15
            elif gst_turnover >= 5000000:  # 50 Lakhs
                score += 10
            elif gst_turnover >= 1000000:  # 10 Lakhs
                score += 5
        
        # Quality infrastructure
        if has_quality_lab:
            score += 10
        
        # Tax compliance
        if not tax_compliant:
            score -= 25
        
        # Clamp score to 0-100
        score = max(0, min(100, score))
        
        # Determine category
        if score >= 70:
            category = "low"
        elif score >= 40:
            category = "medium"
        elif score >= 20:
            category = "high"
        else:
            category = "critical"
        
        return {
            "score": score,
            "category": category,
            "factors": factors
        }
    
    def get_approval_workflow_info(self, risk_category: str) -> Dict:
        """
        Get approval workflow information based on risk.
        
        Args:
            risk_category: Risk category
        
        Returns:
            Workflow details
        """
        workflows = {
            "low": {
                "approver": "System (Auto-approved)",
                "estimated_time": "Within 1 hour",
                "requires_manual_review": False,
                "credit_limit_default": "High"
            },
            "medium": {
                "approver": "Operations Manager",
                "estimated_time": "24-48 hours",
                "requires_manual_review": True,
                "credit_limit_default": "Medium"
            },
            "high": {
                "approver": "Senior Manager",
                "estimated_time": "2-3 business days",
                "requires_manual_review": True,
                "credit_limit_default": "Low"
            },
            "critical": {
                "approver": "Director",
                "estimated_time": "3-5 business days",
                "requires_manual_review": True,
                "credit_limit_default": "Very Low / Case-by-case",
                "additional_checks": [
                    "Financial background verification",
                    "Reference checks",
                    "Credit bureau check"
                ]
            }
        }
        
        return workflows.get(
            risk_category,
            {
                "approver": "Manager",
                "estimated_time": "2-3 business days",
                "requires_manual_review": True
            }
        )
    
    def get_kyc_renewal_checklist(self) -> List[str]:
        """
        Get KYC renewal checklist.
        
        Returns:
            List of renewal steps
        """
        return [
            "Review and update business information (if any changes)",
            "Check GST status is still 'Active'",
            "Verify PAN details are current",
            "Upload latest GST return (last filed return)",
            "Upload recent bank statement (last 3 months)",
            "Update address if changed (with address proof)",
            "Update ownership if changed (with relevant documents)",
            "Confirm contact details (email, phone)",
            "Submit for re-verification",
            "Wait for approval (usually 24-48 hours for renewals)"
        ]
    
    def get_amendment_process(self, field_type: str) -> Dict:
        """
        Get amendment process for different field types.
        
        Args:
            field_type: Type of field being amended
        
        Returns:
            Amendment process details
        """
        processes = {
            "critical": {
                "fields": ["business_name", "gst_number", "pan_number", "ownership"],
                "approval_required": True,
                "approver": "Senior Manager",
                "documents_required": True,
                "estimated_time": "3-5 business days",
                "note": "Critical changes require verification and approval"
            },
            "important": {
                "fields": ["address", "entity_type", "bank_account"],
                "approval_required": True,
                "approver": "Manager",
                "documents_required": True,
                "estimated_time": "1-2 business days",
                "note": "Important changes need supporting documents"
            },
            "minor": {
                "fields": ["contact_person", "email", "phone", "description"],
                "approval_required": False,
                "approver": None,
                "documents_required": False,
                "estimated_time": "Immediate",
                "note": "Minor changes update immediately"
            }
        }
        
        # Determine which category the field belongs to
        for category, info in processes.items():
            if field_type in info["fields"]:
                return info
        
        # Default to important
        return processes["important"]

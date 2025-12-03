"""
Partner Assistant Tools

Helper tools for partner onboarding and management operations.
Uses capability-based partner system (CDPS) instead of old partner_type classification.
"""

from typing import Dict, List, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from backend.modules.partners.enums import DocumentType, ServiceProviderType, BusinessEntityType


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
    
    async def get_onboarding_requirements(self, entity_class: str, service_provider_type: Optional[str] = None) -> Dict:
        """
        Get onboarding requirements based on entity classification (CDPS).
        
        Args:
            entity_class: "business_entity" or "service_provider"
            service_provider_type: For service providers: broker, transporter, controller, financer, etc.
        
        Returns:
            Dict with required fields and documents
        """
        # Common requirements for ALL partners
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
            ],
            "cdps_note": "Trading capabilities (buy/sell/import/export) will be auto-detected from your verified documents"
        }
        
        # Entity class specific requirements
        entity_specific = {}
        
        if entity_class == "business_entity":
            # Business entities that can trade (farmers, mills, traders, etc.)
            entity_specific = {
                "business_entity_info": [
                    "Monthly trading volume estimate",
                    "Preferred payment terms (days)",
                    "Credit limit requested (optional)",
                    "Can arrange transport? (Yes/No)",
                    "Has quality testing lab? (Yes/No)"
                ],
                "capabilities_auto_detected": {
                    "domestic_buy_india": "Auto-granted if you have GST + PAN",
                    "domestic_sell_india": "Auto-granted if you have GST + PAN",
                    "import_allowed": "Requires IEC certificate",
                    "export_allowed": "Requires IEC certificate"
                },
                "note": "You can buy, sell, or both based on your documents. System will auto-detect."
            }
            
        elif entity_class == "service_provider":
            # Service providers (brokers, transporters, controllers, etc.)
            entity_specific = {
                "service_provider_info": [
                    "Service type (broker/transporter/controller/financer)",
                    "Service coverage areas",
                    "Years of experience"
                ],
                "note": "Service providers CANNOT trade commodities directly. They facilitate trading services."
            }
            
            # Service provider type specific requirements
            if service_provider_type == ServiceProviderType.TRANSPORTER.value:
                entity_specific.update({
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
                })
            
            elif service_provider_type == ServiceProviderType.BROKER.value:
                entity_specific.update({
                    "broker_specific": [
                        "Service coverage areas",
                        "Commodities handled",
                        "Years of experience in commodity trade"
                    ],
                    "commission": "Commission rates configured after approval"
                })
            
            elif service_provider_type == ServiceProviderType.SUB_BROKER.value:
                entity_specific.update({
                    "sub_broker_specific": [
                        "Parent broker details",
                        "Service coverage areas",
                        "Commodities handled"
                    ],
                    "note": "Sub-brokers must specify parent broker"
                })
            
            elif service_provider_type == ServiceProviderType.CONTROLLER.value:
                entity_specific.update({
                    "controller_specific": [
                        "Service types offered",
                        "Coverage areas",
                        "Team size"
                    ],
                    "note": "Controllers manage quality inspections and logistics"
                })
            
            elif service_provider_type == ServiceProviderType.FINANCER.value:
                entity_specific.update({
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
                })
        
        # Combine all requirements
        return {
            **common_requirements,
            **entity_specific,
            "entity_class": entity_class,
            "service_provider_type": service_provider_type
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
    
    def get_document_checklist(self, entity_class: str, service_provider_type: Optional[str] = None) -> List[Dict]:
        """
        Get document checklist based on entity classification (CDPS).
        
        Args:
            entity_class: "business_entity" or "service_provider"
            service_provider_type: For service providers: broker, transporter, etc.
        
        Returns:
            List of required documents with details
        """
        # Common documents for ALL partners
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
        
        # Add entity-specific documents for service providers
        if entity_class == "service_provider":
            if service_provider_type == ServiceProviderType.TRANSPORTER.value:
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
            
            elif service_provider_type == ServiceProviderType.FINANCER.value:
                documents.append({
                    "type": "nbfc_license",
                    "name": "NBFC License / RBI Registration",
                    "mandatory": False,
                    "format": "PDF or Image",
                    "max_size": "5 MB",
                    "ocr_enabled": False,
                    "note": "If applicable for financial institutions"
                })
        
        # For business entities that want import/export
        # (IEC will auto-grant import/export capabilities)
        documents.append({
            "type": DocumentType.IEC.value,
            "name": "Import Export Code Certificate",
            "mandatory": False,
            "format": "PDF or Image",
            "max_size": "5 MB",
            "ocr_enabled": True,
            "note": "Optional - required only if you want to import/export"
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

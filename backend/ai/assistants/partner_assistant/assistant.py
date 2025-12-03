"""
Partner Assistant Implementation

AI-powered assistant for business partner onboarding and management.
Uses capability-based partner system (CDPS) instead of old partner_type classification.
"""

from typing import Dict, List, Optional
from uuid import UUID

from backend.ai.assistants.partner_assistant.tools import PartnerTools


class PartnerAssistant:
    """
    AI assistant for partner onboarding and management.
    
    Capabilities:
    - Guide users through onboarding process
    - Explain verification requirements
    - Help with document preparation
    - Provide GST/PAN lookup assistance
    - Explain risk scoring
    - Remind about KYC renewals
    - Answer partner-related queries
    """
    
    def __init__(self, tools: Optional[PartnerTools] = None):
        """
        Initialize Partner Assistant.
        
        Args:
            tools: Partner-specific tools (optional)
        """
        self.tools = tools or PartnerTools()
        self.context_history: List[Dict] = []
    
    async def assist_onboarding_start(
        self,
        entity_class: str,
        service_provider_type: Optional[str] = None,
        user_message: Optional[str] = None
    ) -> Dict:
        """
        Guide user through onboarding start using CDPS (Capability-Driven Partner System).
        
        Args:
            entity_class: "business_entity" or "service_provider"
            service_provider_type: For service providers: broker, transporter, controller, etc.
            user_message: Optional user query
        
        Returns:
            Dict with guidance, required fields, and next steps
        """
        # Get partner-specific requirements
        requirements = await self.tools.get_onboarding_requirements(entity_class, service_provider_type)
        
        # Determine friendly name
        if entity_class == "business_entity":
            friendly_name = "business entity (trader/farmer/mill/ginner)"
        elif service_provider_type:
            friendly_name = service_provider_type.replace("_", " ")
        else:
            friendly_name = "service provider"
        
        response = {
            "greeting": f"Welcome! Let's get you onboarded as a {friendly_name}.",
            "requirements": requirements,
            "estimated_time": self._estimate_onboarding_time(entity_class, service_provider_type),
            "next_steps": [
                "Enter basic business information (Name, GST, PAN)",
                "We'll auto-fetch and verify your GST details",
                "Upload required documents (GST Certificate, PAN Card, Bank Proof)",
                "Add business location(s) - we'll verify using Google Maps",
                "Submit for verification and approval"
            ],
            "tips": [
                "Keep your GST certificate ready for upload",
                "Ensure GST number is active and valid",
                "Business address should match GST registration",
                "PAN should be linked to the business entity"
            ],
            "cdps_info": {
                "title": "Automatic Capability Detection",
                "message": "Your trading rights (buy/sell/import/export) will be AUTO-DETECTED from your verified documents.",
                "examples": [
                    "GST + PAN = Domestic buy & sell rights in India",
                    "GST + PAN + IEC = Import & export rights",
                    "Service providers CANNOT trade commodities directly"
                ]
            }
        }
        
        # Add entity-specific guidance
        if entity_class == "business_entity":
            response["additional_info"] = {
                "message": "As a business entity, you can buy and/or sell commodities",
                "capability_detection": "System will auto-detect if you can buy, sell, import, or export based on your documents",
                "credit_approval": "Credit limits assigned based on risk assessment"
            }
        elif service_provider_type == "transporter":
            response["additional_info"] = {
                "message": "As a transporter, you can also add vehicle details",
                "vehicle_types": ["Open Body", "Container", "Tanker", "Trailer"],
                "required_docs": ["RC Book", "Insurance", "Fitness Certificate"]
            }
        elif service_provider_type in ["broker", "sub_broker"]:
            response["additional_info"] = {
                "message": "Brokers need to specify service areas and commodities",
                "commission_setup": "Commission rates configured after approval",
                "note": "Brokers facilitate trades but cannot trade directly"
            }
        
        return response
    
    async def explain_verification_status(
        self,
        application_id: UUID
    ) -> Dict:
        """
        Explain current verification status and what's needed.
        
        Args:
            application_id: Onboarding application ID
        
        Returns:
            Human-friendly explanation of status
        """
        # Get verification status from tools
        status = await self.tools.get_verification_status(application_id)
        
        # Create human-friendly explanation
        explanation = {
            "current_stage": status.get("stage"),
            "status_summary": self._create_status_summary(status),
            "pending_items": [],
            "completed_items": [],
            "next_action": ""
        }
        
        # Analyze what's done and what's pending
        if status.get("gst_verified"):
            explanation["completed_items"].append("✓ GST verified successfully")
        else:
            explanation["pending_items"].append("○ GST verification pending")
        
        if status.get("pan_verified"):
            explanation["completed_items"].append("✓ PAN verified")
        else:
            explanation["pending_items"].append("○ PAN verification pending")
        
        if status.get("documents_uploaded"):
            explanation["completed_items"].append("✓ Documents uploaded")
        else:
            explanation["pending_items"].append("○ Documents need to be uploaded")
        
        if status.get("location_verified"):
            explanation["completed_items"].append("✓ Location verified via Google Maps")
        else:
            explanation["pending_items"].append("○ Location verification pending")
        
        # Determine next action
        if not status.get("gst_verified"):
            explanation["next_action"] = "Please verify your GST number is correct and active"
        elif not status.get("documents_uploaded"):
            explanation["next_action"] = "Upload GST certificate, PAN card, and bank proof"
        elif not status.get("location_verified"):
            explanation["next_action"] = "Confirm your business address for location verification"
        elif status.get("stage") == "pending_approval":
            explanation["next_action"] = "Application under review. You'll be notified once approved."
        
        return explanation
    
    async def help_with_document_upload(
        self,
        document_type: str
    ) -> Dict:
        """
        Provide guidance for document upload.
        
        Args:
            document_type: Type of document (GST/PAN/Bank/etc.)
        
        Returns:
            Upload guidelines and requirements
        """
        guidelines = {
            "GST_CERTIFICATE": {
                "title": "GST Registration Certificate",
                "requirements": [
                    "Clear, readable copy of GST certificate",
                    "Should show GSTIN, business name, and address",
                    "PDF or image format (max 5MB)",
                    "Should match the GSTIN entered during registration"
                ],
                "sample_info": "Certificate issued by GST department after registration",
                "ocr_enabled": True,
                "auto_verification": "We'll auto-extract GSTIN and verify"
            },
            "PAN_CARD": {
                "title": "PAN Card",
                "requirements": [
                    "Clear copy of PAN card (front side)",
                    "Should be a valid business/individual PAN",
                    "PAN should match business entity type",
                    "PDF or image format (max 2MB)"
                ],
                "sample_info": "Permanent Account Number issued by Income Tax Department",
                "ocr_enabled": True,
                "auto_verification": "We'll auto-extract PAN and verify format"
            },
            "BANK_PROOF": {
                "title": "Bank Account Proof",
                "requirements": [
                    "Cancelled cheque OR bank statement",
                    "Should show account number, IFSC, account holder name",
                    "Account holder should match business name",
                    "PDF or image format (max 5MB)"
                ],
                "sample_info": "Cancelled cheque or first page of bank statement",
                "ocr_enabled": True,
                "auto_verification": "We'll extract account details automatically"
            },
            "RC_BOOK": {
                "title": "Vehicle Registration Certificate",
                "requirements": [
                    "Clear copy of RC book (both sides)",
                    "Vehicle should be registered in business/owner name",
                    "Must be valid and not expired",
                    "PDF or image format (max 5MB)"
                ],
                "sample_info": "Registration certificate for transport vehicles",
                "ocr_enabled": True,
                "auto_verification": "We'll verify with Parivahan/Vahan database"
            }
        }
        
        return guidelines.get(
            document_type,
            {
                "title": "Document Upload",
                "requirements": [
                    "Clear, readable copy",
                    "PDF or image format (max 5MB)",
                    "Should be recent and valid"
                ],
                "ocr_enabled": False
            }
        )
    
    async def explain_risk_score(
        self,
        risk_score: int,
        risk_category: str,
        factors: Dict
    ) -> Dict:
        """
        Explain risk score in user-friendly terms.
        
        Args:
            risk_score: Numerical score (0-100)
            risk_category: low/medium/high/critical
            factors: Factors contributing to score
        
        Returns:
            Human-readable risk explanation
        """
        # Base explanation by category
        category_explanations = {
            "low": {
                "message": "Excellent! Your business profile shows low risk.",
                "impact": "You'll get higher credit limits and faster approvals.",
                "color": "green"
            },
            "medium": {
                "message": "Your business profile shows moderate risk.",
                "impact": "Standard credit limits apply. May require manager approval for large transactions.",
                "color": "yellow"
            },
            "high": {
                "message": "Your business profile indicates higher risk.",
                "impact": "Lower credit limits. Transactions require approval.",
                "color": "orange"
            },
            "critical": {
                "message": "Your business profile shows critical risk factors.",
                "impact": "Limited credit. All transactions require senior approval.",
                "color": "red"
            }
        }
        
        explanation = category_explanations.get(risk_category, {})
        explanation["score"] = risk_score
        explanation["category"] = risk_category
        
        # Explain contributing factors
        explanation["factors"] = []
        
        if factors.get("business_age_months", 0) < 12:
            explanation["factors"].append({
                "factor": "New Business",
                "impact": "Negative",
                "detail": "Business is less than 1 year old",
                "improvement": "Risk score will improve as business matures"
            })
        
        if factors.get("entity_type") == "proprietorship":
            explanation["factors"].append({
                "factor": "Business Entity",
                "impact": "Minor Negative",
                "detail": "Proprietorship has higher perceived risk than Pvt Ltd",
                "improvement": "Consider incorporating as you grow"
            })
        
        if not factors.get("tax_compliant", True):
            explanation["factors"].append({
                "factor": "Tax Compliance",
                "impact": "Significant Negative",
                "detail": "Issues found in GST/tax compliance",
                "improvement": "Ensure all GST returns are filed on time"
            })
        
        if factors.get("has_quality_lab"):
            explanation["factors"].append({
                "factor": "Quality Infrastructure",
                "impact": "Positive",
                "detail": "Having in-house quality lab reduces risk",
                "improvement": "N/A"
            })
        
        return explanation
    
    async def kyc_renewal_reminder(
        self,
        partner_id: UUID,
        days_to_expiry: int
    ) -> Dict:
        """
        Create KYC renewal reminder message.
        
        Args:
            partner_id: Business partner ID
            days_to_expiry: Days until KYC expires
        
        Returns:
            Reminder message with action items
        """
        if days_to_expiry <= 0:
            urgency = "expired"
            message = "⚠️ Your KYC has expired! Please renew immediately."
        elif days_to_expiry <= 7:
            urgency = "critical"
            message = f"⚠️ Your KYC expires in {days_to_expiry} days! Please renew ASAP."
        elif days_to_expiry <= 30:
            urgency = "high"
            message = f"⏰ Your KYC expires in {days_to_expiry} days. Please plan renewal."
        else:
            urgency = "normal"
            message = f"📅 KYC renewal due in {days_to_expiry} days."
        
        return {
            "urgency": urgency,
            "message": message,
            "days_remaining": days_to_expiry,
            "renewal_process": [
                "Review and update business information",
                "Upload fresh documents if any have expired",
                "Verify GST status is still active",
                "Confirm bank account details",
                "Submit for re-verification"
            ],
            "documents_needed": [
                "Latest GST return proof",
                "Updated bank statement",
                "Any changed documents (address, ownership, etc.)"
            ],
            "consequences_if_expired": [
                "Account may be temporarily suspended",
                "No new transactions allowed",
                "Existing orders may be affected",
                "Re-verification required for reactivation"
            ]
        }
    
    async def answer_faq(self, question: str) -> str:
        """
        Answer common partner onboarding FAQs.
        
        Args:
            question: User's question
        
        Returns:
            Answer text
        """
        question_lower = question.lower()
        
        # GST related
        if "gst" in question_lower and "multiple" in question_lower:
            return (
                "Yes, if your business has multiple GSTIN numbers across different states, "
                "you can add them all during onboarding. Our system will verify each GSTIN "
                "separately and link them to your account."
            )
        
        if "gst" in question_lower and "verify" in question_lower:
            return (
                "We verify GST by:\n"
                "1. Checking GSTIN format (15 characters)\n"
                "2. Fetching details from GSTN portal\n"
                "3. Matching business name and address\n"
                "4. Verifying GST status is 'Active'\n"
                "This happens automatically when you enter your GSTIN."
            )
        
        # Approval timeline
        if "how long" in question_lower or "approval" in question_lower:
            return (
                "Approval timeline depends on risk score:\n"
                "• Low risk (score > 70): Auto-approved within 1 hour\n"
                "• Medium risk (40-70): Manager review, 24-48 hours\n"
                "• High risk (< 40): Director approval, 3-5 business days\n"
                "You'll receive notifications at each stage."
            )
        
        # Credit limit
        if "credit" in question_lower and "limit" in question_lower:
            return (
                "Credit limits for buyers are calculated based on:\n"
                "• Business age and entity type\n"
                "• GST turnover data\n"
                "• Risk score\n"
                "• Banking relationships\n"
                "Initial limits are conservative and increase with good payment history."
            )
        
        # KYC renewal
        if "kyc" in question_lower and ("renew" in question_lower or "expire" in question_lower):
            return (
                "KYC renewal is required yearly from approval date.\n"
                "You'll get reminders 30 days before expiry.\n"
                "Process: Update info → Upload fresh docs → Submit for re-verification\n"
                "If KYC expires, account is suspended until renewed."
            )
        
        # Document requirements
        if "document" in question_lower or "upload" in question_lower:
            return (
                "Required documents for onboarding:\n"
                "1. GST Registration Certificate (mandatory)\n"
                "2. PAN Card (mandatory)\n"
                "3. Bank Account Proof - cancelled cheque (mandatory)\n"
                "4. For transporters: Vehicle RC, Insurance\n"
                "All documents auto-verified using OCR."
            )
        
        # Employee addition
        if "employee" in question_lower or "user" in question_lower or "add" in question_lower:
            return (
                "After approval, you can add up to 2 additional employees:\n"
                "1. Go to Settings → Team Management\n"
                "2. Click 'Invite Employee'\n"
                "3. Enter email and assign role\n"
                "4. Employee receives invitation email\n"
                "You (admin) + 2 employees = 3 users total per partner account."
            )
        
        # Amendment
        if "change" in question_lower or "update" in question_lower or "amend" in question_lower:
            return (
                "To change approved partner details:\n"
                "1. Submit amendment request with reason\n"
                "2. Upload supporting documents (if address/ownership changes)\n"
                "3. Approval required for critical changes (name, GST, ownership)\n"
                "4. Non-critical changes (contact, email) update immediately\n"
                "Amendment history is maintained for audit."
            )
        
        # Default response
        return (
            "I can help you with:\n"
            "• Onboarding process and requirements\n"
            "• Document upload guidance\n"
            "• Verification status explanation\n"
            "• Risk score details\n"
            "• KYC renewal process\n"
            "• Adding employees\n"
            "• Submitting amendments\n"
            "Please ask a specific question!"
        )
    
    def _estimate_onboarding_time(self, entity_class: str, service_provider_type: Optional[str] = None) -> str:
        """
        Estimate onboarding completion time based on entity class (CDPS).
        
        Args:
            entity_class: "business_entity" or "service_provider"
            service_provider_type: For service providers
        
        Returns:
            Estimated time range
        """
        if entity_class == "service_provider":
            if service_provider_type == "transporter":
                return "20-30 minutes (including vehicle details)"
            elif service_provider_type in ["broker", "sub_broker"]:
                return "15-20 minutes (including service areas)"
            elif service_provider_type == "financer":
                return "25-35 minutes (additional compliance docs required)"
            else:
                return "15-20 minutes"
        else:  # business_entity
            return "15-20 minutes"
    
    def _create_status_summary(self, status: Dict) -> str:
        """Create human-readable status summary."""
        stage = status.get("stage", "unknown")
        
        summaries = {
            "draft": "Your application is in draft. Complete all required fields to submit.",
            "submitted": "Application submitted! We're verifying your details.",
            "verification_in_progress": "Verification in progress. We're checking your GST and documents.",
            "pending_approval": "Verification complete! Waiting for approval.",
            "approved": "🎉 Congratulations! Your application is approved.",
            "rejected": "Application rejected. Please contact support for details.",
            "additional_info_required": "We need more information. Check pending items below."
        }
        
        return summaries.get(stage, "Status unknown. Please contact support.")

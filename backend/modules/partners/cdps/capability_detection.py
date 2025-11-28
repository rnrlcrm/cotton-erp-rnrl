"""
Capability Detection Service

Automatically detects partner capabilities from verified compliance documents.

CRITICAL RULES:
1. Indian Domestic: GST + PAN → domestic_buy_india, domestic_sell_india
2. Import/Export: IEC + GST + PAN (ALL THREE REQUIRED) → import_allowed, export_allowed
3. Foreign Domestic: Foreign Tax ID → domestic_buy_home_country, domestic_sell_home_country
   ⚠️ CRITICAL: Foreign entities can ONLY trade domestically in THEIR home country
   ⚠️ Foreign entities CANNOT trade domestically in India (must establish Indian entity with GST+PAN)
4. Foreign Import/Export: Foreign licenses → import_allowed, export_allowed
5. Service Providers: CANNOT trade (all capabilities = False)
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.modules.partners.models import BusinessPartner
from backend.modules.partners.repositories import BusinessPartnerRepository


class CapabilityDetectionService:
    """
    Automatically detects partner capabilities from verified documents.
    
    Detection Rules:
    1. Indian Domestic: GST + PAN → domestic_buy_india, domestic_sell_india
    2. Import/Export: IEC + GST + PAN → import_allowed, export_allowed
    3. Foreign Domestic: Foreign Tax ID → domestic_buy_home_country, domestic_sell_home_country
    4. Foreign International: Foreign licenses → import_allowed, export_allowed
    5. Service Providers: No trading capabilities
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = BusinessPartnerRepository(db)
    
    async def detect_indian_domestic_capability(self, partner_id: UUID) -> dict:
        """
        Grants domestic trading rights inside India.
        
        Requirement: GST Certificate + PAN Card (both verified)
        
        Returns:
            dict: {
                "domestic_buy_india": bool,
                "domestic_sell_india": bool,
                "detected_from_documents": list[str],
                "auto_detected": bool,
                "detected_at": str | None
            }
        """
        # Get verified documents
        docs = await self._get_verified_documents(partner_id)
        
        has_gst = any(
            d.document_type == "gst_certificate" and 
            d.verification_status == "verified" 
            for d in docs
        )
        
        has_pan = any(
            d.document_type == "pan_card" and 
            d.verification_status == "verified" 
            for d in docs
        )
        
        if has_gst and has_pan:
            return {
                "domestic_buy_india": True,
                "domestic_sell_india": True,
                "detected_from_documents": ["GST", "PAN"],
                "auto_detected": True,
                "detected_at": datetime.utcnow().isoformat()
            }
        
        return {
            "domestic_buy_india": False,
            "domestic_sell_india": False
        }
    
    async def detect_import_export_capability(self, partner_id: UUID) -> dict:
        """
        Grants import/export rights.
        
        CRITICAL RULE: IEC MUST be accompanied by GST + PAN.
        IEC alone = NO import/export capability.
        
        Requirement: IEC + GST + PAN (all three verified)
        
        Returns:
            dict: {
                "import_allowed": bool,
                "export_allowed": bool,
                "detected_from_documents": list[str],
                "auto_detected": bool,
                "detected_at": str | None
            }
        """
        docs = await self._get_verified_documents(partner_id)
        
        has_gst = any(
            d.document_type == "gst_certificate" and 
            d.verification_status == "verified" 
            for d in docs
        )
        
        has_pan = any(
            d.document_type == "pan_card" and 
            d.verification_status == "verified" 
            for d in docs
        )
        
        has_iec = any(
            d.document_type == "iec" and 
            d.verification_status == "verified" 
            for d in docs
        )
        
        # ALL THREE REQUIRED
        if has_iec and has_gst and has_pan:
            return {
                "import_allowed": True,
                "export_allowed": True,
                "detected_from_documents": ["IEC", "GST", "PAN"],
                "auto_detected": True,
                "detected_at": datetime.utcnow().isoformat()
            }
        
        # If IEC exists but GST or PAN missing → DENY
        if has_iec and (not has_gst or not has_pan):
            # Log warning
            print(f"⚠️ WARNING: Partner {partner_id} has IEC but missing GST/PAN - import/export DENIED")
            return {
                "import_allowed": False,
                "export_allowed": False,
                "detected_from_documents": ["IEC_INCOMPLETE"]
            }
        
        return {
            "import_allowed": False,
            "export_allowed": False
        }
    
    async def detect_foreign_domestic_capability(self, partner_id: UUID) -> dict:
        """
        Grants domestic trading rights in THEIR home country ONLY.
        
        ⚠️ CRITICAL RULE: Foreign entities can trade domestically ONLY in their home country.
        ⚠️ Foreign entities CANNOT trade domestically in India.
        
        To trade in India, foreign companies must:
        - Establish an Indian legal entity
        - Obtain Indian GST + PAN
        - Then they become "Indian entity" with domestic_buy_india/domestic_sell_india
        
        Requirement: Foreign Tax ID (verified)
        
        Returns:
            dict: {
                "domestic_buy_home_country": bool,
                "domestic_sell_home_country": bool,
                "domestic_buy_india": bool,  # Always False for foreign entities
                "domestic_sell_india": bool,  # Always False for foreign entities
                "detected_from_documents": list[str],
                "auto_detected": bool,
                "detected_at": str | None
            }
        """
        docs = await self._get_verified_documents(partner_id)
        partner = await self.repo.get_by_id(partner_id)
        
        has_foreign_tax_id = any(
            d.document_type == "foreign_tax_id" and 
            d.verification_status == "verified" 
            for d in docs
        )
        
        # CRITICAL: Only grant if NOT India
        if has_foreign_tax_id and partner.country != "India":
            return {
                "domestic_buy_home_country": True,
                "domestic_sell_home_country": True,
                "domestic_buy_india": False,  # ❌ Cannot trade in India
                "domestic_sell_india": False,  # ❌ Cannot trade in India
                "detected_from_documents": ["FOREIGN_TAX_ID"],
                "auto_detected": True,
                "detected_at": datetime.utcnow().isoformat()
            }
        
        return {
            "domestic_buy_home_country": False,
            "domestic_sell_home_country": False,
            "domestic_buy_india": False,
            "domestic_sell_india": False
        }
    
    async def detect_foreign_import_export_capability(self, partner_id: UUID) -> dict:
        """
        Grants import/export rights for foreign entities.
        
        Requirement: Foreign Import License OR Foreign Export License (verified)
        
        Returns:
            dict: {
                "import_allowed": bool,
                "export_allowed": bool,
                "detected_from_documents": list[str],
                "auto_detected": bool,
                "detected_at": str | None
            }
        """
        docs = await self._get_verified_documents(partner_id)
        
        has_import_license = any(
            d.document_type == "foreign_import_license" and 
            d.verification_status == "verified" 
            for d in docs
        )
        
        has_export_license = any(
            d.document_type == "foreign_export_license" and 
            d.verification_status == "verified" 
            for d in docs
        )
        
        result = {}
        detected_docs = []
        
        if has_import_license:
            result["import_allowed"] = True
            detected_docs.append("FOREIGN_IMPORT_LICENSE")
        else:
            result["import_allowed"] = False
        
        if has_export_license:
            result["export_allowed"] = True
            detected_docs.append("FOREIGN_EXPORT_LICENSE")
        else:
            result["export_allowed"] = False
        
        if detected_docs:
            result["detected_from_documents"] = detected_docs
            result["auto_detected"] = True
            result["detected_at"] = datetime.utcnow().isoformat()
        
        return result
    
    async def update_partner_capabilities(
        self, 
        partner_id: UUID,
        force_redetect: bool = False
    ) -> dict:
        """
        Main entry point: Detect and update capabilities.
        
        Args:
            partner_id: Partner to detect capabilities for
            force_redetect: Force re-detection even if already detected
        
        Returns:
            dict: Updated capabilities
        """
        partner = await self.repo.get_by_id(partner_id)
        
        # Service providers cannot trade
        if hasattr(partner, 'entity_class') and partner.entity_class == "service_provider":
            capabilities = {
                "domestic_buy_india": False,
                "domestic_sell_india": False,
                "domestic_buy_home_country": False,
                "domestic_sell_home_country": False,
                "import_allowed": False,
                "export_allowed": False,
                "detected_from_documents": ["SERVICE_PROVIDER_NO_TRADING"],
                "auto_detected": True,
                "detected_at": datetime.utcnow().isoformat()
            }
            return capabilities
        
        # Detect all capabilities
        capabilities = {}
        
        if partner.country == "India":
            # Indian entity detection
            domestic = await self.detect_indian_domestic_capability(partner_id)
            import_export = await self.detect_import_export_capability(partner_id)
            capabilities.update(domestic)
            capabilities.update(import_export)
            
            # Ensure foreign capabilities are False for Indian entities
            capabilities["domestic_buy_home_country"] = False
            capabilities["domestic_sell_home_country"] = False
        else:
            # Foreign entity detection
            foreign_domestic = await self.detect_foreign_domestic_capability(partner_id)
            foreign_intl = await self.detect_foreign_import_export_capability(partner_id)
            capabilities.update(foreign_domestic)
            
            # Merge import/export
            if "import_allowed" in foreign_intl:
                capabilities["import_allowed"] = foreign_intl["import_allowed"]
            if "export_allowed" in foreign_intl:
                capabilities["export_allowed"] = foreign_intl["export_allowed"]
            
            # Ensure India capabilities are False for foreign entities
            capabilities["domestic_buy_india"] = False
            capabilities["domestic_sell_india"] = False
        
        # Merge detected documents
        all_docs = set()
        for result in [capabilities]:
            if "detected_from_documents" in result:
                if isinstance(result["detected_from_documents"], list):
                    all_docs.update(result["detected_from_documents"])
        
        capabilities["detected_from_documents"] = sorted(list(all_docs))
        capabilities["last_detection_run"] = datetime.utcnow().isoformat()
        capabilities["auto_detected"] = True
        capabilities["manual_override"] = False
        capabilities["override_reason"] = None
        
        return capabilities
    
    async def _get_verified_documents(self, partner_id: UUID) -> list:
        """
        Get all verified documents for a partner.
        
        Returns:
            list: List of verified documents
        """
        # TODO: Query from partner_documents table
        # For now, return empty list
        # This will be implemented when we integrate with document verification
        return []
    
    def _get_empty_capabilities(self) -> dict:
        """
        Get default empty capabilities structure.
        
        Returns:
            dict: Empty capabilities with all False
        """
        return {
            "domestic_buy_india": False,
            "domestic_sell_india": False,
            "domestic_buy_home_country": False,
            "domestic_sell_home_country": False,
            "import_allowed": False,
            "export_allowed": False,
            "auto_detected": False,
            "detected_from_documents": [],
            "detected_at": None,
            "manual_override": False,
            "override_reason": None,
            "last_detection_run": None
        }

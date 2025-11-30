"""
Partner Services Module - Service Layer for Business Partner Operations

Extracted services for clean architecture:
- analytics.py: Dashboard, export, KYC expiry queries
- documents.py: Document upload and management

NOTE: Core services (PartnerService, ApprovalService, etc.) are in ../services.py
      Import them directly: from backend.modules.partners import services as partner_services

Part of 15-year architecture hardening (feat/architecture-hardening-15yr)
"""

# Import extracted services only (avoid circular imports with services.py)
from backend.modules.partners.services.analytics import PartnerAnalyticsService
from backend.modules.partners.services.documents import PartnerDocumentService

__all__ = [
    "PartnerAnalyticsService",
    "PartnerDocumentService",
]

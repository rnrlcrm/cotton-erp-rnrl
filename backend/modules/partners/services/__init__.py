"""
Partner Services Module - Service Layer for Business Partner Operations

Extracted from router to achieve proper separation of concerns:
- analytics.py: Dashboard, export, KYC expiry queries
- documents.py: Document upload and management

Part of 15-year architecture hardening (feat/architecture-hardening-15yr)
"""

from backend.modules.partners.services.analytics import PartnerAnalyticsService
from backend.modules.partners.services.documents import PartnerDocumentService

__all__ = [
    "PartnerAnalyticsService",
    "PartnerDocumentService",
]

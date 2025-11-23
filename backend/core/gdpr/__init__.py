"""
GDPR Compliance Module

Implements GDPR requirements:
- Article 7: Consent management
- Article 13-14: Transparency (data collection notices)
- Article 15: Right of access (download my data)
- Article 16: Right to rectification
- Article 17: Right to erasure (deletion)
- Article 18: Right to restriction
- Article 20: Data portability
- Article 30: Records of processing activities
"""

from .consent import ConsentType, UserConsent, ConsentVersion, PrivacyService
from .data_retention import DataRetentionPolicy, RetentionService
from .user_rights import DataExportService, DeletionService

__all__ = [
    "ConsentType",
    "UserConsent",
    "ConsentVersion",
    "PrivacyService",
    "DataRetentionPolicy",
    "RetentionService",
    "DataExportService",
    "DeletionService",
]

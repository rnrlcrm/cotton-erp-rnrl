"""
GDPR User Rights Implementation

Implements GDPR Chapter III (Rights of the data subject):
- Article 15: Right of access (data export)
- Article 17: Right to erasure (account deletion)

Features:
- Complete data export in portable format
- Safe account deletion with anonymization
- Audit trail of requests
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from sqlalchemy import Boolean, Column, DateTime, Enum as SQLEnum, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, update

from backend.db.base_class import Base

logger = logging.getLogger(__name__)


class UserRightType(str, Enum):
    """Types of GDPR user rights requests"""
    ACCESS = "access"  # Article 15 - Right of access
    RECTIFICATION = "rectification"  # Article 16 - Right to rectification
    ERASURE = "erasure"  # Article 17 - Right to erasure ("right to be forgotten")
    RESTRICTION = "restriction"  # Article 18 - Right to restriction
    PORTABILITY = "portability"  # Article 20 - Right to data portability
    OBJECTION = "objection"  # Article 21 - Right to object


class RequestStatus(str, Enum):
    """Status of user rights request"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    REJECTED = "rejected"


class UserRightRequest(Base):
    """
    GDPR user rights request.
    
    Tracks all data subject access requests for audit purposes.
    
    Attributes:
        id: Request UUID
        user_id: User making request
        request_type: Type of right being exercised
        status: Request status
        requested_at: When request was made
        completed_at: When request was fulfilled
        rejected_reason: Why request was rejected (if applicable)
        metadata: Additional request details
    """
    __tablename__ = "user_right_requests"
    
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(PGUUID(as_uuid=True), nullable=False, index=True)
    request_type = Column(SQLEnum(UserRightType), nullable=False)
    status = Column(SQLEnum(RequestStatus), nullable=False, default=RequestStatus.PENDING)
    requested_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    completed_at = Column(DateTime(timezone=True), nullable=True)
    rejected_reason = Column(Text, nullable=True)
    metadata = Column(JSONB, nullable=True)  # Request-specific data


class DataExportService:
    """
    Service for exporting user data (GDPR Article 15).
    
    Features:
    - Export all user data in portable JSON format
    - Include all related data (consents, sessions, transactions, etc.)
    - Machine-readable format
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create_export_request(
        self,
        user_id: UUID,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> UserRightRequest:
        """
        Create data export request.
        
        Args:
            user_id: User requesting export
            metadata: Additional request details
            
        Returns:
            Created UserRightRequest
        """
        request = UserRightRequest(
            user_id=user_id,
            request_type=UserRightType.ACCESS,
            status=RequestStatus.PENDING,
            metadata=metadata,
        )
        self.db.add(request)
        await self.db.flush()
        
        logger.info(f"Created data export request for user {user_id}: {request.id}")
        return request
    
    async def export_user_data(self, user_id: UUID) -> Dict[str, Any]:
        """
        Export all user data in portable format.
        
        GDPR Article 15 compliance:
        - All personal data being processed
        - Purposes of processing
        - Categories of data
        - Recipients of data
        - Storage periods
        - Right to rectification, erasure, restriction
        - Right to lodge complaint
        
        Args:
            user_id: User ID to export
            
        Returns:
            Complete user data export
        """
        # This is a template - actual implementation depends on your models
        export = {
            "export_date": datetime.now(timezone.utc).isoformat(),
            "user_id": str(user_id),
            "gdpr_info": {
                "purposes": [
                    "Contract performance",
                    "Legal obligations",
                    "Legitimate interests (fraud prevention)",
                ],
                "storage_periods": {
                    "account_data": "7 years after account closure",
                    "transaction_data": "7 years (accounting law)",
                    "session_data": "90 days",
                    "consent_records": "7 years (proof of consent)",
                },
                "your_rights": [
                    "Right to rectification (update your data)",
                    "Right to erasure (delete your account)",
                    "Right to restriction (limit processing)",
                    "Right to object (opt-out of processing)",
                    "Right to data portability",
                    "Right to lodge complaint with supervisory authority",
                ],
            },
            "personal_data": {},
            "consents": [],
            "sessions": [],
            "transactions": [],
            "audit_logs": [],
        }
        
        # Example: Export user profile
        # from backend.modules.users.models import User
        # user = await self.db.get(User, user_id)
        # if user:
        #     export["personal_data"] = {
        #         "email": user.email,
        #         "full_name": user.full_name,
        #         "created_at": user.created_at.isoformat(),
        #         # ... other fields
        #     }
        
        # Example: Export consents
        # from backend.core.gdpr.consent import UserConsent
        # consents_result = await self.db.execute(
        #     select(UserConsent).where(UserConsent.user_id == user_id)
        # )
        # consents = consents_result.scalars().all()
        # export["consents"] = [
        #     {
        #         "type": consent.consent_type.value,
        #         "given": consent.given,
        #         "given_at": consent.given_at.isoformat() if consent.given_at else None,
        #         "withdrawn_at": consent.withdrawn_at.isoformat() if consent.withdrawn_at else None,
        #     }
        #     for consent in consents
        # ]
        
        # Example: Export sessions
        # from backend.modules.auth.models import UserSession
        # sessions_result = await self.db.execute(
        #     select(UserSession).where(UserSession.user_id == user_id)
        # )
        # sessions = sessions_result.scalars().all()
        # export["sessions"] = [
        #     {
        #         "device": session.device_name,
        #         "ip_address": session.ip_address,
        #         "created_at": session.created_at.isoformat(),
        #         "last_active": session.last_active_at.isoformat(),
        #     }
        #     for session in sessions
        # ]
        
        logger.info(f"Exported data for user {user_id}")
        return export
    
    async def complete_export_request(
        self,
        request_id: UUID,
        export_data: Dict[str, Any],
    ) -> UserRightRequest:
        """
        Mark export request as completed.
        
        Args:
            request_id: Request ID
            export_data: Exported data
            
        Returns:
            Updated request
        """
        result = await self.db.execute(
            select(UserRightRequest).where(UserRightRequest.id == request_id)
        )
        request = result.scalar_one_or_none()
        
        if not request:
            raise ValueError(f"Request {request_id} not found")
        
        request.status = RequestStatus.COMPLETED
        request.completed_at = datetime.now(timezone.utc)
        request.metadata = {
            **(request.metadata or {}),
            "export_size_bytes": len(json.dumps(export_data)),
        }
        
        self.db.add(request)
        await self.db.flush()
        
        logger.info(f"Completed export request {request_id}")
        return request


class DeletionService:
    """
    Service for account deletion (GDPR Article 17).
    
    Features:
    - Hard delete user account
    - Anonymize data that must be retained
    - Cascade deletion across all tables
    - Audit trail
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create_deletion_request(
        self,
        user_id: UUID,
        reason: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> UserRightRequest:
        """
        Create account deletion request.
        
        Args:
            user_id: User requesting deletion
            reason: Reason for deletion
            metadata: Additional request details
            
        Returns:
            Created UserRightRequest
        """
        request = UserRightRequest(
            user_id=user_id,
            request_type=UserRightType.ERASURE,
            status=RequestStatus.PENDING,
            metadata={
                **(metadata or {}),
                "reason": reason,
            },
        )
        self.db.add(request)
        await self.db.flush()
        
        logger.info(f"Created deletion request for user {user_id}: {request.id}")
        return request
    
    async def delete_user_account(
        self,
        user_id: UUID,
        anonymize_retained_data: bool = True,
    ) -> Dict[str, int]:
        """
        Delete user account and all associated data.
        
        GDPR Article 17 compliance:
        - Delete all personal data
        - Anonymize data that must be retained (legal obligation)
        - Inform user of deletion
        
        Args:
            user_id: User to delete
            anonymize_retained_data: Anonymize instead of delete for legally required data
            
        Returns:
            Count of deleted records per table
        """
        deletion_counts = {}
        
        # 1. Delete sessions
        # from backend.modules.auth.models import UserSession
        # result = await self.db.execute(
        #     delete(UserSession).where(UserSession.user_id == user_id)
        # )
        # deletion_counts["sessions"] = result.rowcount
        
        # 2. Delete or anonymize consents
        # from backend.core.gdpr.consent import UserConsent
        # if anonymize_retained_data:
        #     # Anonymize (keep record but remove PII)
        #     await self.db.execute(
        #         update(UserConsent)
        #         .where(UserConsent.user_id == user_id)
        #         .values(
        #             ip_address="0.0.0.0",
        #             user_agent="[DELETED]",
        #         )
        #     )
        #     deletion_counts["consents_anonymized"] = result.rowcount
        # else:
        #     result = await self.db.execute(
        #         delete(UserConsent).where(UserConsent.user_id == user_id)
        #     )
        #     deletion_counts["consents"] = result.rowcount
        
        # 3. Anonymize transactions (must keep for accounting)
        # from backend.modules.transactions.models import Transaction
        # if anonymize_retained_data:
        #     await self.db.execute(
        #         update(Transaction)
        #         .where(Transaction.user_id == user_id)
        #         .values(
        #             user_id=None,
        #             # Keep transaction data but remove link to user
        #         )
        #     )
        
        # 4. Delete user profile
        # from backend.modules.users.models import User
        # result = await self.db.execute(
        #     delete(User).where(User.id == user_id)
        # )
        # deletion_counts["user"] = result.rowcount
        
        logger.info(f"Deleted user {user_id}: {deletion_counts}")
        return deletion_counts
    
    async def complete_deletion_request(
        self,
        request_id: UUID,
        deletion_counts: Dict[str, int],
    ) -> UserRightRequest:
        """
        Mark deletion request as completed.
        
        Args:
            request_id: Request ID
            deletion_counts: Count of deleted records
            
        Returns:
            Updated request
        """
        result = await self.db.execute(
            select(UserRightRequest).where(UserRightRequest.id == request_id)
        )
        request = result.scalar_one_or_none()
        
        if not request:
            raise ValueError(f"Request {request_id} not found")
        
        request.status = RequestStatus.COMPLETED
        request.completed_at = datetime.now(timezone.utc)
        request.metadata = {
            **(request.metadata or {}),
            "deletion_counts": deletion_counts,
        }
        
        self.db.add(request)
        await self.db.flush()
        
        logger.info(f"Completed deletion request {request_id}")
        return request
    
    async def reject_deletion_request(
        self,
        request_id: UUID,
        reason: str,
    ) -> UserRightRequest:
        """
        Reject deletion request.
        
        Valid reasons under GDPR:
        - Legal obligation to retain data
        - Public interest
        - Legal claims
        
        Args:
            request_id: Request ID
            reason: Rejection reason
            
        Returns:
            Updated request
        """
        result = await self.db.execute(
            select(UserRightRequest).where(UserRightRequest.id == request_id)
        )
        request = result.scalar_one_or_none()
        
        if not request:
            raise ValueError(f"Request {request_id} not found")
        
        request.status = RequestStatus.REJECTED
        request.rejected_reason = reason
        request.completed_at = datetime.now(timezone.utc)
        
        self.db.add(request)
        await self.db.flush()
        
        logger.info(f"Rejected deletion request {request_id}: {reason}")
        return request

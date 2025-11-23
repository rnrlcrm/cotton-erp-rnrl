"""
Data Retention Policies

Implements GDPR Article 5 (Storage limitation) and Article 30 (Records of processing).

Principles:
- Data kept only as long as necessary
- Automatic deletion after retention period
- Clear policies per data type
- Audit trail of deletions
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import Boolean, Column, DateTime, Enum as SQLEnum, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.db.base_class import Base

logger = logging.getLogger(__name__)


class DataCategory(str, Enum):
    """
    Categories of data with different retention requirements.
    """
    USER_ACCOUNT = "user_account"  # User profiles
    TRANSACTION = "transaction"  # Business transactions
    AUDIT_LOG = "audit_log"  # Audit/compliance logs
    SESSION = "session"  # User sessions
    CONSENT = "consent"  # Consent records
    COMMUNICATION = "communication"  # Emails, SMS
    ANALYTICS = "analytics"  # Usage analytics
    BACKUP = "backup"  # Backup data


class DataRetentionPolicy(Base):
    """
    Data retention policy definition.
    
    Defines how long different types of data should be kept.
    
    Attributes:
        id: Policy UUID
        data_category: Category of data
        retention_days: How long to keep (in days)
        description: Human-readable description
        legal_basis: Legal reason for retention
        auto_delete: Automatically delete after retention period
        is_active: Policy is active
        created_at: When policy was created
        updated_at: Last update
    """
    __tablename__ = "data_retention_policies"
    
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    data_category = Column(SQLEnum(DataCategory), nullable=False, unique=True, index=True)
    retention_days = Column(Integer, nullable=False)
    description = Column(Text, nullable=False)
    legal_basis = Column(Text, nullable=True)  # Why we keep it
    auto_delete = Column(Boolean, nullable=False, default=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=True)


# Default retention policies (GDPR-compliant defaults)
DEFAULT_RETENTION_POLICIES = {
    DataCategory.USER_ACCOUNT: {
        "retention_days": 2555,  # 7 years (common for business records)
        "description": "User account data including profile, contact info, business details",
        "legal_basis": "Contract performance, legal obligation (tax/accounting)",
        "auto_delete": False,  # Manual deletion (user request)
    },
    DataCategory.TRANSACTION: {
        "retention_days": 2555,  # 7 years (accounting requirement)
        "description": "Business transactions, invoices, payments, contracts",
        "legal_basis": "Legal obligation (accounting, tax laws)",
        "auto_delete": False,  # Keep for legal compliance
    },
    DataCategory.AUDIT_LOG: {
        "retention_days": 2555,  # 7 years (compliance)
        "description": "Audit logs, security events, access logs",
        "legal_basis": "Legal obligation (GDPR Article 30, security)",
        "auto_delete": True,
    },
    DataCategory.SESSION: {
        "retention_days": 90,  # 3 months
        "description": "User sessions, refresh tokens, device info",
        "legal_basis": "Legitimate interest (security)",
        "auto_delete": True,
    },
    DataCategory.CONSENT: {
        "retention_days": 2555,  # 7 years (proof of consent)
        "description": "Consent records, proof of consent",
        "legal_basis": "Legal obligation (GDPR Article 7.1 - burden of proof)",
        "auto_delete": False,  # Must keep proof
    },
    DataCategory.COMMUNICATION: {
        "retention_days": 365,  # 1 year
        "description": "Emails, SMS, notifications sent to users",
        "legal_basis": "Legitimate interest (customer service)",
        "auto_delete": True,
    },
    DataCategory.ANALYTICS: {
        "retention_days": 730,  # 2 years
        "description": "Usage analytics, product metrics (anonymized when possible)",
        "legal_basis": "Legitimate interest (product improvement)",
        "auto_delete": True,
    },
    DataCategory.BACKUP: {
        "retention_days": 90,  # 3 months
        "description": "Database backups, disaster recovery data",
        "legal_basis": "Legitimate interest (business continuity)",
        "auto_delete": True,
    },
}


class RetentionService:
    """
    Service for managing data retention.
    
    Features:
    - Automatic data deletion
    - Retention policy enforcement
    - Deletion audit trail
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_policy(self, data_category: DataCategory) -> Optional[DataRetentionPolicy]:
        """
        Get retention policy for data category.
        
        Args:
            data_category: Category of data
            
        Returns:
            DataRetentionPolicy or None
        """
        result = await self.db.execute(
            select(DataRetentionPolicy).where(
                DataRetentionPolicy.data_category == data_category,
                DataRetentionPolicy.is_active == True,
            )
        )
        return result.scalar_one_or_none()
    
    async def get_all_policies(self) -> list[DataRetentionPolicy]:
        """Get all active retention policies"""
        result = await self.db.execute(
            select(DataRetentionPolicy).where(DataRetentionPolicy.is_active == True)
        )
        return list(result.scalars().all())
    
    async def create_policy(
        self,
        data_category: DataCategory,
        retention_days: int,
        description: str,
        legal_basis: Optional[str] = None,
        auto_delete: bool = True,
    ) -> DataRetentionPolicy:
        """
        Create or update retention policy.
        
        Args:
            data_category: Category of data
            retention_days: Retention period in days
            description: Policy description
            legal_basis: Legal justification
            auto_delete: Enable automatic deletion
            
        Returns:
            Created/updated DataRetentionPolicy
        """
        # Check if policy exists
        existing = await self.get_policy(data_category)
        
        if existing:
            # Update existing
            existing.retention_days = retention_days
            existing.description = description
            existing.legal_basis = legal_basis
            existing.auto_delete = auto_delete
            existing.updated_at = datetime.now(timezone.utc)
            self.db.add(existing)
            await self.db.flush()
            return existing
        else:
            # Create new
            policy = DataRetentionPolicy(
                data_category=data_category,
                retention_days=retention_days,
                description=description,
                legal_basis=legal_basis,
                auto_delete=auto_delete,
            )
            self.db.add(policy)
            await self.db.flush()
            return policy
    
    async def seed_default_policies(self) -> list[DataRetentionPolicy]:
        """
        Seed default retention policies.
        
        Call during initial setup to create GDPR-compliant defaults.
        
        Returns:
            List of created policies
        """
        policies = []
        
        for category, config in DEFAULT_RETENTION_POLICIES.items():
            policy = await self.create_policy(
                data_category=category,
                retention_days=config["retention_days"],
                description=config["description"],
                legal_basis=config.get("legal_basis"),
                auto_delete=config.get("auto_delete", True),
            )
            policies.append(policy)
        
        logger.info(f"Seeded {len(policies)} default retention policies")
        return policies
    
    def calculate_deletion_date(
        self,
        created_at: datetime,
        retention_days: int,
    ) -> datetime:
        """
        Calculate when data should be deleted.
        
        Args:
            created_at: When data was created
            retention_days: Retention period
            
        Returns:
            Deletion date
        """
        return created_at + timedelta(days=retention_days)
    
    def should_delete(
        self,
        created_at: datetime,
        retention_days: int,
    ) -> bool:
        """
        Check if data should be deleted based on retention policy.
        
        Args:
            created_at: When data was created
            retention_days: Retention period
            
        Returns:
            True if data is past retention period
        """
        deletion_date = self.calculate_deletion_date(created_at, retention_days)
        return datetime.now(timezone.utc) >= deletion_date
    
    async def cleanup_expired_sessions(self) -> int:
        """
        Delete expired user sessions (example cleanup task).
        
        Returns:
            Number of sessions deleted
        """
        policy = await self.get_policy(DataCategory.SESSION)
        if not policy or not policy.auto_delete:
            return 0
        
        # Calculate cutoff date
        cutoff = datetime.now(timezone.utc) - timedelta(days=policy.retention_days)
        
        # This would delete expired sessions from UserSession table
        # Actual implementation depends on session storage
        # Example:
        # from backend.modules.auth.models import UserSession
        # result = await self.db.execute(
        #     delete(UserSession).where(UserSession.last_active_at < cutoff)
        # )
        # return result.rowcount
        
        logger.info(f"Would delete sessions older than {cutoff}")
        return 0  # Placeholder

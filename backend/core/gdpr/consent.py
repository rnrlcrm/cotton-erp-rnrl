"""
GDPR Consent Management

Implements GDPR Article 7 (Conditions for consent) and Article 8 (Child consent).

Requirements:
- Freely given, specific, informed, and unambiguous consent
- Clear and distinguishable from other matters
- Withdrawal must be as easy as giving consent
- Burden of proof on controller
- Version tracking for consent text changes
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import Boolean, Column, DateTime, Enum as SQLEnum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import relationship
from sqlalchemy import select

from backend.db.base_class import Base


class ConsentType(str, Enum):
    """
    Types of consent required under GDPR.
    
    Categories:
    - ESSENTIAL: Required for service (not GDPR consent, but transparency)
    - FUNCTIONAL: Enhance user experience
    - ANALYTICS: Usage tracking
    - MARKETING: Communications
    - DATA_SHARING: Third-party sharing
    """
    ESSENTIAL = "essential"  # Required for service
    FUNCTIONAL = "functional"  # Enhanced features
    ANALYTICS = "analytics"  # Usage tracking
    MARKETING = "marketing"  # Marketing emails/SMS
    DATA_SHARING = "data_sharing"  # Share with partners
    PROFILING = "profiling"  # Automated decision-making


class ConsentVersion(Base):
    """
    Consent text version tracking.
    
    GDPR requires proof of what user consented to.
    Version tracking ensures we can show historical consent text.
    
    Attributes:
        id: Version UUID
        consent_type: Type of consent
        version: Version number (1, 2, 3...)
        title: Short title (e.g., "Privacy Policy")
        description: Full consent text
        effective_date: When this version became active
        created_at: When version was created
        is_active: Currently active version
    """
    __tablename__ = "consent_versions"
    
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    consent_type = Column(SQLEnum(ConsentType), nullable=False, index=True)
    version = Column(String(50), nullable=False)  # "1.0", "2.1", etc.
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)  # Full consent text
    effective_date = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    is_active = Column(Boolean, nullable=False, default=True)
    
    # Relationships
    consents = relationship("UserConsent", back_populates="consent_version")


class UserConsent(Base):
    """
    User consent records.
    
    Stores proof of consent per GDPR Article 7.
    
    Attributes:
        id: Record UUID
        user_id: User who gave consent
        consent_type: Type of consent
        consent_version_id: Version of consent text shown
        given: Whether consent was given (True) or denied (False)
        given_at: When consent was given/denied
        withdrawn_at: When consent was withdrawn (if applicable)
        ip_address: IP address of user when consenting
        user_agent: User agent when consenting
        method: How consent was obtained (web, mobile, api)
        notes: Optional notes (e.g., "Updated after policy change")
    """
    __tablename__ = "user_consents"
    
    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(PGUUID(as_uuid=True), nullable=False, index=True)
    consent_type = Column(SQLEnum(ConsentType), nullable=False, index=True)
    consent_version_id = Column(PGUUID(as_uuid=True), ForeignKey("consent_versions.id"), nullable=False)
    
    given = Column(Boolean, nullable=False)  # True = consent, False = denied
    given_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    withdrawn_at = Column(DateTime(timezone=True), nullable=True)
    
    # Proof of consent (GDPR Article 7.1)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    method = Column(String(50), nullable=True)  # "web", "mobile", "api"
    
    notes = Column(Text, nullable=True)
    
    # Relationships
    consent_version = relationship("ConsentVersion", back_populates="consents")


class PrivacyService:
    """
    Service for managing user consents and privacy preferences.
    
    Implements GDPR consent requirements:
    - Record consent with proof
    - Allow withdrawal
    - Version tracking
    - Audit trail
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_active_consent_versions(self) -> dict[ConsentType, ConsentVersion]:
        """
        Get currently active consent versions for all types.
        
        Returns:
            Dict mapping ConsentType to active ConsentVersion
        """
        result = await self.db.execute(
            select(ConsentVersion).where(ConsentVersion.is_active == True)
        )
        versions = result.scalars().all()
        
        return {v.consent_type: v for v in versions}
    
    async def get_user_consents(
        self,
        user_id: UUID,
        consent_type: Optional[ConsentType] = None,
    ) -> list[UserConsent]:
        """
        Get user's consent records.
        
        Args:
            user_id: User ID
            consent_type: Optional filter by consent type
            
        Returns:
            List of UserConsent records (most recent first)
        """
        query = select(UserConsent).where(UserConsent.user_id == user_id)
        
        if consent_type:
            query = query.where(UserConsent.consent_type == consent_type)
        
        query = query.order_by(UserConsent.given_at.desc())
        
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def give_consent(
        self,
        user_id: UUID,
        consent_type: ConsentType,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        method: str = "web",
    ) -> UserConsent:
        """
        Record user consent.
        
        Args:
            user_id: User giving consent
            consent_type: Type of consent
            ip_address: User's IP address (proof)
            user_agent: User's user agent (proof)
            method: How consent was obtained
            
        Returns:
            Created UserConsent record
        """
        # Get active consent version
        active_versions = await self.get_active_consent_versions()
        consent_version = active_versions.get(consent_type)
        
        if not consent_version:
            raise ValueError(f"No active consent version for {consent_type}")
        
        # Create consent record
        consent = UserConsent(
            user_id=user_id,
            consent_type=consent_type,
            consent_version_id=consent_version.id,
            given=True,
            ip_address=ip_address,
            user_agent=user_agent,
            method=method,
        )
        
        self.db.add(consent)
        await self.db.flush()
        
        return consent
    
    async def withdraw_consent(
        self,
        user_id: UUID,
        consent_type: ConsentType,
    ) -> UserConsent:
        """
        Withdraw user consent.
        
        GDPR Article 7.3: "It shall be as easy to withdraw as to give consent."
        
        Args:
            user_id: User withdrawing consent
            consent_type: Type of consent to withdraw
            
        Returns:
            Updated UserConsent record
        """
        # Get most recent consent
        consents = await self.get_user_consents(user_id, consent_type)
        
        if not consents:
            raise ValueError(f"No consent found for {consent_type}")
        
        latest_consent = consents[0]
        
        if latest_consent.withdrawn_at:
            raise ValueError(f"Consent already withdrawn at {latest_consent.withdrawn_at}")
        
        # Mark as withdrawn
        latest_consent.withdrawn_at = datetime.now(timezone.utc)
        self.db.add(latest_consent)
        await self.db.flush()
        
        return latest_consent
    
    async def has_valid_consent(
        self,
        user_id: UUID,
        consent_type: ConsentType,
    ) -> bool:
        """
        Check if user has valid (non-withdrawn) consent.
        
        Args:
            user_id: User ID
            consent_type: Type of consent
            
        Returns:
            True if user has given and not withdrawn consent
        """
        consents = await self.get_user_consents(user_id, consent_type)
        
        if not consents:
            return False
        
        latest_consent = consents[0]
        
        return latest_consent.given and not latest_consent.withdrawn_at
    
    async def get_consent_history(
        self,
        user_id: UUID,
    ) -> dict[ConsentType, list[dict]]:
        """
        Get full consent history for user (for transparency).
        
        GDPR Article 15: User has right to access consent history.
        
        Args:
            user_id: User ID
            
        Returns:
            Dict mapping ConsentType to list of consent events
        """
        consents = await self.get_user_consents(user_id)
        
        history: dict[ConsentType, list[dict]] = {}
        
        for consent in consents:
            if consent.consent_type not in history:
                history[consent.consent_type] = []
            
            history[consent.consent_type].append({
                "given": consent.given,
                "given_at": consent.given_at.isoformat(),
                "withdrawn_at": consent.withdrawn_at.isoformat() if consent.withdrawn_at else None,
                "version": consent.consent_version.version,
                "version_title": consent.consent_version.title,
                "ip_address": consent.ip_address,
                "method": consent.method,
            })
        
        return history
    
    async def create_consent_version(
        self,
        consent_type: ConsentType,
        version: str,
        title: str,
        description: str,
        effective_date: Optional[datetime] = None,
    ) -> ConsentVersion:
        """
        Create new consent version.
        
        Use when privacy policy or consent text changes.
        Deactivates previous version and creates new one.
        
        Args:
            consent_type: Type of consent
            version: Version number (e.g., "2.0")
            title: Short title
            description: Full consent text
            effective_date: When this version becomes active
            
        Returns:
            Created ConsentVersion
        """
        # Deactivate previous versions
        result = await self.db.execute(
            select(ConsentVersion).where(
                ConsentVersion.consent_type == consent_type,
                ConsentVersion.is_active == True,
            )
        )
        old_versions = result.scalars().all()
        
        for old_version in old_versions:
            old_version.is_active = False
            self.db.add(old_version)
        
        # Create new version
        new_version = ConsentVersion(
            consent_type=consent_type,
            version=version,
            title=title,
            description=description,
            effective_date=effective_date or datetime.now(timezone.utc),
            is_active=True,
        )
        
        self.db.add(new_version)
        await self.db.flush()
        
        return new_version

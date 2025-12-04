"""
Trade Signature Model - Digital signature records for contracts

Handles:
- 3-tier signature system (BASIC, AADHAAR_ESIGN, DSC)
- Signature metadata and audit trail
- Document hash verification
- IP address and geolocation tracking

In Phase 1:
- Only BASIC tier (pre-uploaded signatures from profile)
- Signatures embedded in PDF at generation time
- This table stores metadata/audit trail

Future Phases:
- AADHAAR_ESIGN: Integration with NSDL/CDAC
- DSC: Digital Signature Certificate support
"""

from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import (
    Column, String, DateTime, ForeignKey, Text,
    Index, CheckConstraint, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import relationship, Mapped, mapped_column

from backend.db.base import Base
from backend.core.events.mixins import EventMixin


class TradeSignature(Base, EventMixin):
    """
    Trade Signature - Audit record of contract signatures.
    
    NOTE: In Phase 1 (instant contract approach):
    - Signatures are pre-uploaded in user profile
    - Contract PDF is generated WITH signatures already embedded
    - This table stores metadata for audit/compliance
    - Actual signature image comes from BusinessPartner.digital_signature_url
    
    One signature per partner per trade (buyer + seller = 2 signatures total)
    """
    __tablename__ = "trade_signatures"
    
    # ============================================
    # PRIMARY KEY
    # ============================================
    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4
    )
    
    # ============================================
    # TRADE REFERENCE
    # ============================================
    trade_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("trades.id", ondelete="CASCADE"),
        nullable=False
    )
    
    # ============================================
    # SIGNER
    # ============================================
    partner_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("business_partners.id", ondelete="RESTRICT"),
        nullable=False,
        comment="Business partner who signed"
    )
    
    signed_by_user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        comment="User who performed the signature"
    )
    
    party_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="BUYER or SELLER"
    )
    
    # ============================================
    # SIGNATURE TIER
    # ============================================
    signature_tier: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="BASIC (Phase 1), AADHAAR_ESIGN (Phase 2), DSC (Phase 2)"
    )
    
    # ============================================
    # SIGNATURE DATA - BASIC TIER
    # ============================================
    signature_image_url: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        comment="For BASIC tier - URL to signature image (from partner profile)"
    )
    
    # ============================================
    # SIGNATURE DATA - AADHAAR ESIGN (Phase 2)
    # ============================================
    aadhaar_reference_id: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="NSDL/CDAC eSign reference ID"
    )
    
    aadhaar_transaction_id: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="Aadhaar eSign transaction ID"
    )
    
    # ============================================
    # SIGNATURE DATA - DSC (Phase 2)
    # ============================================
    dsc_signature_value: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Encrypted digital signature value from DSC"
    )
    
    dsc_certificate_serial: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="DSC certificate serial number"
    )
    
    # ============================================
    # DOCUMENT HASH (what was signed)
    # ============================================
    document_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        comment="SHA-256 hash of contract PDF that was signed"
    )
    
    # ============================================
    # METADATA (audit trail)
    # ============================================
    ip_address: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="IP address from which signature was performed"
    )
    
    user_agent: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Browser user agent string"
    )
    
    geolocation: Mapped[Optional[str]] = mapped_column(
        String(200),
        nullable=True,
        comment="Geolocation data (city, country)"
    )
    
    # ============================================
    # TIMESTAMP
    # ============================================
    signed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        comment="Timestamp when contract was signed"
    )
    
    # ============================================
    # CONSTRAINTS
    # ============================================
    __table_args__ = (
        UniqueConstraint('trade_id', 'partner_id', name='uq_trade_signature_per_partner'),
        CheckConstraint(
            "signature_tier IN ('BASIC', 'AADHAAR_ESIGN', 'DSC')",
            name='ck_trade_signatures_tier'
        ),
        CheckConstraint(
            "party_type IN ('BUYER', 'SELLER')",
            name='ck_trade_signatures_party_type'
        ),
        Index('ix_trade_signatures_trade_id', 'trade_id'),
        Index('ix_trade_signatures_partner_id', 'partner_id'),
    )
    
    # ============================================
    # RELATIONSHIPS
    # ============================================
    # trade: Mapped["Trade"] = relationship("Trade", back_populates="signatures")
    # partner: Mapped["BusinessPartner"] = relationship("BusinessPartner")
    # signed_by_user: Mapped["User"] = relationship("User")
    
    # ============================================
    # METHODS
    # ============================================
    def verify_document_hash(self, pdf_hash: str) -> bool:
        """
        Verify that the current PDF hash matches what was signed
        """
        return self.document_hash == pdf_hash
    
    def __repr__(self) -> str:
        return f"<TradeSignature {self.party_type} - {self.signature_tier}>"

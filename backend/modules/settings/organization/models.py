from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from backend.db.session import Base


class Organization(Base):
    __tablename__ = "organizations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False, unique=True)
    legal_name = Column(String(255), nullable=True)
    type = Column(String(64), nullable=True)
    CIN = Column(String(21), nullable=True)
    PAN = Column(String(10), nullable=True)
    base_currency = Column(String(3), nullable=False, default="INR")
    address_line1 = Column(String(255), nullable=True)
    address_line2 = Column(String(255), nullable=True)
    city = Column(String(128), nullable=True)
    state = Column(String(128), nullable=True)
    pincode = Column(String(16), nullable=True)
    contact_email = Column(String(255), nullable=True)
    contact_phone = Column(String(32), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)

    # Business settings
    threshold_limit = Column(Integer, nullable=True)
    einvoice_required = Column(Boolean, nullable=False, default=False)
    auto_block_if_einvoice_required = Column(Boolean, nullable=False, default=False)

    # FX settings
    fx_enabled = Column(Boolean, nullable=False, default=False)

    # Branding
    logo_url = Column(String(255), nullable=True)
    theme_color = Column(String(64), nullable=True)
    invoice_footer = Column(String(1024), nullable=True)
    digital_signature_url = Column(String(255), nullable=True)

    # Tax settings
    tds_rate = Column(Integer, nullable=True)
    tcs_rate = Column(Integer, nullable=True)
    audit_firm_name = Column(String(255), nullable=True)
    audit_firm_email = Column(String(255), nullable=True)
    audit_firm_phone = Column(String(32), nullable=True)
    gst_audit_required = Column(Boolean, nullable=False, default=False)

    # Automation
    auto_invoice = Column(Boolean, nullable=False, default=False)
    auto_contract_number = Column(Boolean, nullable=False, default=False)
    extra_config = Column(JSONB, nullable=False, default={})
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    gst_branches = relationship("OrganizationGST", back_populates="organization")
    bank_accounts = relationship("OrganizationBankAccount", back_populates="organization")
    financial_years = relationship("OrganizationFinancialYear", back_populates="organization")
    document_series = relationship("OrganizationDocumentSeries", back_populates="organization")


class OrganizationGST(Base):
    __tablename__ = "organization_gst"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    gstin = Column(String(15), nullable=False, unique=True)
    legal_name = Column(String(255), nullable=True)
    address = Column(String(255), nullable=True)
    state = Column(String(128), nullable=True)
    branch_code = Column(String(32), nullable=True)
    is_primary = Column(Boolean, nullable=False, default=False)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    organization = relationship("Organization", back_populates="gst_branches")


class OrganizationBankAccount(Base):
    __tablename__ = "organization_bank_accounts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    account_holder = Column(String(255), nullable=False)
    bank_name = Column(String(255), nullable=False)
    account_number = Column(String(64), nullable=False)
    ifsc = Column(String(11), nullable=True)
    branch = Column(String(255), nullable=True)
    is_default = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    organization = relationship("Organization", back_populates="bank_accounts")


class OrganizationFinancialYear(Base):
    __tablename__ = "organization_financial_years"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    is_active = Column(Boolean, nullable=False, default=False)
    allow_year_split = Column(Boolean, nullable=False, default=False)
    version = Column(Integer, nullable=False, default=1)  # Optimistic locking
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    organization = relationship("Organization", back_populates="financial_years")
    document_series = relationship("OrganizationDocumentSeries", back_populates="financial_year")


class OrganizationDocumentSeries(Base):
    __tablename__ = "organization_document_series"
    __table_args__ = (
        UniqueConstraint("organization_id", "document_type", "financial_year_id", name="uq_org_doc_series"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    financial_year_id = Column(UUID(as_uuid=True), ForeignKey("organization_financial_years.id", ondelete="CASCADE"), nullable=False)
    document_type = Column(String(64), nullable=False)  # 'INVOICE', 'CONTRACT', etc.
    prefix = Column(String(32), nullable=True)
    current_number = Column(Integer, nullable=False, default=1)
    reset_annually = Column(Boolean, nullable=False, default=True)
    is_active = Column(Boolean, nullable=False, default=True)
    extra_config = Column(JSONB, nullable=False, default={})
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    organization = relationship("Organization", back_populates="document_series")
    financial_year = relationship("OrganizationFinancialYear", back_populates="document_series")

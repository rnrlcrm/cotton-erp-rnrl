from __future__ import annotations

from datetime import date, datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


# Organization Schemas
class OrganizationCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    legal_name: Optional[str] = Field(None, max_length=255)
    type: Optional[str] = Field(None, max_length=64)
    CIN: Optional[str] = Field(None, max_length=21)
    PAN: Optional[str] = Field(None, max_length=10)
    base_currency: str = Field(default="INR", max_length=3)
    address_line1: Optional[str] = Field(None, max_length=255)
    address_line2: Optional[str] = Field(None, max_length=255)
    city: Optional[str] = Field(None, max_length=128)
    state: Optional[str] = Field(None, max_length=128)
    pincode: Optional[str] = Field(None, max_length=16)
    contact_email: Optional[str] = Field(None, max_length=255)
    contact_phone: Optional[str] = Field(None, max_length=32)
    threshold_limit: Optional[int] = None
    einvoice_required: bool = False
    auto_block_if_einvoice_required: bool = False
    fx_enabled: bool = False
    logo_url: Optional[str] = Field(None, max_length=255)
    theme_color: Optional[str] = Field(None, max_length=64)
    invoice_footer: Optional[str] = Field(None, max_length=1024)
    digital_signature_url: Optional[str] = Field(None, max_length=255)
    tds_rate: Optional[int] = None
    tcs_rate: Optional[int] = None
    audit_firm_name: Optional[str] = Field(None, max_length=255)
    audit_firm_email: Optional[str] = Field(None, max_length=255)
    audit_firm_phone: Optional[str] = Field(None, max_length=32)
    gst_audit_required: bool = False
    auto_invoice: bool = False
    auto_contract_number: bool = False
    extra_config: dict = Field(default_factory=dict)

    @field_validator("PAN")
    @classmethod
    def validate_pan(cls, v: Optional[str]) -> Optional[str]:
        if v and len(v) != 10:
            raise ValueError("PAN must be 10 characters")
        return v


class OrganizationUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    legal_name: Optional[str] = Field(None, max_length=255)
    type: Optional[str] = Field(None, max_length=64)
    CIN: Optional[str] = Field(None, max_length=21)
    PAN: Optional[str] = Field(None, max_length=10)
    base_currency: Optional[str] = Field(None, max_length=3)
    address_line1: Optional[str] = Field(None, max_length=255)
    address_line2: Optional[str] = Field(None, max_length=255)
    city: Optional[str] = Field(None, max_length=128)
    state: Optional[str] = Field(None, max_length=128)
    pincode: Optional[str] = Field(None, max_length=16)
    contact_email: Optional[str] = Field(None, max_length=255)
    contact_phone: Optional[str] = Field(None, max_length=32)
    is_active: Optional[bool] = None
    threshold_limit: Optional[int] = None
    einvoice_required: Optional[bool] = None
    auto_block_if_einvoice_required: Optional[bool] = None
    fx_enabled: Optional[bool] = None
    logo_url: Optional[str] = Field(None, max_length=255)
    theme_color: Optional[str] = Field(None, max_length=64)
    invoice_footer: Optional[str] = Field(None, max_length=1024)
    digital_signature_url: Optional[str] = Field(None, max_length=255)
    tds_rate: Optional[int] = None
    tcs_rate: Optional[int] = None
    audit_firm_name: Optional[str] = Field(None, max_length=255)
    audit_firm_email: Optional[str] = Field(None, max_length=255)
    audit_firm_phone: Optional[str] = Field(None, max_length=32)
    gst_audit_required: Optional[bool] = None
    auto_invoice: Optional[bool] = None
    auto_contract_number: Optional[bool] = None
    extra_config: Optional[dict] = None


class OrganizationResponse(BaseModel):
    id: UUID
    name: str
    legal_name: Optional[str]
    type: Optional[str]
    CIN: Optional[str]
    PAN: Optional[str]
    base_currency: str
    address_line1: Optional[str]
    address_line2: Optional[str]
    city: Optional[str]
    state: Optional[str]
    pincode: Optional[str]
    contact_email: Optional[str]
    contact_phone: Optional[str]
    is_active: bool
    threshold_limit: Optional[int]
    einvoice_required: bool
    auto_block_if_einvoice_required: bool
    fx_enabled: bool
    logo_url: Optional[str]
    theme_color: Optional[str]
    invoice_footer: Optional[str]
    digital_signature_url: Optional[str]
    tds_rate: Optional[int]
    tcs_rate: Optional[int]
    audit_firm_name: Optional[str]
    audit_firm_email: Optional[str]
    audit_firm_phone: Optional[str]
    gst_audit_required: bool
    auto_invoice: bool
    auto_contract_number: bool
    extra_config: dict
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


# GST Schemas
class OrganizationGSTCreate(BaseModel):
    organization_id: UUID
    gstin: str = Field(..., min_length=15, max_length=15)
    legal_name: Optional[str] = Field(None, max_length=255)
    address: Optional[str] = Field(None, max_length=255)
    state: Optional[str] = Field(None, max_length=128)
    branch_code: Optional[str] = Field(None, max_length=32)
    is_primary: bool = False

    @field_validator("gstin")
    @classmethod
    def validate_gstin(cls, v: str) -> str:
        if len(v) != 15:
            raise ValueError("GSTIN must be 15 characters")
        return v.upper()


class OrganizationGSTUpdate(BaseModel):
    legal_name: Optional[str] = Field(None, max_length=255)
    address: Optional[str] = Field(None, max_length=255)
    state: Optional[str] = Field(None, max_length=128)
    branch_code: Optional[str] = Field(None, max_length=32)
    is_primary: Optional[bool] = None
    is_active: Optional[bool] = None


class OrganizationGSTResponse(BaseModel):
    id: UUID
    organization_id: UUID
    gstin: str
    legal_name: Optional[str]
    address: Optional[str]
    state: Optional[str]
    branch_code: Optional[str]
    is_primary: bool
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


# Bank Account Schemas
class OrganizationBankAccountCreate(BaseModel):
    organization_id: UUID
    account_holder: str = Field(..., min_length=1, max_length=255)
    bank_name: str = Field(..., min_length=1, max_length=255)
    account_number: str = Field(..., min_length=1, max_length=64)
    ifsc: Optional[str] = Field(None, min_length=11, max_length=11)
    branch: Optional[str] = Field(None, max_length=255)
    is_default: bool = False

    @field_validator("ifsc")
    @classmethod
    def validate_ifsc(cls, v: Optional[str]) -> Optional[str]:
        if v and len(v) != 11:
            raise ValueError("IFSC must be 11 characters")
        return v.upper() if v else v


class OrganizationBankAccountUpdate(BaseModel):
    account_holder: Optional[str] = Field(None, min_length=1, max_length=255)
    bank_name: Optional[str] = Field(None, min_length=1, max_length=255)
    account_number: Optional[str] = Field(None, min_length=1, max_length=64)
    ifsc: Optional[str] = Field(None, min_length=11, max_length=11)
    branch: Optional[str] = Field(None, max_length=255)
    is_default: Optional[bool] = None


class OrganizationBankAccountResponse(BaseModel):
    id: UUID
    organization_id: UUID
    account_holder: str
    bank_name: str
    account_number: str
    ifsc: Optional[str]
    branch: Optional[str]
    is_default: bool
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


# Financial Year Schemas
class OrganizationFinancialYearCreate(BaseModel):
    organization_id: UUID
    start_date: date
    end_date: date
    is_active: bool = False
    allow_year_split: bool = False

    @field_validator("end_date")
    @classmethod
    def validate_dates(cls, v: date, info) -> date:
        if "start_date" in info.data and v <= info.data["start_date"]:
            raise ValueError("end_date must be after start_date")
        return v


class OrganizationFinancialYearUpdate(BaseModel):
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    is_active: Optional[bool] = None
    allow_year_split: Optional[bool] = None
    version: int = Field(..., description="Current version for optimistic locking")


class OrganizationFinancialYearResponse(BaseModel):
    id: UUID
    organization_id: UUID
    start_date: date
    end_date: date
    is_active: bool
    allow_year_split: bool
    version: int
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


# Document Series Schemas
class OrganizationDocumentSeriesCreate(BaseModel):
    organization_id: UUID
    financial_year_id: UUID
    document_type: str = Field(..., min_length=1, max_length=64)
    prefix: Optional[str] = Field(None, max_length=32)
    current_number: int = Field(default=1, ge=1)
    reset_annually: bool = True
    extra_config: dict = Field(default_factory=dict)


class OrganizationDocumentSeriesUpdate(BaseModel):
    prefix: Optional[str] = Field(None, max_length=32)
    current_number: Optional[int] = Field(None, ge=1)
    reset_annually: Optional[bool] = None
    is_active: Optional[bool] = None
    extra_config: Optional[dict] = None


class OrganizationDocumentSeriesResponse(BaseModel):
    id: UUID
    organization_id: UUID
    financial_year_id: UUID
    document_type: str
    prefix: Optional[str]
    current_number: int
    reset_annually: bool
    is_active: bool
    extra_config: dict
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class NextDocumentNumberResponse(BaseModel):
    document_number: str
    series_id: UUID
    next_number: int

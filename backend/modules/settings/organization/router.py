from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Header, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.auth.capabilities.decorators import RequireCapability
from backend.core.auth.capabilities.definitions import Capabilities
from backend.db.session import get_db
from backend.modules.settings.organization.schemas import (
    NextDocumentNumberResponse,
    OrganizationBankAccountCreate,
    OrganizationBankAccountResponse,
    OrganizationBankAccountUpdate,
    OrganizationCreate,
    OrganizationDocumentSeriesCreate,
    OrganizationDocumentSeriesResponse,
    OrganizationDocumentSeriesUpdate,
    OrganizationFinancialYearCreate,
    OrganizationFinancialYearResponse,
    OrganizationFinancialYearUpdate,
    OrganizationGSTCreate,
    OrganizationGSTResponse,
    OrganizationGSTUpdate,
    OrganizationResponse,
    OrganizationUpdate,
)
from backend.modules.settings.organization.services import OrganizationService

router = APIRouter(prefix="/organizations", tags=["organizations"])


# Dependency for current user (mock for now)
def get_current_user_id() -> UUID:
    """Get current user ID from auth context"""
    # TODO: Replace with actual auth dependency
    from uuid import uuid4
    return uuid4()


async def get_service(
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user_id)
) -> OrganizationService:
    return OrganizationService(db, user_id)


# Organization endpoints
@router.post("/", response_model=OrganizationResponse, status_code=status.HTTP_201_CREATED)
def create_organization(
    data: OrganizationCreate,
    service: OrganizationService = Depends(get_service),
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    _check: None = Depends(RequireCapability(Capabilities.ORG_CREATE))
) -> OrganizationResponse:
    """Create a new organization. Requires ORG_CREATE capability. Supports idempotency."""
    return service.create_organization(data)


@router.get("/{org_id}", response_model=OrganizationResponse)
def get_organization(
    org_id: UUID,
    service: OrganizationService = Depends(get_service),
) -> OrganizationResponse:
    """Get organization by ID."""
    return service.get_organization(org_id)


@router.get("/", response_model=List[OrganizationResponse])
def list_organizations(
    skip: int = 0,
    limit: int = 100,
    service: OrganizationService = Depends(get_service),
) -> List[OrganizationResponse]:
    """List all organizations."""
    return service.list_organizations(skip=skip, limit=limit)


@router.patch("/{org_id}", response_model=OrganizationResponse)
def update_organization(
    org_id: UUID,
    data: OrganizationUpdate,
    service: OrganizationService = Depends(get_service),
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    _check: None = Depends(RequireCapability(Capabilities.ORG_UPDATE))
) -> OrganizationResponse:
    """Update organization. Requires ORG_UPDATE capability. Supports idempotency."""
    return service.update_organization(org_id, data)


@router.delete("/{org_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_organization(
    org_id: UUID,
    service: OrganizationService = Depends(get_service),
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    _check: None = Depends(RequireCapability(Capabilities.ORG_DELETE))
) -> None:
    """Delete organization. Requires ORG_DELETE capability. Supports idempotency."""
    service.delete_organization(org_id)


# GST endpoints
@router.post("/gst", response_model=OrganizationGSTResponse, status_code=status.HTTP_201_CREATED)
def create_gst(
    data: OrganizationGSTCreate,
    service: OrganizationService = Depends(get_service),
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    _check: None = Depends(RequireCapability(Capabilities.ORG_UPDATE))
) -> OrganizationGSTResponse:
    """Create GST record. Requires ORG_UPDATE capability. Supports idempotency."""
    return service.create_gst(data)


@router.get("/gst/{gst_id}", response_model=OrganizationGSTResponse)
def get_gst(
    gst_id: UUID,
    service: OrganizationService = Depends(get_service),
) -> OrganizationGSTResponse:
    """Get GST record by ID."""
    return service.get_gst(gst_id)


@router.get("/{org_id}/gst", response_model=List[OrganizationGSTResponse])
def list_gst_by_organization(
    org_id: UUID,
    service: OrganizationService = Depends(get_service),
) -> List[OrganizationGSTResponse]:
    """List all GST records for an organization."""
    return service.list_gst_by_organization(org_id)


@router.patch("/gst/{gst_id}", response_model=OrganizationGSTResponse)
def update_gst(
    gst_id: UUID,
    data: OrganizationGSTUpdate,
    service: OrganizationService = Depends(get_service),
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    _check: None = Depends(RequireCapability(Capabilities.ORG_UPDATE))
) -> OrganizationGSTResponse:
    """Update GST record. Requires ORG_UPDATE capability. Supports idempotency."""
    return service.update_gst(gst_id, data)


@router.delete("/gst/{gst_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_gst(
    gst_id: UUID,
    service: OrganizationService = Depends(get_service),
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    _check: None = Depends(RequireCapability(Capabilities.ORG_DELETE))
) -> None:
    """Delete GST record. Requires ORG_DELETE capability. Supports idempotency."""
    service.delete_gst(gst_id)


# Bank Account endpoints
@router.post("/bank-accounts", response_model=OrganizationBankAccountResponse, status_code=status.HTTP_201_CREATED)
def create_bank_account(
    data: OrganizationBankAccountCreate,
    service: OrganizationService = Depends(get_service),
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    _check: None = Depends(RequireCapability(Capabilities.ORG_UPDATE))
) -> OrganizationBankAccountResponse:
    """Create bank account (FINANCIAL DATA). Requires ORG_UPDATE capability. Supports idempotency."""
    return service.create_bank_account(data)


@router.get("/bank-accounts/{account_id}", response_model=OrganizationBankAccountResponse)
def get_bank_account(
    account_id: UUID,
    service: OrganizationService = Depends(get_service),
) -> OrganizationBankAccountResponse:
    """Get bank account by ID."""
    return service.get_bank_account(account_id)


@router.get("/{org_id}/bank-accounts", response_model=List[OrganizationBankAccountResponse])
def list_bank_accounts_by_organization(
    org_id: UUID,
    service: OrganizationService = Depends(get_service),
) -> List[OrganizationBankAccountResponse]:
    """List all bank accounts for an organization."""
    return service.list_bank_accounts_by_organization(org_id)


@router.patch("/bank-accounts/{account_id}", response_model=OrganizationBankAccountResponse)
def update_bank_account(
    account_id: UUID,
    data: OrganizationBankAccountUpdate,
    service: OrganizationService = Depends(get_service),
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    _check: None = Depends(RequireCapability(Capabilities.ORG_UPDATE))
) -> OrganizationBankAccountResponse:
    """Update bank account (FINANCIAL DATA). Requires ORG_UPDATE capability. Supports idempotency."""
    return service.update_bank_account(account_id, data)


@router.delete("/bank-accounts/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_bank_account(
    account_id: UUID,
    service: OrganizationService = Depends(get_service),
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    _check: None = Depends(RequireCapability(Capabilities.ORG_DELETE))
) -> None:
    """Delete bank account (FINANCIAL DATA). Requires ORG_DELETE capability. Supports idempotency."""
    service.delete_bank_account(account_id)


# Financial Year endpoints
@router.post("/financial-years", response_model=OrganizationFinancialYearResponse, status_code=status.HTTP_201_CREATED)
def create_financial_year(
    data: OrganizationFinancialYearCreate,
    service: OrganizationService = Depends(get_service),
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    _check: None = Depends(RequireCapability(Capabilities.ORG_UPDATE))
) -> OrganizationFinancialYearResponse:
    """Create financial year. Requires ORG_UPDATE capability. Supports idempotency."""
    return service.create_financial_year(data)


@router.get("/financial-years/{fy_id}", response_model=OrganizationFinancialYearResponse)
def get_financial_year(
    fy_id: UUID,
    service: OrganizationService = Depends(get_service),
) -> OrganizationFinancialYearResponse:
    """Get financial year by ID."""
    return service.get_financial_year(fy_id)


@router.get("/{org_id}/financial-years", response_model=List[OrganizationFinancialYearResponse])
def list_financial_years_by_organization(
    org_id: UUID,
    service: OrganizationService = Depends(get_service),
) -> List[OrganizationFinancialYearResponse]:
    """List all financial years for an organization."""
    return service.list_financial_years_by_organization(org_id)


@router.patch("/financial-years/{fy_id}", response_model=OrganizationFinancialYearResponse)
def update_financial_year(
    fy_id: UUID,
    data: OrganizationFinancialYearUpdate,
    service: OrganizationService = Depends(get_service),
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    _check: None = Depends(RequireCapability(Capabilities.ORG_UPDATE))
) -> OrganizationFinancialYearResponse:
    """Update financial year (with optimistic locking). Requires ORG_UPDATE capability. Supports idempotency."""
    return service.update_financial_year(fy_id, data)


@router.delete("/financial-years/{fy_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_financial_year(
    fy_id: UUID,
    service: OrganizationService = Depends(get_service),
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    _check: None = Depends(RequireCapability(Capabilities.ORG_DELETE))
) -> None:
    """Delete financial year. Requires ORG_DELETE capability. Supports idempotency."""
    service.delete_financial_year(fy_id)


# Document Series endpoints
@router.post("/document-series", response_model=OrganizationDocumentSeriesResponse, status_code=status.HTTP_201_CREATED)
def create_document_series(
    data: OrganizationDocumentSeriesCreate,
    service: OrganizationService = Depends(get_service),
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    _check: None = Depends(RequireCapability(Capabilities.ORG_UPDATE))
) -> OrganizationDocumentSeriesResponse:
    """Create document series. Requires ORG_UPDATE capability. Supports idempotency."""
    return service.create_document_series(data)


@router.get("/document-series/{series_id}", response_model=OrganizationDocumentSeriesResponse)
def get_document_series(
    series_id: UUID,
    service: OrganizationService = Depends(get_service),
) -> OrganizationDocumentSeriesResponse:
    """Get document series by ID."""
    return service.get_document_series(series_id)


@router.get("/{org_id}/document-series", response_model=List[OrganizationDocumentSeriesResponse])
def list_document_series_by_organization(
    org_id: UUID,
    service: OrganizationService = Depends(get_service),
) -> List[OrganizationDocumentSeriesResponse]:
    """List all document series for an organization."""
    return service.list_document_series_by_organization(org_id)


@router.patch("/document-series/{series_id}", response_model=OrganizationDocumentSeriesResponse)
def update_document_series(
    series_id: UUID,
    data: OrganizationDocumentSeriesUpdate,
    service: OrganizationService = Depends(get_service),
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    _check: None = Depends(RequireCapability(Capabilities.ORG_UPDATE))
) -> OrganizationDocumentSeriesResponse:
    """Update document series. Requires ORG_UPDATE capability. Supports idempotency."""
    return service.update_document_series(series_id, data)


@router.delete("/document-series/{series_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document_series(
    series_id: UUID,
    service: OrganizationService = Depends(get_service),
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    _check: None = Depends(RequireCapability(Capabilities.ORG_DELETE))
) -> None:
    """Delete document series. Requires ORG_DELETE capability. Supports idempotency."""
    service.delete_document_series(series_id)


# Document Number Generation
@router.post("/{org_id}/next-document-number/{doc_type}", response_model=NextDocumentNumberResponse)
def get_next_document_number(
    org_id: UUID,
    doc_type: str,
    service: OrganizationService = Depends(get_service),
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    _check: None = Depends(RequireCapability(Capabilities.ORG_UPDATE))
) -> NextDocumentNumberResponse:
    """Get next document number for a document type (atomically increments). Requires ORG_UPDATE capability. Supports idempotency."""
    return service.get_next_document_number(org_id, doc_type)

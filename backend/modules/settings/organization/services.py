from __future__ import annotations

from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from backend.core.errors.exceptions import BadRequestException, NotFoundException
from backend.modules.settings.organization.models import (
    Organization,
    OrganizationBankAccount,
    OrganizationDocumentSeries,
    OrganizationFinancialYear,
    OrganizationGST,
)
from backend.modules.settings.organization.repositories import (
    OrganizationBankAccountRepository,
    OrganizationDocumentSeriesRepository,
    OrganizationFinancialYearRepository,
    OrganizationGSTRepository,
    OrganizationRepository,
)
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


class OrganizationService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = OrganizationRepository(db)
        self.gst_repo = OrganizationGSTRepository(db)
        self.bank_repo = OrganizationBankAccountRepository(db)
        self.fy_repo = OrganizationFinancialYearRepository(db)
        self.series_repo = OrganizationDocumentSeriesRepository(db)

    # Organization CRUD
    def create_organization(self, data: OrganizationCreate) -> OrganizationResponse:
        # Check if name already exists
        existing = self.repo.get_by_name(data.name)
        if existing:
            raise BadRequestException(f"Organization with name '{data.name}' already exists")
        
        org = self.repo.create(**data.model_dump())
        self.db.commit()
        return OrganizationResponse.model_validate(org)

    def get_organization(self, org_id: UUID) -> OrganizationResponse:
        org = self.repo.get_by_id(org_id)
        if not org:
            raise NotFoundException(f"Organization {org_id} not found")
        return OrganizationResponse.model_validate(org)

    def list_organizations(self, skip: int = 0, limit: int = 100) -> list[OrganizationResponse]:
        orgs = self.repo.list_all(skip=skip, limit=limit)
        return [OrganizationResponse.model_validate(o) for o in orgs]

    def update_organization(self, org_id: UUID, data: OrganizationUpdate) -> OrganizationResponse:
        update_data = data.model_dump(exclude_unset=True)
        org = self.repo.update(org_id, **update_data)
        if not org:
            raise NotFoundException(f"Organization {org_id} not found")
        self.db.commit()
        return OrganizationResponse.model_validate(org)

    def delete_organization(self, org_id: UUID) -> bool:
        success = self.repo.delete(org_id)
        if not success:
            raise NotFoundException(f"Organization {org_id} not found")
        self.db.commit()
        return True

    # GST CRUD
    def create_gst(self, data: OrganizationGSTCreate) -> OrganizationGSTResponse:
        # Check GSTIN uniqueness
        existing = self.gst_repo.get_by_gstin(data.gstin)
        if existing:
            raise BadRequestException(f"GSTIN '{data.gstin}' already exists")
        
        # If setting as primary, unset other primary GSTs
        if data.is_primary:
            primary = self.gst_repo.get_primary(data.organization_id)
            if primary:
                self.gst_repo.update(primary.id, is_primary=False)
        
        gst = self.gst_repo.create(**data.model_dump())
        self.db.commit()
        return OrganizationGSTResponse.model_validate(gst)

    def get_gst(self, gst_id: UUID) -> OrganizationGSTResponse:
        gst = self.gst_repo.get_by_id(gst_id)
        if not gst:
            raise NotFoundException(f"GST record {gst_id} not found")
        return OrganizationGSTResponse.model_validate(gst)

    def list_gst_by_organization(self, org_id: UUID) -> list[OrganizationGSTResponse]:
        gsts = self.gst_repo.list_by_organization(org_id)
        return [OrganizationGSTResponse.model_validate(g) for g in gsts]

    def update_gst(self, gst_id: UUID, data: OrganizationGSTUpdate) -> OrganizationGSTResponse:
        gst = self.gst_repo.get_by_id(gst_id)
        if not gst:
            raise NotFoundException(f"GST record {gst_id} not found")
        
        # If setting as primary, unset other primary GSTs
        if data.is_primary:
            primary = self.gst_repo.get_primary(gst.organization_id)
            if primary and primary.id != gst_id:
                self.gst_repo.update(primary.id, is_primary=False)
        
        update_data = data.model_dump(exclude_unset=True)
        gst = self.gst_repo.update(gst_id, **update_data)
        self.db.commit()
        return OrganizationGSTResponse.model_validate(gst)

    def delete_gst(self, gst_id: UUID) -> bool:
        success = self.gst_repo.delete(gst_id)
        if not success:
            raise NotFoundException(f"GST record {gst_id} not found")
        self.db.commit()
        return True

    # Bank Account CRUD
    def create_bank_account(self, data: OrganizationBankAccountCreate) -> OrganizationBankAccountResponse:
        # If setting as default, unset other defaults
        if data.is_default:
            default = self.bank_repo.get_default(data.organization_id)
            if default:
                self.bank_repo.update(default.id, is_default=False)
        
        account = self.bank_repo.create(**data.model_dump())
        self.db.commit()
        return OrganizationBankAccountResponse.model_validate(account)

    def get_bank_account(self, account_id: UUID) -> OrganizationBankAccountResponse:
        account = self.bank_repo.get_by_id(account_id)
        if not account:
            raise NotFoundException(f"Bank account {account_id} not found")
        return OrganizationBankAccountResponse.model_validate(account)

    def list_bank_accounts_by_organization(self, org_id: UUID) -> list[OrganizationBankAccountResponse]:
        accounts = self.bank_repo.list_by_organization(org_id)
        return [OrganizationBankAccountResponse.model_validate(a) for a in accounts]

    def update_bank_account(
        self, account_id: UUID, data: OrganizationBankAccountUpdate
    ) -> OrganizationBankAccountResponse:
        account = self.bank_repo.get_by_id(account_id)
        if not account:
            raise NotFoundException(f"Bank account {account_id} not found")
        
        # If setting as default, unset other defaults
        if data.is_default:
            default = self.bank_repo.get_default(account.organization_id)
            if default and default.id != account_id:
                self.bank_repo.update(default.id, is_default=False)
        
        update_data = data.model_dump(exclude_unset=True)
        account = self.bank_repo.update(account_id, **update_data)
        self.db.commit()
        return OrganizationBankAccountResponse.model_validate(account)

    def delete_bank_account(self, account_id: UUID) -> bool:
        success = self.bank_repo.delete(account_id)
        if not success:
            raise NotFoundException(f"Bank account {account_id} not found")
        self.db.commit()
        return True

    # Financial Year CRUD
    def create_financial_year(self, data: OrganizationFinancialYearCreate) -> OrganizationFinancialYearResponse:
        # If setting as active, unset other active FYs
        if data.is_active:
            active = self.fy_repo.get_active(data.organization_id)
            if active:
                self.fy_repo.update(active.id, is_active=False, version=active.version)
        
        fy = self.fy_repo.create(**data.model_dump())
        self.db.commit()
        return OrganizationFinancialYearResponse.model_validate(fy)

    def get_financial_year(self, fy_id: UUID) -> OrganizationFinancialYearResponse:
        fy = self.fy_repo.get_by_id(fy_id)
        if not fy:
            raise NotFoundException(f"Financial year {fy_id} not found")
        return OrganizationFinancialYearResponse.model_validate(fy)

    def list_financial_years_by_organization(self, org_id: UUID) -> list[OrganizationFinancialYearResponse]:
        fys = self.fy_repo.list_by_organization(org_id)
        return [OrganizationFinancialYearResponse.model_validate(f) for f in fys]

    def update_financial_year(
        self, fy_id: UUID, data: OrganizationFinancialYearUpdate
    ) -> OrganizationFinancialYearResponse:
        fy = self.fy_repo.get_by_id(fy_id)
        if not fy:
            raise NotFoundException(f"Financial year {fy_id} not found")
        
        # If setting as active, unset other active FYs
        if data.is_active:
            active = self.fy_repo.get_active(fy.organization_id)
            if active and active.id != fy_id:
                self.fy_repo.update(active.id, is_active=False, version=active.version)
        
        try:
            update_data = data.model_dump(exclude_unset=True)
            fy = self.fy_repo.update(fy_id, **update_data)
            self.db.commit()
            return OrganizationFinancialYearResponse.model_validate(fy)
        except ValueError as e:
            raise BadRequestException(str(e))

    def delete_financial_year(self, fy_id: UUID) -> bool:
        success = self.fy_repo.delete(fy_id)
        if not success:
            raise NotFoundException(f"Financial year {fy_id} not found")
        self.db.commit()
        return True

    # Document Series CRUD
    def create_document_series(
        self, data: OrganizationDocumentSeriesCreate
    ) -> OrganizationDocumentSeriesResponse:
        # Check uniqueness: org + doc_type + FY
        existing = self.series_repo.get_by_type(
            data.organization_id, data.financial_year_id, data.document_type
        )
        if existing:
            raise BadRequestException(
                f"Document series for '{data.document_type}' already exists for this FY"
            )
        
        series = self.series_repo.create(**data.model_dump())
        self.db.commit()
        return OrganizationDocumentSeriesResponse.model_validate(series)

    def get_document_series(self, series_id: UUID) -> OrganizationDocumentSeriesResponse:
        series = self.series_repo.get_by_id(series_id)
        if not series:
            raise NotFoundException(f"Document series {series_id} not found")
        return OrganizationDocumentSeriesResponse.model_validate(series)

    def list_document_series_by_organization(self, org_id: UUID) -> list[OrganizationDocumentSeriesResponse]:
        series_list = self.series_repo.list_by_organization(org_id)
        return [OrganizationDocumentSeriesResponse.model_validate(s) for s in series_list]

    def update_document_series(
        self, series_id: UUID, data: OrganizationDocumentSeriesUpdate
    ) -> OrganizationDocumentSeriesResponse:
        update_data = data.model_dump(exclude_unset=True)
        series = self.series_repo.update(series_id, **update_data)
        if not series:
            raise NotFoundException(f"Document series {series_id} not found")
        self.db.commit()
        return OrganizationDocumentSeriesResponse.model_validate(series)

    def delete_document_series(self, series_id: UUID) -> bool:
        success = self.series_repo.delete(series_id)
        if not success:
            raise NotFoundException(f"Document series {series_id} not found")
        self.db.commit()
        return True

    def get_next_document_number(
        self, org_id: UUID, doc_type: str
    ) -> NextDocumentNumberResponse:
        # Get active financial year
        fy = self.fy_repo.get_active(org_id)
        if not fy:
            raise NotFoundException("No active financial year found")
        
        # Get document series
        series = self.series_repo.get_by_type(org_id, fy.id, doc_type)
        if not series:
            raise NotFoundException(f"No document series found for '{doc_type}'")
        
        # Atomically increment
        series = self.series_repo.increment_number(series.id)
        self.db.commit()
        
        # Generate document number
        prefix = series.prefix or ""
        doc_number = f"{prefix}{series.current_number:06d}"
        
        return NextDocumentNumberResponse(
            document_number=doc_number,
            series_id=series.id,
            next_number=series.current_number,
        )

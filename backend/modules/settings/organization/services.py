from __future__ import annotations

from typing import Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.errors.exceptions import BadRequestException, NotFoundException
from backend.core.events.emitter import EventEmitter
from backend.modules.settings.organization.events import (
    OrganizationBankAccountAdded,
    OrganizationBankAccountUpdated,
    OrganizationCreated,
    OrganizationDeleted,
    OrganizationDocumentSeriesAdded,
    OrganizationFinancialYearAdded,
    OrganizationGSTAdded,
    OrganizationGSTUpdated,
    OrganizationUpdated,
)
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
    def __init__(self, db: AsyncSession, current_user_id: UUID):
        self.db = db
        self.current_user_id = current_user_id
        self.repo = OrganizationRepository(db)
        self.gst_repo = OrganizationGSTRepository(db)
        self.bank_repo = OrganizationBankAccountRepository(db)
        self.fy_repo = OrganizationFinancialYearRepository(db)
        self.series_repo = OrganizationDocumentSeriesRepository(db)
        self.events = EventEmitter(db)

    # Organization CRUD
    async def create_organization(self, data: OrganizationCreate) -> OrganizationResponse:
        # Check if name already exists
        existing = await self.repo.get_by_name(data.name)
        if existing:
            raise BadRequestException(f"Organization with name '{data.name}' already exists")
        
        org = await self.repo.create(**data.model_dump())
        await self.db.flush()
        
        # Emit event
        await self.events.emit(
            OrganizationCreated(
                aggregate_id=org.id,
                user_id=self.current_user_id,
                data={
                    "name": org.name,
                    "type": org.type if org.type else None,
                    "contact_email": org.contact_email,
                    "contact_phone": org.contact_phone,
                },
            )
        )
        
        await self.db.commit()
        return OrganizationResponse.model_validate(org)

    async def get_organization(self, org_id: UUID) -> OrganizationResponse:
        org = await self.repo.get_by_id(org_id)
        if not org:
            raise NotFoundException(f"Organization {org_id} not found")
        return OrganizationResponse.model_validate(org)

    async def list_organizations(self, skip: int = 0, limit: int = 100) -> list[OrganizationResponse]:
        orgs = await self.repo.list_all(skip=skip, limit=limit)
        return [OrganizationResponse.model_validate(o) for o in orgs]

    async def update_organization(self, org_id: UUID, data: OrganizationUpdate) -> OrganizationResponse:
        old_org = await self.repo.get_by_id(org_id)
        if not old_org:
            raise NotFoundException(f"Organization {org_id} not found")
        
        update_data = data.model_dump(exclude_unset=True)
        org = await self.repo.update(org_id, **update_data)
        await self.db.flush()
        
        # Emit event with changes
        changes = {}
        for key, new_value in update_data.items():
            old_value = getattr(old_org, key, None)
            if old_value != new_value:
                changes[key] = {"old": old_value, "new": new_value}
        
        if changes:
            await self.events.emit(
                OrganizationUpdated(
                    aggregate_id=org.id,
                    user_id=self.current_user_id,
                    data={"changes": changes},
                )
            )
        
        await self.db.commit()
        return OrganizationResponse.model_validate(org)

    async def delete_organization(self, org_id: UUID) -> bool:
        org = await self.repo.get_by_id(org_id)
        if not org:
            raise NotFoundException(f"Organization {org_id} not found")
        
        success = await self.repo.delete(org_id)
        await self.db.flush()
        
        # Emit event
        await self.events.emit(
            OrganizationDeleted(
                aggregate_id=org_id,
                user_id=self.current_user_id,
                data={"name": org.name},
            )
        )
        
        await self.db.commit()
        return True

    # GST CRUD
    async def create_gst(self, data: OrganizationGSTCreate) -> OrganizationGSTResponse:
        # Check GSTIN uniqueness
        existing = await self.gst_repo.get_by_gstin(data.gstin)
        if existing:
            raise BadRequestException(f"GSTIN '{data.gstin}' already exists")
        
        # If setting as primary, unset other primary GSTs
        if data.is_primary:
            primary = await self.gst_repo.get_primary(data.organization_id)
            if primary:
                await self.gst_repo.update(primary.id, is_primary=False)
        
        gst = await self.gst_repo.create(**data.model_dump())
        await self.db.flush()
        
        # Emit event
        await self.events.emit(
            OrganizationGSTAdded(
                aggregate_id=gst.organization_id,
                user_id=self.current_user_id,
                data={
                    "gst_id": str(gst.id),
                    "gstin": gst.gstin,
                    "state": gst.state,
                    "is_primary": gst.is_primary,
                },
            )
        )
        
        await self.db.commit()
        return OrganizationGSTResponse.model_validate(gst)

    async def get_gst(self, gst_id: UUID) -> OrganizationGSTResponse:
        gst = await self.gst_repo.get_by_id(gst_id)
        if not gst:
            raise NotFoundException(f"GST record {gst_id} not found")
        return OrganizationGSTResponse.model_validate(gst)

    async def list_gst_by_organization(self, org_id: UUID) -> list[OrganizationGSTResponse]:
        gsts = await self.gst_repo.list_by_organization(org_id)
        return [OrganizationGSTResponse.model_validate(g) for g in gsts]

    async def update_gst(self, gst_id: UUID, data: OrganizationGSTUpdate) -> OrganizationGSTResponse:
        gst = await self.gst_repo.get_by_id(gst_id)
        if not gst:
            raise NotFoundException(f"GST record {gst_id} not found")
        
        # If setting as primary, unset other primary GSTs
        if data.is_primary:
            primary = await self.gst_repo.get_primary(gst.organization_id)
            if primary and primary.id != gst_id:
                await self.gst_repo.update(primary.id, is_primary=False)
        
        update_data = data.model_dump(exclude_unset=True)
        gst = await self.gst_repo.update(gst_id, **update_data)
        await self.db.flush()
        
        # Emit event
        await self.events.emit(
            OrganizationGSTUpdated(
                aggregate_id=gst.organization_id,
                user_id=self.current_user_id,
                data={"gst_id": str(gst_id), "changes": update_data},
            )
        )
        
        await self.db.commit()
        return OrganizationGSTResponse.model_validate(gst)

    async def delete_gst(self, gst_id: UUID) -> bool:
        success = await self.gst_repo.delete(gst_id)
        if not success:
            raise NotFoundException(f"GST record {gst_id} not found")
        await self.db.commit()
        return True

    # Bank Account CRUD
    async def create_bank_account(self, data: OrganizationBankAccountCreate) -> OrganizationBankAccountResponse:
        # If setting as default, unset other defaults
        if data.is_default:
            default = await self.bank_repo.get_default(data.organization_id)
            if default:
                await self.bank_repo.update(default.id, is_default=False)
        
        account = await self.bank_repo.create(**data.model_dump())
        await self.db.flush()
        
        # Emit event
        await self.events.emit(
            OrganizationBankAccountAdded(
                aggregate_id=account.organization_id,
                user_id=self.current_user_id,
                data={
                    "account_id": str(account.id),
                    "bank_name": account.bank_name,
                    "account_number": account.account_number,
                    "is_default": account.is_default,
                },
            )
        )
        
        await self.db.commit()
        return OrganizationBankAccountResponse.model_validate(account)

    async def get_bank_account(self, account_id: UUID) -> OrganizationBankAccountResponse:
        account = await self.bank_repo.get_by_id(account_id)
        if not account:
            raise NotFoundException(f"Bank account {account_id} not found")
        return OrganizationBankAccountResponse.model_validate(account)

    async def list_bank_accounts_by_organization(self, org_id: UUID) -> list[OrganizationBankAccountResponse]:
        accounts = await self.bank_repo.list_by_organization(org_id)
        return [OrganizationBankAccountResponse.model_validate(a) for a in accounts]

    async def update_bank_account(
        self, account_id: UUID, data: OrganizationBankAccountUpdate
    ) -> OrganizationBankAccountResponse:
        account = await self.bank_repo.get_by_id(account_id)
        if not account:
            raise NotFoundException(f"Bank account {account_id} not found")
        
        # If setting as default, unset other defaults
        if data.is_default:
            default = await self.bank_repo.get_default(account.organization_id)
            if default and default.id != account_id:
                await self.bank_repo.update(default.id, is_default=False)
        
        update_data = data.model_dump(exclude_unset=True)
        account = await self.bank_repo.update(account_id, **update_data)
        await self.db.flush()
        
        # Emit event
        await self.events.emit(
            OrganizationBankAccountUpdated(
                aggregate_id=account.organization_id,
                user_id=self.current_user_id,
                data={"account_id": str(account_id), "changes": update_data},
            )
        )
        
        await self.db.commit()
        return OrganizationBankAccountResponse.model_validate(account)

    async def delete_bank_account(self, account_id: UUID) -> bool:
        success = await self.bank_repo.delete(account_id)
        if not success:
            raise NotFoundException(f"Bank account {account_id} not found")
        await self.db.commit()
        return True

    # Financial Year CRUD
    async def create_financial_year(self, data: OrganizationFinancialYearCreate) -> OrganizationFinancialYearResponse:
        # If setting as active, unset other active FYs
        if data.is_active:
            active = await self.fy_repo.get_active(data.organization_id)
            if active:
                await self.fy_repo.update(active.id, is_active=False, version=active.version)
        
        fy = await self.fy_repo.create(**data.model_dump())
        await self.db.flush()
        
        # Emit event
        await self.events.emit(
            OrganizationFinancialYearAdded(
                aggregate_id=fy.organization_id,
                user_id=self.current_user_id,
                data={
                    "fy_id": str(fy.id),
                    "start_date": fy.start_date.isoformat(),
                    "end_date": fy.end_date.isoformat(),
                    "is_active": fy.is_active,
                },
            )
        )
        
        await self.db.commit()
        return OrganizationFinancialYearResponse.model_validate(fy)

    async def get_financial_year(self, fy_id: UUID) -> OrganizationFinancialYearResponse:
        fy = await self.fy_repo.get_by_id(fy_id)
        if not fy:
            raise NotFoundException(f"Financial year {fy_id} not found")
        return OrganizationFinancialYearResponse.model_validate(fy)

    async def list_financial_years_by_organization(self, org_id: UUID) -> list[OrganizationFinancialYearResponse]:
        fys = await self.fy_repo.list_by_organization(org_id)
        return [OrganizationFinancialYearResponse.model_validate(f) for f in fys]

    async def update_financial_year(
        self, fy_id: UUID, data: OrganizationFinancialYearUpdate
    ) -> OrganizationFinancialYearResponse:
        fy = await self.fy_repo.get_by_id(fy_id)
        if not fy:
            raise NotFoundException(f"Financial year {fy_id} not found")
        
        # If setting as active, unset other active FYs
        if data.is_active:
            active = await self.fy_repo.get_active(fy.organization_id)
            if active and active.id != fy_id:
                await self.fy_repo.update(active.id, is_active=False, version=active.version)
        
        try:
            update_data = data.model_dump(exclude_unset=True)
            fy = await self.fy_repo.update(fy_id, **update_data)
            await self.db.commit()
            return OrganizationFinancialYearResponse.model_validate(fy)
        except ValueError as e:
            raise BadRequestException(str(e))

    async def delete_financial_year(self, fy_id: UUID) -> bool:
        success = await self.fy_repo.delete(fy_id)
        if not success:
            raise NotFoundException(f"Financial year {fy_id} not found")
        await self.db.commit()
        return True

    # Document Series CRUD
    async def create_document_series(
        self, data: OrganizationDocumentSeriesCreate
    ) -> OrganizationDocumentSeriesResponse:
        # Check uniqueness: org + doc_type + FY
        existing = await self.series_repo.get_by_type(
            data.organization_id, data.financial_year_id, data.document_type
        )
        if existing:
            raise BadRequestException(
                f"Document series for '{data.document_type}' already exists for this FY"
            )
        
        series = await self.series_repo.create(**data.model_dump())
        await self.db.flush()
        
        # Emit event
        await self.events.emit(
            OrganizationDocumentSeriesAdded(
                aggregate_id=series.organization_id,
                user_id=self.current_user_id,
                data={
                    "series_id": str(series.id),
                    "document_type": series.document_type,
                    "prefix": series.prefix,
                    "current_number": series.current_number,
                },
            )
        )
        
        await self.db.commit()
        return OrganizationDocumentSeriesResponse.model_validate(series)

    async def get_document_series(self, series_id: UUID) -> OrganizationDocumentSeriesResponse:
        series = await self.series_repo.get_by_id(series_id)
        if not series:
            raise NotFoundException(f"Document series {series_id} not found")
        return OrganizationDocumentSeriesResponse.model_validate(series)

    async def list_document_series_by_organization(self, org_id: UUID) -> list[OrganizationDocumentSeriesResponse]:
        series_list = await self.series_repo.list_by_organization(org_id)
        return [OrganizationDocumentSeriesResponse.model_validate(s) for s in series_list]

    async def update_document_series(
        self, series_id: UUID, data: OrganizationDocumentSeriesUpdate
    ) -> OrganizationDocumentSeriesResponse:
        update_data = data.model_dump(exclude_unset=True)
        series = await self.series_repo.update(series_id, **update_data)
        if not series:
            raise NotFoundException(f"Document series {series_id} not found")
        await self.db.commit()
        return OrganizationDocumentSeriesResponse.model_validate(series)

    async def delete_document_series(self, series_id: UUID) -> bool:
        success = await self.series_repo.delete(series_id)
        if not success:
            raise NotFoundException(f"Document series {series_id} not found")
        await self.db.commit()
        return True

    async def get_next_document_number(
        self, org_id: UUID, doc_type: str
    ) -> NextDocumentNumberResponse:
        # Get active financial year
        fy = await self.fy_repo.get_active(org_id)
        if not fy:
            raise NotFoundException("No active financial year found")
        
        # Get document series
        series = await self.series_repo.get_by_type(org_id, fy.id, doc_type)
        if not series:
            raise NotFoundException(f"No document series found for '{doc_type}'")
        
        # Atomically increment
        series = await self.series_repo.increment_number(series.id)
        await self.db.commit()
        
        # Generate document number
        prefix = series.prefix or ""
        doc_number = f"{prefix}{series.current_number:06d}"
        
        return NextDocumentNumberResponse(
            document_number=doc_number,
            series_id=series.id,
            next_number=series.current_number,
        )

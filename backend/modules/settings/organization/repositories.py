from __future__ import annotations

from typing import Optional
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from backend.modules.settings.organization.models import (
    Organization,
    OrganizationBankAccount,
    OrganizationDocumentSeries,
    OrganizationFinancialYear,
    OrganizationGST,
)


class OrganizationRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, **kwargs) -> Organization:
        org = Organization(**kwargs)
        self.db.add(org)
        self.db.flush()
        self.db.refresh(org)
        return org

    def get_by_id(self, org_id: UUID) -> Optional[Organization]:
        return self.db.query(Organization).filter(Organization.id == org_id).first()

    def get_by_name(self, name: str) -> Optional[Organization]:
        return self.db.query(Organization).filter(Organization.name == name).first()

    def list_all(self, skip: int = 0, limit: int = 100) -> list[Organization]:
        return self.db.query(Organization).offset(skip).limit(limit).all()

    def update(self, org_id: UUID, **kwargs) -> Optional[Organization]:
        org = self.get_by_id(org_id)
        if not org:
            return None
        for key, value in kwargs.items():
            if value is not None:
                setattr(org, key, value)
        self.db.flush()
        self.db.refresh(org)
        return org

    def delete(self, org_id: UUID) -> bool:
        org = self.get_by_id(org_id)
        if not org:
            return False
        self.db.delete(org)
        self.db.flush()
        return True


class OrganizationGSTRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, **kwargs) -> OrganizationGST:
        gst = OrganizationGST(**kwargs)
        self.db.add(gst)
        self.db.flush()
        self.db.refresh(gst)
        return gst

    def get_by_id(self, gst_id: UUID) -> Optional[OrganizationGST]:
        return self.db.query(OrganizationGST).filter(OrganizationGST.id == gst_id).first()

    def get_by_gstin(self, gstin: str) -> Optional[OrganizationGST]:
        return self.db.query(OrganizationGST).filter(OrganizationGST.gstin == gstin).first()

    def get_primary(self, org_id: UUID) -> Optional[OrganizationGST]:
        return (
            self.db.query(OrganizationGST)
            .filter(
                and_(
                    OrganizationGST.organization_id == org_id,
                    OrganizationGST.is_primary == True,
                    OrganizationGST.is_active == True,
                )
            )
            .first()
        )

    def list_by_organization(self, org_id: UUID) -> list[OrganizationGST]:
        return (
            self.db.query(OrganizationGST)
            .filter(OrganizationGST.organization_id == org_id)
            .all()
        )

    def update(self, gst_id: UUID, **kwargs) -> Optional[OrganizationGST]:
        gst = self.get_by_id(gst_id)
        if not gst:
            return None
        for key, value in kwargs.items():
            if value is not None:
                setattr(gst, key, value)
        self.db.flush()
        self.db.refresh(gst)
        return gst

    def delete(self, gst_id: UUID) -> bool:
        gst = self.get_by_id(gst_id)
        if not gst:
            return False
        self.db.delete(gst)
        self.db.flush()
        return True


class OrganizationBankAccountRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, **kwargs) -> OrganizationBankAccount:
        account = OrganizationBankAccount(**kwargs)
        self.db.add(account)
        self.db.flush()
        self.db.refresh(account)
        return account

    def get_by_id(self, account_id: UUID) -> Optional[OrganizationBankAccount]:
        return (
            self.db.query(OrganizationBankAccount)
            .filter(OrganizationBankAccount.id == account_id)
            .first()
        )

    def get_default(self, org_id: UUID) -> Optional[OrganizationBankAccount]:
        return (
            self.db.query(OrganizationBankAccount)
            .filter(
                and_(
                    OrganizationBankAccount.organization_id == org_id,
                    OrganizationBankAccount.is_default == True,
                )
            )
            .first()
        )

    def list_by_organization(self, org_id: UUID) -> list[OrganizationBankAccount]:
        return (
            self.db.query(OrganizationBankAccount)
            .filter(OrganizationBankAccount.organization_id == org_id)
            .all()
        )

    def update(self, account_id: UUID, **kwargs) -> Optional[OrganizationBankAccount]:
        account = self.get_by_id(account_id)
        if not account:
            return None
        for key, value in kwargs.items():
            if value is not None:
                setattr(account, key, value)
        self.db.flush()
        self.db.refresh(account)
        return account

    def delete(self, account_id: UUID) -> bool:
        account = self.get_by_id(account_id)
        if not account:
            return False
        self.db.delete(account)
        self.db.flush()
        return True


class OrganizationFinancialYearRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, **kwargs) -> OrganizationFinancialYear:
        fy = OrganizationFinancialYear(**kwargs)
        self.db.add(fy)
        self.db.flush()
        self.db.refresh(fy)
        return fy

    def get_by_id(self, fy_id: UUID) -> Optional[OrganizationFinancialYear]:
        return (
            self.db.query(OrganizationFinancialYear)
            .filter(OrganizationFinancialYear.id == fy_id)
            .first()
        )

    def get_active(self, org_id: UUID) -> Optional[OrganizationFinancialYear]:
        return (
            self.db.query(OrganizationFinancialYear)
            .filter(
                and_(
                    OrganizationFinancialYear.organization_id == org_id,
                    OrganizationFinancialYear.is_active == True,
                )
            )
            .first()
        )

    def list_by_organization(self, org_id: UUID) -> list[OrganizationFinancialYear]:
        return (
            self.db.query(OrganizationFinancialYear)
            .filter(OrganizationFinancialYear.organization_id == org_id)
            .order_by(OrganizationFinancialYear.start_date.desc())
            .all()
        )

    def update(self, fy_id: UUID, **kwargs) -> Optional[OrganizationFinancialYear]:
        fy = self.get_by_id(fy_id)
        if not fy:
            return None
        
        # Check version for optimistic locking
        if "version" in kwargs:
            expected_version = kwargs.pop("version")
            if fy.version != expected_version:
                raise ValueError(f"Version conflict: expected {expected_version}, found {fy.version}")
            fy.version += 1
        
        for key, value in kwargs.items():
            if value is not None:
                setattr(fy, key, value)
        self.db.flush()
        self.db.refresh(fy)
        return fy

    def delete(self, fy_id: UUID) -> bool:
        fy = self.get_by_id(fy_id)
        if not fy:
            return False
        self.db.delete(fy)
        self.db.flush()
        return True


class OrganizationDocumentSeriesRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, **kwargs) -> OrganizationDocumentSeries:
        series = OrganizationDocumentSeries(**kwargs)
        self.db.add(series)
        self.db.flush()
        self.db.refresh(series)
        return series

    def get_by_id(self, series_id: UUID) -> Optional[OrganizationDocumentSeries]:
        return (
            self.db.query(OrganizationDocumentSeries)
            .filter(OrganizationDocumentSeries.id == series_id)
            .first()
        )

    def get_by_type(
        self, org_id: UUID, fy_id: UUID, doc_type: str
    ) -> Optional[OrganizationDocumentSeries]:
        return (
            self.db.query(OrganizationDocumentSeries)
            .filter(
                and_(
                    OrganizationDocumentSeries.organization_id == org_id,
                    OrganizationDocumentSeries.financial_year_id == fy_id,
                    OrganizationDocumentSeries.document_type == doc_type,
                    OrganizationDocumentSeries.is_active == True,
                )
            )
            .first()
        )

    def list_by_organization(self, org_id: UUID) -> list[OrganizationDocumentSeries]:
        return (
            self.db.query(OrganizationDocumentSeries)
            .filter(OrganizationDocumentSeries.organization_id == org_id)
            .all()
        )

    def list_by_financial_year(self, fy_id: UUID) -> list[OrganizationDocumentSeries]:
        return (
            self.db.query(OrganizationDocumentSeries)
            .filter(OrganizationDocumentSeries.financial_year_id == fy_id)
            .all()
        )

    def increment_number(self, series_id: UUID) -> Optional[OrganizationDocumentSeries]:
        """Atomically increment document number and return updated series."""
        series = self.get_by_id(series_id)
        if not series:
            return None
        series.current_number += 1
        self.db.flush()
        self.db.refresh(series)
        return series

    def update(self, series_id: UUID, **kwargs) -> Optional[OrganizationDocumentSeries]:
        series = self.get_by_id(series_id)
        if not series:
            return None
        for key, value in kwargs.items():
            if value is not None:
                setattr(series, key, value)
        self.db.flush()
        self.db.refresh(series)
        return series

    def delete(self, series_id: UUID) -> bool:
        series = self.get_by_id(series_id)
        if not series:
            return False
        self.db.delete(series)
        self.db.flush()
        return True

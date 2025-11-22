from __future__ import annotations

from enum import Enum


class PermissionCodes(str, Enum):
    # Organization & User Management
    ORG_CREATE = "org.create"
    ORG_READ = "org.read"
    USER_CREATE = "user.create"
    USER_READ = "user.read"
    ROLE_CREATE = "role.create"
    ROLE_ASSIGN_PERMS = "role.assign_permissions"
    
    # === Data Isolation & Security (Phase 1) ===
    
    # Settings Management (Super Admin Only)
    SETTINGS_VIEW_ALL = "settings.view.all"
    SETTINGS_MANAGE_ORGANIZATIONS = "settings.organizations.manage"
    SETTINGS_MANAGE_COMMODITIES = "settings.commodities.manage"
    SETTINGS_MANAGE_LOCATIONS = "settings.locations.manage"
    
    # Business Partner Management (Internal Users)
    BP_VIEW_ALL = "business_partners.view.all"
    BP_CREATE = "business_partners.create"
    BP_UPDATE = "business_partners.update"
    BP_DELETE = "business_partners.delete"
    BP_VERIFY_KYC = "business_partners.kyc.verify"
    
    # Cross-Branch Operations (Back-Office)
    INVOICE_CREATE_ANY_BRANCH = "invoices.create.any_branch"
    INVOICE_VIEW_ALL_BRANCHES = "invoices.view.all_branches"
    
    # External User Permissions
    CONTRACT_VIEW_OWN = "contracts.view.own"
    INVOICE_VIEW_OWN = "invoices.view.own"
    PAYMENT_VIEW_OWN = "payments.view.own"
    SHIPMENT_VIEW_OWN = "shipments.view.own"
    
    # GDPR Compliance
    DATA_EXPORT_OWN = "data.export.own"
    DATA_DELETE_OWN = "data.delete.own"
    DATA_EXPORT_ALL = "data.export.all"  # Super Admin only
    DATA_DELETE_ALL = "data.delete.all"  # Super Admin only
    
    # Audit & Compliance (Super Admin Only)
    AUDIT_VIEW_ALL = "audit.view.all"
    AUDIT_EXPORT = "audit.export"

    @classmethod
    def all(cls) -> list[str]:
        return [p.value for p in cls]


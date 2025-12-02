"""
Capability Definitions

Central registry of all capabilities in the system.
These are loaded into the database via migrations.
"""

from enum import Enum


class Capabilities(str, Enum):
    """
    All capabilities in the Cotton ERP system.
    
    Naming Convention: {MODULE}_{ACTION}
    - MODULE: auth, org, partner, commodity, location, availability, requirement, matching
    - ACTION: create, read, update, delete, approve, execute, etc.
    """
    
    # ==================== AUTH MODULE ====================
    AUTH_LOGIN = "AUTH_LOGIN"
    AUTH_REGISTER = "AUTH_REGISTER"
    AUTH_RESET_PASSWORD = "AUTH_RESET_PASSWORD"
    AUTH_VERIFY_EMAIL = "AUTH_VERIFY_EMAIL"
    AUTH_MANAGE_SESSIONS = "AUTH_MANAGE_SESSIONS"
    AUTH_CREATE_ACCOUNT = "AUTH_CREATE_ACCOUNT"
    AUTH_UPDATE_PROFILE = "AUTH_UPDATE_PROFILE"
    
    # ==================== PUBLIC ACCESS ====================
    PUBLIC_ACCESS = "PUBLIC_ACCESS"  # Unauthenticated access for public endpoints
    
    # ==================== ORGANIZATION MODULE ====================
    ORG_CREATE = "ORG_CREATE"
    ORG_READ = "ORG_READ"
    ORG_UPDATE = "ORG_UPDATE"
    ORG_DELETE = "ORG_DELETE"
    ORG_MANAGE_USERS = "ORG_MANAGE_USERS"
    ORG_MANAGE_ROLES = "ORG_MANAGE_ROLES"
    ORG_VIEW_AUDIT_LOGS = "ORG_VIEW_AUDIT_LOGS"
    
    # ==================== PARTNER MODULE ====================
    PARTNER_CREATE = "PARTNER_CREATE"
    PARTNER_READ = "PARTNER_READ"
    PARTNER_UPDATE = "PARTNER_UPDATE"
    PARTNER_DELETE = "PARTNER_DELETE"
    PARTNER_APPROVE = "PARTNER_APPROVE"
    PARTNER_VERIFY_GST = "PARTNER_VERIFY_GST"
    PARTNER_MANAGE_BANK_ACCOUNTS = "PARTNER_MANAGE_BANK_ACCOUNTS"
    PARTNER_VIEW_SENSITIVE = "PARTNER_VIEW_SENSITIVE"  # View PII data
    
    # ==================== COMMODITY MODULE ====================
    COMMODITY_CREATE = "COMMODITY_CREATE"
    COMMODITY_READ = "COMMODITY_READ"
    COMMODITY_UPDATE = "COMMODITY_UPDATE"
    COMMODITY_DELETE = "COMMODITY_DELETE"
    COMMODITY_UPDATE_PRICE = "COMMODITY_UPDATE_PRICE"
    COMMODITY_MANAGE_SPECIFICATIONS = "COMMODITY_MANAGE_SPECIFICATIONS"
    COMMODITY_MANAGE_HSN = "COMMODITY_MANAGE_HSN"
    
    # ==================== LOCATION MODULE ====================
    LOCATION_CREATE = "LOCATION_CREATE"
    LOCATION_READ = "LOCATION_READ"
    LOCATION_UPDATE = "LOCATION_UPDATE"
    LOCATION_DELETE = "LOCATION_DELETE"
    LOCATION_MANAGE_HIERARCHY = "LOCATION_MANAGE_HIERARCHY"
    
    # ==================== AVAILABILITY MODULE ====================
    AVAILABILITY_CREATE = "AVAILABILITY_CREATE"
    AVAILABILITY_READ = "AVAILABILITY_READ"
    AVAILABILITY_UPDATE = "AVAILABILITY_UPDATE"
    AVAILABILITY_DELETE = "AVAILABILITY_DELETE"
    AVAILABILITY_APPROVE = "AVAILABILITY_APPROVE"
    AVAILABILITY_REJECT = "AVAILABILITY_REJECT"
    AVAILABILITY_RESERVE = "AVAILABILITY_RESERVE"
    AVAILABILITY_RELEASE = "AVAILABILITY_RELEASE"
    AVAILABILITY_MARK_SOLD = "AVAILABILITY_MARK_SOLD"
    AVAILABILITY_CANCEL = "AVAILABILITY_CANCEL"
    AVAILABILITY_VIEW_ANALYTICS = "AVAILABILITY_VIEW_ANALYTICS"
    
    # ==================== REQUIREMENT MODULE ====================
    REQUIREMENT_CREATE = "REQUIREMENT_CREATE"
    REQUIREMENT_READ = "REQUIREMENT_READ"
    REQUIREMENT_UPDATE = "REQUIREMENT_UPDATE"
    REQUIREMENT_DELETE = "REQUIREMENT_DELETE"
    REQUIREMENT_APPROVE = "REQUIREMENT_APPROVE"
    REQUIREMENT_REJECT = "REQUIREMENT_REJECT"
    REQUIREMENT_AI_ADJUST = "REQUIREMENT_AI_ADJUST"  # AI-assisted adjustments
    REQUIREMENT_CANCEL = "REQUIREMENT_CANCEL"
    REQUIREMENT_FULFILL = "REQUIREMENT_FULFILL"
    REQUIREMENT_VIEW_ANALYTICS = "REQUIREMENT_VIEW_ANALYTICS"
    
    # ==================== MATCHING ENGINE ====================
    MATCHING_EXECUTE = "MATCHING_EXECUTE"
    MATCHING_VIEW_RESULTS = "MATCHING_VIEW_RESULTS"
    MATCHING_APPROVE_MATCH = "MATCHING_APPROVE_MATCH"
    MATCHING_REJECT_MATCH = "MATCHING_REJECT_MATCH"
    MATCHING_CONFIGURE_RULES = "MATCHING_CONFIGURE_RULES"
    MATCHING_MANUAL = "MATCHING_MANUAL"  # Manual matching operations
    
    # ==================== SETTINGS MODULE ====================
    SETTINGS_VIEW_ALL = "SETTINGS_VIEW_ALL"
    SETTINGS_MANAGE_ORGANIZATIONS = "SETTINGS_MANAGE_ORGANIZATIONS"
    SETTINGS_MANAGE_COMMODITIES = "SETTINGS_MANAGE_COMMODITIES"
    SETTINGS_MANAGE_LOCATIONS = "SETTINGS_MANAGE_LOCATIONS"
    
    # ==================== INVOICE MODULE ====================
    INVOICE_CREATE_ANY_BRANCH = "INVOICE_CREATE_ANY_BRANCH"
    INVOICE_VIEW_ALL_BRANCHES = "INVOICE_VIEW_ALL_BRANCHES"
    INVOICE_VIEW_OWN = "INVOICE_VIEW_OWN"
    
    # ==================== CONTRACT MODULE ====================
    CONTRACT_VIEW_OWN = "CONTRACT_VIEW_OWN"
    
    # ==================== PAYMENT MODULE ====================
    PAYMENT_VIEW_OWN = "PAYMENT_VIEW_OWN"
    
    # ==================== SHIPMENT MODULE ====================
    SHIPMENT_VIEW_OWN = "SHIPMENT_VIEW_OWN"
    
    # ==================== DATA PRIVACY & GDPR ====================
    DATA_EXPORT_OWN = "DATA_EXPORT_OWN"
    DATA_DELETE_OWN = "DATA_DELETE_OWN"
    DATA_EXPORT_ALL = "DATA_EXPORT_ALL"  # Super Admin only
    DATA_DELETE_ALL = "DATA_DELETE_ALL"  # Super Admin only
    
    # ==================== AUDIT & COMPLIANCE ====================
    AUDIT_VIEW_ALL = "AUDIT_VIEW_ALL"
    AUDIT_EXPORT = "AUDIT_EXPORT"
    
    # ==================== ADMIN CAPABILITIES ====================
    ADMIN_MANAGE_USERS = "ADMIN_MANAGE_USERS"
    ADMIN_MANAGE_ROLES = "ADMIN_MANAGE_ROLES"
    ADMIN_MANAGE_CAPABILITIES = "ADMIN_MANAGE_CAPABILITIES"
    ADMIN_VIEW_ALL_DATA = "ADMIN_VIEW_ALL_DATA"
    ADMIN_EXECUTE_MIGRATIONS = "ADMIN_EXECUTE_MIGRATIONS"
    ADMIN_VIEW_SYSTEM_LOGS = "ADMIN_VIEW_SYSTEM_LOGS"
    ADMIN_MANAGE_INTEGRATIONS = "ADMIN_MANAGE_INTEGRATIONS"
    
    # ==================== SYSTEM CAPABILITIES ====================
    SYSTEM_API_ACCESS = "SYSTEM_API_ACCESS"  # Basic API access
    SYSTEM_WEBSOCKET_ACCESS = "SYSTEM_WEBSOCKET_ACCESS"
    SYSTEM_EXPORT_DATA = "SYSTEM_EXPORT_DATA"
    SYSTEM_IMPORT_DATA = "SYSTEM_IMPORT_DATA"
    SYSTEM_VIEW_AUDIT_TRAIL = "SYSTEM_VIEW_AUDIT_TRAIL"
    SYSTEM_CONFIGURE = "SYSTEM_CONFIGURE"  # Configure system settings


# Capability metadata for documentation and UI
CAPABILITY_METADATA = {
    # Auth
    Capabilities.AUTH_LOGIN: {
        "name": "User Login",
        "description": "Authenticate and log into the system",
        "category": "auth",
        "is_system": True,
    },
    Capabilities.AUTH_REGISTER: {
        "name": "User Registration",
        "description": "Register new user accounts",
        "category": "auth",
        "is_system": False,
    },
    
    # Organization
    Capabilities.ORG_CREATE: {
        "name": "Create Organization",
        "description": "Create new organizations in the system",
        "category": "organization",
        "is_system": False,
    },
    Capabilities.ORG_MANAGE_USERS: {
        "name": "Manage Organization Users",
        "description": "Add, remove, and manage users within organization",
        "category": "organization",
        "is_system": False,
    },
    
    # Partner
    Capabilities.PARTNER_CREATE: {
        "name": "Create Partner",
        "description": "Onboard new business partners",
        "category": "partner",
        "is_system": False,
    },
    Capabilities.PARTNER_APPROVE: {
        "name": "Approve Partner",
        "description": "Approve or reject partner onboarding",
        "category": "partner",
        "is_system": False,
    },
    Capabilities.PARTNER_VERIFY_GST: {
        "name": "Verify GST",
        "description": "Trigger GST verification API calls",
        "category": "partner",
        "is_system": False,
    },
    
    # Commodity
    Capabilities.COMMODITY_CREATE: {
        "name": "Create Commodity",
        "description": "Add new commodities to master data",
        "category": "commodity",
        "is_system": False,
    },
    Capabilities.COMMODITY_UPDATE_PRICE: {
        "name": "Update Commodity Price",
        "description": "Modify commodity pricing",
        "category": "commodity",
        "is_system": False,
    },
    
    # Availability
    Capabilities.AVAILABILITY_CREATE: {
        "name": "Post Availability",
        "description": "Post new availability for sale",
        "category": "availability",
        "is_system": False,
    },
    Capabilities.AVAILABILITY_APPROVE: {
        "name": "Approve Availability",
        "description": "Approve availability postings",
        "category": "availability",
        "is_system": False,
    },
    Capabilities.AVAILABILITY_RESERVE: {
        "name": "Reserve Availability",
        "description": "Reserve availability for potential match",
        "category": "availability",
        "is_system": False,
    },
    
    # Requirement
    Capabilities.REQUIREMENT_CREATE: {
        "name": "Post Requirement",
        "description": "Post procurement requirements",
        "category": "requirement",
        "is_system": False,
    },
    Capabilities.REQUIREMENT_AI_ADJUST: {
        "name": "AI-Adjust Requirement",
        "description": "Use AI to adjust requirement parameters",
        "category": "requirement",
        "is_system": False,
    },
    Capabilities.REQUIREMENT_APPROVE: {
        "name": "Approve Requirement",
        "description": "Approve requirement postings",
        "category": "requirement",
        "is_system": False,
    },
    
    # Matching
    Capabilities.MATCHING_EXECUTE: {
        "name": "Execute Matching",
        "description": "Run matching engine to find matches",
        "category": "matching",
        "is_system": False,
    },
    Capabilities.MATCHING_APPROVE_MATCH: {
        "name": "Approve Match",
        "description": "Approve a proposed match",
        "category": "matching",
        "is_system": False,
    },
    
    # Admin
    Capabilities.ADMIN_MANAGE_CAPABILITIES: {
        "name": "Manage Capabilities",
        "description": "Grant/revoke capabilities to users and roles",
        "category": "admin",
        "is_system": True,
    },
    Capabilities.ADMIN_VIEW_ALL_DATA: {
        "name": "View All Data",
        "description": "Access all data across all organizations (super admin)",
        "category": "admin",
        "is_system": True,
    },
    
    # Settings
    Capabilities.SETTINGS_VIEW_ALL: {
        "name": "View All Settings",
        "description": "View all system settings (super admin)",
        "category": "settings",
        "is_system": True,
    },
    Capabilities.SETTINGS_MANAGE_ORGANIZATIONS: {
        "name": "Manage Organizations",
        "description": "Create and manage organizations",
        "category": "settings",
        "is_system": False,
    },
    
    # Invoice
    Capabilities.INVOICE_CREATE_ANY_BRANCH: {
        "name": "Create Invoice (Any Branch)",
        "description": "Create invoices for any branch",
        "category": "invoice",
        "is_system": False,
    },
    Capabilities.INVOICE_VIEW_ALL_BRANCHES: {
        "name": "View Invoices (All Branches)",
        "description": "View invoices across all branches",
        "category": "invoice",
        "is_system": False,
    },
    
    # GDPR
    Capabilities.DATA_EXPORT_OWN: {
        "name": "Export Own Data",
        "description": "Export personal data (GDPR compliance)",
        "category": "privacy",
        "is_system": False,
    },
    Capabilities.DATA_DELETE_OWN: {
        "name": "Delete Own Data",
        "description": "Request deletion of personal data (GDPR compliance)",
        "category": "privacy",
        "is_system": False,
    },
    Capabilities.DATA_EXPORT_ALL: {
        "name": "Export All Data",
        "description": "Export any user's data (super admin)",
        "category": "privacy",
        "is_system": True,
    },
    
    # Audit
    Capabilities.AUDIT_VIEW_ALL: {
        "name": "View Audit Logs",
        "description": "Access complete audit trail",
        "category": "audit",
        "is_system": True,
    },
    Capabilities.AUDIT_EXPORT: {
        "name": "Export Audit Logs",
        "description": "Export audit logs for compliance",
        "category": "audit",
        "is_system": True,
    },
    
    # System
    Capabilities.SYSTEM_API_ACCESS: {
        "name": "API Access",
        "description": "Basic access to API endpoints",
        "category": "system",
        "is_system": True,
    },
}

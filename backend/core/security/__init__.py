from __future__ import annotations

# Security context exports
from backend.core.security.context import (
    UserType,
    SecurityError,
    current_user_id,
    current_user_type,
    current_business_partner_id,
    current_organization_id,
    current_allowed_modules,
    get_current_user_id,
    get_current_user_type,
    get_current_business_partner_id,
    get_current_organization_id,
    get_allowed_modules,
    is_super_admin,
    is_internal_user,
    is_external_user,
    has_module_access,
    set_security_context,
    reset_security_context,
    get_security_context_summary,
)

__all__ = [
    # Enums & Exceptions
    "UserType",
    "SecurityError",
    # Context Variables
    "current_user_id",
    "current_user_type",
    "current_business_partner_id",
    "current_organization_id",
    "current_allowed_modules",
    # Getters
    "get_current_user_id",
    "get_current_user_type",
    "get_current_business_partner_id",
    "get_current_organization_id",
    "get_allowed_modules",
    # Type Checks
    "is_super_admin",
    "is_internal_user",
    "is_external_user",
    # Module Access
    "has_module_access",
    # Management (for middleware/testing only)
    "set_security_context",
    "reset_security_context",
    "get_security_context_summary",
]

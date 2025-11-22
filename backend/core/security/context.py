"""
Security Context Module - Data Isolation Foundation

Thread-safe context management for user isolation across the application.
Uses ContextVars for async-safe state management (same pattern as request_id_ctx).

Compliance:
- GDPR Article 32: Security of Processing
- IT Act 2000 Section 43A: Reasonable Security Practices
- Income Tax Act 1961: Audit Trail Requirements

Author: Cotton ERP Security Team
Date: November 22, 2025
"""

from __future__ import annotations

from contextvars import ContextVar
from enum import Enum
from typing import Optional
from uuid import UUID


class UserType(str, Enum):
    """
    User types for access control and data isolation.
    
    - SUPER_ADMIN: Full system access, manages settings (organizations, commodities, locations)
    - INTERNAL: Your employees (back-office), can see all business partners
    - EXTERNAL: Business partner users, see only their own data
    """
    SUPER_ADMIN = "SUPER_ADMIN"
    INTERNAL = "INTERNAL"
    EXTERNAL = "EXTERNAL"


class SecurityError(Exception):
    """Raised when security context is invalid or missing"""
    pass


# Thread-safe context variables (follows pattern of request_id_ctx in audit logger)
# These are set by DataIsolationMiddleware on every request
current_user_id: ContextVar[Optional[UUID]] = ContextVar('user_id', default=None)
current_user_type: ContextVar[Optional[UserType]] = ContextVar('user_type', default=None)
current_business_partner_id: ContextVar[Optional[UUID]] = ContextVar('bp_id', default=None)
current_organization_id: ContextVar[Optional[UUID]] = ContextVar('org_id', default=None)
current_allowed_modules: ContextVar[list[str]] = ContextVar('allowed_modules', default=[])


# === Context Getters (with validation) ===

def get_current_user_id() -> UUID:
    """
    Get current authenticated user ID.
    
    Raises:
        SecurityError: If user context not set (authentication required)
    
    Returns:
        UUID: Current user's ID
    """
    user_id = current_user_id.get()
    if not user_id:
        raise SecurityError("User context not set - authentication required")
    return user_id


def get_current_user_type() -> UserType:
    """
    Get current user type.
    
    Raises:
        SecurityError: If user type not set (invalid session)
    
    Returns:
        UserType: SUPER_ADMIN, INTERNAL, or EXTERNAL
    """
    user_type = current_user_type.get()
    if not user_type:
        raise SecurityError("User type not set - invalid session")
    return user_type


def get_current_business_partner_id() -> Optional[UUID]:
    """
    Get current business partner ID.
    
    Returns:
        UUID: Business partner ID for EXTERNAL users
        None: For INTERNAL and SUPER_ADMIN users
    """
    return current_business_partner_id.get()


def get_current_organization_id() -> Optional[UUID]:
    """
    Get current organization ID.
    
    Returns:
        UUID: Organization ID for INTERNAL users
        None: For EXTERNAL and SUPER_ADMIN users
    """
    return current_organization_id.get()


def get_allowed_modules() -> list[str]:
    """
    Get list of modules user is allowed to access (RBAC).
    
    Returns:
        list[str]: Module names (e.g., ['trade-desk', 'accounting'])
        Empty list: If not set or user has no module access
    """
    return current_allowed_modules.get() or []


# === User Type Checks ===

def is_super_admin() -> bool:
    """
    Check if current user is Super Admin.
    
    Returns:
        bool: True if SUPER_ADMIN, False otherwise
    """
    try:
        return get_current_user_type() == UserType.SUPER_ADMIN
    except SecurityError:
        return False


def is_internal_user() -> bool:
    """
    Check if current user is Internal (employee).
    
    Returns:
        bool: True if INTERNAL, False otherwise
    """
    try:
        return get_current_user_type() == UserType.INTERNAL
    except SecurityError:
        return False


def is_external_user() -> bool:
    """
    Check if current user is External (business partner).
    
    Returns:
        bool: True if EXTERNAL, False otherwise
    """
    try:
        return get_current_user_type() == UserType.EXTERNAL
    except SecurityError:
        return False


# === Module Access Control (RBAC) ===

def has_module_access(module_name: str) -> bool:
    """
    Check if user has access to a specific module.
    
    Super Admin always has access to all modules.
    Other users checked against allowed_modules list.
    
    Args:
        module_name: Module identifier (e.g., 'trade-desk', 'accounting')
    
    Returns:
        bool: True if user can access module, False otherwise
    """
    if is_super_admin():
        return True  # Super admin has access to all modules
    
    allowed = get_allowed_modules()
    return module_name in allowed if allowed else False


# === Context Management ===

def set_security_context(
    user_id: UUID,
    user_type: UserType,
    business_partner_id: Optional[UUID] = None,
    organization_id: Optional[UUID] = None,
    allowed_modules: Optional[list[str]] = None
) -> None:
    """
    Set security context for current request.
    
    Called by DataIsolationMiddleware - DO NOT call directly in application code.
    
    Args:
        user_id: User's unique identifier
        user_type: SUPER_ADMIN, INTERNAL, or EXTERNAL
        business_partner_id: Business partner ID (for EXTERNAL users)
        organization_id: Organization ID (for INTERNAL users)
        allowed_modules: List of modules user can access
    
    Raises:
        SecurityError: If context is invalid for user_type
    """
    # Validate context based on user type
    if user_type == UserType.SUPER_ADMIN:
        if business_partner_id or organization_id:
            raise SecurityError("SUPER_ADMIN cannot have business_partner_id or organization_id")
    
    elif user_type == UserType.INTERNAL:
        if business_partner_id:
            raise SecurityError("INTERNAL user cannot have business_partner_id")
        if not organization_id:
            raise SecurityError("INTERNAL user must have organization_id")
    
    elif user_type == UserType.EXTERNAL:
        if organization_id:
            raise SecurityError("EXTERNAL user cannot have organization_id")
        if not business_partner_id:
            raise SecurityError("EXTERNAL user must have business_partner_id")
    
    # Set context
    current_user_id.set(user_id)
    current_user_type.set(user_type)
    current_business_partner_id.set(business_partner_id)
    current_organization_id.set(organization_id)
    current_allowed_modules.set(allowed_modules or [])


def reset_security_context() -> None:
    """
    Clear all security context.
    
    Used in testing and cleanup. DO NOT use in application code.
    """
    current_user_id.set(None)
    current_user_type.set(None)
    current_business_partner_id.set(None)
    current_organization_id.set(None)
    current_allowed_modules.set([])


def get_security_context_summary() -> dict:
    """
    Get summary of current security context (for debugging/logging).
    
    Returns:
        dict: Current context state
    """
    return {
        'user_id': str(current_user_id.get()) if current_user_id.get() else None,
        'user_type': current_user_type.get().value if current_user_type.get() else None,
        'business_partner_id': str(current_business_partner_id.get()) if current_business_partner_id.get() else None,
        'organization_id': str(current_organization_id.get()) if current_organization_id.get() else None,
        'allowed_modules': current_allowed_modules.get() or [],
    }

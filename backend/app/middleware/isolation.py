"""
Data Isolation Middleware

CRITICAL SECURITY MIDDLEWARE - Enforces data isolation for all API requests.

Responsibilities:
1. Extract authenticated user from request
2. Set security context based on user_type
3. Configure PostgreSQL Row Level Security (RLS)
4. Log all data access (GDPR compliance)
5. Enforce module-level access control (RBAC)

Integration:
- Runs AFTER auth middleware (needs authenticated user)
- Runs BEFORE business logic
- Works with existing RequestIDMiddleware pattern

Compliance:
- GDPR Article 30: Records of Processing Activities
- GDPR Article 32: Security of Processing
- IT Act 2000 Section 43A: Data Protection
- Income Tax Act 1961: Audit Trail

Author: Cotton ERP Security Team
Date: November 22, 2025
"""

from __future__ import annotations

from typing import Callable

from fastapi import HTTPException, Request, status
from sqlalchemy.orm import Session
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from backend.core.audit.logger import log_data_access, log_isolation_violation
from backend.core.security.context import (
    SecurityError,
    UserType,
    has_module_access,
    set_security_context,
)


class DataIsolationMiddleware(BaseHTTPMiddleware):
    """
    Data Isolation Middleware - Enforces business partner isolation.
    
    Flow:
    1. Check if path requires authentication
    2. Get authenticated user from request.state.user
    3. Validate user object
    4. Set security context (ContextVars)
    5. Configure PostgreSQL RLS session variables
    6. Log access (GDPR compliance)
    7. Check module access (RBAC)
    8. Process request
    
    Security:
    - Double layer: Application context + Database RLS
    - All access logged for audit
    - Context cannot be spoofed (set from authenticated user only)
    """
    
    # Public endpoints (no authentication required)
    SKIP_PATHS = [
        '/health',
        '/healthz',
        '/ready',
        '/docs',
        '/redoc',
        '/openapi.json',
        '/api/v1/auth/login',
        '/api/v1/auth/register',
        '/api/v1/auth/forgot-password',
        '/api/v1/auth/reset-password',
        '/api/v1/auth/send-otp',
        '/api/v1/auth/verify-otp',
        '/api/v1/auth/complete-profile',
        '/api/v1/partners/onboarding',  # Onboarding endpoints (user doesn't have business_partner_id yet)
    ]
    
    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)
    
    async def dispatch(self, request: Request, call_next: Callable):
        """
        Process request with data isolation.
        
        Args:
            request: FastAPI request
            call_next: Next middleware in chain
        
        Returns:
            Response from next middleware
        
        Raises:
            HTTPException: 401 if not authenticated, 403 if access denied
        """
        # Skip public endpoints
        if self._is_public_path(request.url.path):
            return await call_next(request)
        
        # Get authenticated user (set by auth middleware - must run before this)
        user = getattr(request.state, 'user', None)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Validate user object has required fields
        self._validate_user_object(user)
        
        # Get database session (for RLS configuration)
        db: Session = getattr(request.state, 'db', None)
        if not db:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Database session not available",
            )
        
        # Set security context and configure RLS
        try:
            self._configure_isolation(user, db)
        except SecurityError as e:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=str(e),
            )
        
        # Log data access (GDPR Article 30 - Records of Processing)
        self._log_access(user, request)
        
        # Check module-level access (RBAC)
        module = self._extract_module_from_path(request.url.path)
        if module and not has_module_access(module):
            # Log violation
            log_isolation_violation(
                user_id=user.id,
                user_type=user.user_type,
                attempted_resource=request.url.path,
                attempted_business_partner_id=None,
                user_business_partner_id=getattr(user, 'business_partner_id', None),
                reason=f"Module access denied: {module}",
            )
            
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied to module: {module}",
            )
        
        # Process request
        response = await call_next(request)
        
        return response
    
    def _is_public_path(self, path: str) -> bool:
        """
        Check if path is public (no auth required).
        
        Args:
            path: Request path
        
        Returns:
            bool: True if public, False if requires auth
        """
        # Exact match
        if any(path == skip_path for skip_path in self.SKIP_PATHS):
            return True
        
        # Prefix match (e.g., /api/v1/partners/onboarding/*)
        skip_prefixes = [
            "/api/v1/partners/onboarding",
            "/api/v1/auth",
        ]
        return any(path.startswith(prefix) for prefix in skip_prefixes)
    
    def _validate_user_object(self, user) -> None:
        """
        Validate user object has required fields.
        
        Args:
            user: User object from auth middleware
        
        Raises:
            HTTPException: If user object invalid
        """
        if not hasattr(user, 'id'):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Invalid user object: missing 'id'",
            )
        
        if not hasattr(user, 'user_type'):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Invalid user object: missing 'user_type'",
            )
    
    def _configure_isolation(self, user, db: Session) -> None:
        """
        Configure security context and PostgreSQL RLS.
        
        Args:
            user: Authenticated user
            db: Database session
        
        Raises:
            SecurityError: If user configuration invalid
        """
        user_type = UserType(user.user_type)
        
        # Set application context
        if user_type == UserType.SUPER_ADMIN:
            set_security_context(
                user_id=user.id,
                user_type=user_type,
                business_partner_id=None,
                organization_id=None,
                allowed_modules=getattr(user, 'allowed_modules', None),
            )
            
            # Set PostgreSQL RLS variables
            self._set_postgres_rls(
                db,
                user_id=user.id,
                user_type='SUPER_ADMIN',
            )
        
        elif user_type == UserType.INTERNAL:
            # Internal user - must have organization_id
            org_id = getattr(user, 'organization_id', None)
            if not org_id:
                raise SecurityError(
                    "Internal user must have organization_id"
                )
            
            set_security_context(
                user_id=user.id,
                user_type=user_type,
                business_partner_id=None,
                organization_id=org_id,
                allowed_modules=getattr(user, 'allowed_modules', None),
            )
            
            # Set PostgreSQL RLS variables
            self._set_postgres_rls(
                db,
                user_id=user.id,
                user_type='INTERNAL',
                organization_id=org_id,
            )
        
        elif user_type == UserType.EXTERNAL:
            # External user - must have business_partner_id
            bp_id = getattr(user, 'business_partner_id', None)
            if not bp_id:
                raise SecurityError(
                    "External user must have business_partner_id"
                )
            
            set_security_context(
                user_id=user.id,
                user_type=user_type,
                business_partner_id=bp_id,
                organization_id=None,
                allowed_modules=getattr(user, 'allowed_modules', None),
            )
            
            # Set PostgreSQL RLS variables
            self._set_postgres_rls(
                db,
                user_id=user.id,
                user_type='EXTERNAL',
                business_partner_id=bp_id,
            )
        
        else:
            raise SecurityError(f"Invalid user_type: {user.user_type}")
    
    def _set_postgres_rls(
        self,
        db: Session,
        user_id,
        user_type: str,
        business_partner_id = None,
        organization_id = None,
    ) -> None:
        """
        Set PostgreSQL session variables for Row Level Security.
        
        These variables are used in RLS policies to filter data at database level.
        Provides second layer of security (defense in depth).
        
        Args:
            db: Database session
            user_id: User UUID
            user_type: SUPER_ADMIN, INTERNAL, or EXTERNAL
            business_partner_id: Business partner UUID (for EXTERNAL)
            organization_id: Organization UUID (for INTERNAL)
        """
        # Set base variables
        db.execute(f"SET app.user_id = '{user_id}'")
        db.execute(f"SET app.user_type = '{user_type}'")
        
        # Set type-specific variables
        if business_partner_id:
            db.execute(f"SET app.business_partner_id = '{business_partner_id}'")
        
        if organization_id:
            db.execute(f"SET app.organization_id = '{organization_id}'")
    
    def _log_access(self, user, request: Request) -> None:
        """
        Log API access for compliance (GDPR Article 30).
        
        Args:
            user: Authenticated user
            request: FastAPI request
        """
        log_data_access(
            user_id=user.id,
            user_type=user.user_type,
            business_partner_id=getattr(user, 'business_partner_id', None),
            path=request.url.path,
            method=request.method,
            ip_address=request.client.host if request.client else 'unknown',
            user_agent=request.headers.get('user-agent', ''),
        )
    
    def _extract_module_from_path(self, path: str) -> str | None:
        """
        Extract module name from API path for RBAC check.
        
        Example: /api/v1/trade-desk/contracts -> trade-desk
        
        Args:
            path: Request path
        
        Returns:
            Module name or None if not a module path
        """
        parts = path.split('/')
        if len(parts) >= 4 and parts[1] == 'api' and parts[2] == 'v1':
            return parts[3]
        return None

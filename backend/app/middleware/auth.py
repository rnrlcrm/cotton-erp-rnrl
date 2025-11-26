"""
Authentication Middleware

Validates JWT tokens and sets request.state.user for all authenticated requests.
This middleware is required before DataIsolationMiddleware can run.

Key Features:
1. JWT token validation using existing auth system
2. User loading with all required isolation fields
3. Sets request.state.user for downstream middleware
4. Skips public/health endpoints
5. Returns 401 for invalid/missing tokens
"""

from __future__ import annotations

import logging
from typing import Callable

from fastapi import HTTPException, Request, Response, status
from starlette.middleware.base import BaseHTTPMiddleware

from backend.core.auth.jwt import decode_token
from backend.db.async_session import AsyncSessionLocal
from backend.modules.settings.repositories.settings_repositories import UserRepository

logger = logging.getLogger(__name__)

# Paths that don't require authentication
SKIP_AUTH_PATHS = {
    "/",
    "/healthz",
    "/ready",
    "/health",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/api/v1/auth/login",
    "/api/v1/auth/register",
    "/api/v1/auth/refresh",
    "/api/v1/auth/send-otp",
    "/api/v1/auth/verify-otp",
    "/api/v1/auth/complete-profile",
    "/api/v1/settings/auth/signup",
    "/api/v1/settings/auth/login",
    "/api/v1/settings/auth/refresh",
    "/api/v1/settings/auth/logout",
    "/api/v1/settings/auth/me",  # Uses its own get_current_user dependency
    "/api/v1/settings/auth/sub-users",  # Uses its own get_current_user dependency
    "/api/v1/partners/onboarding",  # Onboarding endpoints use token with mobile as subject
}


class AuthMiddleware(BaseHTTPMiddleware):
    """
    Authentication middleware that validates JWT tokens and loads user data.
    
    Sets request.state.user with:
    - user.id (UUID)
    - user.user_type (SUPER_ADMIN | INTERNAL | EXTERNAL)
    - user.business_partner_id (UUID | None)
    - user.organization_id (UUID | None)
    - user.allowed_modules (list[str] | None)
    - user.email
    - user.full_name
    - user.is_active
    
    This data is used by:
    - DataIsolationMiddleware (sets security context)
    - Route handlers (access user info)
    - RBAC checks (permission validation)
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process each request through authentication"""
        
        # Skip authentication for public endpoints
        if self._should_skip_auth(request):
            return await call_next(request)
        
        # Extract and validate token
        token = self._extract_token(request)
        if not token:
            logger.warning(f"Missing auth token for {request.url.path}")
            return Response(
                content='{"detail":"Missing authentication token"}',
                status_code=status.HTTP_401_UNAUTHORIZED,
                media_type="application/json",
            )
        
        # Decode and validate JWT
        try:
            payload = decode_token(token)
        except Exception as e:
            logger.warning(f"Invalid token: {e}")
            return Response(
                content='{"detail":"Invalid authentication token"}',
                status_code=status.HTTP_401_UNAUTHORIZED,
                media_type="application/json",
            )
        
        # Extract user_id from token
        user_id = payload.get("sub")
        if not user_id:
            logger.warning("Token missing 'sub' claim")
            return Response(
                content='{"detail":"Invalid token payload"}',
                status_code=status.HTTP_401_UNAUTHORIZED,
                media_type="application/json",
            )
        
        # Load user from database with all isolation fields
        async with AsyncSessionLocal() as db:
            try:
                user_repo = UserRepository(db)
                user = await user_repo.get_by_id(user_id)
                
                if user is None:
                    logger.warning(f"User {user_id} not found")
                    return Response(
                        content='{"detail":"User not found"}',
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        media_type="application/json",
                    )
                
                if not user.is_active:
                    logger.warning(f"Inactive user {user_id} attempted access")
                    return Response(
                        content='{"detail":"User account is inactive"}',
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        media_type="application/json",
                    )
                
                # Set user on request state for downstream middleware/handlers
                request.state.user = user
                
                logger.debug(
                    f"Authenticated user {user.id} ({user.user_type}) for {request.method} {request.url.path}"
                )
                
            except Exception as e:
                logger.error(f"Error loading user: {e}")
                return Response(
                    content='{"detail":"Authentication error"}',
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    media_type="application/json",
                )
        
        # Proceed to next middleware/handler
        response = await call_next(request)
        return response
    
    def _should_skip_auth(self, request: Request) -> bool:
        """Check if request path should skip authentication"""
        path = request.url.path
        
        # Exact match for public paths
        if path in SKIP_AUTH_PATHS:
            return True
        
        # Prefix match for certain endpoints (e.g., /api/v1/partners/onboarding/*)
        skip_prefixes = [
            "/docs",
            "/static",
            "/api/v1/partners/onboarding",
            "/api/v1/auth",
            "/api/v1/settings/auth",  # All settings auth endpoints use get_current_user dependency
        ]
        for prefix in skip_prefixes:
            if path.startswith(prefix):
                return True
        
        return False
    
    def _extract_token(self, request: Request) -> str | None:
        """Extract Bearer token from Authorization header"""
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            return None
        
        # Check for Bearer scheme
        if not auth_header.lower().startswith("bearer "):
            return None
        
        # Extract token (everything after "Bearer ")
        token = auth_header[7:].strip()
        return token if token else None

"""
EXTERNAL User Mobile OTP Login Integration Tests

Tests the mobile OTP authentication flow for EXTERNAL users (business partners and sub-users).
INTERNAL users must use email/password login.
"""
import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from unittest.mock import AsyncMock, patch, MagicMock

from backend.modules.settings.models.settings_models import User


class TestExternalUserOTPLogin:
    """Test EXTERNAL user authentication via mobile OTP."""

    @pytest.mark.asyncio
    async def test_send_otp_success(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession
    ):
        """✅ Test: Successfully send OTP to mobile number."""
        # Mock Redis dependency on app
        async def mock_redis_gen():
            mock = MagicMock()
            mock.aclose = AsyncMock()
            yield mock
        
        from backend.app.main import app
        from backend.modules.settings.router import get_redis
        app.dependency_overrides[get_redis] = mock_redis_gen
        
        try:
            with patch('backend.modules.user_onboarding.services.otp_service.OTPService.send_otp') as mock_send:
                from datetime import datetime, timezone
                mock_send.return_value = {
                    "expires_at": datetime.now(timezone.utc),
                    "otp": "123456"
                }
                
                response = await async_client.post(
                    "/api/v1/settings/auth/send-otp",
                    json={
                        "mobile_number": "+919876543210",
                        "country_code": "+91"
                    }
                )
                
                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True
                assert "OTP sent" in data["message"]
                assert data["expires_in_seconds"] == 300
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_verify_otp_external_user_success(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        seed_business_partner
    ):
        """✅ Test: EXTERNAL user can login with valid OTP."""
        # Create EXTERNAL user (business partner) - mobile ONLY, NO email/password
        external_user = User(
            mobile_number="+919876500001",  # Unique number to avoid DB collision
            full_name="External Partner User",
            user_type="EXTERNAL",
            business_partner_id=seed_business_partner.id,
            is_active=True,
            is_verified=True
        )
        db_session.add(external_user)
        await db_session.flush()
        
        # Mock Redis dependency
        async def mock_redis_gen():
            mock = MagicMock()
            mock.aclose = AsyncMock()
            yield mock
        
        from backend.app.main import app
        from backend.modules.settings.router import get_redis
        app.dependency_overrides[get_redis] = mock_redis_gen
        
        try:
            with patch('backend.modules.user_onboarding.services.otp_service.OTPService.verify_otp') as mock_verify:
                mock_verify.return_value = True
                
                response = await async_client.post(
                    "/api/v1/settings/auth/verify-otp",
                    json={
                        "mobile_number": "+919876500001",
                        "otp": "123456"
                    }
                )
                
                assert response.status_code == 200
                data = response.json()
                assert "access_token" in data
                assert "refresh_token" in data
                assert data["token_type"] == "Bearer"
                assert data["expires_in"] > 0
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_verify_otp_sub_user_success(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        seed_business_partner
    ):
        """✅ Test: Sub-user (EXTERNAL) can login with valid OTP."""
        # Create parent EXTERNAL user - mobile ONLY
        parent = User(
            mobile_number="+919876543212",
            full_name="Parent User",
            user_type="EXTERNAL",
            business_partner_id=seed_business_partner.id,
            is_active=True,
            is_verified=True
        )
        db_session.add(parent)
        await db_session.flush()
        
        # Create sub-user - mobile ONLY
        sub_user = User(
            mobile_number="+919876543213",
            full_name="Sub User",
            user_type="EXTERNAL",
            business_partner_id=seed_business_partner.id,
            parent_user_id=parent.id,
            is_active=True,
            is_verified=True
        )
        db_session.add(sub_user)
        await db_session.flush()
        
        # Mock Redis dependency
        async def mock_redis_gen():
            mock = MagicMock()
            mock.aclose = AsyncMock()
            yield mock
        
        from backend.app.main import app
        from backend.modules.settings.router import get_redis
        app.dependency_overrides[get_redis] = mock_redis_gen
        
        try:
            with patch('backend.modules.user_onboarding.services.otp_service.OTPService.verify_otp') as mock_verify:
                mock_verify.return_value = True
                
                response = await async_client.post(
                    "/api/v1/settings/auth/verify-otp",
                    json={
                        "mobile_number": "+919876543213",
                        "otp": "123456"
                    }
                )
                
                assert response.status_code == 200
                data = response.json()
                assert "access_token" in data
                assert "refresh_token" in data
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_verify_otp_user_not_found(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession
    ):
        """✅ Test: OTP verification fails if user doesn't exist."""
        # Mock OTP verification to succeed, but user doesn't exist in DB
        with patch('backend.modules.user_onboarding.services.otp_service.OTPService.verify_otp') as mock_verify:
            mock_verify.return_value = True
            
            response = await async_client.post(
                "/api/v1/settings/auth/verify-otp",
                json={
                    "mobile_number": "+919999999999",  # Non-existent
                    "otp": "123456"
                }
            )
            
            assert response.status_code == 404
            assert "User not found" in response.json()["detail"]
            assert "onboarding" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_verify_otp_internal_user_rejected(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        seed_organization
    ):
        """✅ Test: INTERNAL user cannot login via OTP."""
        # Create INTERNAL user
        internal_user = User(
            mobile_number="+919876543214",
            email="internal@company.com",
            full_name="Internal User",
            user_type="INTERNAL",
            organization_id=seed_organization.id,
            is_active=True,
            is_verified=True
        )
        db_session.add(internal_user)
        await db_session.flush()
        
        # Mock OTP verification
        with patch('backend.modules.user_onboarding.services.otp_service.OTPService.verify_otp') as mock_verify:
            mock_verify.return_value = True
            
            response = await async_client.post(
                "/api/v1/settings/auth/verify-otp",
                json={
                    "mobile_number": "+919876543214",
                    "otp": "123456"
                }
            )
            
            assert response.status_code == 403
            assert "INTERNAL users must use email/password" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_verify_otp_inactive_user_rejected(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        seed_business_partner
    ):
        """✅ Test: Inactive EXTERNAL user cannot login."""
        # Create inactive EXTERNAL user
        inactive_user = User(
            mobile_number="+919876543215",
            full_name="Inactive User",
            user_type="EXTERNAL",
            business_partner_id=seed_business_partner.id,
            is_active=False,  # Inactive
            is_verified=True
        )
        db_session.add(inactive_user)
        await db_session.flush()
        
        # Mock OTP verification
        with patch('backend.modules.user_onboarding.services.otp_service.OTPService.verify_otp') as mock_verify:
            mock_verify.return_value = True
            
            response = await async_client.post(
                "/api/v1/settings/auth/verify-otp",
                json={
                    "mobile_number": "+919876543215",
                    "otp": "123456"
                }
            )
            
            assert response.status_code == 403
            assert "inactive" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_verify_otp_invalid_otp(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        seed_business_partner
    ):
        """✅ Test: Invalid OTP is rejected."""
        # Create EXTERNAL user
        external_user = User(
            mobile_number="+919876543216",
            full_name="Test User",
            user_type="EXTERNAL",
            business_partner_id=seed_business_partner.id,
            is_active=True,
            is_verified=True
        )
        db_session.add(external_user)
        await db_session.flush()
        
        # Mock OTP verification to fail
        with patch('backend.modules.user_onboarding.services.otp_service.OTPService.verify_otp') as mock_verify:
            from fastapi import HTTPException, status
            mock_verify.side_effect = HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired OTP"
            )
            
            response = await async_client.post(
                "/api/v1/settings/auth/verify-otp",
                json={
                    "mobile_number": "+919876543216",
                    "otp": "999999"  # Wrong OTP
                }
            )
            
            assert response.status_code == 401
            assert "Invalid or expired OTP" in response.json()["detail"]


class TestInternalUserPasswordLogin:
    """Test that INTERNAL users must use email/password login."""

    @pytest.mark.asyncio
    async def test_internal_user_password_login_works(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        seed_organization
    ):
        """✅ Test: INTERNAL user CAN use password login."""
        from backend.core.auth.passwords import PasswordHasher
        hasher = PasswordHasher()
        
        # Create INTERNAL user (email + password ONLY, NO mobile)
        internal_user = User(
            email="test_internal_user_unique@company.com",
            password_hash=hasher.hash("Password123!"),
            full_name="Test Internal User",
            user_type="INTERNAL",
            organization_id=seed_organization.id,
            is_active=True,
            is_verified=True
        )
        db_session.add(internal_user)
        await db_session.flush()
        
        # INTERNAL user can login with email/password
        response = await async_client.post(
            "/api/v1/settings/auth/login",
            json={
                "email": "test_internal_user_unique@company.com",
                "password": "Password123!"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data

    @pytest.mark.asyncio
    async def test_external_user_cannot_use_password_login(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        seed_business_partner
    ):
        """✅ Test: EXTERNAL user cannot login via email/password endpoint."""
        from backend.core.auth.passwords import PasswordHasher
        hasher = PasswordHasher()
        
        # Create EXTERNAL user with email and password (edge case)
        external_user = User(
            email="external@partner.com",
            password_hash=hasher.hash("Password123!"),
            mobile_number="+919876543217",
            full_name="External User",
            user_type="EXTERNAL",
            business_partner_id=seed_business_partner.id,
            is_active=True,
            is_verified=True
        )
        db_session.add(external_user)
        await db_session.flush()
        
        # EXTERNAL user should be rejected from password login
        response = await async_client.post(
            "/api/v1/settings/auth/login",
            json={
                "email": "external@partner.com",
                "password": "Password123!"
            }
        )
        
        assert response.status_code == 401
        assert "EXTERNAL users must login via mobile OTP" in response.json()["detail"]

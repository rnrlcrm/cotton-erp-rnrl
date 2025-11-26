"""
Sub-User Integration Tests

Tests the complete sub-user functionality:
- Creating sub-users (max 2 per parent)
- Listing sub-users
- Deleting sub-users
- Validation rules (no recursive sub-users, max limit)
"""
import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from backend.modules.settings.models.settings_models import User
from backend.core.auth.passwords import PasswordHasher

pwd_hasher = PasswordHasher()


class TestSubUserCreation:
    """Test sub-user creation functionality."""

    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_create_sub_user_success(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        seed_organization
    ):
        """✅ Test: Parent user can create a sub-user."""
        # Create parent user
        parent = User(
            email="parent@example.com",
            password_hash=pwd_hasher.hash("Password123!"),
            full_name="Parent User",
            organization_id=seed_organization.id,
            is_active=True
        )
        db_session.add(parent)
        await db_session.flush()  # Flush is enough for login to see it

        # Login as parent
        login_response = await async_client.post(
            "/api/v1/settings/auth/login",
            json={"email": "parent@example.com", "password": "Password123!"}
        )
        assert login_response.status_code == 200
        access_token = login_response.json()["access_token"]

        # Create sub-user
        response = await async_client.post(
            "/api/v1/settings/auth/sub-users",
            json={
                "email": "subuser1@example.com",
                "full_name": "Sub User 1",
                "password": "SubPass123!",
                "role": "assistant"
            },
            headers={"Authorization": f"Bearer {access_token}"}
        )

        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "subuser1@example.com"
        assert data["full_name"] == "Sub User 1"
        assert data["role"] == "assistant"
        assert data["is_active"] is True
        assert data["parent_user_id"] == str(parent.id)
        assert "id" in data
        assert "created_at" in data

    @pytest.mark.asyncio
    async def test_create_second_sub_user_success(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        seed_organization
    ):
        """✅ Test: Parent can create a second sub-user (max 2)."""
        # Create parent user
        parent = User(
            email="parent2@example.com",
            password_hash=pwd_hasher.hash("Password123!"),
            full_name="Parent User 2",
            organization_id=seed_organization.id,
            is_active=True
        )
        db_session.add(parent)
        await db_session.flush()  # Flush is enough for login

        # Login as parent
        login_response = await async_client.post(
            "/api/v1/settings/auth/login",
            json={"email": "parent2@example.com", "password": "Password123!"}
        )
        access_token = login_response.json()["access_token"]

        # Create first sub-user
        response1 = await async_client.post(
            "/api/v1/settings/auth/sub-users",
            json={
                "email": "sub2a@example.com",
                "full_name": "Sub User 2A",
                "password": "SubPass123!"
            },
            headers={"Authorization": f"Bearer {access_token}"}
        )
        assert response1.status_code == 201

        # Create second sub-user (will now see first one in DB)
        response2 = await async_client.post(
            "/api/v1/settings/auth/sub-users",
            json={
                "email": "sub2b@example.com",
                "full_name": "Sub User 2B",
                "password": "SubPass123!"
            },
            headers={"Authorization": f"Bearer {access_token}"}
        )
        assert response2.status_code == 201
        assert response2.json()["email"] == "sub2b@example.com"

    @pytest.mark.asyncio
    async def test_create_third_sub_user_fails(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        seed_organization
    ):
        """✅ Test: Cannot create more than 2 sub-users per parent."""
        # Create parent user
        parent = User(
            email="parent3@example.com",
            password_hash=pwd_hasher.hash("Password123!"),
            full_name="Parent User 3",
            organization_id=seed_organization.id,
            is_active=True
        )
        db_session.add(parent)
        await db_session.flush()  # Flush so login endpoint can see parent

        # Login as parent
        login_response = await async_client.post(
            "/api/v1/settings/auth/login",
            json={"email": "parent3@example.com", "password": "Password123!"}
        )
        access_token = login_response.json()["access_token"]

        # Create first sub-user
        await async_client.post(
            "/api/v1/settings/auth/sub-users",
            json={"email": "sub3a@example.com", "full_name": "Sub 3A", "password": "Pass123!"},
            headers={"Authorization": f"Bearer {access_token}"}
        )

        # Create second sub-user
        await async_client.post(
            "/api/v1/settings/auth/sub-users",
            json={"email": "sub3b@example.com", "full_name": "Sub 3B", "password": "Pass123!"},
            headers={"Authorization": f"Bearer {access_token}"}
        )

        # Try to create third sub-user (should fail)
        response = await async_client.post(
            "/api/v1/settings/auth/sub-users",
            json={"email": "sub3c@example.com", "full_name": "Sub 3C", "password": "Pass123!"},
            headers={"Authorization": f"Bearer {access_token}"}
        )

        assert response.status_code == 400
        assert "Maximum of 2 sub-users" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_sub_user_cannot_create_sub_user(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        seed_organization
    ):
        """✅ Test: Sub-users cannot create their own sub-users (no recursion)."""
        # Create parent user
        parent = User(
            email="parent4@example.com",
            password_hash=pwd_hasher.hash("Password123!"),
            full_name="Parent User 4",
            organization_id=seed_organization.id,
            is_active=True
        )
        db_session.add(parent)
        await db_session.flush()  # Flush so login endpoint can see parent

        # Login as parent and create sub-user
        login_response = await async_client.post(
            "/api/v1/settings/auth/login",
            json={"email": "parent4@example.com", "password": "Password123!"}
        )
        parent_token = login_response.json()["access_token"]

        await async_client.post(
            "/api/v1/settings/auth/sub-users",
            json={"email": "sub4@example.com", "full_name": "Sub 4", "password": "SubPass123!"},
            headers={"Authorization": f"Bearer {parent_token}"}
        )

        # Login as sub-user
        sub_login = await async_client.post(
            "/api/v1/settings/auth/login",
            json={"email": "sub4@example.com", "password": "SubPass123!"}
        )
        sub_token = sub_login.json()["access_token"]

        # Try to create sub-sub-user (should fail)
        response = await async_client.post(
            "/api/v1/settings/auth/sub-users",
            json={"email": "subsub@example.com", "full_name": "Sub Sub", "password": "Pass123!"},
            headers={"Authorization": f"Bearer {sub_token}"}
        )

        assert response.status_code == 400
        assert "cannot create their own sub-users" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_create_sub_user_duplicate_email_fails(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        seed_organization
    ):
        """✅ Test: Cannot create sub-user with duplicate email."""
        # Create parent user
        parent = User(
            email="parent5@example.com",
            password_hash=pwd_hasher.hash("Password123!"),
            full_name="Parent User 5",
            organization_id=seed_organization.id,
            is_active=True
        )
        db_session.add(parent)
        await db_session.flush()  # Flush so login endpoint can see parent

        # Login as parent
        login_response = await async_client.post(
            "/api/v1/settings/auth/login",
            json={"email": "parent5@example.com", "password": "Password123!"}
        )
        access_token = login_response.json()["access_token"]

        # Create first sub-user
        await async_client.post(
            "/api/v1/settings/auth/sub-users",
            json={"email": "duplicate@example.com", "full_name": "First", "password": "Pass123!"},
            headers={"Authorization": f"Bearer {access_token}"}
        )

        # Try to create second sub-user with same email
        response = await async_client.post(
            "/api/v1/settings/auth/sub-users",
            json={"email": "duplicate@example.com", "full_name": "Second", "password": "Pass123!"},
            headers={"Authorization": f"Bearer {access_token}"}
        )

        assert response.status_code == 400
        assert "Email already registered" in response.json()["detail"]


class TestSubUserListing:
    """Test listing sub-users functionality."""

    @pytest.mark.asyncio
    async def test_list_sub_users_empty(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        seed_organization
    ):
        """✅ Test: Parent with no sub-users gets empty list."""
        # Create parent user
        parent = User(
            email="parent6@example.com",
            password_hash=pwd_hasher.hash("Password123!"),
            full_name="Parent User 6",
            organization_id=seed_organization.id,
            is_active=True
        )
        db_session.add(parent)
        await db_session.flush()  # Flush so login endpoint can see parent

        # Login as parent
        login_response = await async_client.post(
            "/api/v1/settings/auth/login",
            json={"email": "parent6@example.com", "password": "Password123!"}
        )
        access_token = login_response.json()["access_token"]

        # List sub-users
        response = await async_client.get(
            "/api/v1/settings/auth/sub-users",
            headers={"Authorization": f"Bearer {access_token}"}
        )

        assert response.status_code == 200
        assert response.json() == []

    @pytest.mark.asyncio
    async def test_list_sub_users_success(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        seed_organization
    ):
        """✅ Test: Parent can list their sub-users."""
        # Create parent user
        parent = User(
            email="parent7@example.com",
            password_hash=pwd_hasher.hash("Password123!"),
            full_name="Parent User 7",
            organization_id=seed_organization.id,
            is_active=True
        )
        db_session.add(parent)
        await db_session.flush()  # Flush so login endpoint can see parent

        # Login as parent
        login_response = await async_client.post(
            "/api/v1/settings/auth/login",
            json={"email": "parent7@example.com", "password": "Password123!"}
        )
        access_token = login_response.json()["access_token"]

        # Create two sub-users
        await async_client.post(
            "/api/v1/settings/auth/sub-users",
            json={"email": "sub7a@example.com", "full_name": "Sub 7A", "password": "Pass123!", "role": "manager"},
            headers={"Authorization": f"Bearer {access_token}"}
        )
        await async_client.post(
            "/api/v1/settings/auth/sub-users",
            json={"email": "sub7b@example.com", "full_name": "Sub 7B", "password": "Pass123!", "role": "assistant"},
            headers={"Authorization": f"Bearer {access_token}"}
        )

        # List sub-users
        response = await async_client.get(
            "/api/v1/settings/auth/sub-users",
            headers={"Authorization": f"Bearer {access_token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        
        emails = {sub["email"] for sub in data}
        assert "sub7a@example.com" in emails
        assert "sub7b@example.com" in emails
        
        # Verify all have correct parent_user_id
        for sub in data:
            assert sub["parent_user_id"] == str(parent.id)
            assert sub["is_active"] is True


class TestSubUserDeletion:
    """Test deleting sub-users functionality."""

    @pytest.mark.asyncio
    async def test_delete_sub_user_success(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        seed_organization
    ):
        """✅ Test: Parent can delete their sub-user."""
        # Create parent user
        parent = User(
            email="parent8@example.com",
            password_hash=pwd_hasher.hash("Password123!"),
            full_name="Parent User 8",
            organization_id=seed_organization.id,
            is_active=True
        )
        db_session.add(parent)
        await db_session.flush()  # Flush so login endpoint can see parent

        # Login as parent
        login_response = await async_client.post(
            "/api/v1/settings/auth/login",
            json={"email": "parent8@example.com", "password": "Password123!"}
        )
        access_token = login_response.json()["access_token"]

        # Create sub-user
        create_response = await async_client.post(
            "/api/v1/settings/auth/sub-users",
            json={"email": "sub8@example.com", "full_name": "Sub 8", "password": "Pass123!"},
            headers={"Authorization": f"Bearer {access_token}"}
        )
        sub_user_id = create_response.json()["id"]

        # Delete sub-user
        response = await async_client.delete(
            f"/api/v1/settings/auth/sub-users/{sub_user_id}",
            headers={"Authorization": f"Bearer {access_token}"}
        )

        assert response.status_code == 204

        # Verify sub-user is gone
        list_response = await async_client.get(
            "/api/v1/settings/auth/sub-users",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        assert len(list_response.json()) == 0

    @pytest.mark.asyncio
    async def test_delete_other_users_sub_user_fails(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        seed_organization
    ):
        """✅ Test: Cannot delete another user's sub-user."""
        # Create two parent users
        parent1 = User(
            email="parent9a@example.com",
            password_hash=pwd_hasher.hash("Password123!"),
            full_name="Parent 9A",
            organization_id=seed_organization.id,
            is_active=True
        )
        parent2 = User(
            email="parent9b@example.com",
            password_hash=pwd_hasher.hash("Password123!"),
            full_name="Parent 9B",
            organization_id=seed_organization.id,
            is_active=True
        )
        db_session.add(parent1)
        db_session.add(parent2)
        await db_session.flush()  # Flush so login endpoint can see parent

        # Login as parent1 and create sub-user
        login1 = await async_client.post(
            "/api/v1/settings/auth/login",
            json={"email": "parent9a@example.com", "password": "Password123!"}
        )
        token1 = login1.json()["access_token"]

        create_response = await async_client.post(
            "/api/v1/settings/auth/sub-users",
            json={"email": "sub9@example.com", "full_name": "Sub 9", "password": "Pass123!"},
            headers={"Authorization": f"Bearer {token1}"}
        )
        sub_user_id = create_response.json()["id"]

        # Login as parent2 and try to delete parent1's sub-user
        login2 = await async_client.post(
            "/api/v1/settings/auth/login",
            json={"email": "parent9b@example.com", "password": "Password123!"}
        )
        token2 = login2.json()["access_token"]

        response = await async_client.delete(
            f"/api/v1/settings/auth/sub-users/{sub_user_id}",
            headers={"Authorization": f"Bearer {token2}"}
        )

        assert response.status_code == 403
        assert "only delete your own sub-users" in response.json()["detail"]


class TestSubUserLogin:
    """Test that sub-users can login independently."""

    @pytest.mark.asyncio
    async def test_sub_user_can_login(
        self,
        async_client: AsyncClient,
        db_session: AsyncSession,
        seed_organization
    ):
        """✅ Test: Sub-user can login with their own credentials."""
        # Create parent user
        parent = User(
            email="parent10@example.com",
            password_hash=pwd_hasher.hash("Password123!"),
            full_name="Parent User 10",
            organization_id=seed_organization.id,
            is_active=True
        )
        db_session.add(parent)
        await db_session.flush()  # Flush so login endpoint can see parent

        # Login as parent and create sub-user
        parent_login = await async_client.post(
            "/api/v1/settings/auth/login",
            json={"email": "parent10@example.com", "password": "Password123!"}
        )
        parent_token = parent_login.json()["access_token"]

        await async_client.post(
            "/api/v1/settings/auth/sub-users",
            json={"email": "sub10@example.com", "full_name": "Sub 10", "password": "SubPassword123!"},
            headers={"Authorization": f"Bearer {parent_token}"}
        )

        # Sub-user login
        sub_login = await async_client.post(
            "/api/v1/settings/auth/login",
            json={"email": "sub10@example.com", "password": "SubPassword123!"}
        )

        assert sub_login.status_code == 200
        data = sub_login.json()
        assert "access_token" in data
        assert "refresh_token" in data

        # Verify sub-user can access /auth/me
        me_response = await async_client.get(
            "/api/v1/settings/auth/me",
            headers={"Authorization": f"Bearer {data['access_token']}"}
        )

        assert me_response.status_code == 200
        me_data = me_response.json()
        assert me_data["email"] == "sub10@example.com"
        assert me_data["parent_user_id"] == str(parent.id)

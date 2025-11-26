from __future__ import annotations

from typing import Iterable, Optional
from datetime import datetime, timedelta, timezone

from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.rbac.permissions import PermissionCodes
from backend.core.auth.passwords import PasswordHasher
from backend.core.auth.jwt import create_token
from backend.core.settings.config import settings
from backend.modules.settings.models.settings_models import Permission, Role, RolePermission, User, UserRole, RefreshToken
from backend.modules.settings.repositories.settings_repositories import (
	OrganizationRepository,
	PermissionRepository,
	RolePermissionRepository,
	RoleRepository,
	UserRepository,
	UserRoleRepository,
)


pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")


class RBACService:
	def __init__(self, db: AsyncSession) -> None:
		self.db = db

	async def user_has_permissions(self, user_id, codes: Iterable[str]) -> bool:  # noqa: ANN001 - FastAPI dep compatibility
		stmt = (
			select(Permission.code)
			.join(RolePermission, RolePermission.permission_id == Permission.id)
			.join(Role, Role.id == RolePermission.role_id)
			.join(UserRole, UserRole.role_id == Role.id)
			.where(UserRole.user_id == user_id, Permission.code.in_(list(codes)))
		)
		result = await self.db.execute(stmt)
		found = {row[0] for row in result.all()}
		return set(codes).issubset(found)


class SeedService:
	def __init__(self, db: AsyncSession) -> None:
		self.db = db
		self.org_repo = OrganizationRepository(db)
		self.user_repo = UserRepository(db)
		self.role_repo = RoleRepository(db)
		self.perm_repo = PermissionRepository(db)
		self.role_perm_repo = RolePermissionRepository(db)
		self.user_role_repo = UserRoleRepository(db)

	async def seed_defaults(self, org_name: str, admin_email: str, admin_password: str) -> None:
		org = await self.org_repo.get_by_name(org_name) or await self.org_repo.create(org_name)
		# permissions
		perms = await self.perm_repo.ensure_many(PermissionCodes.all())
		# admin role
		role = await self.role_repo.get_by_name("admin") or await self.role_repo.create("admin", "Administrator")
		await self.role_perm_repo.ensure(role.id, [p.id for p in perms])
		# admin user
		user = await self.user_repo.get_by_email(admin_email)
		if not user:
			phash = pwd_context.hash(admin_password)
			user = await self.user_repo.create(org.id, admin_email, "Admin", phash)
		await self.user_role_repo.ensure(user.id, role.id)


class AuthService:
	def __init__(self, db: AsyncSession) -> None:
		self.db = db
		self.user_repo = UserRepository(db)
		self.org_repo = OrganizationRepository(db)
		self.hasher = PasswordHasher()

	async def signup(self, email: str, password: str, full_name: Optional[str] = None) -> User:
		if await self.user_repo.get_by_email(email):
			raise ValueError("User already exists")
		org = await self.org_repo.get_by_name("Cotton Corp") or await self.org_repo.create("Cotton Corp")
		hashed = self.hasher.hash(password)
		user = await self.user_repo.create(org.id, email, full_name, hashed)
		return user

	async def login(self, email: str, password: str) -> tuple[str, str, int]:
		user = await self.user_repo.get_by_email(email)
		if not user:
			raise ValueError("Invalid credentials")
		if not user.is_active:
			raise ValueError("User account is inactive")
		if not self.hasher.verify(password, user.password_hash):
			raise ValueError("Invalid credentials")
		access_minutes = settings.ACCESS_TOKEN_EXPIRES_MINUTES
		refresh_days = settings.REFRESH_TOKEN_EXPIRES_DAYS
		access = create_token(str(user.id), str(user.organization_id), minutes=access_minutes, token_type="access")
		refresh = create_token(str(user.id), str(user.organization_id), days=refresh_days, token_type="refresh")
		from backend.core.auth.jwt import decode_token
		payload = decode_token(refresh)
		rt = RefreshToken(
			user_id=user.id,
			jti=payload["jti"],
			expires_at=datetime.fromtimestamp(payload["exp"], tz=timezone.utc),
			revoked=False,
		)
		self.db.add(rt)
		await self.db.flush()
		return access, refresh, access_minutes * 60

	async def refresh(self, refresh_token_str: str) -> tuple[str, str, int]:
		from backend.core.auth.jwt import decode_token
		try:
			payload = decode_token(refresh_token_str)
		except Exception:
			raise ValueError("Invalid refresh token")
		if payload.get("type") != "refresh":
			raise ValueError("Invalid refresh token")
		jti = payload.get("jti")
		user_id = payload.get("sub")
		if not jti or not user_id:
			raise ValueError("Malformed token")
		result = await self.db.execute(select(RefreshToken).where(RefreshToken.jti == jti))
		token_row = result.scalar_one_or_none()
		if token_row is None or token_row.revoked:
			raise ValueError("Refresh token revoked or missing")
		if token_row.expires_at < datetime.now(timezone.utc):
			raise ValueError("Refresh token expired")
		# Rotate: revoke old, issue new refresh + access
		token_row.revoked = True
		access_minutes = settings.ACCESS_TOKEN_EXPIRES_MINUTES
		refresh_days = settings.REFRESH_TOKEN_EXPIRES_DAYS
		access = create_token(str(user_id), payload["org_id"], minutes=access_minutes, token_type="access")
		new_refresh = create_token(str(user_id), payload["org_id"], days=refresh_days, token_type="refresh")
		new_payload = decode_token(new_refresh)
		new_rt = RefreshToken(
			user_id=token_row.user_id,
			jti=new_payload["jti"],
			expires_at=datetime.fromtimestamp(new_payload["exp"], tz=timezone.utc),
			revoked=False,
		)
		self.db.add(new_rt)
		await self.db.flush()
		return access, new_refresh, access_minutes * 60

	async def logout(self, refresh_token_str: str) -> None:
		from backend.core.auth.jwt import decode_token
		try:
			payload = decode_token(refresh_token_str)
		except Exception:
			raise ValueError("Invalid refresh token")
		if payload.get("type") != "refresh":
			raise ValueError("Invalid refresh token")
		jti = payload.get("jti")
		if not jti:
			raise ValueError("Malformed token")
		result = await self.db.execute(select(RefreshToken).where(RefreshToken.jti == jti))
		token_row = result.scalar_one_or_none()
		if token_row and not token_row.revoked:
			token_row.revoked = True
			self.db.add(token_row)

	async def create_sub_user(
		self,
		parent_user_id: str,
		email: str,
		password: str,
		full_name: str,
		role: Optional[str] = None
	) -> User:
		"""Create a sub-user for the authenticated parent user."""
		from uuid import UUID
		
		# Check if email already exists
		if await self.user_repo.get_by_email(email):
			raise ValueError("Email already registered")
		
		# Hash password
		hashed = self.hasher.hash(password)
		
		# Create sub-user (repository enforces max 2 limit and no recursive sub-users)
		sub_user = await self.user_repo.create_sub_user(
			parent_user_id=UUID(parent_user_id),
			email=email,
			full_name=full_name,
			password_hash=hashed,
			role=role
		)
		await self.db.flush()
		return sub_user

	async def get_sub_users(self, parent_user_id: str) -> list[User]:
		"""Get all sub-users for a parent user."""
		from uuid import UUID
		return await self.user_repo.get_sub_users(UUID(parent_user_id))

	async def delete_sub_user(self, parent_user_id: str, sub_user_id: str) -> None:
		"""Delete a sub-user (only if owned by parent)."""
		from uuid import UUID
		
		sub_user = await self.user_repo.get_by_id(UUID(sub_user_id))
		if not sub_user:
			raise ValueError("Sub-user not found")
		
		if str(sub_user.parent_user_id) != parent_user_id:
			raise ValueError("You can only delete your own sub-users")
		
		await self.db.delete(sub_user)
		await self.db.flush()


from __future__ import annotations

from typing import Iterable, Optional
from datetime import datetime, timedelta, timezone

from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.orm import Session

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
	def __init__(self, db: Session) -> None:
		self.db = db

	def user_has_permissions(self, user_id, codes: Iterable[str]) -> bool:  # noqa: ANN001 - FastAPI dep compatibility
		stmt = (
			select(Permission.code)
			.join(RolePermission, RolePermission.permission_id == Permission.id)
			.join(Role, Role.id == RolePermission.role_id)
			.join(UserRole, UserRole.role_id == Role.id)
			.where(UserRole.user_id == user_id, Permission.code.in_(list(codes)))
		)
		found = {row[0] for row in self.db.execute(stmt).all()}
		return set(codes).issubset(found)


class SeedService:
	def __init__(self, db: Session) -> None:
		self.db = db
		self.org_repo = OrganizationRepository(db)
		self.user_repo = UserRepository(db)
		self.role_repo = RoleRepository(db)
		self.perm_repo = PermissionRepository(db)
		self.role_perm_repo = RolePermissionRepository(db)
		self.user_role_repo = UserRoleRepository(db)

	def seed_defaults(self, org_name: str, admin_email: str, admin_password: str) -> None:
		org = self.org_repo.get_by_name(org_name) or self.org_repo.create(org_name)
		# permissions
		perms = self.perm_repo.ensure_many(PermissionCodes.all())
		# admin role
		role = self.role_repo.get_by_name("admin") or self.role_repo.create("admin", "Administrator")
		self.role_perm_repo.ensure(role.id, [p.id for p in perms])
		# admin user
		user = self.user_repo.get_by_email(admin_email)
		if not user:
			phash = pwd_context.hash(admin_password)
			user = self.user_repo.create(org.id, admin_email, "Admin", phash)
		self.user_role_repo.ensure(user.id, role.id)


class AuthService:
	def __init__(self, db: Session) -> None:
		self.db = db
		self.user_repo = UserRepository(db)
		self.org_repo = OrganizationRepository(db)
		self.hasher = PasswordHasher()

	def signup(self, email: str, password: str, full_name: Optional[str] = None) -> User:
		if self.user_repo.get_by_email(email):
			raise ValueError("User already exists")
		org = self.org_repo.get_by_name("Cotton Corp") or self.org_repo.create("Cotton Corp")
		hashed = self.hasher.hash(password)
		user = self.user_repo.create(org.id, email, full_name, hashed)
		return user

	def login(self, email: str, password: str) -> tuple[str, str, int]:
		user = self.user_repo.get_by_email(email)
		if not user:
			raise ValueError("Invalid credentials")
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
		self.db.flush()
		return access, refresh, access_minutes * 60

	def refresh(self, refresh_token_str: str) -> tuple[str, str, int]:
		from backend.core.auth.jwt import decode_token
		payload = decode_token(refresh_token_str)
		if payload.get("type") != "refresh":
			raise ValueError("Invalid refresh token")
		jti = payload.get("jti")
		user_id = payload.get("sub")
		if not jti or not user_id:
			raise ValueError("Malformed token")
		token_row = self.db.execute(select(RefreshToken).where(RefreshToken.jti == jti)).scalar_one_or_none()
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
		self.db.flush()
		return access, new_refresh, access_minutes * 60

	def logout(self, refresh_token_str: str) -> None:
		from backend.core.auth.jwt import decode_token
		payload = decode_token(refresh_token_str)
		if payload.get("type") != "refresh":
			raise ValueError("Invalid refresh token")
		jti = payload.get("jti")
		if not jti:
			raise ValueError("Malformed token")
		token_row = self.db.execute(select(RefreshToken).where(RefreshToken.jti == jti)).scalar_one_or_none()
		if token_row and not token_row.revoked:
			token_row.revoked = True
			self.db.add(token_row)


from __future__ import annotations

from typing import Iterable, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.modules.settings.models.settings_models import (
	Organization,
	Location,
	Permission,
	Role,
	RolePermission,
	User,
	UserRole,
	RefreshToken,
)


class BaseRepo:
	def __init__(self, db: Session) -> None:
		self.db = db


class OrganizationRepository(BaseRepo):
	def get_by_name(self, name: str) -> Optional[Organization]:
		return self.db.execute(select(Organization).where(Organization.name == name)).scalar_one_or_none()

	def create(self, name: str, code: Optional[str] = None) -> Organization:
		obj = Organization(name=name, code=code)
		self.db.add(obj)
		self.db.flush()
		return obj


class UserRepository(BaseRepo):
	def get_by_id(self, user_id: str | UUID) -> Optional[User]:
		return self.db.get(User, user_id)

	def get_by_email(self, email: str) -> Optional[User]:
		return self.db.execute(select(User).where(User.email == email)).scalar_one_or_none()

	def get_first(self) -> Optional[User]:
		return self.db.execute(select(User).limit(1)).scalar_one_or_none()

	def create(self, organization_id: UUID, email: str, full_name: Optional[str], password_hash: str) -> User:
		obj = User(organization_id=organization_id, email=email, full_name=full_name, password_hash=password_hash)
		self.db.add(obj)
		self.db.flush()
		return obj


class RoleRepository(BaseRepo):
	def get_by_name(self, name: str) -> Optional[Role]:
		return self.db.execute(select(Role).where(Role.name == name)).scalar_one_or_none()

	def create(self, name: str, description: Optional[str] = None) -> Role:
		obj = Role(name=name, description=description)
		self.db.add(obj)
		self.db.flush()
		return obj


class PermissionRepository(BaseRepo):
	def get_by_code(self, code: str) -> Optional[Permission]:
		return self.db.execute(select(Permission).where(Permission.code == code)).scalar_one_or_none()

	def ensure_many(self, codes: Iterable[str]) -> list[Permission]:
		existing = self.db.execute(select(Permission).where(Permission.code.in_(list(codes)))).scalars().all()
		existing_codes = {p.code for p in existing}
		created: list[Permission] = []
		for code in codes:
			if code not in existing_codes:
				p = Permission(code=code)
				self.db.add(p)
				created.append(p)
		if created:
			self.db.flush()
		return existing + created


class RolePermissionRepository(BaseRepo):
	def ensure(self, role_id: UUID, permission_ids: Iterable[UUID]) -> None:
		for pid in permission_ids:
			rp = self.db.get(RolePermission, {"role_id": role_id, "permission_id": pid})
			if rp is None:
				self.db.add(RolePermission(role_id=role_id, permission_id=pid))


class UserRoleRepository(BaseRepo):
	def ensure(self, user_id: UUID, role_id: UUID) -> None:
		ur = self.db.get(UserRole, {"user_id": user_id, "role_id": role_id})
		if ur is None:
			self.db.add(UserRole(user_id=user_id, role_id=role_id))


class RefreshTokenRepository(BaseRepo):
	def get_by_jti(self, jti: str) -> RefreshToken | None:
		return self.db.execute(select(RefreshToken).where(RefreshToken.jti == jti)).scalar_one_or_none()

	def create(self, user_id: UUID, jti: str, expires_at) -> RefreshToken:  # noqa: ANN001
		obj = RefreshToken(user_id=user_id, jti=jti, expires_at=expires_at, revoked=False)
		self.db.add(obj)
		self.db.flush()
		return obj

	def revoke(self, token: RefreshToken) -> None:
		token.revoked = True
		self.db.add(token)


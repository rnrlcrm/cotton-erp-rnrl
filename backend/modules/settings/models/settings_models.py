from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
	Boolean,
	CheckConstraint,
	Column,
	DateTime,
	ForeignKey,
	String,
	Text,
	UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, Mapped, mapped_column

from backend.db.session import Base
from backend.modules.settings.organization.models import Organization


def utcnow() -> datetime:
	return datetime.now(timezone.utc)


# Organization model moved to backend.modules.settings.organization.models
# to avoid duplication with the more complete implementation there

# Location model moved to backend.modules.settings.locations.models
# New implementation with Google Maps API integration


class Permission(Base):
	__tablename__ = "permissions"

	id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
	code: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
	description: Mapped[str | None] = mapped_column(String(255), nullable=True)


class Role(Base):
	__tablename__ = "roles"

	id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
	name: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
	description: Mapped[str | None] = mapped_column(String(255), nullable=True)


class RolePermission(Base):
	__tablename__ = "role_permissions"
	__table_args__ = (
		UniqueConstraint("role_id", "permission_id", name="uq_role_permission"),
	)

	role_id: Mapped[uuid.UUID] = mapped_column(
		UUID(as_uuid=True), ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True
	)
	permission_id: Mapped[uuid.UUID] = mapped_column(
		UUID(as_uuid=True), ForeignKey("permissions.id", ondelete="CASCADE"), primary_key=True
	)


class User(Base):
	__tablename__ = "users"
	__table_args__ = (
		CheckConstraint("email <> ''", name="ck_user_email_nonempty"),
	)

	id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
	organization_id: Mapped[uuid.UUID] = mapped_column(
		UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False
	)
	email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
	full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
	password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
	is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
	created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
	updated_at: Mapped[datetime] = mapped_column(
		DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
	)

	organization: Mapped[Organization] = relationship("Organization", back_populates="users")


class UserRole(Base):
	__tablename__ = "user_roles"
	__table_args__ = (
		UniqueConstraint("user_id", "role_id", name="uq_user_role"),
	)

	user_id: Mapped[uuid.UUID] = mapped_column(
		UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
	)
	role_id: Mapped[uuid.UUID] = mapped_column(
		UUID(as_uuid=True), ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True
	)


class RefreshToken(Base):
	__tablename__ = "refresh_tokens"

	id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
	user_id: Mapped[uuid.UUID] = mapped_column(
		UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
	)
	jti: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
	expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
	revoked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


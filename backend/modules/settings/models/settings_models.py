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
from sqlalchemy.dialects.postgresql import ARRAY, UUID
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
		CheckConstraint("email IS NOT NULL OR mobile_number IS NOT NULL", name="ck_user_has_email_or_mobile"),
		# Data isolation constraints based on user_type
		CheckConstraint(
			"""
			(user_type = 'SUPER_ADMIN' AND business_partner_id IS NULL AND organization_id IS NULL) OR
			(user_type = 'INTERNAL' AND business_partner_id IS NULL AND organization_id IS NOT NULL) OR
			(user_type = 'EXTERNAL' AND business_partner_id IS NOT NULL AND organization_id IS NULL)
			""",
			name="ck_user_type_isolation"
		),
	)

	id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
	
	# Data Isolation Fields
	user_type: Mapped[str] = mapped_column(
		String(20),
		nullable=False,
		default='INTERNAL',
		comment="SUPER_ADMIN, INTERNAL, or EXTERNAL"
	)
	business_partner_id: Mapped[uuid.UUID | None] = mapped_column(
		UUID(as_uuid=True),
		ForeignKey("business_partners.id", ondelete="RESTRICT"),
		nullable=True,
		comment="For EXTERNAL users only"
	)
	organization_id: Mapped[uuid.UUID | None] = mapped_column(
		UUID(as_uuid=True),
		ForeignKey("organizations.id", ondelete="RESTRICT"),
		nullable=True,
		comment="For INTERNAL users only"
	)
	allowed_modules: Mapped[list[str] | None] = mapped_column(
		ARRAY(String),
		nullable=True,
		comment="RBAC: List of modules user can access"
	)
	
	# Existing Fields
	email: Mapped[str | None] = mapped_column(String(255), nullable=True, unique=True)
	mobile_number: Mapped[str | None] = mapped_column(
		String(20),
		nullable=True,
		unique=True,
		index=True,
		comment="Mobile number for OTP authentication"
	)
	full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
	password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="Null for OTP-only users")
	is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
	is_verified: Mapped[bool] = mapped_column(
		Boolean,
		nullable=False,
		default=False,
		comment="Mobile/email verified via OTP"
	)
	role: Mapped[str | None] = mapped_column(
		String(50),
		nullable=True,
		comment="User role: partner_user, manager, director, etc."
	)
	created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
	updated_at: Mapped[datetime] = mapped_column(
		DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
	)

	# Relationships
	# organization relationship commented out until Organization.users backref is added
	# organization: Mapped[Organization | None] = relationship("Organization", back_populates="users")
	# business_partner relationship will be added when BP module is fully implemented


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


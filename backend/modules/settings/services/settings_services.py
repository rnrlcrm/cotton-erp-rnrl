from __future__ import annotations

from typing import Iterable, Optional
from datetime import datetime, timedelta, timezone
import json

from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as redis

from backend.core.auth.capabilities.definitions import Capabilities
from backend.core.auth.passwords import PasswordHasher
from backend.core.auth.jwt import create_token
from backend.core.settings.config import settings
from backend.core.outbox import OutboxRepository
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
	def __init__(self, db: AsyncSession, redis_client: Optional[redis.Redis] = None) -> None:
		self.db = db
		self.redis = redis_client
		self.outbox_repo = OutboxRepository(db)

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
	def __init__(self, db: AsyncSession, redis_client: Optional[redis.Redis] = None) -> None:
		self.db = db
		self.redis = redis_client
		self.outbox_repo = OutboxRepository(db)
		self.org_repo = OrganizationRepository(db)
		self.user_repo = UserRepository(db)
		self.role_repo = RoleRepository(db)
		self.perm_repo = PermissionRepository(db)
		self.role_perm_repo = RolePermissionRepository(db)
		self.user_role_repo = UserRoleRepository(db)

	async def seed_defaults(self, org_name: str, admin_email: str, admin_password: str) -> None:
		org = await self.org_repo.get_by_name(org_name) or await self.org_repo.create(org_name)
		# permissions - use all Capabilities enum values
		all_capability_codes = [c.value for c in Capabilities]
		perms = await self.perm_repo.ensure_many(all_capability_codes)
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
	def __init__(self, db: AsyncSession, redis_client: Optional[redis.Redis] = None) -> None:
		self.db = db
		self.redis = redis_client
		self.outbox_repo = OutboxRepository(db)
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
		"""
		Login for INTERNAL users (backoffice) only.
		EXTERNAL users (business partners) must use mobile OTP.
		"""
		user = await self.user_repo.get_by_email(email)
		if not user:
			raise ValueError("Invalid credentials")
		
		# Enforce user_type: Only INTERNAL and SUPER_ADMIN can login with email/password
		if user.user_type not in ['INTERNAL', 'SUPER_ADMIN']:
			raise ValueError("EXTERNAL users must login via mobile OTP")
		
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

	async def logout_all_devices(self, user_id: str) -> int:
		"""
		Logout user from all devices by revoking all refresh tokens.
		Returns the number of tokens revoked.
		"""
		from uuid import UUID
		
		# Revoke all non-revoked refresh tokens for this user
		result = await self.db.execute(
			select(RefreshToken).where(
				RefreshToken.user_id == UUID(user_id),
				RefreshToken.revoked == False
			)
		)
		tokens = result.scalars().all()
		
		count = 0
		for token in tokens:
			token.revoked = True
			self.db.add(token)
			count += 1
		
		await self.db.flush()
		return count

	async def revoke_all_sessions(self, user_id: str) -> None:
		"""
		Revoke all sessions for a user (called on password change).
		This forces re-authentication on all devices.
		"""
		await self.logout_all_devices(user_id)

	async def create_sub_user(
		self,
		parent_user_id: str,
		mobile_number: str,
		full_name: str,
		pin: Optional[str] = None,
		role: Optional[str] = None
	) -> User:
		"""
		Create a sub-user for the authenticated parent user (business partner).
		Sub-users login via mobile OTP or secure PIN.
		"""
		from uuid import UUID
		import re
		
		# Validate mobile number format
		if not re.match(r'^\+?[1-9]\d{1,14}$', mobile_number):
			raise ValueError("Invalid mobile number format")
		
		# Check if mobile already exists
		existing = await self.db.execute(
			select(User).where(User.mobile_number == mobile_number)
		)
		if existing.scalar_one_or_none():
			raise ValueError("Mobile number already registered")
		
		# Hash PIN if provided
		pin_hash = None
		if pin:
			if not re.match(r'^\d{4,6}$', pin):
				raise ValueError("PIN must be 4-6 digits")
			pin_hash = self.hasher.hash(pin)
		
		# Create sub-user (repository enforces max 2 limit and validations)
		sub_user = await self.user_repo.create_sub_user(
			parent_user_id=UUID(parent_user_id),
			mobile_number=mobile_number,
			full_name=full_name,
			pin_hash=pin_hash,
			role=role
		)
		await self.db.flush()
		
		# Emit event for audit trail
		sub_user.emit_event(
			event_type="sub_user.created",
			user_id=UUID(parent_user_id),
			data={
				"sub_user_id": str(sub_user.id),
				"mobile_number": mobile_number,
				"full_name": full_name,
				"role": role,
				"business_partner_id": str(sub_user.business_partner_id)
			}
		)
		await sub_user.flush_events(self.db)
		
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
		
		# Emit event before deletion
		sub_user.emit_event(
			event_type="sub_user.deleted",
			user_id=UUID(parent_user_id),
			data={
				"sub_user_id": sub_user_id,
				"mobile_number": sub_user.mobile_number,
				"business_partner_id": str(sub_user.business_partner_id)
			}
		)
		await sub_user.flush_events(self.db)
		
		await self.db.delete(sub_user)
		await self.db.flush()

	async def disable_sub_user(self, parent_user_id: str, sub_user_id: str) -> User:
		"""Disable a sub-user (only if owned by parent)."""
		from uuid import UUID
		
		sub_user = await self.user_repo.get_by_id(UUID(sub_user_id))
		if not sub_user:
			raise ValueError("Sub-user not found")
		
		if str(sub_user.parent_user_id) != parent_user_id:
			raise ValueError("You can only disable your own sub-users")
		
		await self.user_repo.disable_sub_user(UUID(sub_user_id))
		
		# Emit event
		sub_user.emit_event(
			event_type="sub_user.disabled",
			user_id=UUID(parent_user_id),
			data={
				"sub_user_id": sub_user_id,
				"mobile_number": sub_user.mobile_number
			}
		)
		await sub_user.flush_events(self.db)
		
		return sub_user

	async def enable_sub_user(self, parent_user_id: str, sub_user_id: str) -> User:
		"""Enable a sub-user (only if owned by parent)."""
		from uuid import UUID
		
		sub_user = await self.user_repo.get_by_id(UUID(sub_user_id))
		if not sub_user:
			raise ValueError("Sub-user not found")
		
		if str(sub_user.parent_user_id) != parent_user_id:
			raise ValueError("You can only enable your own sub-users")
		
		await self.user_repo.enable_sub_user(UUID(sub_user_id))
		
		# Emit event
		sub_user.emit_event(
			event_type="sub_user.enabled",
			user_id=UUID(parent_user_id),
			data={
				"sub_user_id": sub_user_id,
				"mobile_number": sub_user.mobile_number
			}
		)
		await sub_user.flush_events(self.db)
		
		return sub_user

	async def setup_2fa(self, user_id: str, pin: str) -> None:
		"""Enable 2FA and set PIN for a user."""
		from uuid import UUID
		import re
		
		# Validate PIN (4-6 digits)
		if not re.match(r'^\d{4,6}$', pin):
			raise ValueError("PIN must be 4-6 digits")
		
		# Hash the PIN
		pin_hash = self.hasher.hash(pin)
		
		# Enable 2FA
		await self.user_repo.enable_2fa(UUID(user_id), pin_hash)

	async def verify_pin(self, email: str, pin: str) -> tuple[str, str, int]:
		"""Verify 2FA PIN and issue tokens."""
		user = await self.user_repo.get_by_email(email)
		if not user:
			raise ValueError("Invalid credentials")
		
		if not user.two_fa_enabled or not user.pin_hash:
			raise ValueError("2FA not enabled for this user")
		
		if not self.hasher.verify(pin, user.pin_hash):
			raise ValueError("Invalid PIN")
		
		# Issue tokens
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

	async def disable_2fa(self, user_id: str) -> None:
		"""Disable 2FA for a user."""
		from uuid import UUID
		await self.user_repo.disable_2fa(UUID(user_id))
	
	async def login_with_lockout(self, email: str, password: str, lockout_service) -> tuple[User, str, str, int, bool]:
		"""
		Login with account lockout protection.
		Returns: (user, access_token, refresh_token, expires_in, requires_2fa)
		Raises: ValueError with specific error messages for the router to handle
		"""
		# Check if account is locked
		is_locked, ttl = await lockout_service.is_locked(email)
		if is_locked:
			raise ValueError(f"Account locked due to too many failed login attempts. Try again in {ttl // 60} minutes.")
		
		# Get user
		user = await self.user_repo.get_by_email(email)
		if not user:
			await lockout_service.record_failed_attempt(email)
			raise ValueError("Invalid credentials")
		
		# Check user type
		if user.user_type not in ['INTERNAL', 'SUPER_ADMIN']:
			raise ValueError("EXTERNAL users must login via mobile OTP")
		
		if not user.is_active:
			raise ValueError("User account is inactive")
		
		# Verify password
		if not self.hasher.verify(password, user.password_hash):
			lockout_info = await lockout_service.record_failed_attempt(email)
			if lockout_info["locked"]:
				raise ValueError(lockout_info["message"])
			raise ValueError(f"Invalid credentials. {lockout_info['remaining_attempts']} attempts remaining.")
		
		# Clear failed attempts on successful password verification
		await lockout_service.clear_failed_attempts(email)
		
		# Check if 2FA is enabled
		if user.two_fa_enabled:
			return (user, "", "", 0, True)  # Signal 2FA required
		
		# Generate tokens
		access_minutes = settings.ACCESS_TOKEN_EXPIRES_MINUTES
		refresh_days = settings.REFRESH_TOKEN_EXPIRES_DAYS
		access = create_token(str(user.id), str(user.organization_id), minutes=access_minutes, token_type="access")
		refresh = create_token(str(user.id), str(user.organization_id), days=refresh_days, token_type="refresh")
		
		# Store refresh token
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
		
		return (user, access, refresh, access_minutes * 60, False)
	
	async def login_with_otp(self, mobile_number: str) -> tuple[str, str, int]:
		"""
		Login for EXTERNAL users with OTP.
		Returns: (access_token, refresh_token, expires_in)
		"""
		# Get user by mobile number
		user = await self.user_repo.get_by_mobile(mobile_number)
		
		if not user:
			raise ValueError("User not found. Please complete partner onboarding first.")
		
		# Verify user is EXTERNAL type
		if user.user_type not in ['EXTERNAL']:
			raise ValueError("This login method is only for EXTERNAL users (business partners). INTERNAL users must use email/password.")
		
		if not user.is_active:
			raise ValueError("User account is inactive. Please contact support.")
		
		# Use business_partner_id for EXTERNAL users
		org_or_partner_id = str(user.business_partner_id) if user.business_partner_id else None
		
		if not org_or_partner_id:
			raise ValueError("User has no associated business partner")
		
		# Generate tokens
		access_minutes = settings.ACCESS_TOKEN_EXPIRES_MINUTES
		refresh_days = settings.REFRESH_TOKEN_EXPIRES_DAYS
		
		access = create_token(str(user.id), org_or_partner_id, minutes=access_minutes, token_type="access")
		refresh = create_token(str(user.id), org_or_partner_id, days=refresh_days, token_type="refresh")
		
		# Store refresh token
		from backend.core.auth.jwt import decode_token
		payload_data = decode_token(refresh)
		rt = RefreshToken(
			user_id=user.id,
			jti=payload_data["jti"],
			expires_at=datetime.fromtimestamp(payload_data["exp"], tz=timezone.utc),
			revoked=False,
		)
		self.db.add(rt)
		await self.db.flush()
		
		return (access, refresh, access_minutes * 60)








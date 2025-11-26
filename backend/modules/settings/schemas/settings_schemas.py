from __future__ import annotations

from datetime import datetime
from typing import Optional
import re

from pydantic import BaseModel, EmailStr, Field, field_validator


class SignupRequest(BaseModel):
	email: EmailStr
	password: str = Field(min_length=8, max_length=128)
	full_name: Optional[str] = None


class LoginRequest(BaseModel):
	email: EmailStr
	password: str


class TokenResponse(BaseModel):
	access_token: str
	refresh_token: str
	token_type: str = "Bearer"
	expires_in: int


class UserOut(BaseModel):
	id: str
	email: EmailStr
	full_name: Optional[str] = None
	organization_id: str
	is_active: bool
	parent_user_id: Optional[str] = None
	role: Optional[str] = None
	created_at: datetime
	updated_at: datetime

	class Config:
		from_attributes = True


class CreateSubUserRequest(BaseModel):
	"""Request to create a sub-user (EXTERNAL user under business partner)."""
	mobile_number: str = Field(
		pattern=r'^\+[1-9]\d{1,14}$',
		description="Mobile number in E.164 format (e.g., +919876543210)"
	)
	full_name: str
	pin: Optional[str] = Field(None, min_length=4, max_length=6, pattern=r'^\d+$')
	role: Optional[str] = None


class SubUserOut(BaseModel):
	"""Sub-user response."""
	id: str
	mobile_number: str
	full_name: Optional[str]
	role: Optional[str]
	is_active: bool
	parent_user_id: str
	business_partner_id: str
	created_at: datetime
	updated_at: datetime

	class Config:
		from_attributes = True


class Setup2FARequest(BaseModel):
	"""Request to setup or update 2FA PIN."""
	pin: str = Field(min_length=4, max_length=6, pattern=r'^\d+$')


class Verify2FARequest(BaseModel):
	"""Request to verify 2FA PIN during login."""
	email: EmailStr
	pin: str = Field(min_length=4, max_length=6, pattern=r'^\d+$')


class TwoFAStatusResponse(BaseModel):
	"""Response for 2FA status."""
	two_fa_enabled: bool
	message: str


class LoginWith2FAResponse(BaseModel):
	"""Response when 2FA is enabled - requires PIN verification."""
	two_fa_required: bool
	message: str
	email: EmailStr


class SendOTPRequest(BaseModel):
	"""Request to send OTP to mobile number for EXTERNAL user login."""
	mobile_number: str = Field(
		pattern=r'^\+[1-9]\d{1,14}$',
		description="Mobile number in E.164 format (e.g., +919876543210)"
	)
	country_code: str = Field(default="+91")


class VerifyOTPRequest(BaseModel):
	"""Request to verify OTP for EXTERNAL user login."""
	mobile_number: str = Field(
		pattern=r'^\+[1-9]\d{1,14}$',
		description="Mobile number in E.164 format (e.g., +919876543210)"
	)
	otp: str = Field(min_length=6, max_length=6, pattern=r'^\d+$')


class OTPResponse(BaseModel):
	"""Response after sending OTP."""
	success: bool
	message: str
	otp_sent_at: Optional[datetime] = None
	expires_in_seconds: int = 300


class InternalUserSignupRequest(BaseModel):
	"""Signup request for INTERNAL users (backoffice) with password policy."""
	email: EmailStr
	password: str = Field(
		min_length=8,
		max_length=128,
		description="Password must be at least 8 characters with 1 uppercase, 1 lowercase, and 1 number"
	)
	full_name: Optional[str] = None

	@field_validator('password')
	@classmethod
	def validate_password_strength(cls, v: str) -> str:
		"""Enforce password policy for INTERNAL users: min 8 chars, 1 uppercase, 1 lowercase, 1 number."""
		if len(v) < 8:
			raise ValueError('Password must be at least 8 characters long')
		if not re.search(r'[A-Z]', v):
			raise ValueError('Password must contain at least one uppercase letter')
		if not re.search(r'[a-z]', v):
			raise ValueError('Password must contain at least one lowercase letter')
		if not re.search(r'\d', v):
			raise ValueError('Password must contain at least one number')
		return v


class ChangePasswordRequest(BaseModel):
	"""Request to change password for INTERNAL users."""
	old_password: str
	new_password: str = Field(
		min_length=8,
		max_length=128,
		description="Password must be at least 8 characters with 1 uppercase, 1 lowercase, and 1 number"
	)

	@field_validator('new_password')
	@classmethod
	def validate_password_strength(cls, v: str) -> str:
		"""Enforce password policy for INTERNAL users."""
		if len(v) < 8:
			raise ValueError('Password must be at least 8 characters long')
		if not re.search(r'[A-Z]', v):
			raise ValueError('Password must contain at least one uppercase letter')
		if not re.search(r'[a-z]', v):
			raise ValueError('Password must contain at least one lowercase letter')
		if not re.search(r'\d', v):
			raise ValueError('Password must contain at least one number')
		return v

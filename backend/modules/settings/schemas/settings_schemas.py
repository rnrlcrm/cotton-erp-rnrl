from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


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
	"""Request to create a sub-user."""
	email: EmailStr
	full_name: str
	password: str = Field(min_length=8, max_length=128)
	role: Optional[str] = None


class SubUserOut(BaseModel):
	"""Sub-user response."""
	id: str
	email: EmailStr
	full_name: Optional[str]
	role: Optional[str]
	is_active: bool
	parent_user_id: str
	created_at: datetime
	updated_at: datetime

	class Config:
		from_attributes = True


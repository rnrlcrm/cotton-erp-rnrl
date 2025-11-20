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
	created_at: datetime
	updated_at: datetime


"""
Pydantic schemas for authentication: registration, login, and the current
user's public profile. These validate every request body and shape every
response — raw ORM objects never go straight into an HTTP response.
"""

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.enums import UserRole


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128, description="Minimum 8 characters.")
    full_name: str = Field(min_length=1, max_length=255)
    phone: Optional[str] = Field(default=None, max_length=30)
    role: UserRole

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "email": "hotel.manager@example.com",
                "password": "strongpassword123",
                "full_name": "Asha Rao",
                "phone": "+91-9876543210",
                "role": "PROVIDER",
            }
        }
    )


class LoginRequest(BaseModel):
    email: EmailStr
    password: str

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "email": "hotel.manager@example.com",
                "password": "strongpassword123",
            }
        }
    )


class RefreshRequest(BaseModel):
    refresh_token: str

    model_config = ConfigDict(
        json_schema_extra={"example": {"refresh_token": "<paste the refresh_token from /login here>"}}
    )


class UserPublic(BaseModel):
    """Safe, public-facing representation of a User — never includes the password hash."""

    id: uuid.UUID
    email: EmailStr
    full_name: str
    phone: Optional[str] = None
    role: UserRole
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TokenData(BaseModel):
    """Returned by /login: both tokens, plus the user's profile."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserPublic


class RefreshedTokenData(BaseModel):
    """
    Returned by /refresh: a new access/refresh pair (rotated — the old
    refresh token should be discarded by the client). No `user` field,
    since the caller already has it from /login and this is meant to be a
    cheap, frequent call.
    """

    access_token: str
    refresh_token: str
    token_type: str = "bearer"

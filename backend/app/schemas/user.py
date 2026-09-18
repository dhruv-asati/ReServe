"""
Pydantic schemas for user profile management:

    GET /api/users/me
    PUT /api/users/me
    GET /api/users/{user_id}

`UserProfileOut` is the clean, public-facing shape returned by all three
endpoints — it never includes `hashed_password` or any other auth
internals, regardless of what's added to the User model later, because it
only lists the fields it wants to expose rather than deriving from the
ORM object's __dict__.
"""

import re
import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.enums import UserRole

# E.164-ish: optional leading '+', then 7-15 digits, allowing spaces/hyphens
# between digits (matches examples already used elsewhere in this API,
# e.g. "+91-9876543210").
_PHONE_RE = re.compile(r"^\+?[0-9][0-9\s\-]{5,19}$")


class UserProfileUpdate(BaseModel):
    """
    All fields optional — only the ones provided are changed. Used for
    PUT /api/users/me. A user may only ever update their own profile
    (enforced in the route/service, not here).
    """

    full_name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    phone: Optional[str] = Field(default=None, max_length=30)

    organization_name: Optional[str] = Field(default=None, max_length=255)
    organization_description: Optional[str] = Field(default=None, max_length=5000)
    profile_image_url: Optional[str] = Field(default=None, max_length=1000)

    address: Optional[str] = Field(default=None, max_length=500)
    latitude: Optional[float] = Field(default=None, ge=-90, le=90)
    longitude: Optional[float] = Field(default=None, ge=-180, le=180)

    @field_validator("phone")
    @classmethod
    def _validate_phone(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        v = v.strip()
        if not v:
            return None
        if not _PHONE_RE.match(v):
            raise ValueError(
                "phone must contain 7-20 digits, optionally starting with '+' and "
                "using spaces or hyphens as separators (e.g. '+91-9876543210')."
            )
        return v

    @field_validator("profile_image_url")
    @classmethod
    def _validate_profile_image_url(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        v = v.strip()
        if not v:
            return None
        if not (v.startswith("http://") or v.startswith("https://")):
            raise ValueError("profile_image_url must be a valid http(s) URL.")
        return v

    @field_validator("full_name", "organization_name", "address")
    @classmethod
    def _reject_blank(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not v.strip():
            raise ValueError("This field cannot be blank.")
        return v

    @model_validator(mode="after")
    def _validate_lat_lng_pair(self) -> "UserProfileUpdate":
        # Allow either both coordinates set or neither, so a lat/lng pair
        # is never stored half-updated (e.g. new latitude with a stale
        # longitude left over from a previous address).
        if (self.latitude is None) != (self.longitude is None):
            raise ValueError("latitude and longitude must be provided together.")
        return self

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "full_name": "Asha Rao",
                "phone": "+91-9876543210",
                "organization_name": "Grand Plaza Hotel",
                "organization_description": "Mid-size hotel donating surplus banquet meals.",
                "profile_image_url": "https://example.com/images/asha.jpg",
                "address": "MG Road, Bengaluru",
                "latitude": 12.9716,
                "longitude": 77.5946,
            }
        }
    )


class UserProfileOut(BaseModel):
    """
    Clean, safe representation of a user's profile. Deliberately lists
    only the fields meant to be public — never the password hash or any
    other auth internals.
    """

    id: uuid.UUID
    email: str
    full_name: str
    phone: Optional[str] = None
    role: UserRole
    is_active: bool

    organization_name: Optional[str] = None
    organization_description: Optional[str] = None
    profile_image_url: Optional[str] = None

    address: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None

    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

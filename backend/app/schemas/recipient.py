"""
Pydantic schemas for the Recipient endpoints.

A Recipient is the profile record for an NGO, shelter, community
organization, or authorized medical recipient organization — one-to-one
with a User whose role is RECIPIENT. Self-service create/update always
targets the caller's own profile; an ADMIN may additionally create one on
behalf of a specific RECIPIENT-role user (for seeding/demo data) and may
view or edit any recipient's profile.
"""

import re
import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.enums import RecipientType
from app.schemas.common import OwnerSummary

# 7-20 chars: optional leading '+', digits, spaces, hyphens.
PHONE_RE = re.compile(r"^\+?[0-9][0-9\s\-]{5,19}$")

# Either "24/7" (case-insensitive) or an "HH:MM-HH:MM" 24-hour range, e.g.
# "09:00-18:00". Deliberately simple — a single daily window is enough for
# a hackathon build; multi-day schedules aren't modeled.
OPERATING_HOURS_RE = re.compile(
    r"^(24/7)$|^([01]\d|2[0-3]):[0-5]\d-([01]\d|2[0-3]):[0-5]\d$", re.IGNORECASE
)


class RecipientCreate(BaseModel):
    # Admin-only: create a recipient profile on behalf of another
    # RECIPIENT-role user (e.g. seeding demo data). Ignored — always
    # overridden with the caller's own id — for a self-service RECIPIENT
    # creating their own profile.
    user_id: Optional[uuid.UUID] = Field(
        default=None, description="Admin only. Ignored when the caller is a RECIPIENT."
    )

    organization_name: str = Field(min_length=1, max_length=255)
    recipient_type: RecipientType

    accepts_food: bool = True
    accepts_medical: bool = False

    capacity: Optional[int] = Field(default=None, gt=0, description="Must be greater than 0.")
    current_availability: bool = True

    location_address: str = Field(min_length=1, max_length=500)
    latitude: Optional[float] = Field(default=None, ge=-90, le=90)
    longitude: Optional[float] = Field(default=None, ge=-180, le=180)
    service_area_km: Optional[float] = Field(default=None, gt=0)

    contact_phone: Optional[str] = Field(default=None, max_length=30)
    operating_hours: Optional[str] = Field(default=None, max_length=50)

    @field_validator("contact_phone")
    @classmethod
    def _validate_contact_phone(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        v = v.strip()
        if not v:
            return None
        if not PHONE_RE.match(v):
            raise ValueError(
                "contact_phone must contain 7-20 digits, optionally starting with '+' and using "
                "spaces or hyphens as separators (e.g. '+91-9876543210')."
            )
        return v

    @field_validator("operating_hours")
    @classmethod
    def _validate_operating_hours(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        v = v.strip()
        if not v:
            return None
        if not OPERATING_HOURS_RE.match(v):
            raise ValueError(
                "operating_hours must be '24/7' or an 'HH:MM-HH:MM' 24-hour range, e.g. '09:00-18:00'."
            )
        return v

    @model_validator(mode="after")
    def _validate_lat_lng_pair(self) -> "RecipientCreate":
        if (self.latitude is None) != (self.longitude is None):
            raise ValueError("latitude and longitude must be provided together.")
        return self

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "organization_name": "Hope Community Shelter",
                "recipient_type": "SHELTER",
                "accepts_food": True,
                "accepts_medical": False,
                "capacity": 150,
                "current_availability": True,
                "location_address": "12 Church Street, Bengaluru",
                "latitude": 12.9758,
                "longitude": 77.6044,
                "service_area_km": 10,
                "contact_phone": "+91-9876500000",
                "operating_hours": "09:00-18:00",
            }
        }
    )


class RecipientUpdate(BaseModel):
    """All fields optional — only the ones provided are changed. `is_verified`
    is rejected (403, not silently ignored) for anyone but an ADMIN — see
    the service layer."""

    organization_name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    recipient_type: Optional[RecipientType] = None

    accepts_food: Optional[bool] = None
    accepts_medical: Optional[bool] = None

    capacity: Optional[int] = Field(default=None, gt=0)
    current_availability: Optional[bool] = None

    location_address: Optional[str] = Field(default=None, min_length=1, max_length=500)
    latitude: Optional[float] = Field(default=None, ge=-90, le=90)
    longitude: Optional[float] = Field(default=None, ge=-180, le=180)
    service_area_km: Optional[float] = Field(default=None, gt=0)

    contact_phone: Optional[str] = Field(default=None, max_length=30)
    operating_hours: Optional[str] = Field(default=None, max_length=50)

    # Admin only. A non-admin sending this field gets a 403 from the
    # service layer, not a silent no-op.
    is_verified: Optional[bool] = None

    @field_validator("contact_phone")
    @classmethod
    def _validate_contact_phone(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        v = v.strip()
        if not v:
            return None
        if not PHONE_RE.match(v):
            raise ValueError(
                "contact_phone must contain 7-20 digits, optionally starting with '+' and using "
                "spaces or hyphens as separators (e.g. '+91-9876543210')."
            )
        return v

    @field_validator("operating_hours")
    @classmethod
    def _validate_operating_hours(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        v = v.strip()
        if not v:
            return None
        if not OPERATING_HOURS_RE.match(v):
            raise ValueError(
                "operating_hours must be '24/7' or an 'HH:MM-HH:MM' 24-hour range, e.g. '09:00-18:00'."
            )
        return v

    @model_validator(mode="after")
    def _validate_lat_lng_pair(self) -> "RecipientUpdate":
        if (self.latitude is None) != (self.longitude is None):
            raise ValueError("latitude and longitude must be provided together.")
        return self


class RecipientOut(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    user: Optional[OwnerSummary] = None

    organization_name: str
    recipient_type: RecipientType

    accepts_food: bool
    accepts_medical: bool
    medical_verified: bool

    capacity: Optional[int] = None
    current_availability: bool

    location_address: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    service_area_km: Optional[float] = None

    contact_phone: Optional[str] = None
    operating_hours: Optional[str] = None
    is_verified: bool

    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RecipientListData(BaseModel):
    items: list[RecipientOut]
    total: int
    skip: int
    limit: int
    has_more: bool

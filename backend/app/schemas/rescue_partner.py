"""
Pydantic schemas for the Rescue Partner endpoints.

A RescuePartner is the profile record for whoever physically moves a
resource — a volunteer, transport partner, or organization — one-to-one
with a User whose role is RESCUE_PARTNER. Mirrors app/schemas/recipient.py
in shape and permission model; see that module's docstring for the
self-service-vs-admin creation rationale.
"""

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.enums import PartnerType
from app.schemas.common import OwnerSummary
from app.schemas.recipient import OPERATING_HOURS_RE, PHONE_RE


class PartnerCreate(BaseModel):
    # Admin-only: create a partner profile on behalf of another
    # RESCUE_PARTNER-role user (e.g. seeding demo data). Ignored — always
    # overridden with the caller's own id — for a self-service partner
    # creating their own profile.
    user_id: Optional[uuid.UUID] = Field(
        default=None, description="Admin only. Ignored when the caller is a RESCUE_PARTNER."
    )

    organization_name: Optional[str] = Field(
        default=None, max_length=255, description="Relevant mainly for ORGANIZATION/TRANSPORT_ORG types."
    )
    partner_type: PartnerType
    vehicle_type: Optional[str] = Field(default=None, max_length=100)
    capacity: Optional[int] = Field(default=None, gt=0, description="Must be greater than 0.")

    is_available: bool = True
    accepts_food: bool = True
    accepts_medical: bool = False

    contact_phone: Optional[str] = Field(default=None, max_length=30)
    location_address: Optional[str] = Field(default=None, max_length=500)
    latitude: Optional[float] = Field(default=None, ge=-90, le=90)
    longitude: Optional[float] = Field(default=None, ge=-180, le=180)
    service_radius_km: Optional[float] = Field(default=None, gt=0, description="Service area, in km.")
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
    def _validate_lat_lng_pair(self) -> "PartnerCreate":
        if (self.latitude is None) != (self.longitude is None):
            raise ValueError("latitude and longitude must be provided together.")
        return self

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "organization_name": "QuickRelief Logistics",
                "partner_type": "TRANSPORT_ORG",
                "vehicle_type": "refrigerated van",
                "capacity": 200,
                "is_available": True,
                "accepts_food": True,
                "accepts_medical": True,
                "contact_phone": "+91-9876511111",
                "location_address": "Whitefield, Bengaluru",
                "latitude": 12.9698,
                "longitude": 77.7500,
                "service_radius_km": 15,
                "operating_hours": "24/7",
            }
        }
    )


class PartnerUpdate(BaseModel):
    """All fields optional — only the ones provided are changed. `is_verified`
    is rejected (403, not silently ignored) for anyone but an ADMIN — see
    the service layer. `rating` is never client-settable at all — it's
    computed/assigned elsewhere, not part of this schema."""

    organization_name: Optional[str] = Field(default=None, max_length=255)
    partner_type: Optional[PartnerType] = None
    vehicle_type: Optional[str] = Field(default=None, max_length=100)
    capacity: Optional[int] = Field(default=None, gt=0)

    is_available: Optional[bool] = None
    accepts_food: Optional[bool] = None
    accepts_medical: Optional[bool] = None

    contact_phone: Optional[str] = Field(default=None, max_length=30)
    location_address: Optional[str] = Field(default=None, max_length=500)
    latitude: Optional[float] = Field(default=None, ge=-90, le=90)
    longitude: Optional[float] = Field(default=None, ge=-180, le=180)
    service_radius_km: Optional[float] = Field(default=None, gt=0)
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
    def _validate_lat_lng_pair(self) -> "PartnerUpdate":
        if (self.latitude is None) != (self.longitude is None):
            raise ValueError("latitude and longitude must be provided together.")
        return self


class PartnerOut(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    user: Optional[OwnerSummary] = None

    organization_name: Optional[str] = None
    partner_type: PartnerType
    vehicle_type: Optional[str] = None
    capacity: Optional[int] = None

    is_available: bool
    accepts_food: bool
    accepts_medical: bool

    contact_phone: Optional[str] = None
    location_address: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    service_radius_km: Optional[float] = None
    operating_hours: Optional[str] = None
    is_verified: bool

    rating: Optional[float] = None

    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PartnerListData(BaseModel):
    items: list[PartnerOut]
    total: int
    skip: int
    limit: int
    has_more: bool

"""
Pydantic schemas for the ResourceRequest endpoints (POST/GET/PATCH/DELETE
/api/requests).

A ResourceRequest is a RECIPIENT's demand-side ask for a quantity of some
resource type — separate from Resource/RescueRequest (see
app/models/resource_request.py for why). Only `status`, via a dedicated
PATCH .../status endpoint, changes after creation; there is no general
PUT here on purpose, since every other field is a snapshot of what was
needed at request time.
"""

import uuid
from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import RecipientType, ResourceRequestStatus, ResourceType, UrgencyLevel


class ResourceRequestCreate(BaseModel):
    # Admin-only: create a request on behalf of a specific recipient.
    # Ignored — always overridden with the caller's own recipient profile
    # id — for a self-service RECIPIENT creating their own request.
    recipient_id: Optional[uuid.UUID] = Field(
        default=None, description="Admin only. Ignored when the caller is a RECIPIENT."
    )

    resource_type: ResourceType
    requested_quantity: float = Field(gt=0, description="Must be greater than 0.")

    # Optional on input: defaults to the recipient's own organization_name
    # if omitted, but can be overridden (e.g. a specific branch/program
    # name different from the account's registered org name).
    requesting_organization: Optional[str] = Field(default=None, min_length=1, max_length=255)

    urgency: UrgencyLevel = UrgencyLevel.MEDIUM
    needed_by: datetime = Field(description="Deadline by which this request must be fulfilled.")

    eligibility_requirements: Optional[str] = Field(default=None, max_length=2000)
    can_self_pickup: bool = False
    notes: Optional[str] = Field(default=None, max_length=2000)

    @field_validator("needed_by")
    @classmethod
    def _validate_needed_by_future(cls, v: datetime) -> datetime:
        now = datetime.now(timezone.utc)
        compare = v if v.tzinfo is not None else v.replace(tzinfo=timezone.utc)
        if compare <= now:
            raise ValueError("needed_by must be a future date/time.")
        return v

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "resource_type": "FOOD",
                "requested_quantity": 50,
                "urgency": "HIGH",
                "needed_by": "2026-09-19T18:00:00Z",
                "eligibility_requirements": "Must be nut-free — we serve children with allergies.",
                "can_self_pickup": True,
                "notes": "Can send a van with 2 volunteers on short notice.",
            }
        }
    )


class ResourceRequestStatusUpdate(BaseModel):
    """Body for PATCH /api/requests/{id}/status."""

    status: ResourceRequestStatus
    note: Optional[str] = Field(
        default=None, max_length=1000, description="Optional reason/context, recorded in the status history."
    )

    model_config = ConfigDict(
        json_schema_extra={"example": {"status": "APPROVED", "note": "Confirmed we can cover this from tonight's pickup."}}
    )


class RecipientSummary(BaseModel):
    """Minimal recipient info embedded in a ResourceRequest response."""

    id: uuid.UUID
    organization_name: str
    recipient_type: RecipientType
    contact_phone: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class StatusHistoryEntry(BaseModel):
    id: uuid.UUID
    from_status: Optional[ResourceRequestStatus] = None
    to_status: ResourceRequestStatus
    note: Optional[str] = None
    changed_by_user_id: Optional[uuid.UUID] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ResourceRequestOut(BaseModel):
    id: uuid.UUID
    recipient_id: uuid.UUID
    recipient: Optional[RecipientSummary] = None

    resource_type: ResourceType
    requested_quantity: float
    requesting_organization: str

    urgency: UrgencyLevel
    needed_by: datetime

    eligibility_requirements: Optional[str] = None
    can_self_pickup: bool
    notes: Optional[str] = None

    status: ResourceRequestStatus
    status_history: list[StatusHistoryEntry] = []

    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ResourceRequestListData(BaseModel):
    items: list[ResourceRequestOut]
    total: int
    skip: int
    limit: int

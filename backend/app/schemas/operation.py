"""
Pydantic schemas for:

    POST  /api/operations
    GET   /api/operations
    PATCH /api/operations/{operation_id}/status

A RescueOperation is the execution of a RescueRequest: one assigned
RescuePartner, one status lifecycle (PLANNED -> IN_TRANSIT -> DELIVERED ->
COMPLETED, or -> FAILED from any non-terminal state), and the Allocation(s)
it's carrying out. See app/services/operation_service.py for the business
rules (allowed transitions, allocation linking, authorization).
"""

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import MatchCandidateType, OperationStatus, PartnerType


class OperationCreate(BaseModel):
    rescue_request_id: uuid.UUID = Field(
        description="The RescueRequest this operation will execute. It must have at least one "
        "active (PENDING/CONFIRMED) allocation, and must not already have an operation."
    )
    partner_id: Optional[uuid.UUID] = Field(
        default=None,
        description="RescuePartner to assign at creation. Optional — an operation can be planned "
        "before a partner is assigned, and assigned later via a status update or a future "
        "dedicated endpoint.",
    )
    allocation_ids: Optional[list[uuid.UUID]] = Field(
        default=None,
        description="Specific allocation(s) this operation should carry out. Omit to "
        "automatically link every currently-unlinked, active allocation on the rescue request.",
    )
    notes: Optional[str] = Field(default=None, max_length=2000)

    model_config = ConfigDict(
        json_schema_extra={"example": {"rescue_request_id": "5b2e6f0e-1111-4444-8888-abc123456789"}}
    )


class OperationStatusUpdate(BaseModel):
    status: OperationStatus = Field(description="The status to move this operation to.")
    reason: Optional[str] = Field(
        default=None,
        max_length=1000,
        description="Why the status is changing. Required in practice for FAILED (explains what "
        "went wrong); optional, but recorded either way, for every other transition.",
    )

    model_config = ConfigDict(json_schema_extra={"example": {"status": "IN_TRANSIT"}})


class OperationLocationUpdate(BaseModel):
    latitude: float = Field(ge=-90, le=90, description="Current latitude of the operation.")
    longitude: float = Field(ge=-180, le=180, description="Current longitude of the operation.")

    model_config = ConfigDict(json_schema_extra={"example": {"latitude": 12.9716, "longitude": 77.5946}})


class OperationRouteLeg(BaseModel):
    """
    Distance/duration for one allocation on the operation: from the
    resource's pickup point to that allocation's delivery point (a
    Recipient or a RescueHub). `distance_km`/`estimated_duration_minutes`
    are null when either endpoint's coordinates aren't known — see
    app/services/location_service.py.
    """

    allocation_id: uuid.UUID
    target_type: MatchCandidateType
    target_name: Optional[str] = None
    pickup_latitude: Optional[float] = None
    pickup_longitude: Optional[float] = None
    delivery_latitude: Optional[float] = None
    delivery_longitude: Optional[float] = None
    distance_km: Optional[float] = None
    estimated_duration_minutes: Optional[float] = None

    model_config = ConfigDict(from_attributes=True)


class PartnerSummary(BaseModel):
    id: uuid.UUID
    organization_name: Optional[str] = None
    partner_type: PartnerType
    vehicle_type: Optional[str] = None
    contact_phone: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class OperationAllocationSummary(BaseModel):
    id: uuid.UUID
    recipient_id: Optional[uuid.UUID] = None
    rescue_hub_id: Optional[uuid.UUID] = None
    allocated_quantity: float
    status: str

    model_config = ConfigDict(from_attributes=True)


class OperationEventOut(BaseModel):
    id: uuid.UUID
    event_type: str
    description: Optional[str] = None
    event_metadata: Optional[dict] = None
    created_by_user_id: Optional[uuid.UUID] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class OperationOut(BaseModel):
    id: uuid.UUID
    rescue_request_id: uuid.UUID
    resource_id: uuid.UUID

    partner: Optional[PartnerSummary] = None
    status: OperationStatus

    allocations: list[OperationAllocationSummary] = Field(default_factory=list)
    events: list[OperationEventOut] = Field(default_factory=list)

    pickup_started_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    failure_reason: Optional[str] = None

    current_latitude: Optional[float] = Field(
        default=None, description="Latest known latitude, set via PATCH .../location."
    )
    current_longitude: Optional[float] = Field(
        default=None, description="Latest known longitude, set via PATCH .../location."
    )
    location_updated_at: Optional[datetime] = Field(
        default=None, description="When current_latitude/current_longitude were last set."
    )
    route: list[OperationRouteLeg] = Field(
        default_factory=list,
        description="Pickup -> delivery distance and estimated travel duration for each "
        "allocation on this operation. Computed with a straight-line (haversine) distance and "
        "an assumed average speed — no external routing API is used.",
    )

    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class OperationEventListData(BaseModel):
    items: list[OperationEventOut]
    total: int


class OperationListData(BaseModel):
    items: list[OperationOut]
    total: int
    skip: int
    limit: int
    has_more: bool

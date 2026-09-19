"""
Pydantic schemas for:

    POST /api/allocations
    GET  /api/allocations

An Allocation commits a slice of a resource's quantity to a specific
matched candidate (a Recipient or a RescueHub, never both — same XOR
shape as Match). Creating one is how a PROPOSED Match becomes a real
commitment; see app/services/allocation_service.py for the business
rules (capacity/quantity checks, double-allocation prevention, and the
resource/rescue-request status transitions this triggers).
"""

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import AllocationStatus, MatchCandidateType
from app.schemas.matching import RecipientSummary


class AllocationCreate(BaseModel):
    match_id: uuid.UUID = Field(
        description="A PROPOSED Match from a prior matching run (see POST /api/matching/{resource_id})."
    )
    allocated_quantity: Optional[float] = Field(
        default=None,
        gt=0,
        description="Quantity to commit to this candidate. Defaults to the resource's full "
        "remaining (unallocated) quantity if omitted — pass a smaller number for a partial "
        "allocation, e.g. to split one resource across multiple recipients.",
    )
    reason: Optional[str] = Field(
        default=None,
        max_length=1000,
        description="Optional human-readable note, e.g. 'Closest verified recipient with capacity'.",
    )

    model_config = ConfigDict(json_schema_extra={"example": {"match_id": "5b2e6f0e-1111-4444-8888-abc123456789", "allocated_quantity": 40}})


class RescueHubSummary(BaseModel):
    id: uuid.UUID
    name: str
    location_address: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None

    model_config = ConfigDict(from_attributes=True)


class AllocationOut(BaseModel):
    id: uuid.UUID
    rescue_request_id: uuid.UUID
    resource_id: uuid.UUID
    match_id: Optional[uuid.UUID] = None

    candidate_type: MatchCandidateType
    recipient: Optional[RecipientSummary] = None
    rescue_hub: Optional[RescueHubSummary] = None

    allocated_quantity: float
    status: AllocationStatus
    reason: Optional[str] = None

    resource_remaining_quantity: float = Field(
        description="The resource's quantity still unallocated, computed fresh as of this response "
        "(resource.quantity minus every active — PENDING/CONFIRMED — allocation against it)."
    )

    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AllocationListData(BaseModel):
    items: list[AllocationOut]
    total: int
    skip: int
    limit: int
    has_more: bool

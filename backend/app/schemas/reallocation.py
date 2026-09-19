"""
Pydantic schemas for:

    POST /api/operations/{operation_id}/reallocate

Reallocation handles the "a recipient just became unavailable mid-
operation" scenario: the allocation committed to them is cancelled, the
deterministic matching engine (app/services/matching_engine.py) is asked
for the next-best eligible recipient, and — if one exists — a new
allocation is created in its place and linked onto the same operation.
See app/services/reallocation_service.py for the full business logic.
"""

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.allocation import AllocationOut
from app.schemas.operation import OperationOut


class ReallocationRequest(BaseModel):
    allocation_id: uuid.UUID = Field(
        description="The active (PENDING/CONFIRMED) allocation on this operation whose "
        "recipient/hub has become unavailable and needs to be replaced."
    )
    reason: str = Field(
        min_length=3,
        max_length=1000,
        description="Why this reallocation is happening, e.g. 'Recipient reported they can no "
        "longer accept this delivery.' Stored on both the new allocation and the operation's "
        "event log so the decision stays auditable.",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "allocation_id": "5b2e6f0e-1111-4444-8888-abc123456789",
                "reason": "Recipient reported they can no longer accept this delivery.",
            }
        }
    )


class ReallocationResultData(BaseModel):
    operation: OperationOut = Field(description="The operation after reallocation, including the new allocation.")

    cancelled_allocation: AllocationOut = Field(
        description="The original allocation, now in REALLOCATED status with quantity freed back up."
    )
    new_allocation: Optional[AllocationOut] = Field(
        default=None,
        description="The freshly-created allocation replacing it, or null if no eligible "
        "replacement recipient could be found (the original allocation is still cancelled — "
        "the freed quantity is simply unassigned for now).",
    )

    reallocated: bool = Field(description="True if a replacement recipient was found and allocated.")
    reason: str
    reallocated_at: datetime

    model_config = ConfigDict(from_attributes=True)

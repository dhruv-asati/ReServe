"""
Allocation endpoints:

    POST /api/allocations   Commit a PROPOSED match into a real allocation
    GET  /api/allocations   List allocations, with filters

Creating an allocation is restricted to the underlying resource's own
provider (or an ADMIN) — same rule as every other resource-scoped write
in this project. Listing is open to any authenticated user, same as
viewing resources or matching results.
"""

import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.database import get_db
from app.models.allocation import Allocation
from app.models.enums import AllocationStatus, MatchCandidateType
from app.models.user import User
from app.schemas.allocation import AllocationCreate, AllocationListData, AllocationOut, RescueHubSummary
from app.schemas.common import SuccessResponse
from app.schemas.matching import RecipientSummary
from app.services import allocation_service

router = APIRouter(prefix="/api/allocations", tags=["Allocations"])


def _to_allocation_out(db: Session, allocation: Allocation) -> AllocationOut:
    resource = allocation.rescue_request.resource
    return AllocationOut(
        id=allocation.id,
        rescue_request_id=allocation.rescue_request_id,
        resource_id=resource.id,
        match_id=allocation.match_id,
        candidate_type=(
            MatchCandidateType.RECIPIENT if allocation.recipient_id else MatchCandidateType.RESCUE_HUB
        ),
        recipient=RecipientSummary.model_validate(allocation.recipient) if allocation.recipient else None,
        rescue_hub=RescueHubSummary.model_validate(allocation.rescue_hub) if allocation.rescue_hub else None,
        allocated_quantity=float(allocation.allocated_quantity),
        status=allocation.status,
        reason=allocation.reason,
        resource_remaining_quantity=allocation_service.get_remaining_quantity(db, resource),
        created_at=allocation.created_at,
        updated_at=allocation.updated_at,
    )


@router.post(
    "",
    response_model=SuccessResponse[AllocationOut],
    status_code=status.HTTP_201_CREATED,
    summary="Allocate a resource to a matched recipient",
    description=(
        "Commits a PROPOSED match (from a prior POST /api/matching/{resource_id} run) into a "
        "real allocation: reserves `allocated_quantity` of the resource for that recipient/rescue "
        "hub, moves the match to SELECTED, and moves the resource to ALLOCATED once its full "
        "quantity is committed (or to PARTIALLY_MATCHED at the rescue-request level if only some "
        "of it is, so the rest can still be allocated to other matched candidates later). "
        "Omit `allocated_quantity` to allocate everything still remaining. Rejects the request if "
        "the match isn't PROPOSED, if the candidate already holds an active allocation for this "
        "rescue request, if the requested quantity exceeds what's left on the resource, or if it "
        "exceeds the candidate's own declared capacity. Only the resource's own provider or an "
        "admin may call this."
    ),
)
def create_allocation(
    payload: AllocationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    allocation = allocation_service.create_allocation(db, payload, current_user)
    data = _to_allocation_out(db, allocation)
    return SuccessResponse(data=data, message=f"Allocated {data.allocated_quantity:g} unit(s).")


@router.get(
    "",
    response_model=SuccessResponse[AllocationListData],
    summary="List allocations",
    description="Lists allocations, newest first, with optional filters. Available to any "
    "authenticated user.",
)
def list_allocations(
    resource_id: uuid.UUID | None = Query(default=None),
    recipient_id: uuid.UUID | None = Query(default=None),
    rescue_hub_id: uuid.UUID | None = Query(default=None),
    rescue_request_id: uuid.UUID | None = Query(default=None),
    status_filter: AllocationStatus | None = Query(default=None, alias="status"),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    items, total = allocation_service.list_allocations(
        db,
        resource_id=resource_id,
        recipient_id=recipient_id,
        rescue_hub_id=rescue_hub_id,
        rescue_request_id=rescue_request_id,
        status_filter=status_filter,
        skip=skip,
        limit=limit,
    )
    data = AllocationListData(
        items=[_to_allocation_out(db, item) for item in items],
        total=total,
        skip=skip,
        limit=limit,
        has_more=skip + len(items) < total,
    )
    return SuccessResponse(data=data, message=f"Found {total} allocation(s).")

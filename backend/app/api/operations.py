"""
Operation endpoints:

    POST  /api/operations                       Create an operation for a rescue request
    GET   /api/operations                        List operations, with filters
    GET   /api/operations/active                 Not-yet-closed operations (dashboard feed)
    PATCH /api/operations/{operation_id}/status   Move an operation through its status lifecycle

Creating an operation is restricted to the underlying resource's own
provider (or an ADMIN) — same rule as allocations. Updating status is
open to the resource's provider/admin *or* the partner assigned to that
specific operation, since they're the one actually moving the resource
and reporting what happened. Listing is open to any authenticated user.
"""

import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.database import get_db
from app.models.allocation import Allocation
from app.models.enums import MatchCandidateType, OperationStatus
from app.models.operation import RescueOperation
from app.models.user import User
from app.schemas.allocation import AllocationOut, RescueHubSummary
from app.schemas.common import SuccessResponse
from app.schemas.dashboard import ActiveOperationOut
from app.schemas.matching import RecipientSummary
from app.schemas.operation import (
    OperationAllocationSummary,
    OperationCreate,
    OperationEventListData,
    OperationEventOut,
    OperationListData,
    OperationLocationUpdate,
    OperationOut,
    OperationRouteLeg,
    OperationStatusUpdate,
    PartnerSummary,
)
from app.schemas.reallocation import ReallocationRequest, ReallocationResultData
from app.services import allocation_service, dashboard_service, operation_service, reallocation_service

router = APIRouter(prefix="/api/operations", tags=["Operations"])


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


def _to_operation_out(operation: RescueOperation) -> OperationOut:
    return OperationOut(
        id=operation.id,
        rescue_request_id=operation.rescue_request_id,
        resource_id=operation.rescue_request.resource_id,
        partner=PartnerSummary.model_validate(operation.partner) if operation.partner else None,
        status=operation.status,
        allocations=[OperationAllocationSummary.model_validate(a) for a in operation.allocations],
        events=[OperationEventOut.model_validate(e) for e in operation.events],
        pickup_started_at=operation.pickup_started_at,
        delivered_at=operation.delivered_at,
        completed_at=operation.completed_at,
        failure_reason=operation.failure_reason,
        current_latitude=operation.current_latitude,
        current_longitude=operation.current_longitude,
        location_updated_at=operation.location_updated_at,
        route=[OperationRouteLeg(**leg) for leg in operation_service.compute_route(operation)],
        created_at=operation.created_at,
        updated_at=operation.updated_at,
    )


@router.post(
    "",
    response_model=SuccessResponse[OperationOut],
    status_code=status.HTTP_201_CREATED,
    summary="Create a rescue operation",
    description=(
        "Creates the RescueOperation that executes a rescue request: links it to the request's "
        "active allocation(s) (either the ones you specify, or every currently-unlinked "
        "PENDING/CONFIRMED allocation on the request if you omit `allocation_ids`), optionally "
        "assigns a rescue partner, and starts it in PLANNED status. A rescue request can only "
        "have one operation. Only the resource's own provider or an admin may call this."
    ),
)
def create_operation(
    payload: OperationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    operation = operation_service.create_operation(db, payload, current_user)
    data = _to_operation_out(operation)
    return SuccessResponse(data=data, message=f"Operation created with status '{data.status.value}'.")


@router.get(
    "",
    response_model=SuccessResponse[OperationListData],
    summary="List rescue operations",
    description="Lists operations, newest first, with optional filters. Available to any "
    "authenticated user.",
)
def list_operations(
    resource_id: uuid.UUID | None = Query(default=None),
    rescue_request_id: uuid.UUID | None = Query(default=None),
    partner_id: uuid.UUID | None = Query(default=None),
    status_filter: OperationStatus | None = Query(default=None, alias="status"),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    items, total = operation_service.list_operations(
        db,
        resource_id=resource_id,
        rescue_request_id=rescue_request_id,
        partner_id=partner_id,
        status_filter=status_filter,
        skip=skip,
        limit=limit,
    )
    data = OperationListData(
        items=[_to_operation_out(item) for item in items],
        total=total,
        skip=skip,
        limit=limit,
        has_more=skip + len(items) < total,
    )
    return SuccessResponse(data=data, message=f"Found {total} operation(s).")


@router.get(
    "/active",
    response_model=SuccessResponse[list[ActiveOperationOut]],
    summary="Active rescue operations",
    description="Operations that are not yet closed out (PLANNED, IN_TRANSIT or DELIVERED), most recently "
    "updated first, in the display shape the dashboard renders. Available to any authenticated user.",
)
def list_active_operations(
    limit: int = Query(default=10, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    items = dashboard_service.get_active_operations(db, limit=limit)
    return SuccessResponse(data=items, message=f"{len(items)} active operation(s).")


@router.get(
    "/{operation_id}/events",
    response_model=SuccessResponse[OperationEventListData],
    summary="List an operation's status-change events",
    description=(
        "Returns the full OperationEvent audit log for one operation — every status change, "
        "creation, reallocation, and note — in chronological order (oldest first). Each event "
        "records its type, description, timestamp, and the ID of the user who caused it (null "
        "for system-raised events). Requires authentication."
    ),
)
def list_operation_events(
    operation_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    events = operation_service.list_events(db, operation_id)
    data = OperationEventListData(
        items=[OperationEventOut.model_validate(e) for e in events],
        total=len(events),
    )
    return SuccessResponse(data=data, message=f"Found {len(events)} event(s).")


@router.patch(
    "/{operation_id}/status",
    response_model=SuccessResponse[OperationOut],
    summary="Update a rescue operation's status",
    description=(
        "Moves an operation to a new status: PLANNED -> IN_TRANSIT -> DELIVERED -> COMPLETED, or "
        "-> FAILED from any non-terminal status. Rejects any other transition with a clear "
        "explanation of which statuses are valid next. A 'reason' is required when failing an "
        "operation. Reaching DELIVERED marks every linked allocation DELIVERED and the resource "
        "DELIVERED. Every change is recorded as an OperationEvent, visible in the response's "
        "`events` list. Callable by the resource's provider/admin, or by the partner assigned to "
        "this operation."
    ),
)
def update_operation_status(
    operation_id: uuid.UUID,
    payload: OperationStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    operation = operation_service.update_status(db, operation_id, payload, current_user)
    data = _to_operation_out(operation)
    return SuccessResponse(data=data, message=f"Operation status updated to '{data.status.value}'.")


@router.patch(
    "/{operation_id}/location",
    response_model=SuccessResponse[OperationOut],
    summary="Update an operation's current location",
    description=(
        "Records the latest known latitude/longitude for an operation — e.g. a rescue partner "
        "periodically reporting their position while en route. Only the most recent fix is "
        "stored (`current_latitude`/`current_longitude`/`location_updated_at` on the response), "
        "not a location history. The response's `route` also reports the straight-line distance "
        "and an estimated travel duration from the resource's pickup point to each allocation's "
        "delivery point, computed offline (haversine distance / an assumed average speed) — no "
        "external routing API is used. Callable by the resource's provider/admin, or by the "
        "partner assigned to this operation."
    ),
)
def update_operation_location(
    operation_id: uuid.UUID,
    payload: OperationLocationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    operation = operation_service.update_location(db, operation_id, payload, current_user)
    data = _to_operation_out(operation)
    return SuccessResponse(data=data, message="Operation location updated.")


@router.post(
    "/{operation_id}/reallocate",
    response_model=SuccessResponse[ReallocationResultData],
    summary="Reallocate an operation after a recipient becomes unavailable",
    description=(
        "Handles a recipient becoming unavailable mid-operation: cancels the affected allocation "
        "(moved to REALLOCATED status, freeing its quantity), runs the same deterministic "
        "matching engine used by POST /api/matching/{resource_id} to find the next-best eligible "
        "recipient (excluding anyone already holding an active allocation on this rescue "
        "request), and — if one is found — creates a new allocation for them, linked to this "
        "operation, capped at whatever quantity is still free and at their own declared "
        "capacity. The affected recipient is also marked unavailable. If no eligible replacement "
        "exists, the original allocation is still cancelled but `reallocated` comes back false — "
        "this is a successful call either way, not an error. Every step is recorded as a "
        "REALLOCATED operation event with the reason you provide. Only the resource's own "
        "provider/admin, or the partner assigned to this operation, may call this. Only "
        "PLANNED/IN_TRANSIT operations can be reallocated."
    ),
)
def reallocate_operation(
    operation_id: uuid.UUID,
    payload: ReallocationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    operation, old_allocation, new_allocation, reallocated = reallocation_service.reallocate(
        db, operation_id, payload, current_user
    )
    data = ReallocationResultData(
        operation=_to_operation_out(operation),
        cancelled_allocation=_to_allocation_out(db, old_allocation),
        new_allocation=_to_allocation_out(db, new_allocation) if new_allocation else None,
        reallocated=reallocated,
        reason=payload.reason,
        reallocated_at=old_allocation.updated_at,
    )
    message = (
        f"Reallocated {data.new_allocation.allocated_quantity:g} unit(s) to a new recipient."
        if reallocated
        else "Allocation cancelled, but no eligible replacement recipient was found."
    )
    return SuccessResponse(data=data, message=message)

"""
ResourceRequest endpoints:

    POST  /api/requests
    GET   /api/requests
    GET   /api/requests/incoming | /outgoing | /completed   (Rescue Requests page queues;
                                                             declared before /{request_id})
    GET   /api/requests/{request_id}
    PATCH /api/requests/{request_id}/status
    DELETE /api/requests/{request_id}

All endpoints require authentication. Creating a request is restricted to
RECIPIENT (self-service, against their own profile) and ADMIN (on behalf
of a specific recipient) roles. Status changes and deletion are enforced
in the service layer: the owning recipient may cancel, a PROVIDER/ADMIN
may approve/reject/mark fulfilled, and an ADMIN may do either.
"""

import logging
import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, require_roles
from app.db.database import get_db
from app.models.enums import ResourceRequestStatus, ResourceType, UrgencyLevel, UserRole
from app.models.user import User
from app.schemas.common import SuccessResponse
from app.schemas.request_queue import RequestRowOut
from app.schemas.resource_request import (
    ResourceRequestCreate,
    ResourceRequestListData,
    ResourceRequestOut,
    ResourceRequestStatusUpdate,
)
from app.services import request_queue_service, resource_request_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/requests", tags=["Resource Requests"])


@router.post(
    "",
    response_model=SuccessResponse[ResourceRequestOut],
    status_code=status.HTTP_201_CREATED,
    summary="Create a resource request",
    description="RECIPIENT accounts create requests against their own profile (any 'recipient_id' "
    "in the body is ignored). ADMIN accounts must supply 'recipient_id'. Rejects a resource_type "
    "the recipient doesn't accept, and MEDICAL requests from a recipient that isn't medical-verified.",
)
def create_request(
    payload: ResourceRequestCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.RECIPIENT, UserRole.ADMIN)),
):
    request = resource_request_service.create_resource_request(db, payload, current_user)
    return SuccessResponse(
        data=ResourceRequestOut.model_validate(request), message="Resource request created successfully."
    )


@router.get(
    "",
    response_model=SuccessResponse[ResourceRequestListData],
    summary="List resource requests",
    description="RECIPIENTs always see only their own requests. PROVIDER, RESCUE_PARTNER, and ADMIN "
    "see the full list, optionally filtered by resource type, status, urgency, recipient, or a text "
    "search across organization/notes/eligibility.",
)
def list_requests(
    resource_type: ResourceType | None = Query(default=None),
    status_filter: ResourceRequestStatus | None = Query(default=None, alias="status"),
    urgency: UrgencyLevel | None = Query(default=None),
    recipient_id: uuid.UUID | None = Query(default=None, description="Ignored for RECIPIENT callers."),
    search: str | None = Query(default=None, description="Text search across organization, notes, eligibility."),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    items, total = resource_request_service.list_resource_requests(
        db,
        current_user=current_user,
        resource_type=resource_type,
        status_filter=status_filter,
        recipient_id=recipient_id,
        urgency=urgency,
        search=search,
        skip=skip,
        limit=limit,
    )
    data = ResourceRequestListData(
        items=[ResourceRequestOut.model_validate(item) for item in items],
        total=total,
        skip=skip,
        limit=limit,
    )
    return SuccessResponse(data=data, message=f"Found {total} resource request(s).")


# NOTE: the three queue routes must stay above GET "/{request_id}" — FastAPI
# matches in declaration order, so below it "incoming"/"outgoing"/"completed"
# would be parsed as a UUID and rejected with 422.
@router.get(
    "/incoming",
    response_model=SuccessResponse[list[RequestRowOut]],
    summary="Incoming requests",
    description="Open (PENDING/APPROVED) requests raised by other organizations, for PROVIDER, RESCUE_PARTNER and "
    "ADMIN accounts. Always empty for RECIPIENT accounts.",
)
def list_incoming_requests(
    limit: int = Query(default=100, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    items = request_queue_service.get_queue(db, current_user, "incoming", limit=limit)
    return SuccessResponse(data=items, message=f"{len(items)} incoming request(s).")


@router.get(
    "/outgoing",
    response_model=SuccessResponse[list[RequestRowOut]],
    summary="Outgoing requests",
    description="Open (PENDING/APPROVED) requests raised by the caller's own recipient organization.",
)
def list_outgoing_requests(
    limit: int = Query(default=100, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    items = request_queue_service.get_queue(db, current_user, "outgoing", limit=limit)
    return SuccessResponse(data=items, message=f"{len(items)} outgoing request(s).")


@router.get(
    "/completed",
    response_model=SuccessResponse[list[RequestRowOut]],
    summary="Completed requests",
    description="Requests in a final state (FULFILLED, REJECTED or CANCELLED). RECIPIENTs see their own; "
    "everyone else sees all.",
)
def list_completed_requests(
    limit: int = Query(default=100, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    items = request_queue_service.get_queue(db, current_user, "completed", limit=limit)
    return SuccessResponse(data=items, message=f"{len(items)} completed request(s).")


@router.get(
    "/{request_id}",
    response_model=SuccessResponse[ResourceRequestOut],
    summary="Get a resource request by id",
)
def get_request(
    request_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    request = resource_request_service.get_resource_request_or_404(db, request_id)
    return SuccessResponse(
        data=ResourceRequestOut.model_validate(request), message="Resource request retrieved successfully."
    )


@router.patch(
    "/{request_id}/status",
    response_model=SuccessResponse[ResourceRequestOut],
    summary="Update a resource request's status",
    description="The requesting recipient (or an admin) may CANCEL. A provider (or an admin) may "
    "set APPROVED, REJECTED, or FULFILLED. Invalid transitions (e.g. approving an already-REJECTED "
    "request) are rejected with 409. Every change is recorded in the request's status history.",
)
def update_request_status(
    request_id: uuid.UUID,
    payload: ResourceRequestStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    request = resource_request_service.update_resource_request_status(db, request_id, payload, current_user)
    return SuccessResponse(
        data=ResourceRequestOut.model_validate(request), message="Resource request status updated successfully."
    )


@router.delete(
    "/{request_id}",
    response_model=SuccessResponse[None],
    summary="Delete a resource request",
    description="Only the requesting recipient or an admin may delete it. Locked once APPROVED or "
    "FULFILLED — cancel it instead via PATCH .../status.",
)
def delete_request(
    request_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    resource_request_service.delete_resource_request(db, request_id, current_user)
    return SuccessResponse(data=None, message="Resource request deleted successfully.")

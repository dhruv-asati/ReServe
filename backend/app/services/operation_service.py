"""
Operation service: business logic for POST/GET /api/operations and
PATCH /api/operations/{operation_id}/status.

A RescueOperation is the execution of a RescueRequest: it links to the
Allocation(s) it's carrying out, tracks an assigned RescuePartner, and
moves through a small, strictly-enforced status lifecycle:

    PLANNED -> IN_TRANSIT -> DELIVERED -> COMPLETED
       \\          \\             \\
        -----------> FAILED <------

Every transition is validated against ALLOWED_TRANSITIONS below and
recorded as an OperationEvent, so "save status changes" means an
operation's full history — not just its current status — is always
available (see get_operation_or_404, which loads `events` ordered by
time).

Kept separate from the router so it's reusable without going through
HTTP, same as every other *_service module in this project.
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.core.errors import AppError
from app.models.allocation import Allocation
from app.models.enums import (
    AllocationStatus,
    MatchCandidateType,
    OperationEventType,
    OperationStatus,
    ResourceStatus,
    ResourceType,
    UserRole,
)
from app.models.operation import OperationEvent, RescueOperation
from app.models.rescue_partner import RescuePartner
from app.models.rescue_request import RescueRequest
from app.models.user import User
from app.schemas.operation import OperationCreate, OperationLocationUpdate, OperationStatusUpdate
from app.services import location_service, notification_service

logger = logging.getLogger(__name__)

# Allocation statuses that represent a live, uncommitted-to-execution
# commitment — the only ones eligible to be linked to a new operation.
ACTIVE_ALLOCATION_STATUSES = {AllocationStatus.PENDING, AllocationStatus.CONFIRMED}

# The state machine this service enforces. COMPLETED and FAILED are
# terminal — nothing may follow them. FAILED is reachable from every
# non-terminal state (a rescue can go wrong at any point); the "happy
# path" otherwise moves strictly forward one step at a time.
ALLOWED_TRANSITIONS: dict[OperationStatus, set[OperationStatus]] = {
    OperationStatus.PLANNED: {OperationStatus.IN_TRANSIT, OperationStatus.FAILED},
    OperationStatus.IN_TRANSIT: {OperationStatus.DELIVERED, OperationStatus.FAILED},
    OperationStatus.DELIVERED: {OperationStatus.COMPLETED, OperationStatus.FAILED},
    OperationStatus.COMPLETED: set(),
    OperationStatus.FAILED: set(),
}


def _is_resource_owner_or_admin(resource, current_user: User) -> bool:
    return current_user.role == UserRole.ADMIN or resource.provider_id == current_user.id


def _is_assigned_partner(operation: RescueOperation, current_user: User) -> bool:
    return (
        current_user.role == UserRole.RESCUE_PARTNER
        and operation.partner is not None
        and operation.partner.user_id == current_user.id
    )


def _get_rescue_request_or_404(db: Session, rescue_request_id: uuid.UUID) -> RescueRequest:
    rescue_request = (
        db.query(RescueRequest)
        .options(joinedload(RescueRequest.resource))
        .filter(RescueRequest.id == rescue_request_id)
        .first()
    )
    if rescue_request is None:
        raise AppError(status_code=404, code="RESCUE_REQUEST_NOT_FOUND", message="Rescue request not found.")
    return rescue_request


def _get_partner_or_404(db: Session, partner_id: uuid.UUID) -> RescuePartner:
    partner = db.query(RescuePartner).filter(RescuePartner.id == partner_id).first()
    if partner is None:
        raise AppError(status_code=404, code="PARTNER_NOT_FOUND", message="Rescue partner not found.")
    return partner


def _validate_partner_for_resource(partner: RescuePartner, resource) -> None:
    if not partner.is_available:
        raise AppError(
            status_code=409,
            code="PARTNER_UNAVAILABLE",
            message="This rescue partner is not currently available.",
        )
    accepts = partner.accepts_food if resource.resource_type == ResourceType.FOOD else partner.accepts_medical
    if not accepts:
        raise AppError(
            status_code=409,
            code="PARTNER_TYPE_MISMATCH",
            message=f"This partner does not handle {resource.resource_type.value} resources.",
        )


def _resolve_allocations(
    db: Session, rescue_request: RescueRequest, allocation_ids: Optional[list[uuid.UUID]]
) -> list[Allocation]:
    if allocation_ids:
        allocations = []
        for allocation_id in allocation_ids:
            allocation = db.query(Allocation).filter(Allocation.id == allocation_id).first()
            if allocation is None:
                raise AppError(
                    status_code=404, code="ALLOCATION_NOT_FOUND", message=f"Allocation {allocation_id} not found."
                )
            if allocation.rescue_request_id != rescue_request.id:
                raise AppError(
                    status_code=409,
                    code="ALLOCATION_MISMATCH",
                    message=f"Allocation {allocation_id} does not belong to this rescue request.",
                )
            if allocation.operation_id is not None:
                raise AppError(
                    status_code=409,
                    code="ALLOCATION_ALREADY_LINKED",
                    message=f"Allocation {allocation_id} is already linked to another operation.",
                )
            if allocation.status not in ACTIVE_ALLOCATION_STATUSES:
                raise AppError(
                    status_code=409,
                    code="ALLOCATION_NOT_ACTIVE",
                    message=f"Allocation {allocation_id} is '{allocation.status.value}' and can't be executed.",
                )
            allocations.append(allocation)
        return allocations

    allocations = (
        db.query(Allocation)
        .filter(
            Allocation.rescue_request_id == rescue_request.id,
            Allocation.operation_id.is_(None),
            Allocation.status.in_(ACTIVE_ALLOCATION_STATUSES),
        )
        .all()
    )
    if not allocations:
        raise AppError(
            status_code=409,
            code="NO_ACTIVE_ALLOCATIONS",
            message="This rescue request has no active, unlinked allocations to execute. "
            "Create one first via POST /api/allocations.",
        )
    return allocations


def create_operation(db: Session, payload: OperationCreate, current_user: User) -> RescueOperation:
    rescue_request = _get_rescue_request_or_404(db, payload.rescue_request_id)
    resource = rescue_request.resource

    if not _is_resource_owner_or_admin(resource, current_user):
        raise AppError(
            status_code=403,
            code="NOT_RESOURCE_OWNER",
            message="Only the provider who posted this resource (or an admin) can create an "
            "operation for it.",
        )

    existing = db.query(RescueOperation).filter(RescueOperation.rescue_request_id == rescue_request.id).first()
    if existing is not None:
        raise AppError(
            status_code=409,
            code="OPERATION_ALREADY_EXISTS",
            message=f"An operation ({existing.id}) already exists for this rescue request. "
            "Use PATCH /api/operations/{operation_id}/status to update it instead.",
        )

    partner: Optional[RescuePartner] = None
    if payload.partner_id is not None:
        partner = _get_partner_or_404(db, payload.partner_id)
        _validate_partner_for_resource(partner, resource)

    allocations = _resolve_allocations(db, rescue_request, payload.allocation_ids)

    operation = RescueOperation(
        rescue_request_id=rescue_request.id,
        partner_id=partner.id if partner else None,
        status=OperationStatus.PLANNED,
    )
    db.add(operation)
    db.flush()  # assign operation.id without committing yet

    for allocation in allocations:
        allocation.operation_id = operation.id

    description = f"Operation created with {len(allocations)} allocation(s)"
    if partner is not None:
        description += f", assigned to partner {partner.id}"
    if payload.notes:
        description += f". Notes: {payload.notes}"

    db.add(
        OperationEvent(
            operation_id=operation.id,
            event_type=OperationEventType.CREATED,
            description=description,
            event_metadata={
                "allocation_ids": [str(a.id) for a in allocations],
                "partner_id": str(partner.id) if partner else None,
            },
            created_by_user_id=current_user.id,
        )
    )

    if partner is not None:
        notification_service.notify_operation_assigned(
            db, operation=operation, partner=partner, resource=resource
        )

    db.commit()
    db.refresh(operation)

    logger.info(
        "Operation %s created for rescue request %s: %d allocation(s), partner=%s (by %s)",
        operation.id,
        rescue_request.id,
        len(allocations),
        partner.id if partner else None,
        current_user.id,
    )
    return operation


def get_operation_or_404(db: Session, operation_id: uuid.UUID) -> RescueOperation:
    operation = (
        db.query(RescueOperation)
        .options(
            joinedload(RescueOperation.partner),
            joinedload(RescueOperation.allocations).joinedload(Allocation.recipient),
            joinedload(RescueOperation.allocations).joinedload(Allocation.rescue_hub),
            joinedload(RescueOperation.events),
            joinedload(RescueOperation.rescue_request).joinedload(RescueRequest.resource),
        )
        .filter(RescueOperation.id == operation_id)
        .first()
    )
    if operation is None:
        raise AppError(status_code=404, code="OPERATION_NOT_FOUND", message="Operation not found.")
    return operation


def list_events(db: Session, operation_id: uuid.UUID) -> list[OperationEvent]:
    """Every OperationEvent for an operation, oldest first (chronological order).

    Raises 404 via get_operation_or_404 if the operation doesn't exist, so
    callers get the same "not found" behavior as every other
    operation-scoped endpoint.
    """
    get_operation_or_404(db, operation_id)
    return (
        db.query(OperationEvent)
        .filter(OperationEvent.operation_id == operation_id)
        .order_by(OperationEvent.created_at.asc())
        .all()
    )


def list_operations(
    db: Session,
    *,
    resource_id: Optional[uuid.UUID] = None,
    rescue_request_id: Optional[uuid.UUID] = None,
    partner_id: Optional[uuid.UUID] = None,
    status_filter: Optional[OperationStatus] = None,
    skip: int = 0,
    limit: int = 20,
) -> tuple[list[RescueOperation], int]:
    query = db.query(RescueOperation).options(
        joinedload(RescueOperation.partner),
        joinedload(RescueOperation.allocations).joinedload(Allocation.recipient),
        joinedload(RescueOperation.allocations).joinedload(Allocation.rescue_hub),
        joinedload(RescueOperation.events),
        joinedload(RescueOperation.rescue_request).joinedload(RescueRequest.resource),
    )

    if resource_id is not None:
        query = query.join(RescueRequest, RescueOperation.rescue_request_id == RescueRequest.id).filter(
            RescueRequest.resource_id == resource_id
        )
    if rescue_request_id is not None:
        query = query.filter(RescueOperation.rescue_request_id == rescue_request_id)
    if partner_id is not None:
        query = query.filter(RescueOperation.partner_id == partner_id)
    if status_filter is not None:
        query = query.filter(RescueOperation.status == status_filter)

    total = query.with_entities(func.count(RescueOperation.id)).scalar() or 0
    items = query.order_by(RescueOperation.created_at.desc()).offset(skip).limit(limit).all()

    return items, total


def update_status(
    db: Session, operation_id: uuid.UUID, payload: OperationStatusUpdate, current_user: User
) -> RescueOperation:
    operation = get_operation_or_404(db, operation_id)
    resource = operation.rescue_request.resource

    if not (_is_resource_owner_or_admin(resource, current_user) or _is_assigned_partner(operation, current_user)):
        raise AppError(
            status_code=403,
            code="NOT_AUTHORIZED",
            message="Only the resource's provider, the partner assigned to this operation, or an "
            "admin can update its status.",
        )

    old_status = operation.status
    new_status = payload.status

    if new_status == old_status:
        raise AppError(
            status_code=409,
            code="NO_STATUS_CHANGE",
            message=f"Operation is already '{old_status.value}'.",
        )

    allowed_next = ALLOWED_TRANSITIONS.get(old_status, set())
    if new_status not in allowed_next:
        if not allowed_next:
            message = f"Operation is already in a terminal state ('{old_status.value}') and cannot change further."
        else:
            valid = ", ".join(s.value for s in allowed_next)
            message = f"Cannot move from '{old_status.value}' to '{new_status.value}'. Valid next status(es): {valid}."
        raise AppError(status_code=409, code="INVALID_STATUS_TRANSITION", message=message)

    if new_status == OperationStatus.FAILED and not payload.reason:
        raise AppError(
            status_code=422,
            code="FAILURE_REASON_REQUIRED",
            message="A 'reason' is required when moving an operation to FAILED.",
        )

    now = datetime.now(timezone.utc)
    operation.status = new_status

    if new_status == OperationStatus.IN_TRANSIT and operation.pickup_started_at is None:
        operation.pickup_started_at = now
    elif new_status == OperationStatus.DELIVERED:
        operation.delivered_at = now
        # Only allocations that are still live get marked DELIVERED. An
        # allocation that was superseded by a reallocation stays linked to
        # this operation (that link is the audit trail) but is REALLOCATED,
        # not PENDING/CONFIRMED — flipping it to DELIVERED here would claim
        # a recipient who dropped out actually received the goods, and
        # would double-count its quantity in
        # analytics_service._total_quantity_rescued alongside the
        # replacement allocation that really was delivered. Same reasoning
        # applies to a CANCELLED allocation.
        for allocation in operation.allocations:
            if allocation.status in ACTIVE_ALLOCATION_STATUSES:
                allocation.status = AllocationStatus.DELIVERED
        resource.status = ResourceStatus.DELIVERED
    elif new_status == OperationStatus.COMPLETED:
        operation.completed_at = now
        # Delivery already happened at the DELIVERED step, where these
        # allocations were flipped to DELIVERED — that's the set of
        # recipients who actually received something on this operation.
        recipient_user_ids = [
            allocation.recipient.user_id
            for allocation in operation.allocations
            if allocation.status == AllocationStatus.DELIVERED and allocation.recipient is not None
        ]
        notification_service.notify_operation_completed(
            db, operation=operation, resource=resource, recipient_user_ids=recipient_user_ids
        )
    elif new_status == OperationStatus.FAILED:
        operation.failure_reason = payload.reason
        # Everyone who was counting on this rescue: the provider, the
        # assigned partner, and any recipient still holding a live
        # allocation. Recipients whose allocation was already superseded
        # (REALLOCATED) or cancelled are intentionally left out — they were
        # told at the time and aren't waiting on this operation any more.
        recipient_user_ids = [
            allocation.recipient.user_id
            for allocation in operation.allocations
            if allocation.status in ACTIVE_ALLOCATION_STATUSES and allocation.recipient is not None
        ]
        notification_service.notify_operation_failed(
            db,
            operation=operation,
            resource=resource,
            reason=payload.reason,
            recipient_user_ids=recipient_user_ids,
        )

    description = f"Status changed from {old_status.value} to {new_status.value}"
    if payload.reason:
        description += f": {payload.reason}"

    db.add(
        OperationEvent(
            operation_id=operation.id,
            event_type=OperationEventType.STATUS_CHANGED,
            description=description,
            event_metadata={"from": old_status.value, "to": new_status.value, "reason": payload.reason},
            created_by_user_id=current_user.id,
        )
    )

    db.commit()
    db.refresh(operation)

    logger.info(
        "Operation %s: %s -> %s (by %s)%s",
        operation.id,
        old_status.value,
        new_status.value,
        current_user.id,
        f" — {payload.reason}" if payload.reason else "",
    )
    return operation


def update_location(
    db: Session, operation_id: uuid.UUID, payload: OperationLocationUpdate, current_user: User
) -> RescueOperation:
    """
    Sets an operation's latest known latitude/longitude —
    "where is it right now", not a location history. Authorization mirrors
    update_status: the resource's provider/admin, or the partner assigned
    to this operation (i.e. whoever is actually en route can report their
    own position). Deliberately does NOT write an OperationEvent — GPS
    fixes can arrive frequently and aren't a state-changing occurrence the
    way a status change or a reallocation is; only the latest fix is kept.
    """
    operation = get_operation_or_404(db, operation_id)
    resource = operation.rescue_request.resource

    if not (_is_resource_owner_or_admin(resource, current_user) or _is_assigned_partner(operation, current_user)):
        raise AppError(
            status_code=403,
            code="NOT_AUTHORIZED",
            message="Only the resource's provider, the partner assigned to this operation, or an "
            "admin can update its location.",
        )

    operation.current_latitude = payload.latitude
    operation.current_longitude = payload.longitude
    operation.location_updated_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(operation)

    logger.info(
        "Operation %s location updated to (%.6f, %.6f) by %s",
        operation.id,
        payload.latitude,
        payload.longitude,
        current_user.id,
    )
    return operation


def compute_route(operation: RescueOperation) -> list[dict]:
    """
    One entry per allocation on this operation: the straight-line
    (haversine) distance and an offline estimated travel duration from the
    resource's pickup point to that allocation's delivery point (a
    Recipient or a RescueHub) — see app/services/location_service.py. No
    external routing/mapping API is used. A leg's distance/duration is
    None when either endpoint's coordinates aren't known yet, same as
    matching_engine's distance scoring treats missing coordinates.

    Requires operation.allocations[*].recipient/rescue_hub and
    operation.rescue_request.resource to already be loaded (see the
    joinedload chains in get_operation_or_404/list_operations) — this
    function itself never queries the database.
    """
    resource = operation.rescue_request.resource
    pickup_lat, pickup_lng = resource.latitude, resource.longitude

    legs: list[dict] = []
    for allocation in operation.allocations:
        if allocation.recipient is not None:
            target_type = MatchCandidateType.RECIPIENT
            target_name = allocation.recipient.organization_name
            delivery_lat = allocation.recipient.latitude
            delivery_lng = allocation.recipient.longitude
        else:
            target_type = MatchCandidateType.RESCUE_HUB
            target_name = allocation.rescue_hub.name if allocation.rescue_hub else None
            delivery_lat = allocation.rescue_hub.latitude if allocation.rescue_hub else None
            delivery_lng = allocation.rescue_hub.longitude if allocation.rescue_hub else None

        distance_km, duration_minutes = location_service.compute_leg(
            pickup_lat, pickup_lng, delivery_lat, delivery_lng
        )

        legs.append(
            {
                "allocation_id": allocation.id,
                "target_type": target_type,
                "target_name": target_name,
                "pickup_latitude": pickup_lat,
                "pickup_longitude": pickup_lng,
                "delivery_latitude": delivery_lat,
                "delivery_longitude": delivery_lng,
                "distance_km": distance_km,
                "estimated_duration_minutes": duration_minutes,
            }
        )
    return legs

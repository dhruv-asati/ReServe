"""
Allocation service: business logic for POST/GET /api/allocations.

An Allocation turns a PROPOSED Match (from a prior matching run — see
app/services/matching_service.py) into a committed slice of a resource's
quantity for a specific Recipient or RescueHub. This module is
responsible for:

  - Validating the match is real, still PROPOSED, and its resource is
    still in an allocatable state.
  - Computing the resource's live remaining quantity (quantity minus
    every active allocation against it) and rejecting anything that
    would over-allocate it.
  - Preventing double allocation: the same match can't be committed
    twice, and the same recipient/hub can't hold two active allocations
    against the same rescue request (even via a different match row,
    e.g. after a matching re-run).
  - Supporting partial allocation: allocated_quantity may be less than
    the full remaining amount, in which case the resource stays
    MATCHING and the rescue request moves to PARTIALLY_MATCHED rather
    than MATCHED — a further allocation later (to another recipient) can
    still fill the rest.
  - Flipping the Match to SELECTED and the Resource to ALLOCATED once its
    full quantity is committed, so the rest of the app (resource
    listing, a future operations stage) sees a consistent picture.

Kept separate from the router so it's reusable without going through
HTTP, same as every other *_service module in this project.
"""

import logging
import uuid
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.core.errors import AppError
from app.models.allocation import Allocation
from app.models.enums import (
    AllocationStatus,
    MatchCandidateType,
    MatchStatus,
    ResourceStatus,
    RescueRequestStatus,
    UserRole,
)
from app.models.match import Match
from app.models.recipient import Recipient
from app.models.rescue_hub import RescueHub
from app.models.rescue_request import RescueRequest
from app.models.resource import Resource
from app.models.user import User
from app.schemas.allocation import AllocationCreate
from app.services import notification_service

logger = logging.getLogger(__name__)

# A resource can only receive a new allocation while it's in one of these
# states — anything else (already fully ALLOCATED and moved on, EXPIRED,
# CANCELLED, DELIVERED, IN_TRANSIT) means there's no honest "remaining
# quantity" left to commit, or the resource is no longer part of an
# active rescue at all.
ALLOCATABLE_RESOURCE_STATUSES = {ResourceStatus.AVAILABLE, ResourceStatus.MATCHING}

# Allocation statuses that actually consume quantity from the resource —
# a CANCELLED or REALLOCATED allocation has given its quantity back up,
# so it's excluded from every "how much is left" computation below.
ACTIVE_ALLOCATION_STATUSES = {AllocationStatus.PENDING, AllocationStatus.CONFIRMED}


def _is_owner_or_admin(resource: Resource, current_user: User) -> bool:
    return current_user.role == UserRole.ADMIN or resource.provider_id == current_user.id


def _get_match_or_404(db: Session, match_id: uuid.UUID) -> Match:
    match = (
        db.query(Match)
        .options(joinedload(Match.rescue_request).joinedload(RescueRequest.resource))
        .filter(Match.id == match_id)
        .first()
    )
    if match is None:
        raise AppError(status_code=404, code="MATCH_NOT_FOUND", message="Match not found.")
    return match


def _allocated_quantity_for_resource(db: Session, resource_id: uuid.UUID) -> float:
    """Sum of every active (PENDING/CONFIRMED) allocation's quantity
    against any rescue request tied to this resource."""
    total = (
        db.query(func.coalesce(func.sum(Allocation.allocated_quantity), 0))
        .join(RescueRequest, Allocation.rescue_request_id == RescueRequest.id)
        .filter(RescueRequest.resource_id == resource_id, Allocation.status.in_(ACTIVE_ALLOCATION_STATUSES))
        .scalar()
    )
    return float(total or 0)


def _remaining_quantity(db: Session, resource: Resource) -> float:
    return float(resource.quantity) - _allocated_quantity_for_resource(db, resource.id)


def get_remaining_quantity(db: Session, resource: Resource) -> float:
    """Public wrapper for the API layer — how much of `resource` is still
    unallocated right now (quantity minus every active allocation)."""
    return _remaining_quantity(db, resource)


def _existing_active_allocation_for_candidate(
    db: Session,
    rescue_request_id: uuid.UUID,
    recipient_id: Optional[uuid.UUID],
    rescue_hub_id: Optional[uuid.UUID],
) -> Optional[Allocation]:
    """
    True double-allocation guard: catches the same recipient/hub already
    holding an active commitment against this rescue request, even if it
    came from a *different* Match row (e.g. a matching re-run generated a
    fresh Match for a recipient who was already allocated from an earlier
    one — re-running matching only deletes Match rows, never
    Allocations, so this is the check that actually matters).
    """
    query = db.query(Allocation).filter(
        Allocation.rescue_request_id == rescue_request_id,
        Allocation.status.in_(ACTIVE_ALLOCATION_STATUSES),
    )
    if recipient_id is not None:
        query = query.filter(Allocation.recipient_id == recipient_id)
    else:
        query = query.filter(Allocation.rescue_hub_id == rescue_hub_id)
    return query.first()


def create_allocation(db: Session, payload: AllocationCreate, current_user: User) -> Allocation:
    match = _get_match_or_404(db, payload.match_id)
    rescue_request = match.rescue_request
    resource = rescue_request.resource

    if not _is_owner_or_admin(resource, current_user):
        raise AppError(
            status_code=403,
            code="NOT_RESOURCE_OWNER",
            message="Only the provider who posted this resource (or an admin) can allocate it.",
        )

    if resource.status not in ALLOCATABLE_RESOURCE_STATUSES:
        raise AppError(
            status_code=409,
            code="RESOURCE_NOT_ALLOCATABLE",
            message=f"Resource status is '{resource.status.value}' and can no longer be allocated.",
        )

    # Prevent double allocation, part 1: this exact match was already
    # committed (or was never eligible in the first place).
    if match.status == MatchStatus.SELECTED:
        raise AppError(
            status_code=409,
            code="MATCH_ALREADY_ALLOCATED",
            message="This match has already been allocated.",
        )
    if match.status != MatchStatus.PROPOSED:
        raise AppError(
            status_code=409,
            code="MATCH_NOT_ELIGIBLE",
            message=f"This match is '{match.status.value}' and is not eligible for allocation. "
            "Only PROPOSED matches can be allocated.",
        )

    # Prevent double allocation, part 2: this recipient/hub already holds
    # an active allocation against this rescue request via some other
    # match row.
    duplicate = _existing_active_allocation_for_candidate(
        db, rescue_request.id, match.recipient_id, match.rescue_hub_id
    )
    if duplicate is not None:
        raise AppError(
            status_code=409,
            code="CANDIDATE_ALREADY_ALLOCATED",
            message="This recipient/rescue hub already has an active allocation for this rescue request.",
        )

    remaining = _remaining_quantity(db, resource)
    if remaining <= 0:
        raise AppError(
            status_code=409,
            code="RESOURCE_FULLY_ALLOCATED",
            message="This resource's full quantity has already been allocated.",
        )

    allocated_quantity = float(payload.allocated_quantity) if payload.allocated_quantity is not None else remaining
    if allocated_quantity > remaining:
        raise AppError(
            status_code=409,
            code="INSUFFICIENT_QUANTITY_AVAILABLE",
            message=f"Only {remaining:g} of this resource remains unallocated; "
            f"cannot allocate {allocated_quantity:g}.",
        )

    recipient: Optional[Recipient] = None
    hub: Optional[RescueHub] = None
    if match.candidate_type == MatchCandidateType.RECIPIENT:
        recipient = db.query(Recipient).filter(Recipient.id == match.recipient_id).first()
        if (
            recipient is not None
            and recipient.capacity is not None
            and allocated_quantity > float(recipient.capacity)
        ):
            raise AppError(
                status_code=409,
                code="EXCEEDS_RECIPIENT_CAPACITY",
                message=f"This recipient's declared capacity ({recipient.capacity:g}) is below the "
                f"requested allocation ({allocated_quantity:g}).",
            )
    else:
        hub = db.query(RescueHub).filter(RescueHub.id == match.rescue_hub_id).first()
        if hub is not None and hub.capacity is not None:
            hub_remaining = float(hub.capacity) - float(hub.current_load)
            if allocated_quantity > hub_remaining:
                raise AppError(
                    status_code=409,
                    code="EXCEEDS_HUB_CAPACITY",
                    message=f"This rescue hub only has {hub_remaining:g} of capacity remaining.",
                )

    allocation = Allocation(
        rescue_request_id=rescue_request.id,
        match_id=match.id,
        recipient_id=match.recipient_id,
        rescue_hub_id=match.rescue_hub_id,
        allocated_quantity=allocated_quantity,
        status=AllocationStatus.PENDING,
        reason=payload.reason,
    )
    db.add(allocation)

    match.status = MatchStatus.SELECTED

    if hub is not None:
        hub.current_load = hub.current_load + int(allocated_quantity)

    new_remaining = remaining - allocated_quantity
    if new_remaining <= 0:
        resource.status = ResourceStatus.ALLOCATED
        rescue_request.status = RescueRequestStatus.MATCHED
    else:
        rescue_request.status = RescueRequestStatus.PARTIALLY_MATCHED

    # Queued on this same transaction, so the allocation and the
    # notifications announcing it are committed together.
    notification_service.notify_allocation_confirmed(
        db, allocation=allocation, resource=resource, recipient=recipient, hub=hub
    )

    db.commit()
    db.refresh(allocation)

    logger.info(
        "Allocation %s created for resource %s: %.2f units to %s %s (by %s)",
        allocation.id,
        resource.id,
        allocated_quantity,
        match.candidate_type.value,
        match.recipient_id or match.rescue_hub_id,
        current_user.id,
    )
    return allocation


def get_allocation_or_404(db: Session, allocation_id: uuid.UUID) -> Allocation:
    allocation = (
        db.query(Allocation)
        .options(
            joinedload(Allocation.recipient),
            joinedload(Allocation.rescue_hub),
            joinedload(Allocation.rescue_request).joinedload(RescueRequest.resource),
        )
        .filter(Allocation.id == allocation_id)
        .first()
    )
    if allocation is None:
        raise AppError(status_code=404, code="ALLOCATION_NOT_FOUND", message="Allocation not found.")
    return allocation


def list_allocations(
    db: Session,
    *,
    resource_id: Optional[uuid.UUID] = None,
    recipient_id: Optional[uuid.UUID] = None,
    rescue_hub_id: Optional[uuid.UUID] = None,
    rescue_request_id: Optional[uuid.UUID] = None,
    status_filter: Optional[AllocationStatus] = None,
    skip: int = 0,
    limit: int = 20,
) -> tuple[list[Allocation], int]:
    query = db.query(Allocation).options(
        joinedload(Allocation.recipient),
        joinedload(Allocation.rescue_hub),
        joinedload(Allocation.rescue_request).joinedload(RescueRequest.resource),
    )

    if resource_id is not None or rescue_request_id is not None:
        query = query.join(RescueRequest, Allocation.rescue_request_id == RescueRequest.id)
        if resource_id is not None:
            query = query.filter(RescueRequest.resource_id == resource_id)
        if rescue_request_id is not None:
            query = query.filter(RescueRequest.id == rescue_request_id)
    if recipient_id is not None:
        query = query.filter(Allocation.recipient_id == recipient_id)
    if rescue_hub_id is not None:
        query = query.filter(Allocation.rescue_hub_id == rescue_hub_id)
    if status_filter is not None:
        query = query.filter(Allocation.status == status_filter)

    total = query.with_entities(func.count(Allocation.id)).scalar() or 0
    items = query.order_by(Allocation.created_at.desc()).offset(skip).limit(limit).all()

    return items, total

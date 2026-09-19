"""
Reallocation service: business logic for
POST /api/operations/{operation_id}/reallocate.

Handles the "a recipient just became unavailable mid-operation" scenario,
end to end:

  1. Cancel the affected allocation — moved to REALLOCATED status (not
     CANCELLED: it wasn't abandoned, it was superseded), freeing its
     quantity back up.
  2. Find another eligible recipient using the same deterministic
     matching engine as POST /api/matching/{resource_id}
     (app/services/matching_engine.py) — same six factors, same scoring,
     no AI involved, fully reproducible from the same inputs.
  3. Reassign the remaining resources — a new Allocation is created for
     the best-scoring eligible replacement, capped at whatever quantity
     is actually still free and at the new recipient's own capacity.
  4. Update the operation — the new allocation is linked onto the same
     RescueOperation, and a REALLOCATED OperationEvent records exactly
     what changed (old allocation, new allocation, quantity, reason).
  5. Save the reallocation reason — stored on the new allocation's
     `reason` field, appended to the old allocation's `reason`, and in
     the OperationEvent's metadata, so the decision is auditable from
     every angle.

The affected recipient is also flipped to `current_availability = False`
as part of step 1 — that flag *is* "the recipient became unavailable" in
this data model, and setting it is what makes the matching engine
naturally exclude them from being proposed again as their own
replacement.

If no eligible replacement exists, the original allocation is still
cancelled (the recipient really is unavailable, replacement or not) but
no new allocation is created; the operation/rescue-request status
reflects the resource being partially unassigned again. This is a
successful call with `reallocated: false`, not an error — the caller
(and the OperationEvent log) can see clearly what was attempted and why
it came up empty.

Kept separate from the router so it's reusable without going through
HTTP, same as every other *_service module in this project.
"""

import logging
import uuid
from typing import Optional

from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models.allocation import Allocation
from app.models.enums import (
    AllocationStatus,
    MatchCandidateType,
    MatchStatus,
    OperationEventType,
    OperationStatus,
    ResourceStatus,
    ResourceType,
    RescueRequestStatus,
    UserRole,
)
from app.models.match import Match
from app.models.operation import OperationEvent, RescueOperation
from app.models.recipient import Recipient
from app.models.rescue_request import RescueRequest
from app.models.user import User
from app.schemas.reallocation import ReallocationRequest
from app.services import allocation_service, matching_engine, notification_service, operation_service

logger = logging.getLogger(__name__)

# An operation can only be reallocated while it hasn't finished executing —
# once DELIVERED/COMPLETED/FAILED there's nothing left in flight to
# reassign.
REALLOCATABLE_OPERATION_STATUSES = {OperationStatus.PLANNED, OperationStatus.IN_TRANSIT}

# Same "still consuming quantity" definition allocation_service uses.
ACTIVE_ALLOCATION_STATUSES = {AllocationStatus.PENDING, AllocationStatus.CONFIRMED}


def _is_authorized(operation: RescueOperation, resource, current_user: User) -> bool:
    if current_user.role == UserRole.ADMIN or resource.provider_id == current_user.id:
        return True
    return (
        current_user.role == UserRole.RESCUE_PARTNER
        and operation.partner is not None
        and operation.partner.user_id == current_user.id
    )


def _get_active_allocation_on_operation(operation: RescueOperation, allocation_id: uuid.UUID) -> Allocation:
    for allocation in operation.allocations:
        if allocation.id == allocation_id:
            return allocation
    raise AppError(
        status_code=404,
        code="ALLOCATION_NOT_FOUND_ON_OPERATION",
        message=f"Allocation {allocation_id} is not linked to this operation.",
    )


def find_replacement_recipient(
    db: Session,
    resource,
    rescue_request: RescueRequest,
    exclude_recipient_ids: set,
) -> Optional[tuple[Recipient, "matching_engine.MatchCandidateResult"]]:
    """
    Runs the deterministic matching engine against every eligible
    recipient (excluding whoever already holds an active allocation on
    this rescue request, including the one just cancelled), and returns
    the single best PROPOSED candidate — highest score first, ties broken
    by recipient id (ascending) so the outcome is 100% reproducible for
    identical inputs. Returns None if no candidate clears every hard gate.
    """
    query = db.query(Recipient)
    if resource.resource_type == ResourceType.FOOD:
        query = query.filter(Recipient.accepts_food.is_(True))
    else:
        query = query.filter(Recipient.accepts_medical.is_(True))
    if exclude_recipient_ids:
        query = query.filter(~Recipient.id.in_(exclude_recipient_ids))

    candidates = query.order_by(Recipient.id.asc()).all()

    best: Optional[tuple[Recipient, "matching_engine.MatchCandidateResult"]] = None
    for recipient in candidates:
        result = matching_engine.evaluate_candidate(resource, rescue_request, recipient)
        if result.status != MatchStatus.PROPOSED:
            continue
        if (
            best is None
            or result.overall_score > best[1].overall_score
            or (result.overall_score == best[1].overall_score and str(recipient.id) < str(best[0].id))
        ):
            best = (recipient, result)

    return best


def reallocate(
    db: Session, operation_id: uuid.UUID, payload: ReallocationRequest, current_user: User
) -> tuple[RescueOperation, Allocation, Optional[Allocation], bool]:
    """
    Executes the full reallocation flow. Returns
    (operation, cancelled_allocation, new_allocation_or_None, reallocated).
    """
    operation = operation_service.get_operation_or_404(db, operation_id)
    rescue_request = operation.rescue_request
    resource = rescue_request.resource

    if not _is_authorized(operation, resource, current_user):
        raise AppError(
            status_code=403,
            code="NOT_AUTHORIZED",
            message="Only the resource's provider, the partner assigned to this operation, or an "
            "admin can trigger reallocation.",
        )

    if operation.status not in REALLOCATABLE_OPERATION_STATUSES:
        raise AppError(
            status_code=409,
            code="OPERATION_NOT_REALLOCATABLE",
            message=f"Operation is '{operation.status.value}' and can no longer be reallocated. "
            f"Only {', '.join(s.value for s in REALLOCATABLE_OPERATION_STATUSES)} operations can be.",
        )

    old_allocation = _get_active_allocation_on_operation(operation, payload.allocation_id)

    if old_allocation.status not in ACTIVE_ALLOCATION_STATUSES:
        raise AppError(
            status_code=409,
            code="ALLOCATION_NOT_ACTIVE",
            message=f"Allocation is '{old_allocation.status.value}', not active — there's nothing "
            "to reallocate.",
        )

    if old_allocation.recipient_id is None:
        raise AppError(
            status_code=409,
            code="REALLOCATION_REQUIRES_RECIPIENT",
            message="This allocation is assigned to a rescue hub, not a recipient. Reallocation "
            "by recipient-unavailability only applies to recipient allocations.",
        )

    old_recipient = old_allocation.recipient
    quantity = float(old_allocation.allocated_quantity)

    # Step 1: cancel the affected allocation. Marked REALLOCATED (not
    # CANCELLED) — it wasn't abandoned, it's being superseded — which
    # also frees its quantity back up (excluded from every "how much is
    # left" computation, see allocation_service.ACTIVE_ALLOCATION_STATUSES).
    old_allocation.status = AllocationStatus.REALLOCATED
    old_allocation.reason = (
        f"{old_allocation.reason} — reallocated: {payload.reason}" if old_allocation.reason else
        f"Reallocated: {payload.reason}"
    )

    # "The recipient became unavailable" *is* this flag in this data
    # model. Flipping it is what makes the matching engine's own
    # availability gate naturally exclude them below.
    if old_recipient.current_availability:
        old_recipient.current_availability = False

    db.flush()  # old_allocation is now inactive; remaining-quantity queries below must see that

    # Step 2: find another eligible recipient using the matching engine.
    exclude_ids = {
        a.recipient_id
        for a in rescue_request.allocations
        if a.recipient_id is not None and a.status in ACTIVE_ALLOCATION_STATUSES
    }
    exclude_ids.add(old_recipient.id)

    replacement = find_replacement_recipient(db, resource, rescue_request, exclude_ids)

    new_allocation: Optional[Allocation] = None
    reassigned_quantity = 0.0

    if replacement is not None:
        new_recipient, result = replacement

        # Step 3: reassign the remaining resources — cap at what's
        # actually still free on the resource and at the new recipient's
        # own declared capacity, so this can never over-commit either.
        remaining_on_resource = allocation_service.get_remaining_quantity(db, resource)
        reassigned_quantity = min(quantity, remaining_on_resource)
        if new_recipient.capacity is not None:
            reassigned_quantity = min(reassigned_quantity, float(new_recipient.capacity))
        reassigned_quantity = round(reassigned_quantity, 2)

        if reassigned_quantity <= 0:
            replacement = None  # nothing left to actually hand over — treat as no replacement
        else:
            match = Match(
                rescue_request_id=rescue_request.id,
                candidate_type=MatchCandidateType.RECIPIENT,
                recipient_id=new_recipient.id,
                distance_km=result.distance_km,
                score=result.overall_score,
                status=MatchStatus.SELECTED,
                reasons=result.reasons_payload(),
            )
            db.add(match)
            db.flush()

            new_allocation = Allocation(
                rescue_request_id=rescue_request.id,
                operation_id=operation.id,
                match_id=match.id,
                recipient_id=new_recipient.id,
                allocated_quantity=reassigned_quantity,
                status=AllocationStatus.PENDING,
                # Step 5: save the reallocation reason.
                reason=f"Reallocated from {old_recipient.organization_name} "
                f"({payload.reason}). Matching score {result.overall_score:.2f}.",
            )
            db.add(new_allocation)
            db.flush()

    reallocated = new_allocation is not None

    # Step 4: update the operation — append the audit event.
    if reallocated:
        description = (
            f"Reallocated {reassigned_quantity:g} unit(s) from {old_recipient.organization_name} "
            f"to {new_allocation.recipient.organization_name} — {payload.reason}"
        )
    else:
        description = (
            f"{old_recipient.organization_name} became unavailable ({payload.reason}); no eligible "
            "replacement recipient was found. Allocation cancelled; its quantity is unassigned."
        )

    db.add(
        OperationEvent(
            operation_id=operation.id,
            event_type=OperationEventType.REALLOCATED,
            description=description,
            event_metadata={
                "cancelled_allocation_id": str(old_allocation.id),
                "old_recipient_id": str(old_recipient.id),
                "new_allocation_id": str(new_allocation.id) if new_allocation else None,
                "new_recipient_id": str(new_allocation.recipient_id) if new_allocation else None,
                "reallocated_quantity": reassigned_quantity if reallocated else 0.0,
                "reason": payload.reason,
            },
            created_by_user_id=current_user.id,
        )
    )

    # Reflect the outcome on the resource/rescue request, same "how much
    # is left" logic allocation_service uses when an allocation is first
    # created.
    remaining_after = allocation_service.get_remaining_quantity(db, resource)
    if remaining_after <= 0:
        resource.status = ResourceStatus.ALLOCATED
        rescue_request.status = RescueRequestStatus.MATCHED
    else:
        if resource.status == ResourceStatus.ALLOCATED:
            resource.status = ResourceStatus.MATCHING
        rescue_request.status = RescueRequestStatus.PARTIALLY_MATCHED

    # Queued on this same transaction alongside the allocation changes and
    # the REALLOCATED event above. `new_allocation.recipient` is safe to
    # read here: the row was flushed above, so the relationship resolves.
    notification_service.notify_reallocation(
        db,
        operation=operation,
        resource=resource,
        old_recipient=old_recipient,
        new_recipient=new_allocation.recipient if new_allocation is not None else None,
        quantity=reassigned_quantity,
        reason=payload.reason,
    )

    db.commit()
    db.refresh(operation)
    db.refresh(old_allocation)
    if new_allocation is not None:
        db.refresh(new_allocation)

    logger.info(
        "Reallocation on operation %s: allocation %s (recipient %s) cancelled — %s (by %s)",
        operation.id,
        old_allocation.id,
        old_recipient.id,
        f"reassigned {reassigned_quantity:g} unit(s) to recipient {new_allocation.recipient_id}"
        if reallocated
        else "no eligible replacement found",
        current_user.id,
    )

    return operation, old_allocation, new_allocation, reallocated

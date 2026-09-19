"""
Matching service: orchestrates a matching run for a single Resource.

This is the glue between the API layer (app/api/matching.py) and the pure
scoring logic in app/services/matching_engine.py. It is responsible for:

  - Loading and validating the Resource (rejecting expired/unavailable ones).
  - Creating or reusing the Resource's RescueRequest coordination record.
  - Building the candidate pool of Recipients from the database.
  - Calling the deterministic matching engine for each candidate.
  - Persisting the results as `Match` rows so every candidate — proposed
    or rejected — is stored with its full, auditable score breakdown.
  - Reading back the most recent matching run for a resource.

Stage scope: this is Part 1 of the matching engine. It generates and
persists ranked/explained candidates only. It deliberately does NOT select
a winner, create an Allocation, or move a resource past `MATCHING` status —
that's allocation/reallocation logic for a later stage. It also never
calls Gemini or any other AI service: every decision here is rule-based
and reproducible from the same inputs (see matching_engine.py's docstring).
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session, joinedload

from app.core.errors import AppError
from app.models.enums import (
    MatchCandidateType,
    MatchStatus,
    ResourceStatus,
    ResourceType,
    RescueRequestStatus,
    UserRole,
)
from app.models.match import Match
from app.models.recipient import Recipient
from app.models.resource import Resource
from app.models.rescue_request import RescueRequest
from app.models.user import User
from app.schemas.matching import TriggerMatchingRequest
from app.services import matching_engine

logger = logging.getLogger(__name__)

# Resource statuses a matching run may be triggered against. Anything else
# (ALLOCATED, IN_TRANSIT, DELIVERED, EXPIRED, CANCELLED) is not eligible —
# this is the "exclude expired or unavailable resources" requirement,
# enforced at the resource level before any candidate is even considered.
MATCHABLE_RESOURCE_STATUSES = {ResourceStatus.AVAILABLE, ResourceStatus.MATCHING}

# Non-terminal RescueRequest statuses: if one already exists in one of
# these states for the resource, it is reused/refreshed rather than
# creating a duplicate coordination record.
ACTIVE_RESCUE_REQUEST_STATUSES = {
    RescueRequestStatus.PENDING,
    RescueRequestStatus.MATCHING,
    RescueRequestStatus.PARTIALLY_MATCHED,
}


def _is_owner_or_admin(resource: Resource, current_user: User) -> bool:
    return current_user.role == UserRole.ADMIN or resource.provider_id == current_user.id


def _get_resource_or_404(db: Session, resource_id: uuid.UUID) -> Resource:
    resource = db.query(Resource).filter(Resource.id == resource_id).first()
    if resource is None:
        raise AppError(status_code=404, code="RESOURCE_NOT_FOUND", message="Resource not found.")
    return resource


def _ensure_resource_matchable(db: Session, resource: Resource) -> None:
    """
    Raises if this resource cannot be matched right now: wrong status, or
    past its expiry deadline. Flips an expired-but-not-yet-flagged resource
    to EXPIRED as a side effect, so the data stays consistent for anyone
    looking at it afterwards — this is data hygiene, not an allocation
    decision.
    """
    now = datetime.now(timezone.utc)

    if resource.expiry_time is not None and resource.expiry_time <= now:
        if resource.status not in (ResourceStatus.EXPIRED, ResourceStatus.CANCELLED):
            resource.status = ResourceStatus.EXPIRED
            db.commit()
        raise AppError(
            status_code=409,
            code="RESOURCE_EXPIRED",
            message="This resource's expiry_time has already passed and it can no longer be matched.",
        )

    if resource.status not in MATCHABLE_RESOURCE_STATUSES:
        raise AppError(
            status_code=409,
            code="RESOURCE_NOT_MATCHABLE",
            message=(
                f"Resource status is '{resource.status.value}'. Only resources with status "
                f"{', '.join(s.value for s in MATCHABLE_RESOURCE_STATUSES)} can be matched."
            ),
        )


def _get_or_create_rescue_request(
    db: Session, resource: Resource, payload: TriggerMatchingRequest
) -> RescueRequest:
    existing = (
        db.query(RescueRequest)
        .filter(
            RescueRequest.resource_id == resource.id,
            RescueRequest.status.in_(ACTIVE_RESCUE_REQUEST_STATUSES),
        )
        .order_by(RescueRequest.created_at.desc())
        .first()
    )

    requested_quantity = payload.requested_quantity or float(resource.quantity)
    urgency = payload.urgency_override or resource.urgency

    if existing is not None:
        existing.requested_quantity = requested_quantity
        existing.urgency = urgency
        existing.deadline = resource.expiry_time
        if payload.notes is not None:
            existing.notes = payload.notes
        existing.status = RescueRequestStatus.MATCHING
        db.commit()
        db.refresh(existing)
        return existing

    rescue_request = RescueRequest(
        resource_id=resource.id,
        status=RescueRequestStatus.MATCHING,
        requested_quantity=requested_quantity,
        urgency=urgency,
        deadline=resource.expiry_time,
        notes=payload.notes,
    )
    db.add(rescue_request)
    db.commit()
    db.refresh(rescue_request)
    return rescue_request


def _candidate_recipients(db: Session, resource: Resource) -> list[Recipient]:
    """
    The base candidate pool: every Recipient whose profile says they
    accept this resource_type at all. This is requirement #1 (resource-
    type compatibility) applied as a query filter rather than a per-row
    check, purely for efficiency — every other factor (eligibility,
    availability, capacity, distance, urgency) is still evaluated and
    explained per candidate by the matching engine.
    """
    query = db.query(Recipient)
    if resource.resource_type == ResourceType.FOOD:
        query = query.filter(Recipient.accepts_food.is_(True))
    else:
        query = query.filter(Recipient.accepts_medical.is_(True))

    return query.order_by(Recipient.id.asc()).all()


def run_matching(db: Session, resource_id: uuid.UUID, payload: TriggerMatchingRequest, current_user: User) -> RescueRequest:
    """
    Runs (or re-runs) a full matching pass for a resource: validates the
    resource is matchable, gets/creates its RescueRequest, scores every
    candidate recipient with the deterministic matching engine, and
    persists the results as Match rows. Returns the RescueRequest — call
    get_results() to read the persisted candidates back out.

    Only the resource's own provider or an ADMIN may trigger matching for
    it, same ownership rule as editing/deleting a resource.
    """
    resource = _get_resource_or_404(db, resource_id)

    if not _is_owner_or_admin(resource, current_user):
        raise AppError(
            status_code=403,
            code="NOT_RESOURCE_OWNER",
            message="Only the provider who posted this resource (or an admin) can trigger matching for it.",
        )

    _ensure_resource_matchable(db, resource)

    rescue_request = _get_or_create_rescue_request(db, resource, payload)

    # Recompute from scratch each run: this stage doesn't accumulate a
    # match history, it produces a fresh, current snapshot of candidates.
    db.query(Match).filter(Match.rescue_request_id == rescue_request.id).delete()

    candidates = _candidate_recipients(db, resource)

    match_rows: list[Match] = []
    for recipient in candidates:
        result = matching_engine.evaluate_candidate(resource, rescue_request, recipient)
        match_rows.append(
            Match(
                rescue_request_id=rescue_request.id,
                candidate_type=MatchCandidateType.RECIPIENT,
                recipient_id=recipient.id,
                distance_km=result.distance_km,
                score=result.overall_score,
                status=result.status,
                reasons=result.reasons_payload(),
            )
        )

    db.add_all(match_rows)

    if resource.status == ResourceStatus.AVAILABLE:
        resource.status = ResourceStatus.MATCHING

    # Reflect the outcome of this run on the RescueRequest itself: MATCHED
    # if at least one candidate cleared every hard gate, FAILED if every
    # candidate was rejected (or there were no candidates at all). This is
    # just a status reflecting what was just computed — it does not select
    # a winner or allocate anything (that's a later stage).
    any_proposed = any(m.status == MatchStatus.PROPOSED for m in match_rows)
    rescue_request.status = RescueRequestStatus.MATCHED if any_proposed else RescueRequestStatus.FAILED

    db.commit()
    db.refresh(rescue_request)

    logger.info(
        "Matching run for resource %s: %d candidate(s) considered, %d proposed, %d rejected.",
        resource.id,
        len(match_rows),
        sum(1 for m in match_rows if m.status == MatchStatus.PROPOSED),
        sum(1 for m in match_rows if m.status == MatchStatus.REJECTED),
    )

    return rescue_request


def get_latest_results(db: Session, resource_id: uuid.UUID) -> tuple[Resource, RescueRequest, list[Match]]:
    """
    Reads back the most recent matching run for a resource, without
    recomputing anything. Raises 404 if the resource doesn't exist, or if
    no matching run has ever been performed for it (POST first).
    """
    resource = _get_resource_or_404(db, resource_id)

    rescue_request = (
        db.query(RescueRequest)
        .filter(RescueRequest.resource_id == resource.id)
        .order_by(RescueRequest.created_at.desc())
        .first()
    )
    if rescue_request is None:
        raise AppError(
            status_code=404,
            code="NO_MATCHING_RUN",
            message="No matching run has been performed for this resource yet. "
            "Call POST /api/matching/{resource_id} first.",
        )

    matches = (
        db.query(Match)
        .options(joinedload(Match.recipient))
        .filter(Match.rescue_request_id == rescue_request.id)
        .all()
    )
    matches.sort(key=lambda m: (m.status != MatchStatus.PROPOSED, -(m.score or 0.0)))

    return resource, rescue_request, matches

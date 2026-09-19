"""
Matching endpoints:

    POST /api/matching/{resource_id}          Run (or re-run) matching for a resource
    GET  /api/matching/{resource_id}/results   Read back the latest matching run

The actual scoring is entirely deterministic and lives in
app/services/matching_engine.py; this router and app/services/matching_service.py
only handle HTTP concerns, authorization, and persistence. No AI model is
consulted anywhere in this flow — see matching_engine.py's module docstring.

Triggering a run is restricted to the resource's own provider (or an
ADMIN), same rule as editing/deleting a resource. Reading results is open
to any authenticated user, same as viewing a resource.
"""

import logging
import uuid

from fastapi import APIRouter, Body, Depends, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.database import get_db
from app.models.user import User
from app.schemas.common import SuccessResponse
from app.schemas.matching import (
    MatchCandidateOut,
    MatchingResultsData,
    RecipientSummary,
    TriggerMatchingRequest,
)
from app.services import matching_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/matching", tags=["Matching"])


def _to_candidate_out(match) -> MatchCandidateOut:
    reasons = match.reasons or {}
    breakdown = reasons.get("breakdown", {})
    return MatchCandidateOut(
        match_id=match.id,
        recipient=RecipientSummary.model_validate(match.recipient),
        status=match.status,
        score=match.score or 0.0,
        distance_km=match.distance_km,
        breakdown=breakdown,
        explanation=reasons.get("explanation", ""),
        passed_reasons=reasons.get("passed", []),
        rejection_reasons=reasons.get("failed", []),
    )


def _to_results_data(resource, rescue_request, matches) -> MatchingResultsData:
    candidates = [_to_candidate_out(m) for m in matches]
    eligible_count = sum(1 for c in candidates if c.status.value == "PROPOSED")
    return MatchingResultsData(
        resource_id=resource.id,
        rescue_request_id=rescue_request.id,
        rescue_request_status=rescue_request.status,
        requested_quantity=float(rescue_request.requested_quantity),
        urgency=rescue_request.urgency,
        generated_at=rescue_request.updated_at,
        total_candidates_considered=len(candidates),
        eligible_count=eligible_count,
        rejected_count=len(candidates) - eligible_count,
        candidates=candidates,
    )


@router.post(
    "/{resource_id}",
    response_model=SuccessResponse[MatchingResultsData],
    status_code=status.HTTP_201_CREATED,
    summary="Run matching for a resource",
    description=(
        "Runs the deterministic matching engine for a resource: creates or refreshes its "
        "RescueRequest, scores every eligible recipient against resource-type compatibility, "
        "recipient eligibility, availability, capacity, distance, and urgency, and persists a "
        "fresh, ranked, fully-explained list of candidates (proposed and rejected). Excludes "
        "expired or otherwise unavailable resources. Only the resource's own provider or an "
        "admin may trigger this. Safe to re-run — each call replaces the previous candidate "
        "list with a current one. This never selects a winner or allocates anything; that is a "
        "later stage."
    ),
)
def trigger_matching(
    resource_id: uuid.UUID,
    payload: TriggerMatchingRequest = Body(default_factory=TriggerMatchingRequest),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    matching_service.run_matching(db, resource_id, payload, current_user)
    resource, rescue_request, matches = matching_service.get_latest_results(db, resource_id)
    data = _to_results_data(resource, rescue_request, matches)
    return SuccessResponse(
        data=data, message=f"Matching complete: {data.eligible_count} eligible candidate(s) found."
    )


@router.get(
    "/{resource_id}/results",
    response_model=SuccessResponse[MatchingResultsData],
    summary="Get the latest matching results for a resource",
    description=(
        "Returns the most recent matching run's candidates for a resource, without "
        "recomputing anything. Call POST /api/matching/{resource_id} first if no run has "
        "been performed yet. Available to any authenticated user."
    ),
)
def get_matching_results(
    resource_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    resource, rescue_request, matches = matching_service.get_latest_results(db, resource_id)
    data = _to_results_data(resource, rescue_request, matches)
    return SuccessResponse(data=data, message=f"Found {data.total_candidates_considered} candidate(s).")

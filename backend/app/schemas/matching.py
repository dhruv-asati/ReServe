"""
Pydantic schemas for the matching engine endpoints:

    POST /api/matching/{resource_id}
    GET  /api/matching/{resource_id}/results

These wrap the deterministic output of app/services/matching_engine.py
(via app/services/matching_service.py) for the API layer. Nothing here
performs scoring itself — it's pure request/response shape.
"""

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import MatchStatus, RecipientType, RescueRequestStatus, UrgencyLevel


class TriggerMatchingRequest(BaseModel):
    """
    Optional overrides for a matching run. Everything defaults to the
    resource's own values, so `POST /api/matching/{resource_id}` with an
    empty body (`{}`) is a perfectly valid call.
    """

    requested_quantity: Optional[float] = Field(
        default=None,
        gt=0,
        description="Quantity to match against. Defaults to the resource's full quantity.",
    )
    urgency_override: Optional[UrgencyLevel] = Field(
        default=None,
        description="Override urgency for this matching run only. Defaults to the resource's urgency.",
    )
    notes: Optional[str] = Field(default=None, max_length=2000)


# --- Score breakdown shapes --------------------------------------------------


class ScoreComponentOut(BaseModel):
    score: float
    passed: bool
    detail: str


class DistanceComponentOut(ScoreComponentOut):
    distance_km: Optional[float] = None


class UrgencyComponentOut(ScoreComponentOut):
    pass


class MatchScoreBreakdown(BaseModel):
    resource_type_compatibility: ScoreComponentOut
    recipient_eligibility: ScoreComponentOut
    recipient_availability: ScoreComponentOut
    capacity: ScoreComponentOut
    distance: DistanceComponentOut
    urgency: UrgencyComponentOut


# --- Candidate + recipient summary ------------------------------------------


class RecipientSummary(BaseModel):
    id: uuid.UUID
    organization_name: str
    recipient_type: RecipientType
    location_address: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None

    model_config = ConfigDict(from_attributes=True)


class MatchCandidateOut(BaseModel):
    match_id: uuid.UUID
    recipient: RecipientSummary

    status: MatchStatus
    score: float = Field(description="Overall weighted score in [0, 1]. 0.0 for rejected candidates.")
    distance_km: Optional[float] = None

    breakdown: MatchScoreBreakdown
    explanation: str = Field(description="Human-readable summary of why this candidate was selected or rejected.")
    passed_reasons: list[str] = Field(default_factory=list)
    rejection_reasons: list[str] = Field(default_factory=list)


class MatchingResultsData(BaseModel):
    resource_id: uuid.UUID
    rescue_request_id: uuid.UUID
    rescue_request_status: RescueRequestStatus

    requested_quantity: float
    urgency: UrgencyLevel

    generated_at: datetime

    total_candidates_considered: int
    eligible_count: int
    rejected_count: int

    candidates: list[MatchCandidateOut]

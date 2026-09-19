"""
Matching engine: deterministic candidate scoring for a single Resource.

This module is the "brain" of the matching system and is deliberately kept
separate from both the API routes (app/api/matching.py) and the
orchestration/DB layer (app/services/matching_service.py). Everything here
is pure — it takes already-loaded ORM objects (a Resource, a RescueRequest,
a Recipient) and returns plain dataclasses describing the score. It never
opens a database session, never commits anything, and never calls out to
Gemini or any other AI service.

Why this matters:
  - Testable without a database: construct Resource/RescueRequest/Recipient
    instances in memory and call `evaluate_candidate` directly.
  - Auditable: every candidate — matched or rejected — gets a full,
    human-readable breakdown of every factor that was considered.
  - Deterministic: the same inputs always produce the same score. There is
    no model call, no randomness, and no hidden state. This is intentional
    per ReServe's design: Gemini (see app/services/gemini_service.py) is
    only ever used to *structure/describe* a resource on creation — it is
    never consulted here and has no influence over which candidates are
    proposed, scored, or rejected.

Six factors are evaluated, per the matching engine spec:
  1. Resource-type compatibility  -> hard gate
  2. Recipient eligibility        -> hard gate (platform + medical verification)
  3. Recipient availability       -> hard gate
  4. Available capacity           -> soft-scored, can also hard-fail at zero
  5. Distance provider -> recipient -> soft-scored, can hard-fail outside
     the recipient's declared service area
  6. Urgency of the resource      -> soft-scored + reweights how much
     distance matters (the more urgent the rescue, the more a candidate's
     score is driven by proximity)

A candidate that fails ANY hard gate is returned with status REJECTED and
an overall score of 0.0. A candidate that clears every hard gate is
returned with status PROPOSED and a weighted overall score in [0, 1].
Nothing here ever assigns a final allocation — that is out of scope for
this stage (see app/services/matching_service.py's module docstring).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional, TYPE_CHECKING

from app.models.enums import MatchStatus, ResourceType, UrgencyLevel

if TYPE_CHECKING:
    from app.models.recipient import Recipient
    from app.models.rescue_request import RescueRequest
    from app.models.resource import Resource


# --- Tunable constants (kept here, not scattered through the logic below,
# so the weighting policy is easy to find, review, and change) -------------

# Distance (km) beyond which the proximity score bottoms out at 0. A
# recipient right next door scores 1.0; one exactly at this distance (and
# not blocked by their own service_area_km) scores 0.0.
MAX_SCORED_DISTANCE_KM = 50.0

# Resource urgency contributes its own fixed score component, AND changes
# how heavily distance is weighted in the overall score below — the more
# urgent the rescue, the more that "closest wins".
URGENCY_SCORE_BY_LEVEL: dict[UrgencyLevel, float] = {
    UrgencyLevel.LOW: 0.25,
    UrgencyLevel.MEDIUM: 0.50,
    UrgencyLevel.HIGH: 0.75,
    UrgencyLevel.CRITICAL: 1.00,
}

# Weights for the three soft-scored components (capacity, distance,
# urgency), keyed by resource urgency. Each row sums to 1.0.
_WEIGHTS_BY_URGENCY: dict[UrgencyLevel, dict[str, float]] = {
    UrgencyLevel.LOW: {"capacity": 0.40, "distance": 0.30, "urgency": 0.30},
    UrgencyLevel.MEDIUM: {"capacity": 0.35, "distance": 0.35, "urgency": 0.30},
    UrgencyLevel.HIGH: {"capacity": 0.30, "distance": 0.45, "urgency": 0.25},
    UrgencyLevel.CRITICAL: {"capacity": 0.25, "distance": 0.55, "urgency": 0.20},
}

EARTH_RADIUS_KM = 6371.0088


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance between two lat/lon points, in kilometers."""
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)

    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return EARTH_RADIUS_KM * c


# --- Result shapes ----------------------------------------------------------


@dataclass
class ScoreComponent:
    """One scored/gated factor in the breakdown."""

    score: float  # normalized 0.0-1.0
    passed: bool  # whether this factor alone would block the candidate
    detail: str  # human-readable explanation of this factor's value

    def as_dict(self) -> dict:
        return {"score": round(self.score, 4), "passed": self.passed, "detail": self.detail}


@dataclass
class DistanceComponent(ScoreComponent):
    distance_km: Optional[float] = None

    def as_dict(self) -> dict:
        data = super().as_dict()
        data["distance_km"] = round(self.distance_km, 2) if self.distance_km is not None else None
        return data


@dataclass
class MatchCandidateResult:
    """
    The fully-scored outcome for one (resource, recipient) pair. Maps
    directly onto the fields matching_service.py needs to persist as a
    `Match` row (see app/models/match.py).
    """

    recipient_id: "object"  # uuid.UUID, typed loosely to avoid importing uuid just for this
    status: MatchStatus
    overall_score: float
    distance_km: Optional[float]
    breakdown: dict = field(default_factory=dict)
    passed_reasons: list[str] = field(default_factory=list)
    failed_reasons: list[str] = field(default_factory=list)
    explanation: str = ""

    def reasons_payload(self) -> dict:
        """The structured dict stored in Match.reasons (JSON column)."""
        return {
            "breakdown": self.breakdown,
            "passed": self.passed_reasons,
            "failed": self.failed_reasons,
            "explanation": self.explanation,
        }


# --- Individual factor evaluators -------------------------------------------


def _score_type_compatibility(resource: "Resource", recipient: "Recipient") -> ScoreComponent:
    if resource.resource_type == ResourceType.FOOD:
        passed = bool(recipient.accepts_food)
        detail = (
            "recipient accepts FOOD resources"
            if passed
            else "recipient does not accept FOOD resources"
        )
    else:
        passed = bool(recipient.accepts_medical)
        detail = (
            "recipient accepts MEDICAL resources"
            if passed
            else "recipient does not accept MEDICAL resources"
        )
    return ScoreComponent(score=1.0 if passed else 0.0, passed=passed, detail=detail)


def _score_eligibility(resource: "Resource", recipient: "Recipient") -> ScoreComponent:
    if not recipient.is_verified:
        return ScoreComponent(score=0.0, passed=False, detail="recipient is not platform-verified")

    if resource.resource_type == ResourceType.MEDICAL and not recipient.medical_verified:
        return ScoreComponent(
            score=0.0,
            passed=False,
            detail="recipient is not medical-verified, required for MEDICAL resources",
        )

    return ScoreComponent(score=1.0, passed=True, detail="recipient is verified and eligible")


def _score_availability(recipient: "Recipient") -> ScoreComponent:
    passed = bool(recipient.current_availability)
    detail = "recipient is currently available" if passed else "recipient marked themselves unavailable"
    return ScoreComponent(score=1.0 if passed else 0.0, passed=passed, detail=detail)


def _score_capacity(requested_quantity: float, recipient: "Recipient") -> ScoreComponent:
    capacity = recipient.capacity

    if capacity is None:
        return ScoreComponent(score=1.0, passed=True, detail="no capacity limit set for this recipient")

    capacity = float(capacity)

    if capacity <= 0:
        return ScoreComponent(score=0.0, passed=False, detail="recipient has zero remaining capacity")

    if capacity >= requested_quantity:
        return ScoreComponent(
            score=1.0,
            passed=True,
            detail=f"capacity ({capacity:g}) covers the full requested quantity ({requested_quantity:g})",
        )

    # Positive capacity that only covers part of the request. Not a hard
    # fail (allocation/partial-fulfillment logic is a later stage) but it
    # scores lower than a full-coverage candidate.
    ratio = capacity / requested_quantity
    return ScoreComponent(
        score=round(ratio, 4),
        passed=True,
        detail=f"can only take {capacity:g} of the {requested_quantity:g} requested (partial capacity)",
    )


def _score_distance(resource: "Resource", recipient: "Recipient") -> DistanceComponent:
    if (
        resource.latitude is None
        or resource.longitude is None
        or recipient.latitude is None
        or recipient.longitude is None
    ):
        return DistanceComponent(
            score=0.5,
            passed=True,
            detail="distance unknown — missing coordinates for provider or recipient",
            distance_km=None,
        )

    distance_km = haversine_km(resource.latitude, resource.longitude, recipient.latitude, recipient.longitude)

    if recipient.service_area_km is not None and distance_km > float(recipient.service_area_km):
        return DistanceComponent(
            score=0.0,
            passed=False,
            detail=(
                f"{distance_km:.1f}km away, outside the recipient's declared "
                f"service area of {float(recipient.service_area_km):g}km"
            ),
            distance_km=distance_km,
        )

    proximity_score = max(0.0, min(1.0, 1.0 - (distance_km / MAX_SCORED_DISTANCE_KM)))
    return DistanceComponent(
        score=proximity_score,
        passed=True,
        detail=f"{distance_km:.1f}km from the resource's pickup location",
        distance_km=distance_km,
    )


def _score_urgency(urgency: UrgencyLevel) -> ScoreComponent:
    score = URGENCY_SCORE_BY_LEVEL[urgency]
    return ScoreComponent(
        score=score,
        passed=True,
        detail=f"resource urgency is {urgency.value}",
    )


# --- Public entry point ------------------------------------------------------


def evaluate_candidate(
    resource: "Resource",
    rescue_request: "RescueRequest",
    recipient: "Recipient",
) -> MatchCandidateResult:
    """
    Score a single recipient as a candidate for the given resource /
    rescue request. Pure function — no I/O, no AI, fully deterministic.
    """
    requested_quantity = float(rescue_request.requested_quantity)
    urgency = rescue_request.urgency

    type_component = _score_type_compatibility(resource, recipient)
    eligibility_component = _score_eligibility(resource, recipient)
    availability_component = _score_availability(recipient)
    capacity_component = _score_capacity(requested_quantity, recipient)
    distance_component = _score_distance(resource, recipient)
    urgency_component = _score_urgency(urgency)

    breakdown = {
        "resource_type_compatibility": type_component.as_dict(),
        "recipient_eligibility": eligibility_component.as_dict(),
        "recipient_availability": availability_component.as_dict(),
        "capacity": capacity_component.as_dict(),
        "distance": distance_component.as_dict(),
        "urgency": urgency_component.as_dict(),
    }

    gates = [type_component, eligibility_component, availability_component, capacity_component, distance_component]
    passed_reasons = [c.detail for c in gates + [urgency_component] if c.passed]
    failed_reasons = [c.detail for c in gates if not c.passed]

    hard_pass = all(c.passed for c in gates)

    if not hard_pass:
        explanation = "Rejected — " + "; ".join(failed_reasons) + "."
        return MatchCandidateResult(
            recipient_id=recipient.id,
            status=MatchStatus.REJECTED,
            overall_score=0.0,
            distance_km=distance_component.distance_km,
            breakdown=breakdown,
            passed_reasons=passed_reasons,
            failed_reasons=failed_reasons,
            explanation=explanation,
        )

    weights = _WEIGHTS_BY_URGENCY[urgency]
    overall_score = (
        weights["capacity"] * capacity_component.score
        + weights["distance"] * distance_component.score
        + weights["urgency"] * urgency_component.score
    )
    overall_score = round(overall_score, 4)

    explanation = (
        f"Proposed — passes all eligibility checks; score {overall_score:.2f} driven by "
        f"{capacity_component.detail}, {distance_component.detail}, and {urgency_component.detail}."
    )

    return MatchCandidateResult(
        recipient_id=recipient.id,
        status=MatchStatus.PROPOSED,
        overall_score=overall_score,
        distance_km=distance_component.distance_km,
        breakdown=breakdown,
        passed_reasons=passed_reasons,
        failed_reasons=failed_reasons,
        explanation=explanation,
    )


def rank_candidates(results: list[MatchCandidateResult]) -> list[MatchCandidateResult]:
    """
    Sort candidates for display: PROPOSED before REJECTED, highest score
    first within each group. Purely a presentation concern — does not
    mutate scores and does not decide allocation.
    """
    return sorted(
        results,
        key=lambda r: (r.status != MatchStatus.PROPOSED, -r.overall_score),
    )

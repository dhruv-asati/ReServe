"""
Location service: shared distance/duration math used across ReServe.

`haversine_km` re-exports the exact great-circle distance function
app/services/matching_engine.py already uses for provider -> recipient
proximity scoring, so "how far apart are two points" is computed exactly
one way everywhere in this codebase (matching, operations, anywhere else
that needs it later) rather than being reimplemented per caller.

`estimate_travel_duration_minutes` builds a simple, fully offline ETA on
top of that distance: distance divided by an assumed average road speed.
This is deliberately NOT a real routing engine — it ignores roads,
traffic, and turns — because ReServe does not call any external
routing/mapping API (see the module docstrings on config.py's
SUPABASE_* settings and gemini_service.py for the only two external
services this project does call). It's a reasonable order-of-magnitude
estimate for "how long until this truck gets there", not a turn-by-turn
ETA.
"""

from app.services.matching_engine import haversine_km

__all__ = ["haversine_km", "estimate_travel_duration_minutes", "compute_leg", "AVERAGE_SPEED_KMH"]

# Assumed average speed for a rescue-partner vehicle covering a mixed
# urban/suburban route, including loading/unloading and traffic — a
# deliberately conservative, offline stand-in for a real routing engine's
# ETA. Tunable in one place; every duration estimate in the app flows
# through here.
AVERAGE_SPEED_KMH = 30.0


def estimate_travel_duration_minutes(
    distance_km: float, average_speed_kmh: float = AVERAGE_SPEED_KMH
) -> float:
    """
    Estimated travel time, in minutes, for a great-circle distance at a
    constant average_speed_kmh. Pure arithmetic (distance / speed) — no
    external routing API involved, so this is an approximation, not a
    turn-by-turn ETA.
    """
    if distance_km < 0:
        raise ValueError("distance_km must not be negative")
    if average_speed_kmh <= 0:
        raise ValueError("average_speed_kmh must be positive")
    return (distance_km / average_speed_kmh) * 60.0


def compute_leg(
    origin_lat: float | None,
    origin_lng: float | None,
    dest_lat: float | None,
    dest_lng: float | None,
) -> tuple[float | None, float | None]:
    """
    (distance_km, estimated_duration_minutes) between two points, rounded
    to sane display precision. Returns (None, None) if either point's
    coordinates aren't known, rather than raising — a resource/recipient/
    hub without coordinates yet is an expected, non-error state throughout
    this codebase (see e.g. matching_engine._score_distance).
    """
    if None in (origin_lat, origin_lng, dest_lat, dest_lng):
        return None, None

    distance_km = haversine_km(origin_lat, origin_lng, dest_lat, dest_lng)
    duration_minutes = estimate_travel_duration_minutes(distance_km)
    return round(distance_km, 2), round(duration_minutes, 1)

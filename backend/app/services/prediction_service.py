"""
Prediction service: business logic for GET /api/predictions.

STRICTLY READ-ONLY. This module only runs SELECT aggregates against the
`resources` and `resource_requests` tables and hands the rows to
app/services/prediction_logic.py. It does not import, call, or modify the
matching engine, matching service, or allocation service, and it writes
nothing — so it cannot affect matching or allocation decisions.

Cancelled resources / requests are excluded: they were withdrawn, so they
represent neither surplus that existed nor demand that stood.
"""

from datetime import datetime, time, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.enums import ResourceStatus, ResourceRequestStatus
from app.models.resource import Resource
from app.models.resource_request import ResourceRequest
from app.schemas.predictions import PredictionsData
from app.services import prediction_logic


def _utc_week(column):
    """Monday (UTC) of the week `column` falls in, as a naive UTC timestamp."""
    return func.date_trunc("week", func.timezone("UTC", column))


def _as_date(value):
    return value.date() if isinstance(value, datetime) else value


def _supply_rows(db: Session, since: datetime):
    week = _utc_week(Resource.created_at)
    rows = (
        db.query(
            Resource.resource_type,
            week,
            func.count(Resource.id),
            func.coalesce(func.sum(Resource.quantity), 0),
        )
        .filter(Resource.created_at >= since, Resource.status != ResourceStatus.CANCELLED)
        .group_by(Resource.resource_type, week)
        .all()
    )
    return [(rt.value, _as_date(ws), int(count), float(qty)) for rt, ws, count, qty in rows]


def _category_rows(db: Session, since: datetime):
    # Grouped case-insensitively so "Bakery" and "bakery " count together.
    category = func.lower(func.trim(Resource.category))
    rows = (
        db.query(
            Resource.resource_type,
            category,
            Resource.food_category,
            func.count(Resource.id),
            func.coalesce(func.sum(Resource.quantity), 0),
        )
        .filter(Resource.created_at >= since, Resource.status != ResourceStatus.CANCELLED)
        .group_by(Resource.resource_type, category, Resource.food_category)
        .all()
    )
    return [
        (rt.value, cat, fc.value if fc is not None else None, int(count), float(qty))
        for rt, cat, fc, count, qty in rows
    ]


def _demand_rows(db: Session, since: datetime):
    week = _utc_week(ResourceRequest.created_at)
    rows = (
        db.query(
            ResourceRequest.resource_type,
            week,
            func.count(ResourceRequest.id),
            func.coalesce(func.sum(ResourceRequest.requested_quantity), 0),
        )
        .filter(
            ResourceRequest.created_at >= since,
            ResourceRequest.status != ResourceRequestStatus.CANCELLED,
        )
        .group_by(ResourceRequest.resource_type, week)
        .all()
    )
    return [(rt.value, _as_date(ws), int(count), float(qty)) for rt, ws, count, qty in rows]


def get_predictions(db: Session, days: int, now: datetime | None = None) -> PredictionsData:
    now = now or datetime.now(timezone.utc)
    window = prediction_logic.build_window(now.date(), days)
    since = datetime.combine(window["first_week"], time.min, tzinfo=timezone.utc)

    payload = prediction_logic.build_payload(
        now=now,
        days=days,
        supply_rows=_supply_rows(db, since),
        category_rows=_category_rows(db, since),
        demand_rows=_demand_rows(db, since),
    )
    return PredictionsData.model_validate(payload)

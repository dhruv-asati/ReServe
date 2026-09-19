"""
Analytics service: business logic for GET /api/analytics/overview.

Every number here comes from a real aggregate query against the live
tables — no caching, no sampling, no hardcoded/estimated figures.
Deliberately a single round-trip-per-metric design (six small, indexed
COUNT/SUM queries) rather than pulling every row into Python, since this
is meant to be cheap enough to call on every dashboard load.

Kept separate from the router so it's reusable without going through
HTTP, same as every other *_service module in this project.
"""

from datetime import date, datetime, timedelta, timezone

from sqlalchemy import Date, cast, func
from sqlalchemy.orm import Session

from app.models.allocation import Allocation
from app.models.enums import AllocationStatus, OperationStatus, ResourceStatus, ResourceType
from app.models.operation import RescueOperation
from app.models.rescue_request import RescueRequest
from app.models.resource import Resource
from app.schemas.analytics import (
    AnalyticsOverviewData,
    AnalyticsResourceTypeData,
    AnalyticsTrendsData,
    DailyTrendPoint,
    ResourceTypeStats,
)

# Bounds for GET /api/analytics/trends. One day is the smallest window
# that means anything; 90 keeps the response (and the group-by) small
# enough to stay a cheap dashboard call.
MIN_TREND_DAYS = 1
MAX_TREND_DAYS = 90
DEFAULT_TREND_DAYS = 14


def _count_resources(db: Session, status: ResourceStatus | None = None) -> int:
    query = db.query(func.count(Resource.id))
    if status is not None:
        query = query.filter(Resource.status == status)
    return int(query.scalar() or 0)


def _count_operations(db: Session, status: OperationStatus) -> int:
    return int(
        db.query(func.count(RescueOperation.id)).filter(RescueOperation.status == status).scalar() or 0
    )


def _total_quantity_rescued(db: Session) -> float:
    """
    Sum of allocated_quantity across every Allocation that has actually
    been DELIVERED — i.e. reached a recipient/rescue hub, not merely
    committed (PENDING/CONFIRMED) or superseded (REALLOCATED/CANCELLED).
    This is what "rescued" means here, distinct from "allocated".
    """
    total = (
        db.query(func.coalesce(func.sum(Allocation.allocated_quantity), 0))
        .filter(Allocation.status == AllocationStatus.DELIVERED)
        .scalar()
    )
    return float(total or 0)


def get_overview(db: Session) -> AnalyticsOverviewData:
    return AnalyticsOverviewData(
        total_resources=_count_resources(db),
        available_resources=_count_resources(db, ResourceStatus.AVAILABLE),
        allocated_resources=_count_resources(db, ResourceStatus.ALLOCATED),
        completed_operations=_count_operations(db, OperationStatus.COMPLETED),
        pending_operations=_count_operations(db, OperationStatus.PLANNED),
        total_quantity_rescued=_total_quantity_rescued(db),
        generated_at=datetime.now(timezone.utc),
    )


# --------------------------------------------------------------------------
# GET /api/analytics/trends — basic daily resource & operation activity
# --------------------------------------------------------------------------


def _utc_day(column):
    """
    The UTC calendar day a timestamptz column falls on.

    Bucketing is done explicitly in UTC rather than by casting the
    timestamptz straight to a date, which would silently use the database
    session's TimeZone setting — so the same row could land in a
    different bucket depending on who/where the server is configured for.
    `generated_at` and the window bounds are UTC too, so everything in
    the response agrees on what "a day" means.
    """
    return cast(func.timezone("UTC", column), Date)


def _daily_resource_rows(db: Session, start_day: date) -> dict[date, tuple[int, float]]:
    """(count, total quantity) of resources posted, keyed by UTC day."""
    day = _utc_day(Resource.created_at)
    rows = (
        db.query(day, func.count(Resource.id), func.coalesce(func.sum(Resource.quantity), 0))
        .filter(day >= start_day)
        .group_by(day)
        .all()
    )
    return {r[0]: (int(r[1]), float(r[2] or 0)) for r in rows}


def _daily_counts(db: Session, column, start_day: date) -> dict[date, int]:
    """Count of RescueOperations keyed by the UTC day of `column`.

    Rows where `column` is NULL (e.g. an operation that never reached
    COMPLETED, so has no completed_at) are excluded by the >= comparison
    rather than counted against an arbitrary day.
    """
    day = _utc_day(column)
    rows = (
        db.query(day, func.count(RescueOperation.id))
        .filter(column.isnot(None), day >= start_day)
        .group_by(day)
        .all()
    )
    return {r[0]: int(r[1]) for r in rows}


def _daily_delivered_quantity(db: Session, start_day: date) -> dict[date, float]:
    """
    Quantity that actually reached a recipient/hub, keyed by the UTC day
    its operation was marked delivered.

    Uses RescueOperation.delivered_at rather than the allocation's own
    timestamps: an Allocation has no delivered_at of its own, and its
    updated_at moves for unrelated edits, so the operation's delivery
    moment is the only honest "when did this land" signal available.
    Allocations not linked to an operation are therefore not counted here
    — they have no delivery date to bucket by — even though they would
    still count toward the overview's total_quantity_rescued.
    """
    day = _utc_day(RescueOperation.delivered_at)
    rows = (
        db.query(day, func.coalesce(func.sum(Allocation.allocated_quantity), 0))
        .join(RescueOperation, Allocation.operation_id == RescueOperation.id)
        .filter(
            Allocation.status == AllocationStatus.DELIVERED,
            RescueOperation.delivered_at.isnot(None),
            day >= start_day,
        )
        .group_by(day)
        .all()
    )
    return {r[0]: float(r[1] or 0) for r in rows}


def get_trends(db: Session, days: int = DEFAULT_TREND_DAYS) -> AnalyticsTrendsData:
    """
    Day-by-day resource and operation activity over the last `days` days,
    inclusive of today (UTC).

    Every day in the window appears in `daily`, zero-filled, so a client
    can chart the series directly without patching gaps. `days` is
    clamped to [MIN_TREND_DAYS, MAX_TREND_DAYS] rather than rejected, so
    a silly value degrades to the nearest sensible window instead of
    erroring — the router validates the same bounds, so this clamp only
    matters for non-HTTP callers.
    """
    days = max(MIN_TREND_DAYS, min(MAX_TREND_DAYS, days))

    now = datetime.now(timezone.utc)
    end_day = now.date()
    start_day = end_day - timedelta(days=days - 1)

    posted = _daily_resource_rows(db, start_day)
    started = _daily_counts(db, RescueOperation.created_at, start_day)
    completed = _daily_counts(db, RescueOperation.completed_at, start_day)
    delivered = _daily_delivered_quantity(db, start_day)

    daily: list[DailyTrendPoint] = []
    for offset in range(days):
        current = start_day + timedelta(days=offset)
        count, quantity = posted.get(current, (0, 0.0))
        daily.append(
            DailyTrendPoint(
                day=current,
                resources_posted=count,
                quantity_posted=round(quantity, 2),
                operations_started=started.get(current, 0),
                operations_completed=completed.get(current, 0),
                quantity_delivered=round(delivered.get(current, 0.0), 2),
            )
        )

    return AnalyticsTrendsData(
        window_days=days,
        start_day=start_day,
        end_day=end_day,
        total_resources_posted=sum(p.resources_posted for p in daily),
        total_quantity_posted=round(sum(p.quantity_posted for p in daily), 2),
        total_operations_started=sum(p.operations_started for p in daily),
        total_operations_completed=sum(p.operations_completed for p in daily),
        total_quantity_delivered=round(sum(p.quantity_delivered for p in daily), 2),
        daily=daily,
        generated_at=now,
    )


# --------------------------------------------------------------------------
# GET /api/analytics/resource-types — FOOD vs MEDICAL breakdown
# --------------------------------------------------------------------------


def _resource_totals_by_type(db: Session) -> dict[ResourceType, tuple[int, float]]:
    rows = (
        db.query(
            Resource.resource_type,
            func.count(Resource.id),
            func.coalesce(func.sum(Resource.quantity), 0),
        )
        .group_by(Resource.resource_type)
        .all()
    )
    return {r[0]: (int(r[1]), float(r[2] or 0)) for r in rows}


def _resource_status_counts_by_type(db: Session) -> dict[tuple[ResourceType, ResourceStatus], int]:
    rows = (
        db.query(Resource.resource_type, Resource.status, func.count(Resource.id))
        .group_by(Resource.resource_type, Resource.status)
        .all()
    )
    return {(r[0], r[1]): int(r[2]) for r in rows}


def _rescued_quantity_by_type(db: Session) -> dict[ResourceType, float]:
    """
    Same "DELIVERED allocations only" definition as
    _total_quantity_rescued, split by the resource type each allocation's
    resource was. Joined Allocation -> RescueRequest -> Resource, since an
    Allocation carries no resource_type of its own.
    """
    rows = (
        db.query(
            Resource.resource_type,
            func.coalesce(func.sum(Allocation.allocated_quantity), 0),
        )
        .join(RescueRequest, Allocation.rescue_request_id == RescueRequest.id)
        .join(Resource, RescueRequest.resource_id == Resource.id)
        .filter(Allocation.status == AllocationStatus.DELIVERED)
        .group_by(Resource.resource_type)
        .all()
    )
    return {r[0]: float(r[1] or 0) for r in rows}


def get_resource_type_stats(db: Session) -> AnalyticsResourceTypeData:
    """
    Per-resource-type statistics: how many resources of each type exist,
    how much quantity they represent, where they currently sit in their
    lifecycle, and how much of each type has actually been rescued.

    Every ResourceType is always represented, zero-filled, so a client
    rendering FOOD/MEDICAL side by side never has to handle a missing
    key — and a type with nothing posted yet reads as a real zero rather
    than as absent data.
    """
    totals = _resource_totals_by_type(db)
    status_counts = _resource_status_counts_by_type(db)
    rescued = _rescued_quantity_by_type(db)

    total_resources = sum(count for count, _ in totals.values())

    by_type: list[ResourceTypeStats] = []
    for resource_type in ResourceType:
        count, quantity = totals.get(resource_type, (0, 0.0))
        by_type.append(
            ResourceTypeStats(
                resource_type=resource_type,
                resource_count=count,
                total_quantity=round(quantity, 2),
                share_percent=round(count / total_resources * 100, 1) if total_resources else 0.0,
                available_count=status_counts.get((resource_type, ResourceStatus.AVAILABLE), 0),
                allocated_count=status_counts.get((resource_type, ResourceStatus.ALLOCATED), 0),
                delivered_count=status_counts.get((resource_type, ResourceStatus.DELIVERED), 0),
                quantity_rescued=round(rescued.get(resource_type, 0.0), 2),
            )
        )

    return AnalyticsResourceTypeData(
        total_resources=total_resources,
        by_resource_type=by_type,
        generated_at=datetime.now(timezone.utc),
    )

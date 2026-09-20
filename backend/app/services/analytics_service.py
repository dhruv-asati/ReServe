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

from datetime import date, datetime, time, timedelta, timezone

from sqlalchemy import Date, cast, func
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models.allocation import Allocation
from app.models.enums import (
    AllocationStatus,
    OperationStatus,
    ResourceRequestStatus,
    ResourceStatus,
    ResourceType,
)
from app.models.notification import Notification
from app.models.operation import RescueOperation
from app.models.rescue_partner import RescuePartner
from app.models.rescue_request import RescueRequest
from app.models.resource import Resource
from app.models.resource_request import ResourceRequest
from app.models.user import User
from app.schemas.analytics import (
    AnalyticsInsightsData,
    AnalyticsOverviewData,
    AnalyticsResourceTypeData,
    AnalyticsTrendsData,
    DailyTrendPoint,
    DeadlinePerformanceData,
    OperationCompletionData,
    ResourceTypeStats,
    SurplusAlertData,
    SurplusDay,
    SurplusForecastData,
    SurplusWindow,
    WeeklyAllocationOutcome,
    WeeklyMatchingTime,
    WeeklyOperationOutcome,
    WeeklySupplyDemand,
)
from app.services import analytics_logic, notification_service
from app.services.location_service import haversine_km

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


# --------------------------------------------------------------------------
# GET /api/analytics/insights — weekly supply/demand, allocations, matching
# time, deadline performance and operation outcomes
# --------------------------------------------------------------------------
#
# Each query below only SELECTs the handful of columns a chart needs for the
# last N weeks; the bucketing and averaging happens in
# app/services/analytics_logic.py (pure Python, unit-tested). That keeps the
# week-of-year / timezone maths out of SQL — every bucket is a UTC Monday,
# same as GET /api/predictions — and bounds the work by the window (at most
# MAX_INSIGHT_WEEKS weeks of rows).


def get_insights(
    db: Session, weeks: int = analytics_logic.DEFAULT_INSIGHT_WEEKS, now: datetime | None = None
) -> AnalyticsInsightsData:
    now = now or datetime.now(timezone.utc)
    week_starts = analytics_logic.build_week_starts(now.date(), weeks)
    since = datetime.combine(week_starts[0], time.min, tzinfo=timezone.utc)

    # Supply: resources posted. Demand: quantity recipients asked for.
    supply_rows = (
        db.query(Resource.created_at, Resource.quantity)
        .filter(Resource.created_at >= since, Resource.status != ResourceStatus.CANCELLED)
        .all()
    )
    demand_rows = (
        db.query(ResourceRequest.created_at, ResourceRequest.requested_quantity)
        .filter(
            ResourceRequest.created_at >= since,
            ResourceRequest.status != ResourceRequestStatus.CANCELLED,
        )
        .all()
    )
    supply = analytics_logic.weekly_totals(supply_rows, week_starts)
    demand = analytics_logic.weekly_totals(demand_rows, week_starts)

    # Allocation outcomes, by the week the allocation was created. PENDING /
    # CONFIRMED are still in flight and REALLOCATED was superseded by a
    # replacement, so neither counts as a success or a failure.
    allocation_rows = (
        db.query(Allocation.created_at, Allocation.status)
        .filter(
            Allocation.created_at >= since,
            Allocation.status.in_((AllocationStatus.DELIVERED, AllocationStatus.CANCELLED)),
        )
        .all()
    )
    successful = analytics_logic.weekly_counts(
        (created for created, status in allocation_rows if status == AllocationStatus.DELIVERED), week_starts
    )
    unsuccessful = analytics_logic.weekly_counts(
        (created for created, status in allocation_rows if status == AllocationStatus.CANCELLED), week_starts
    )

    # Matching time: rescue request created -> its first allocation.
    first_allocation = (
        db.query(
            Allocation.rescue_request_id.label("rescue_request_id"),
            func.min(Allocation.created_at).label("first_at"),
        )
        .group_by(Allocation.rescue_request_id)
        .subquery()
    )
    matching_rows = (
        db.query(RescueRequest.created_at, first_allocation.c.first_at)
        .select_from(RescueRequest)
        .join(first_allocation, first_allocation.c.rescue_request_id == RescueRequest.id)
        .filter(RescueRequest.created_at >= since)
        .all()
    )
    matching_weekly, matching_overall, matching_samples = analytics_logic.weekly_matching_time(
        matching_rows, week_starts
    )

    # Operation outcomes and deadline performance.
    operation_rows = [
        (created_at, status.value, delivered_at, completed_at, request_deadline, resource_expiry)
        for created_at, status, delivered_at, completed_at, request_deadline, resource_expiry in (
            db.query(
                RescueOperation.created_at,
                RescueOperation.status,
                RescueOperation.delivered_at,
                RescueOperation.completed_at,
                RescueRequest.deadline,
                Resource.expiry_time,
            )
            .select_from(RescueOperation)
            .join(RescueRequest, RescueOperation.rescue_request_id == RescueRequest.id)
            .join(Resource, RescueRequest.resource_id == Resource.id)
            .filter(RescueOperation.created_at >= since)
            .all()
        )
    ]
    operations = analytics_logic.summarize_operations(operation_rows, week_starts, now)

    return AnalyticsInsightsData(
        window_weeks=len(week_starts),
        start_week=week_starts[0],
        end_week=week_starts[-1],
        supply_vs_demand=[
            WeeklySupplyDemand(week_start=w, supply=supply[i], demand=demand[i])
            for i, w in enumerate(week_starts)
        ],
        allocations=[
            WeeklyAllocationOutcome(week_start=w, successful=successful[i], unsuccessful=unsuccessful[i])
            for i, w in enumerate(week_starts)
        ],
        matching_time=[WeeklyMatchingTime(**point) for point in matching_weekly],
        avg_matching_minutes=matching_overall,
        matching_samples=matching_samples,
        deadline_performance=DeadlinePerformanceData(**operations["deadline"]),
        operation_completion=OperationCompletionData(**operations["completion"]),
        operation_outcomes=[WeeklyOperationOutcome(**point) for point in operations["weekly"]],
        generated_at=now,
    )


# --------------------------------------------------------------------------
# GET /api/analytics/surplus-forecast and POST /api/analytics/surplus-alert
# --------------------------------------------------------------------------

# How far a rescue partner with no service radius of their own is assumed
# willing to travel when deciding who is "nearby" the sender.
DEFAULT_ALERT_RADIUS_KM = 25.0
# A partner alerted within this long ago is not alerted again.
ALERT_COOLDOWN = timedelta(hours=1)


def _surplus_rows(db: Session, now: datetime, days: int) -> list[tuple[datetime, float, str | None]]:
    """
    (ready_at, quantity, unit) for every FOOD resource that became available
    in the last `days` days. "Ready" is available_time when the provider set
    one, else the moment the resource was posted. Cancelled resources are
    excluded — they were withdrawn, so they were never surplus that
    existed. Resources scheduled for the future are history-in-waiting and
    are left out.
    """
    ready_at = func.coalesce(Resource.available_time, Resource.created_at)
    # One extra day of padding so every timezone still sees its whole first day.
    since = now - timedelta(days=days + 1)
    rows = (
        db.query(ready_at, Resource.quantity, Resource.unit)
        .filter(
            Resource.resource_type == ResourceType.FOOD,
            Resource.status != ResourceStatus.CANCELLED,
            ready_at >= since,
            ready_at <= now,
        )
        .all()
    )
    return [(r[0], float(r[1] or 0), r[2]) for r in rows]


def get_surplus_forecast(
    db: Session,
    tz_offset_minutes: int = 0,
    days: int = analytics_logic.FORECAST_WINDOW_DAYS,
    now: datetime | None = None,
) -> SurplusForecastData:
    """
    Recent daily surplus plus, when the history supports one, the hour of the
    day surplus food most reliably shows up in. No demo fallback: with too
    little history `prediction` is None and the UI says so.
    """
    now = now or datetime.now(timezone.utc)
    rows = _surplus_rows(db, now, days)

    history = analytics_logic.surplus_history(rows, now, tz_offset_minutes)
    prediction = analytics_logic.predict_surplus_window(rows, now, tz_offset_minutes, window_days=days)

    return SurplusForecastData(
        unit=analytics_logic.history_unit(rows, now, tz_offset_minutes),
        history=[SurplusDay(**day) for day in history],
        prediction=SurplusWindow(**prediction) if prediction else None,
        min_days_required=analytics_logic.MIN_DAYS_FOR_FORECAST,
        window_days=days,
        generated_at=now,
    )


def _within_reach(sender: User, partner: RescuePartner, partner_user: User) -> bool:
    """True when the partner has a known location inside their own service radius of the sender."""
    latitude = partner.latitude if partner.latitude is not None else partner_user.latitude
    longitude = partner.longitude if partner.longitude is not None else partner_user.longitude
    if latitude is None or longitude is None:
        return False
    radius = partner.service_radius_km or DEFAULT_ALERT_RADIUS_KM
    return haversine_km(sender.latitude, sender.longitude, latitude, longitude) <= radius


def send_surplus_alert(
    db: Session, sender: User, tz_offset_minutes: int = 0, now: datetime | None = None
) -> SurplusAlertData:
    """
    Really notify rescue partners about the predicted surplus window.

    The forecast is recomputed here — the client only says what timezone it
    is in — so nobody can broadcast an invented forecast. Recipients are the
    real, active, currently-available, food-accepting rescue partners (never
    the sender). When the sender has a saved location only partners inside
    their own service radius of it are alerted ("nearby"); a sender with no
    saved location falls back to every available partner. Anyone alerted in
    the last hour is skipped so the button can't spam. With no partners the
    result is simply zero — nothing is faked.
    """
    now = now or datetime.now(timezone.utc)
    forecast = get_surplus_forecast(db, tz_offset_minutes, now=now)
    window = forecast.prediction
    if window is None:
        raise AppError(
            status_code=409,
            code="NO_SURPLUS_FORECAST",
            message="There isn't enough recorded surplus history to predict a window yet, "
            "so no partners were notified.",
        )

    pairs = (
        db.query(RescuePartner, User)
        .join(User, User.id == RescuePartner.user_id)
        .filter(
            User.is_active.is_(True),
            RescuePartner.is_available.is_(True),
            RescuePartner.accepts_food.is_(True),
            RescuePartner.user_id != sender.id,
        )
        .all()
    )

    sender_has_location = sender.latitude is not None and sender.longitude is not None
    if sender_has_location:
        scope = "nearby"
        pairs = [(partner, user) for partner, user in pairs if _within_reach(sender, partner, user)]
    else:
        scope = "all_available"

    eligible_ids = [partner.user_id for partner, _user in pairs]
    already: set = set()
    if eligible_ids:
        already = {
            user_id
            for (user_id,) in db.query(Notification.user_id).filter(
                Notification.title == notification_service.SURPLUS_ALERT_TITLE,
                Notification.created_at >= now - ALERT_COOLDOWN,
                Notification.user_id.in_(eligible_ids),
            )
        }

    label = f"{analytics_logic.format_hour(window.start_hour)} – {analytics_logic.format_hour(window.end_hour)}"
    amount = (
        f"about {window.high:g}"
        if window.low == window.high
        else f"roughly {window.low:g}–{window.high:g}"
    )
    message = (
        f"{sender.organization_name or sender.full_name} expects {amount} {window.unit} of surplus "
        f"food around {label}, based on recent activity. Be ready for pickups."
    )

    notified = 0
    for user_id in eligible_ids:
        if user_id in already:
            continue
        notification_service.notify_surplus_alert(db, partner_user_id=user_id, message=message)
        notified += 1
    if notified:
        db.commit()

    return SurplusAlertData(
        partners_notified=notified,
        already_notified=len(already),
        eligible_partners=len(eligible_ids),
        scope=scope,
        window_label=label,
    )

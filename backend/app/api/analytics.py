"""
Analytics endpoints:

    GET  /api/analytics/overview
    GET  /api/analytics/trends
    GET  /api/analytics/resource-types
    GET  /api/analytics/insights
    GET  /api/analytics/surplus-forecast
    POST /api/analytics/surplus-alert

Platform-wide aggregates computed fresh from the database on every call:
a current-state snapshot, basic day-by-day activity trends, and a
per-resource-type breakdown. All three are read-only and open to any
authenticated user, same as viewing resources or operations — none of
them can influence matching, allocation, or any resource's status.

Every figure comes from a real aggregate query. Unlike GET
/api/predictions, these endpoints never substitute demo data: an empty
database honestly returns zeros.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, require_roles
from app.db.database import get_db
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.analytics import (
    AnalyticsInsightsData,
    AnalyticsOverviewData,
    AnalyticsResourceTypeData,
    AnalyticsTrendsData,
    SurplusAlertData,
    SurplusAlertRequest,
    SurplusForecastData,
)
from app.schemas.common import SuccessResponse
from app.services import analytics_logic, analytics_service

router = APIRouter(prefix="/api/analytics", tags=["Analytics"])


@router.get(
    "/overview",
    response_model=SuccessResponse[AnalyticsOverviewData],
    summary="Platform overview analytics",
    description=(
        "Returns a snapshot of the platform's current state, computed fresh from the database: "
        "total resources posted, resources currently AVAILABLE / ALLOCATED, RescueOperations "
        "currently COMPLETED / PLANNED (pending), and the total quantity that has actually been "
        "rescued — the sum of allocated_quantity across every DELIVERED allocation, i.e. quantity "
        "that reached a recipient or rescue hub, not merely committed. Available to any "
        "authenticated user."
    ),
)
def get_overview(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    data = analytics_service.get_overview(db)
    return SuccessResponse(
        data=data,
        message=f"{data.total_resources} resource(s) tracked; {data.total_quantity_rescued:g} unit(s) rescued so far.",
    )


@router.get(
    "/trends",
    response_model=SuccessResponse[AnalyticsTrendsData],
    summary="Daily resource and operation trends",
    description=(
        "Day-by-day platform activity over the last `days` days (default 14, max 90), inclusive "
        "of today in UTC. Each day reports resources posted and their total quantity, rescue "
        "operations started and completed, and the quantity actually delivered that day. Every "
        "day in the window is present even when nothing happened, so the series can be charted "
        "directly without filling gaps. Days are bucketed in UTC regardless of the database "
        "server's timezone. Available to any authenticated user."
    ),
)
def get_trends(
    days: int = Query(
        default=analytics_service.DEFAULT_TREND_DAYS,
        ge=analytics_service.MIN_TREND_DAYS,
        le=analytics_service.MAX_TREND_DAYS,
        description="Number of days to cover, counting back from today (UTC) inclusive.",
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    data = analytics_service.get_trends(db, days=days)
    return SuccessResponse(
        data=data,
        message=(
            f"{data.window_days} day(s) from {data.start_day.isoformat()} to "
            f"{data.end_day.isoformat()}: {data.total_resources_posted} resource(s) posted, "
            f"{data.total_operations_completed} operation(s) completed."
        ),
    )


@router.get(
    "/resource-types",
    response_model=SuccessResponse[AnalyticsResourceTypeData],
    summary="Per-resource-type statistics",
    description=(
        "Breakdown of every resource type (FOOD, MEDICAL): how many resources of each type have "
        "been posted and their total quantity, each type's share of all resources by count, how "
        "many currently sit in AVAILABLE / ALLOCATED / DELIVERED status, and how much quantity of "
        "that type has actually been rescued (summed across DELIVERED allocations, the same "
        "definition the overview endpoint uses). Every type is always listed, zero-filled when "
        "nothing of that type exists yet. Available to any authenticated user."
    ),
)
def get_resource_type_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    data = analytics_service.get_resource_type_stats(db)
    breakdown = ", ".join(
        f"{stats.resource_type.value}: {stats.resource_count}" for stats in data.by_resource_type
    )
    return SuccessResponse(
        data=data,
        message=f"{data.total_resources} resource(s) across {len(data.by_resource_type)} type(s) ({breakdown}).",
    )


@router.get(
    "/insights",
    response_model=SuccessResponse[AnalyticsInsightsData],
    summary="Weekly supply/demand, allocation, matching-time and operation-outcome analytics",
    description=(
        "Everything the Analytics page's outcome charts need, over the last `weeks` weeks "
        "(default 4, max 12, ending with the current week; weeks start on Monday, UTC): supply "
        "vs. demand quantity, delivered vs. cancelled allocations, average matching time "
        "(rescue request created -> first allocation), how many operations arrived before vs. "
        "after their deadline, how operations resolved, and completed vs. at-risk operations per "
        "week. Computed from real rows only — an empty platform returns zeros and nulls, never "
        "demo data. Available to any authenticated user."
    ),
)
def get_insights(
    weeks: int = Query(
        default=analytics_logic.DEFAULT_INSIGHT_WEEKS,
        ge=analytics_logic.MIN_INSIGHT_WEEKS,
        le=analytics_logic.MAX_INSIGHT_WEEKS,
        description="Number of weeks to cover, ending with the current week.",
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    data = analytics_service.get_insights(db, weeks=weeks)
    return SuccessResponse(
        data=data,
        message=f"Insights for {data.window_weeks} week(s) from {data.start_week.isoformat()}.",
    )


@router.get(
    "/surplus-forecast",
    response_model=SuccessResponse[SurplusForecastData],
    summary="Recent surplus food and the hour it usually appears in",
    description=(
        "The last 7 days of FOOD surplus (by the time it became available) and, when there is "
        "enough recorded history, the local hour of day in which surplus most reliably shows up "
        "with the range it has ranged over. Pass the browser's UTC offset as `tz_offset_minutes` "
        "so hours and days are in the viewer's local time. `prediction` is null when fewer than "
        "`min_days_required` days of history support any hour — there is no demo fallback. "
        "Available to any authenticated user."
    ),
)
def get_surplus_forecast(
    tz_offset_minutes: int = Query(
        default=0, ge=-840, le=840, description="Caller's UTC offset in minutes, e.g. 330 for India."
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    data = analytics_service.get_surplus_forecast(db, tz_offset_minutes=tz_offset_minutes)
    message = (
        "Surplus forecast ready."
        if data.prediction
        else "Not enough recorded surplus history to predict a window yet."
    )
    return SuccessResponse(data=data, message=message)


@router.post(
    "/surplus-alert",
    response_model=SuccessResponse[SurplusAlertData],
    summary="Notify rescue partners about the predicted surplus window",
    description=(
        "Creates a real in-app notification (plus an email when SMTP is configured) for the "
        "active, available, food-accepting rescue partners — never the caller. When the caller "
        "has a saved location only partners within their own service radius of it are alerted; "
        "otherwise every available partner is. Partners already alerted in the last hour are "
        "skipped. The forecast is recomputed server-side; 409 `NO_SURPLUS_FORECAST` when there "
        "isn't enough history to predict a window. `partners_notified` can legitimately be 0. "
        "Requires the PROVIDER, RESCUE_PARTNER or ADMIN role."
    ),
)
def send_surplus_alert(
    payload: SurplusAlertRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.PROVIDER, UserRole.RESCUE_PARTNER, UserRole.ADMIN)),
):
    data = analytics_service.send_surplus_alert(db, current_user, tz_offset_minutes=payload.tz_offset_minutes)
    return SuccessResponse(
        data=data,
        message=f"{data.partners_notified} rescue partner(s) notified ({data.eligible_partners} eligible).",
    )

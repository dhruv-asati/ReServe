"""
Analytics endpoints:

    GET /api/analytics/overview
    GET /api/analytics/trends
    GET /api/analytics/resource-types

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

from app.core.deps import get_current_user
from app.db.database import get_db
from app.models.user import User
from app.schemas.analytics import AnalyticsOverviewData, AnalyticsResourceTypeData, AnalyticsTrendsData
from app.schemas.common import SuccessResponse
from app.services import analytics_service

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

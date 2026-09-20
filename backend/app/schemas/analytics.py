"""
Pydantic schemas for:

    GET  /api/analytics/overview
    GET  /api/analytics/trends
    GET  /api/analytics/resource-types
    GET  /api/analytics/insights
    GET  /api/analytics/surplus-forecast
    POST /api/analytics/surplus-alert

All three are cheap-to-compute snapshots of the platform's current state,
built entirely from real aggregate queries against the live database
(see app/services/analytics_service.py) — no caching, no estimates, and
no demo/placeholder fallback. An empty database produces zeros, not
illustrative figures. (That is the deliberate difference from
GET /api/predictions, which substitutes clearly-labelled demo data when
there isn't enough recorded activity to forecast from.)
"""

from datetime import date, datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field

from app.models.enums import ResourceType


class AnalyticsOverviewData(BaseModel):
    total_resources: int = Field(description="Every Resource ever posted, regardless of status.")
    available_resources: int = Field(description="Resources currently in AVAILABLE status.")
    allocated_resources: int = Field(description="Resources currently in ALLOCATED status.")

    completed_operations: int = Field(description="RescueOperations currently in COMPLETED status.")
    pending_operations: int = Field(description="RescueOperations currently in PLANNED status (queued, not yet moving).")

    total_quantity_rescued: float = Field(
        description="Sum of allocated_quantity across every Allocation with status DELIVERED — "
        "i.e. quantity that has actually reached a recipient or rescue hub, not just committed."
    )

    generated_at: datetime = Field(description="When this snapshot was computed (server time, UTC).")


class DailyTrendPoint(BaseModel):
    """
    One calendar day (UTC) of platform activity. Every day in the
    requested window is present, including days with no activity at all —
    a client charting this doesn't have to fill gaps itself.
    """

    day: date = Field(description="The calendar day (UTC) these figures cover.")

    resources_posted: int = Field(description="Resources created on this day (by Resource.created_at).")
    quantity_posted: float = Field(
        description="Sum of `quantity` across the resources created on this day. Quantities are "
        "summed as recorded, so mixed units (e.g. meals and kg) are added together."
    )

    operations_started: int = Field(
        description="RescueOperations created on this day (by RescueOperation.created_at)."
    )
    operations_completed: int = Field(
        description="RescueOperations that reached COMPLETED on this day (by completed_at)."
    )
    quantity_delivered: float = Field(
        description="Sum of allocated_quantity across DELIVERED allocations whose operation was "
        "marked delivered on this day (by RescueOperation.delivered_at)."
    )


class AnalyticsTrendsData(BaseModel):
    window_days: int = Field(description="Number of days covered, inclusive of today.")
    start_day: date = Field(description="First day in the window (UTC).")
    end_day: date = Field(description="Last day in the window — today, in UTC.")

    total_resources_posted: int = Field(description="Total resources posted across the whole window.")
    total_quantity_posted: float = Field(description="Total quantity posted across the whole window.")
    total_operations_started: int = Field(description="Total operations started across the whole window.")
    total_operations_completed: int = Field(description="Total operations completed across the whole window.")
    total_quantity_delivered: float = Field(description="Total quantity delivered across the whole window.")

    daily: list[DailyTrendPoint] = Field(
        description="One entry per day, oldest first. Always exactly `window_days` entries."
    )

    generated_at: datetime = Field(description="When this snapshot was computed (server time, UTC).")


class ResourceTypeStats(BaseModel):
    """Per-resource-type totals. Every ResourceType is always present, even
    with no resources of that type recorded yet (all zeros)."""

    resource_type: ResourceType

    resource_count: int = Field(description="Every Resource of this type, regardless of status.")
    total_quantity: float = Field(
        description="Sum of `quantity` across every Resource of this type. Summed as recorded, so "
        "mixed units are added together."
    )
    share_percent: float = Field(
        description="This type's share of all resources posted, by count (0.0 when nothing is posted)."
    )

    available_count: int = Field(description="Resources of this type currently in AVAILABLE status.")
    allocated_count: int = Field(description="Resources of this type currently in ALLOCATED status.")
    delivered_count: int = Field(description="Resources of this type currently in DELIVERED status.")

    quantity_rescued: float = Field(
        description="Sum of allocated_quantity across DELIVERED allocations for resources of this "
        "type — the same 'actually reached a recipient or hub' definition used by "
        "total_quantity_rescued on the overview endpoint."
    )


class AnalyticsResourceTypeData(BaseModel):
    total_resources: int = Field(description="Every Resource posted, across all types.")
    by_resource_type: list[ResourceTypeStats] = Field(
        description="One entry per ResourceType, ordered as the enum declares them."
    )
    generated_at: datetime = Field(description="When this snapshot was computed (server time, UTC).")


# --------------------------------------------------------------------------
# GET /api/analytics/insights — the Analytics page's weekly / outcome charts
# --------------------------------------------------------------------------


class WeeklySupplyDemand(BaseModel):
    week_start: date = Field(description="Monday (UTC) of the week.")
    supply: float = Field(description="Quantity of resources posted that week (cancelled ones excluded).")
    demand: float = Field(description="Quantity requested by recipients that week (cancelled ones excluded).")


class WeeklyAllocationOutcome(BaseModel):
    week_start: date
    successful: int = Field(description="Allocations created that week that have been DELIVERED.")
    unsuccessful: int = Field(description="Allocations created that week that were CANCELLED.")


class WeeklyMatchingTime(BaseModel):
    week_start: date
    avg_minutes: Optional[float] = Field(
        description="Average minutes from a rescue request being created to its first allocation. "
        "null when nothing was matched that week."
    )
    samples: int = Field(description="Rescue requests that contributed to the average.")


class DeadlinePerformanceData(BaseModel):
    on_time: int = Field(description="Operations that arrived at or before their deadline.")
    late: int = Field(description="Operations that arrived after their deadline.")
    no_deadline: int = Field(description="Arrived operations with no deadline recorded — not counted as either.")


class OperationCompletionData(BaseModel):
    completed: int = Field(description="Operations in DELIVERED or COMPLETED status.")
    in_progress: int = Field(description="Operations in PLANNED or IN_TRANSIT status.")
    failed: int = Field(description="Operations in FAILED status.")


class WeeklyOperationOutcome(BaseModel):
    week_start: date = Field(description="Monday (UTC) of the week the operations were created.")
    completed: int = Field(description="Arrived, and not after their deadline.")
    at_risk: int = Field(description="Failed, arrived after their deadline, or still open past their deadline.")


class AnalyticsInsightsData(BaseModel):
    """
    Every figure is computed from real rows. An empty platform yields zeros,
    nulls and all-zero series — never illustrative numbers. Quantities are
    summed as recorded (mixed units are not converted).
    """

    window_weeks: int
    start_week: date = Field(description="Monday (UTC) of the first week in the window.")
    end_week: date = Field(description="Monday (UTC) of the current, still in-progress week.")

    supply_vs_demand: list[WeeklySupplyDemand]
    allocations: list[WeeklyAllocationOutcome]
    matching_time: list[WeeklyMatchingTime]
    avg_matching_minutes: Optional[float] = Field(
        description="Average matching time over the whole window; null when nothing was matched."
    )
    matching_samples: int
    deadline_performance: DeadlinePerformanceData
    operation_completion: OperationCompletionData
    operation_outcomes: list[WeeklyOperationOutcome]

    generated_at: datetime


# --------------------------------------------------------------------------
# Predictive surplus
# --------------------------------------------------------------------------


class SurplusDay(BaseModel):
    label: str = Field(description="Short weekday name in the caller's timezone, e.g. 'Mon'.")
    day: date = Field(description="The calendar day (caller's timezone).")
    quantity: float = Field(description="Food surplus that became available that day.")


class SurplusWindow(BaseModel):
    start_hour: int = Field(ge=0, le=23, description="Start of the predicted hour (caller's local time, 0-23).")
    end_hour: int = Field(ge=0, le=23, description="End of the predicted hour (caller's local time, 0-23).")
    low: float = Field(description="Smallest per-day surplus seen in this hour.")
    high: float = Field(description="Largest per-day surplus seen in this hour.")
    unit: str
    days_with_surplus: int = Field(description="How many days in the window had surplus in this hour.")
    window_days: int = Field(description="How many days of history were examined.")


class SurplusForecastData(BaseModel):
    unit: str = Field(description="Unit of the history figures ('units' when the recorded units are mixed).")
    history: list[SurplusDay] = Field(description="Last 7 days, oldest first, zero-filled.")
    prediction: Optional[SurplusWindow] = Field(
        description="null when there is not enough recorded history to predict from."
    )
    min_days_required: int
    window_days: int
    generated_at: datetime


class SurplusAlertRequest(BaseModel):
    tz_offset_minutes: int = Field(
        default=0,
        ge=-840,
        le=840,
        description="Caller's UTC offset in minutes (e.g. 330 for India), so the forecast hour is local.",
    )


class SurplusAlertData(BaseModel):
    partners_notified: int = Field(description="Rescue partners who received a new in-app notification.")
    already_notified: int = Field(description="Eligible partners skipped because they were alerted in the last hour.")
    eligible_partners: int = Field(description="Available, active, food-accepting partners considered.")
    scope: Literal["nearby", "all_available"] = Field(
        description="'nearby' when partners were filtered by distance from the sender's saved location; "
        "'all_available' when the sender has no saved location."
    )
    window_label: str = Field(description="The predicted window as sent, e.g. '10 PM – 11 PM'.")

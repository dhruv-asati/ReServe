"""
Pydantic schemas for:

    GET /api/analytics/overview
    GET /api/analytics/trends
    GET /api/analytics/resource-types

All three are cheap-to-compute snapshots of the platform's current state,
built entirely from real aggregate queries against the live database
(see app/services/analytics_service.py) — no caching, no estimates, and
no demo/placeholder fallback. An empty database produces zeros, not
illustrative figures. (That is the deliberate difference from
GET /api/predictions, which substitutes clearly-labelled demo data when
there isn't enough recorded activity to forecast from.)
"""

from datetime import date, datetime

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

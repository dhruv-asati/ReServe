"""
Pydantic schemas for:

    GET /api/predictions

Every response says explicitly whether it is built from real database
rows (`data_source: "DATABASE"`) or is a fixed placeholder
(`data_source: "DEMO"`, `is_demo: true`) — see app/services/prediction_logic.py.
"""

from datetime import date, datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, Field

from app.models.enums import ResourceType

TrendLabel = Literal["INCREASING", "DECREASING", "STABLE", "INSUFFICIENT_DATA"]


class DataSufficiency(BaseModel):
    is_sufficient: bool = Field(description="True when there was enough recorded activity for a real (non-demo) response.")
    resources_found: int = Field(description="Resources recorded in the window (excluding CANCELLED).")
    resources_required: int
    requests_found: int = Field(description="Resource requests recorded in the window (excluding CANCELLED).")
    requests_required: int


class ResourceTypeTotal(BaseModel):
    resource_type: ResourceType
    resource_count: int
    total_quantity: float


class SupplyPeriod(BaseModel):
    period_start: date = Field(description="Monday (UTC) of the week.")
    is_partial: bool = Field(description="True for the current, still-in-progress week.")
    resource_count: int
    total_quantity: float


class HistoricalTotals(BaseModel):
    total_resources: int
    total_quantity: float = Field(description="Summed as recorded; units (meals, kg, ...) are not converted.")
    by_resource_type: List[ResourceTypeTotal]
    weekly: List[SupplyPeriod]


class CategoryCount(BaseModel):
    category: str
    resource_type: ResourceType
    resource_count: int
    total_quantity: float
    share_percent: float = Field(description="Share of all resources in the window, across every category.")


class DemandPeriod(BaseModel):
    period_start: date
    is_partial: bool
    request_count: int
    requested_quantity: float


class DemandTrend(BaseModel):
    resource_type: ResourceType
    request_count: int
    requested_quantity: float
    earlier_period_quantity: float = Field(description="Requested quantity in the earlier half of the complete weeks.")
    recent_period_quantity: float = Field(description="Requested quantity in the later half of the complete weeks.")
    change_percent: Optional[float] = Field(
        default=None, description="Recent vs earlier, in percent; null when it cannot be expressed as a percentage."
    )
    trend: TrendLabel


class DemandTrends(BaseModel):
    total_requests: int
    total_requested_quantity: float
    by_resource_type: List[DemandTrend]
    weekly: List[DemandPeriod]


class PredictionsData(BaseModel):
    is_demo: bool = Field(description="True when this is a placeholder response, not derived from the database.")
    data_source: Literal["DATABASE", "DEMO"]
    notice: str = Field(description="Plain-language description of what the figures are and how they were derived.")
    window_days: int
    window_start: date
    generated_at: datetime
    data_sufficiency: DataSufficiency
    historical_totals: HistoricalTotals
    top_categories: List[CategoryCount]
    demand_trends: DemandTrends

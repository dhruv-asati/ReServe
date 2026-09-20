"""
Response schemas for the dashboard-facing endpoints:

    GET /api/dashboard/overview
    GET /api/operations/active
    GET /api/resources/at-risk
    GET /api/activity/recent
    GET /api/network/locations
    GET /api/network/organizations

Unlike the rest of the API these use camelCase field names on purpose: the
React dashboard (frontend/src/data/*.js) was built against this exact
shape, and several values (quantity, deadline, time, delta) are
pre-formatted display strings rather than raw numbers, so the dashboard
can render them as-is. Raw/typed data stays available from the regular
snake_case endpoints (/api/resources, /api/operations, /api/analytics).
"""

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel

Tone = Literal["brand", "active", "urgent", "success"]


class StatValue(BaseModel):
    value: int | float
    unit: Optional[str] = None
    delta: str
    tone: Tone


class DashboardOverviewData(BaseModel):
    resourcesRescued: StatValue
    activeRescues: StatValue
    atRiskResources: StatValue
    successfulAllocations: StatValue


class ActiveOperationOut(BaseModel):
    id: str
    resource: str
    resourceType: str  # "food" | "medical"
    quantity: str
    provider: str
    recipient: str
    status: str  # a value from the frontend's STATUS vocabulary (utils/theme.js)
    eta: str


class AtRiskResourceOut(BaseModel):
    id: str
    resource: str
    resourceType: str  # "food" | "medical"
    quantity: str
    deadline: str
    urgency: str  # "critical" | "high" | "medium" | "low"
    status: str


class ActivityEventOut(BaseModel):
    id: str
    stage: str  # a key of ACTIVITY_STAGE_ICONS (utils/icons.js)
    status: str
    title: str
    description: str
    time: str
    timestamp: datetime  # machine-readable twin of `time`


class NetworkLocationOut(BaseModel):
    id: str
    role: Literal["provider", "recipient", "partner", "hub"]
    name: str
    lat: float
    lng: float


# --- Network Directory (GET /api/network/organizations) ----------------------
# Shape consumed by the React Network page (frontend/src/data/networkDirectory.js).


class LatLngOut(BaseModel):
    lat: float
    lng: float


class OrgCapacityOut(BaseModel):
    value: float
    unit: str
    label: str


class OrgWorkloadOut(BaseModel):
    active: int
    max: int
    label: str


class NetworkOrganizationOut(BaseModel):
    id: str
    name: str
    type: Literal["ngo", "shelter", "partner", "hub"]
    area: str
    city: str
    position: LatLngOut
    description: str
    resourceTypes: list[Literal["food", "medical"]]
    capacity: Optional[OrgCapacityOut] = None
    availability: Literal["available", "limited", "unavailable"]
    workload: Optional[OrgWorkloadOut] = None
    verification: Optional[Literal["verified", "pending", "unlisted"]] = None

"""
Dashboard endpoints (read-only, any authenticated user):

    GET /api/dashboard/overview   Headline stat cards
    GET /api/activity/recent      Recent rescue activity timeline
    GET /api/network/locations    Map markers for providers/recipients/partners/hubs
    GET /api/network/organizations  Network Directory: NGOs, shelters, partners, hubs

The other two dashboard feeds live next to the resources they describe —
GET /api/resources/at-risk in app/api/resources.py and
GET /api/operations/active in app/api/operations.py — so route order
relative to `/{resource_id}` / `/{operation_id}/...` is visible in one file.
Response shapes are camelCase display-oriented payloads; see
app/schemas/dashboard.py.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.database import get_db
from app.models.user import User
from app.schemas.common import SuccessResponse
from app.schemas.dashboard import ActivityEventOut, DashboardOverviewData, NetworkLocationOut, NetworkOrganizationOut
from app.services import dashboard_service

router = APIRouter(tags=["Dashboard"])


@router.get(
    "/api/dashboard/overview",
    response_model=SuccessResponse[DashboardOverviewData],
    summary="Dashboard headline stats",
    description="Rescued quantity, active rescues, at-risk resources and allocation success rate, "
    "each with a short display delta. Computed fresh from the database.",
)
def get_dashboard_overview(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return SuccessResponse(data=dashboard_service.get_overview(db), message="Dashboard overview.")


@router.get(
    "/api/activity/recent",
    response_model=SuccessResponse[list[ActivityEventOut]],
    summary="Recent rescue activity",
    description="Newest-first feed combining operation events (created, pickup, delivered, reallocated...) "
    "and newly posted resources.",
)
def get_recent_activity(
    limit: int = Query(default=10, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    items = dashboard_service.get_recent_activity(db, limit=limit)
    return SuccessResponse(data=items, message=f"{len(items)} recent event(s).")


@router.get(
    "/api/network/locations",
    response_model=SuccessResponse[list[NetworkLocationOut]],
    summary="Network map locations",
    description="Active providers, recipients, rescue partners and hubs that have coordinates.",
)
def get_network_locations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    items = dashboard_service.get_network_locations(db)
    return SuccessResponse(data=items, message=f"{len(items)} location(s).")


@router.get(
    "/api/network/organizations",
    response_model=SuccessResponse[list[NetworkOrganizationOut]],
    summary="Network directory",
    description="Recipients (NGOs/shelters), rescue partners and rescue hubs that have coordinates, "
    "in the shape the Network Directory page renders.",
)
def get_network_organizations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    items = dashboard_service.get_network_organizations(db)
    return SuccessResponse(data=items, message=f"{len(items)} organization(s).")

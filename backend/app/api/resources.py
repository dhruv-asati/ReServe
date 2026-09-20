"""
Resource endpoints:

    POST   /api/resources
    GET    /api/resources
    GET    /api/resources/at-risk        (declared before /{resource_id} so it isn't captured by it)
    GET    /api/resources/{resource_id}
    PUT    /api/resources/{resource_id}
    DELETE /api/resources/{resource_id}
    POST   /api/resources/{resource_id}/analyze

All endpoints require authentication. Creating a resource is restricted to
PROVIDER and ADMIN roles. Editing/deleting/analyzing is restricted to the
resource's own provider (or an ADMIN) — enforced in the service layer so
the same check applies consistently across all three.
"""

import logging
import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, require_roles
from app.db.database import get_db
from app.models.enums import ResourceStatus, ResourceType, UserRole
from app.models.user import User
from app.schemas.common import SuccessResponse
from app.schemas.resource import ResourceCreate, ResourceListData, ResourceOut, ResourceUpdate
from app.schemas.dashboard import AtRiskResourceOut
from app.services import dashboard_service, resource_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/resources", tags=["Resources"])


@router.post(
    "",
    response_model=SuccessResponse[ResourceOut],
    status_code=status.HTTP_201_CREATED,
    summary="Create a resource",
    description="Posts a new surplus resource (FOOD or MEDICAL). Only PROVIDER and ADMIN "
    "accounts may create resources. MEDICAL resources are automatically flagged as requiring "
    "verification regardless of what's submitted.",
)
def create_resource(
    payload: ResourceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.PROVIDER, UserRole.ADMIN)),
):
    resource = resource_service.create_resource(db, payload, current_user)
    return SuccessResponse(data=ResourceOut.model_validate(resource), message="Resource created successfully.")


@router.get(
    "",
    response_model=SuccessResponse[ResourceListData],
    summary="List resources",
    description="Returns resources, newest first, optionally filtered by type, status, or "
    "provider, and/or searched by title or description. Available to any authenticated user.",
)
def list_resources(
    resource_type: ResourceType | None = Query(default=None, description="Filter by resource type."),
    status_filter: ResourceStatus | None = Query(default=None, alias="status", description="Filter by status."),
    provider_id: uuid.UUID | None = Query(default=None),
    mine: bool = Query(default=False, description="If true, overrides provider_id with the current user's id."),
    search: str | None = Query(
        default=None,
        min_length=1,
        max_length=255,
        description="Case-insensitive substring search across title and description.",
    ),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    effective_provider_id = current_user.id if mine else provider_id

    items, total = resource_service.list_resources(
        db,
        resource_type=resource_type,
        status_filter=status_filter,
        provider_id=effective_provider_id,
        search=search,
        skip=skip,
        limit=limit,
    )
    data = ResourceListData(
        items=[ResourceOut.model_validate(item) for item in items],
        total=total,
        skip=skip,
        limit=limit,
    )
    return SuccessResponse(data=data, message=f"Found {total} resource(s).")


# NOTE: must stay above GET "/{resource_id}". FastAPI matches routes in
# declaration order, so a later "/at-risk" would be captured by
# "/{resource_id}" and rejected with 422 ("at-risk" is not a UUID).
@router.get(
    "/at-risk",
    response_model=SuccessResponse[list[AtRiskResourceOut]],
    summary="Resources approaching their rescue deadline",
    description="Unrescued (AVAILABLE/MATCHING) resources whose expiry_time falls within the next "
    "few hours, soonest first. Feeds the dashboard's At-Risk card. Available to any authenticated user.",
)
def list_at_risk_resources(
    limit: int = Query(default=10, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    items = dashboard_service.get_at_risk_resources(db, limit=limit)
    return SuccessResponse(data=items, message=f"{len(items)} at-risk resource(s).")


@router.get(
    "/{resource_id}",
    response_model=SuccessResponse[ResourceOut],
    summary="Get a resource by id",
)
def get_resource(
    resource_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    resource = resource_service.get_resource_or_404(db, resource_id)
    return SuccessResponse(data=ResourceOut.model_validate(resource), message="Resource retrieved successfully.")


@router.put(
    "/{resource_id}",
    response_model=SuccessResponse[ResourceOut],
    summary="Update a resource",
    description="Only the resource's own provider or an ADMIN may edit it. `status` may only "
    "be set to AVAILABLE or CANCELLED here — every other status is set automatically by the "
    "matching/operations engine. Locked once a resource is ALLOCATED, IN_TRANSIT, or DELIVERED.",
)
def update_resource(
    resource_id: uuid.UUID,
    payload: ResourceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    resource = resource_service.update_resource(db, resource_id, payload, current_user)
    return SuccessResponse(data=ResourceOut.model_validate(resource), message="Resource updated successfully.")


@router.delete(
    "/{resource_id}",
    response_model=SuccessResponse[None],
    summary="Delete a resource",
    description="Only the resource's own provider or an ADMIN may delete it. Locked once a "
    "resource is ALLOCATED, IN_TRANSIT, or DELIVERED — cancel it instead via PUT.",
)
def delete_resource(
    resource_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    resource_service.delete_resource(db, resource_id, current_user)
    return SuccessResponse(data=None, message="Resource deleted successfully.")


@router.post(
    "/{resource_id}/analyze",
    response_model=SuccessResponse[ResourceOut],
    summary="Run AI analysis on a resource",
    description="Uses Gemini to read this resource's fields and return structured "
    "classification, extracted quantity, urgency, a recommended rescue window, notable "
    "attributes, storage requirements, eligibility notes, warnings, and a confidence score — "
    "stored in `ai_analysis`. Only the resource's own provider or an ADMIN may trigger this. "
    "Safe to re-run at any time; each run overwrites the previous result. Gemini only analyzes "
    "and structures information here — it never decides allocation, matching, or acceptance, "
    "and this endpoint never changes `status`.",
)
def analyze_resource(
    resource_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    resource = resource_service.analyze_resource(db, resource_id, current_user)
    return SuccessResponse(data=ResourceOut.model_validate(resource), message="Resource analyzed successfully.")

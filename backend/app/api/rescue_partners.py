"""
Rescue partner endpoints:

    POST /api/partners
    GET  /api/partners
    GET  /api/partners/{partner_id}
    PUT  /api/partners/{partner_id}

Mirrors app/api/recipients.py in structure and permission model.
"""

import logging
import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, require_roles
from app.db.database import get_db
from app.models.enums import PartnerType, ResourceType, UserRole
from app.models.user import User
from app.schemas.common import SuccessResponse
from app.schemas.rescue_partner import PartnerCreate, PartnerListData, PartnerOut, PartnerUpdate
from app.services import rescue_partner_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/partners", tags=["Rescue Partners"])


@router.post(
    "",
    response_model=SuccessResponse[PartnerOut],
    status_code=status.HTTP_201_CREATED,
    summary="Create a rescue partner profile",
    description="RESCUE_PARTNER accounts create their own profile (any 'user_id' in the body "
    "is ignored). ADMIN accounts must supply 'user_id' — the RESCUE_PARTNER-role user the "
    "profile is for. One profile per account.",
)
def create_partner(
    payload: PartnerCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.RESCUE_PARTNER, UserRole.ADMIN)),
):
    partner = rescue_partner_service.create_partner(db, payload, current_user)
    return SuccessResponse(
        data=PartnerOut.model_validate(partner), message="Rescue partner profile created successfully."
    )


@router.get(
    "",
    response_model=SuccessResponse[PartnerListData],
    summary="List rescue partners",
    description="Returns rescue partners, newest first, optionally filtered by resource type "
    "(FOOD/MEDICAL — maps to accepts_food/accepts_medical), partner_type, current "
    "availability, or a location/organization-name text search. Available to any "
    "authenticated user.",
)
def list_partners(
    resource_type: ResourceType | None = Query(default=None),
    partner_type: PartnerType | None = Query(default=None),
    is_available: bool | None = Query(default=None),
    location: str | None = Query(default=None, description="Text search across address and organization name."),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    items, total = rescue_partner_service.list_partners(
        db,
        resource_type=resource_type,
        partner_type=partner_type,
        is_available=is_available,
        location_search=location,
        skip=skip,
        limit=limit,
    )
    data = PartnerListData(
        items=[PartnerOut.model_validate(item) for item in items],
        total=total,
        skip=skip,
        limit=limit,
        has_more=skip + len(items) < total,
    )
    return SuccessResponse(data=data, message=f"Found {total} rescue partner(s).")


@router.get(
    "/{partner_id}",
    response_model=SuccessResponse[PartnerOut],
    summary="Get a rescue partner by id",
)
def get_partner(
    partner_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    partner = rescue_partner_service.get_partner_or_404(db, partner_id)
    return SuccessResponse(
        data=PartnerOut.model_validate(partner), message="Rescue partner retrieved successfully."
    )


@router.put(
    "/{partner_id}",
    response_model=SuccessResponse[PartnerOut],
    summary="Update a rescue partner profile",
    description="Only this partner's own account or an ADMIN may edit it. `is_verified` can "
    "only be changed by an ADMIN (403 otherwise). `is_available` can be updated here like any "
    "other field.",
)
def update_partner(
    partner_id: uuid.UUID,
    payload: PartnerUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    partner = rescue_partner_service.update_partner(db, partner_id, payload, current_user)
    return SuccessResponse(
        data=PartnerOut.model_validate(partner), message="Rescue partner profile updated successfully."
    )

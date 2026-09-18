"""
Recipient endpoints:

    POST /api/recipients
    GET  /api/recipients
    GET  /api/recipients/{recipient_id}
    PUT  /api/recipients/{recipient_id}

All endpoints require authentication. Creating a recipient profile is
restricted to RECIPIENT (self-service) and ADMIN (on behalf of a specific
RECIPIENT-role user) roles. Editing is restricted to that recipient's own
account or an ADMIN — enforced in the service layer, same as resources.
"""

import logging
import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, require_roles
from app.db.database import get_db
from app.models.enums import RecipientType, ResourceType, UserRole
from app.models.user import User
from app.schemas.common import SuccessResponse
from app.schemas.recipient import RecipientCreate, RecipientListData, RecipientOut, RecipientUpdate
from app.services import recipient_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/recipients", tags=["Recipients"])


@router.post(
    "",
    response_model=SuccessResponse[RecipientOut],
    status_code=status.HTTP_201_CREATED,
    summary="Create a recipient profile",
    description="RECIPIENT accounts create their own profile (any 'user_id' in the body is "
    "ignored). ADMIN accounts must supply 'user_id' — the RECIPIENT-role user the profile is "
    "for. One profile per account.",
)
def create_recipient(
    payload: RecipientCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.RECIPIENT, UserRole.ADMIN)),
):
    recipient = recipient_service.create_recipient(db, payload, current_user)
    return SuccessResponse(
        data=RecipientOut.model_validate(recipient), message="Recipient profile created successfully."
    )


@router.get(
    "",
    response_model=SuccessResponse[RecipientListData],
    summary="List recipients",
    description="Returns recipients, newest first, optionally filtered by resource type "
    "(FOOD/MEDICAL — maps to accepts_food/accepts_medical), recipient_type, current "
    "availability, or a location/organization-name text search. Available to any "
    "authenticated user.",
)
def list_recipients(
    resource_type: ResourceType | None = Query(default=None),
    recipient_type: RecipientType | None = Query(default=None),
    current_availability: bool | None = Query(default=None),
    location: str | None = Query(default=None, description="Text search across address and organization name."),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    items, total = recipient_service.list_recipients(
        db,
        resource_type=resource_type,
        recipient_type=recipient_type,
        current_availability=current_availability,
        location_search=location,
        skip=skip,
        limit=limit,
    )
    data = RecipientListData(
        items=[RecipientOut.model_validate(item) for item in items],
        total=total,
        skip=skip,
        limit=limit,
        has_more=skip + len(items) < total,
    )
    return SuccessResponse(data=data, message=f"Found {total} recipient(s).")


@router.get(
    "/{recipient_id}",
    response_model=SuccessResponse[RecipientOut],
    summary="Get a recipient by id",
)
def get_recipient(
    recipient_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    recipient = recipient_service.get_recipient_or_404(db, recipient_id)
    return SuccessResponse(
        data=RecipientOut.model_validate(recipient), message="Recipient retrieved successfully."
    )


@router.put(
    "/{recipient_id}",
    response_model=SuccessResponse[RecipientOut],
    summary="Update a recipient profile",
    description="Only this recipient's own account or an ADMIN may edit it. `is_verified` can "
    "only be changed by an ADMIN (403 otherwise). `current_availability` can be updated here "
    "like any other field.",
)
def update_recipient(
    recipient_id: uuid.UUID,
    payload: RecipientUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    recipient = recipient_service.update_recipient(db, recipient_id, payload, current_user)
    return SuccessResponse(
        data=RecipientOut.model_validate(recipient), message="Recipient profile updated successfully."
    )

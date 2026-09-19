"""
Admin endpoints:

    GET   /api/admin/users
    PATCH /api/admin/partners/{partner_id}/verify
    PATCH /api/admin/recipients/{recipient_id}/verify

Every route in this module is restricted to ADMIN accounts —
Depends(require_roles(UserRole.ADMIN)) rejects anyone else with a 403
before the request reaches the service layer, so a non-admin caller learns
nothing about whether the underlying user/recipient/partner even exists.
Verifying a partner or recipient sets the same `is_verified` column PUT
/api/recipients/{id} and PUT /api/partners/{id} already expose to admins —
this just gives that action its own purpose-built route rather than
requiring a full profile PUT to flip one flag.
"""

import logging
import uuid

from fastapi import APIRouter, Body, Depends, Query
from sqlalchemy.orm import Session

from app.core.deps import require_roles
from app.db.database import get_db
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.admin import AdminUserListData, AdminUserOut, VerificationUpdate
from app.schemas.common import SuccessResponse
from app.schemas.recipient import RecipientOut
from app.schemas.rescue_partner import PartnerOut
from app.services import admin_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/admin", tags=["Admin"])


def _to_admin_user_out(user: User) -> AdminUserOut:
    profile_id = None
    is_verified = None
    if user.recipient_profile is not None:
        profile_id = user.recipient_profile.id
        is_verified = user.recipient_profile.is_verified
    elif user.partner_profile is not None:
        profile_id = user.partner_profile.id
        is_verified = user.partner_profile.is_verified

    return AdminUserOut(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        phone=user.phone,
        role=user.role,
        is_active=user.is_active,
        organization_name=user.organization_name,
        created_at=user.created_at,
        verification_profile_id=profile_id,
        is_verified=is_verified,
    )


@router.get(
    "/users",
    response_model=SuccessResponse[AdminUserListData],
    summary="List all users",
    description=(
        "Returns every user on the platform, newest first, optionally filtered by role, active "
        "status, or a text search across email/name/organization. ADMIN only. Each item's "
        "`verification_profile_id` and `is_verified` reflect the user's Recipient or "
        "RescuePartner profile (whichever applies), so an admin can find who still needs "
        "verifying and act on it via the two PATCH endpoints below without a second lookup."
    ),
)
def list_users(
    role: UserRole | None = Query(default=None),
    is_active: bool | None = Query(default=None),
    search: str | None = Query(
        default=None,
        min_length=1,
        max_length=255,
        description="Case-insensitive text search across email, full name, and organization name.",
    ),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
):
    items, total = admin_service.list_users(
        db, role=role, is_active=is_active, search=search, skip=skip, limit=limit
    )
    data = AdminUserListData(
        items=[_to_admin_user_out(u) for u in items],
        total=total,
        skip=skip,
        limit=limit,
        has_more=skip + len(items) < total,
    )
    return SuccessResponse(data=data, message=f"Found {total} user(s).")


@router.patch(
    "/partners/{partner_id}/verify",
    response_model=SuccessResponse[PartnerOut],
    summary="Verify (or revoke verification of) a rescue partner",
    description=(
        "Sets a rescue partner's `is_verified` flag. ADMIN only. Defaults to verifying "
        '(`is_verified: true`) when the body is omitted; pass `{"is_verified": false}` to revoke '
        "a previous verification. Idempotent — setting the same value twice succeeds both times."
    ),
)
def verify_partner(
    partner_id: uuid.UUID,
    payload: VerificationUpdate = Body(default_factory=VerificationUpdate),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
):
    partner = admin_service.verify_partner(db, partner_id, payload, current_user)
    verb = "verified" if partner.is_verified else "unverified"
    return SuccessResponse(data=PartnerOut.model_validate(partner), message=f"Rescue partner {verb}.")


@router.patch(
    "/recipients/{recipient_id}/verify",
    response_model=SuccessResponse[RecipientOut],
    summary="Verify (or revoke verification of) a recipient",
    description=(
        "Sets a recipient's `is_verified` flag. ADMIN only. Defaults to verifying "
        '(`is_verified: true`) when the body is omitted; pass `{"is_verified": false}` to revoke '
        "a previous verification. Idempotent — setting the same value twice succeeds both times. "
        "Distinct from `medical_verified`, which this endpoint never touches."
    ),
)
def verify_recipient(
    recipient_id: uuid.UUID,
    payload: VerificationUpdate = Body(default_factory=VerificationUpdate),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
):
    recipient = admin_service.verify_recipient(db, recipient_id, payload, current_user)
    verb = "verified" if recipient.is_verified else "unverified"
    return SuccessResponse(data=RecipientOut.model_validate(recipient), message=f"Recipient {verb}.")

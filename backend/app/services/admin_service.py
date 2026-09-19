"""
Admin service: business logic behind

    GET   /api/admin/users
    PATCH /api/admin/partners/{partner_id}/verify
    PATCH /api/admin/recipients/{recipient_id}/verify

Every function here assumes the caller has already been confirmed as an
ADMIN — that check happens once, at the route level, via
Depends(require_roles(UserRole.ADMIN)) (see app/core/deps.py and
app/api/admin.py). Nothing in this module re-checks the role; that's the
same convention every other *_service module in this project follows for
checks the router's dependency already enforces (e.g. resource_service
trusts the router for authentication and only checks ownership itself).

Verification reuses recipient_service.get_recipient_or_404 and
rescue_partner_service.get_partner_or_404 rather than re-querying, so the
404 behavior (and the joinedload(...user) each already applies) stays
identical to GET /api/recipients/{id} and GET /api/partners/{id}.
"""

import logging
import uuid
from typing import Optional

from sqlalchemy import func, or_
from sqlalchemy.orm import Session, joinedload

from app.models.enums import UserRole
from app.models.recipient import Recipient
from app.models.rescue_partner import RescuePartner
from app.models.user import User
from app.schemas.admin import VerificationUpdate
from app.services import recipient_service, rescue_partner_service

logger = logging.getLogger(__name__)


def list_users(
    db: Session,
    *,
    role: Optional[UserRole] = None,
    is_active: Optional[bool] = None,
    search: Optional[str] = None,
    skip: int = 0,
    limit: int = 20,
) -> tuple[list[User], int]:
    """
    Every user on the platform, newest first. `recipient_profile` and
    `partner_profile` are eager-loaded (both one-to-one, so this can't
    multiply rows) purely so the router can read each user's verification
    status without a query per row.
    """
    query = db.query(User).options(
        joinedload(User.recipient_profile), joinedload(User.partner_profile)
    )

    if role is not None:
        query = query.filter(User.role == role)
    if is_active is not None:
        query = query.filter(User.is_active == is_active)
    if search:
        term = f"%{search.strip()}%"
        query = query.filter(
            or_(
                User.email.ilike(term),
                User.full_name.ilike(term),
                User.organization_name.ilike(term),
            )
        )

    total = query.with_entities(func.count(User.id)).scalar() or 0
    items = query.order_by(User.created_at.desc()).offset(skip).limit(limit).all()

    return items, total


def verify_partner(
    db: Session, partner_id: uuid.UUID, payload: VerificationUpdate, current_user: User
) -> RescuePartner:
    """
    Sets a rescue partner's `is_verified` flag. Idempotent — setting the
    value it already has is a no-op commit-wise (still returns 200 with
    the current state), so a client retrying a verify call never needs to
    special-case "already verified".
    """
    partner = rescue_partner_service.get_partner_or_404(db, partner_id)

    if partner.is_verified != payload.is_verified:
        partner.is_verified = payload.is_verified
        db.commit()
        db.refresh(partner)

    logger.info(
        "Rescue partner %s verification set to %s by admin %s",
        partner.id,
        payload.is_verified,
        current_user.id,
    )
    return partner


def verify_recipient(
    db: Session, recipient_id: uuid.UUID, payload: VerificationUpdate, current_user: User
) -> Recipient:
    """
    Sets a recipient's platform `is_verified` flag. Deliberately leaves
    `medical_verified` untouched — that's a separate, stricter check
    (required before any MEDICAL allocation, see
    app/services/matching_engine.py._score_eligibility) and isn't part of
    what this endpoint verifies.
    """
    recipient = recipient_service.get_recipient_or_404(db, recipient_id)

    if recipient.is_verified != payload.is_verified:
        recipient.is_verified = payload.is_verified
        db.commit()
        db.refresh(recipient)

    logger.info(
        "Recipient %s verification set to %s by admin %s",
        recipient.id,
        payload.is_verified,
        current_user.id,
    )
    return recipient

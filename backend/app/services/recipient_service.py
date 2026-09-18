"""
Recipient service: business logic for POST/GET/PUT /api/recipients, kept
separate from the router so it's reusable (e.g. by the matching engine in
a later stage) without going through HTTP.
"""

import logging
import uuid
from typing import Optional

from sqlalchemy import func, or_
from sqlalchemy.orm import Session, joinedload

from app.core.errors import AppError
from app.models.enums import RecipientType, ResourceType, UserRole
from app.models.recipient import Recipient
from app.models.user import User
from app.schemas.recipient import RecipientCreate, RecipientUpdate

logger = logging.getLogger(__name__)


def _is_owner_or_admin(recipient: Recipient, current_user: User) -> bool:
    return current_user.role == UserRole.ADMIN or recipient.user_id == current_user.id


def create_recipient(db: Session, payload: RecipientCreate, current_user: User) -> Recipient:
    """
    Create a recipient profile.

    Self-service (current_user.role == RECIPIENT): always creates the
    profile for the caller's own account, regardless of any `user_id`
    sent in the payload.

    Admin (current_user.role == ADMIN): must supply `user_id` — the
    RECIPIENT-role user this profile is being created for (e.g. seeding
    demo data). Rejects a target user that doesn't exist or isn't a
    RECIPIENT.

    Either way, rejects if that user already has a recipient profile —
    the relationship is one-to-one.
    """
    if current_user.role == UserRole.ADMIN:
        if payload.user_id is None:
            raise AppError(
                status_code=422,
                code="USER_ID_REQUIRED",
                message="Admins must supply 'user_id' — the RECIPIENT-role user this profile is for.",
            )
        target_user = db.query(User).filter(User.id == payload.user_id).first()
        if target_user is None:
            raise AppError(status_code=404, code="USER_NOT_FOUND", message="No user found with that id.")
        if target_user.role != UserRole.RECIPIENT:
            raise AppError(
                status_code=422,
                code="INVALID_TARGET_ROLE",
                message="The target user must have the RECIPIENT role.",
            )
        target_user_id = target_user.id
    else:
        target_user_id = current_user.id

    existing = db.query(Recipient).filter(Recipient.user_id == target_user_id).first()
    if existing is not None:
        raise AppError(
            status_code=409,
            code="RECIPIENT_PROFILE_EXISTS",
            message="A recipient profile already exists for this account.",
        )

    recipient = Recipient(
        user_id=target_user_id,
        organization_name=payload.organization_name,
        recipient_type=payload.recipient_type,
        accepts_food=payload.accepts_food,
        accepts_medical=payload.accepts_medical,
        capacity=payload.capacity,
        current_availability=payload.current_availability,
        location_address=payload.location_address,
        latitude=payload.latitude,
        longitude=payload.longitude,
        service_area_km=payload.service_area_km,
        contact_phone=payload.contact_phone,
        operating_hours=payload.operating_hours,
        medical_verified=False,
        is_verified=False,
    )
    db.add(recipient)
    db.commit()
    db.refresh(recipient)

    logger.info("Recipient profile %s created for user %s", recipient.id, target_user_id)
    return recipient


def get_recipient_or_404(db: Session, recipient_id: uuid.UUID) -> Recipient:
    recipient = (
        db.query(Recipient)
        .options(joinedload(Recipient.user))
        .filter(Recipient.id == recipient_id)
        .first()
    )
    if recipient is None:
        raise AppError(status_code=404, code="RECIPIENT_NOT_FOUND", message="Recipient not found.")
    return recipient


def list_recipients(
    db: Session,
    *,
    resource_type: Optional[ResourceType] = None,
    recipient_type: Optional[RecipientType] = None,
    current_availability: Optional[bool] = None,
    location_search: Optional[str] = None,
    skip: int = 0,
    limit: int = 20,
) -> tuple[list[Recipient], int]:
    query = db.query(Recipient).options(joinedload(Recipient.user))

    if resource_type is not None:
        if resource_type == ResourceType.FOOD:
            query = query.filter(Recipient.accepts_food.is_(True))
        elif resource_type == ResourceType.MEDICAL:
            query = query.filter(Recipient.accepts_medical.is_(True))
    if recipient_type is not None:
        query = query.filter(Recipient.recipient_type == recipient_type)
    if current_availability is not None:
        query = query.filter(Recipient.current_availability == current_availability)
    if location_search:
        pattern = f"%{location_search.strip()}%"
        query = query.filter(
            or_(Recipient.location_address.ilike(pattern), Recipient.organization_name.ilike(pattern))
        )

    total = query.with_entities(func.count(Recipient.id)).scalar() or 0
    items = query.order_by(Recipient.created_at.desc()).offset(skip).limit(limit).all()

    return items, total


def update_recipient(
    db: Session, recipient_id: uuid.UUID, payload: RecipientUpdate, current_user: User
) -> Recipient:
    recipient = get_recipient_or_404(db, recipient_id)

    if not _is_owner_or_admin(recipient, current_user):
        raise AppError(
            status_code=403,
            code="NOT_RECIPIENT_OWNER",
            message="Only this recipient's own account (or an admin) can edit this profile.",
        )

    update_data = payload.model_dump(exclude_unset=True)

    if "is_verified" in update_data and current_user.role != UserRole.ADMIN:
        raise AppError(
            status_code=403,
            code="ADMIN_ONLY_FIELD",
            message="Only an admin can change verification status.",
        )

    for field, value in update_data.items():
        setattr(recipient, field, value)

    db.commit()
    db.refresh(recipient)

    logger.info("Recipient %s updated by %s", recipient.id, current_user.id)
    return recipient

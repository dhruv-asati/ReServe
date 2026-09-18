"""
Rescue partner service: business logic for POST/GET/PUT /api/partners.
Mirrors app/services/recipient_service.py — see that module for the
self-service-vs-admin creation rationale.
"""

import logging
import uuid
from typing import Optional

from sqlalchemy import func, or_
from sqlalchemy.orm import Session, joinedload

from app.core.errors import AppError
from app.models.enums import PartnerType, ResourceType, UserRole
from app.models.rescue_partner import RescuePartner
from app.models.user import User
from app.schemas.rescue_partner import PartnerCreate, PartnerUpdate

logger = logging.getLogger(__name__)


def _is_owner_or_admin(partner: RescuePartner, current_user: User) -> bool:
    return current_user.role == UserRole.ADMIN or partner.user_id == current_user.id


def create_partner(db: Session, payload: PartnerCreate, current_user: User) -> RescuePartner:
    """
    Create a rescue partner profile.

    Self-service (current_user.role == RESCUE_PARTNER): always creates the
    profile for the caller's own account, regardless of any `user_id`
    sent in the payload.

    Admin (current_user.role == ADMIN): must supply `user_id` — the
    RESCUE_PARTNER-role user this profile is being created for (e.g.
    seeding demo data). Rejects a target user that doesn't exist or isn't
    a RESCUE_PARTNER.

    Either way, rejects if that user already has a partner profile — the
    relationship is one-to-one.
    """
    if current_user.role == UserRole.ADMIN:
        if payload.user_id is None:
            raise AppError(
                status_code=422,
                code="USER_ID_REQUIRED",
                message="Admins must supply 'user_id' — the RESCUE_PARTNER-role user this profile is for.",
            )
        target_user = db.query(User).filter(User.id == payload.user_id).first()
        if target_user is None:
            raise AppError(status_code=404, code="USER_NOT_FOUND", message="No user found with that id.")
        if target_user.role != UserRole.RESCUE_PARTNER:
            raise AppError(
                status_code=422,
                code="INVALID_TARGET_ROLE",
                message="The target user must have the RESCUE_PARTNER role.",
            )
        target_user_id = target_user.id
    else:
        target_user_id = current_user.id

    existing = db.query(RescuePartner).filter(RescuePartner.user_id == target_user_id).first()
    if existing is not None:
        raise AppError(
            status_code=409,
            code="PARTNER_PROFILE_EXISTS",
            message="A rescue partner profile already exists for this account.",
        )

    partner = RescuePartner(
        user_id=target_user_id,
        organization_name=payload.organization_name,
        partner_type=payload.partner_type,
        vehicle_type=payload.vehicle_type,
        capacity=payload.capacity,
        is_available=payload.is_available,
        accepts_food=payload.accepts_food,
        accepts_medical=payload.accepts_medical,
        contact_phone=payload.contact_phone,
        location_address=payload.location_address,
        latitude=payload.latitude,
        longitude=payload.longitude,
        service_radius_km=payload.service_radius_km,
        operating_hours=payload.operating_hours,
        is_verified=False,
        rating=None,
    )
    db.add(partner)
    db.commit()
    db.refresh(partner)

    logger.info("Rescue partner profile %s created for user %s", partner.id, target_user_id)
    return partner


def get_partner_or_404(db: Session, partner_id: uuid.UUID) -> RescuePartner:
    partner = (
        db.query(RescuePartner)
        .options(joinedload(RescuePartner.user))
        .filter(RescuePartner.id == partner_id)
        .first()
    )
    if partner is None:
        raise AppError(status_code=404, code="PARTNER_NOT_FOUND", message="Rescue partner not found.")
    return partner


def list_partners(
    db: Session,
    *,
    resource_type: Optional[ResourceType] = None,
    partner_type: Optional[PartnerType] = None,
    is_available: Optional[bool] = None,
    location_search: Optional[str] = None,
    skip: int = 0,
    limit: int = 20,
) -> tuple[list[RescuePartner], int]:
    query = db.query(RescuePartner).options(joinedload(RescuePartner.user))

    if resource_type is not None:
        if resource_type == ResourceType.FOOD:
            query = query.filter(RescuePartner.accepts_food.is_(True))
        elif resource_type == ResourceType.MEDICAL:
            query = query.filter(RescuePartner.accepts_medical.is_(True))
    if partner_type is not None:
        query = query.filter(RescuePartner.partner_type == partner_type)
    if is_available is not None:
        query = query.filter(RescuePartner.is_available == is_available)
    if location_search:
        pattern = f"%{location_search.strip()}%"
        query = query.filter(
            or_(
                RescuePartner.location_address.ilike(pattern),
                RescuePartner.organization_name.ilike(pattern),
            )
        )

    total = query.with_entities(func.count(RescuePartner.id)).scalar() or 0
    items = query.order_by(RescuePartner.created_at.desc()).offset(skip).limit(limit).all()

    return items, total


def update_partner(
    db: Session, partner_id: uuid.UUID, payload: PartnerUpdate, current_user: User
) -> RescuePartner:
    partner = get_partner_or_404(db, partner_id)

    if not _is_owner_or_admin(partner, current_user):
        raise AppError(
            status_code=403,
            code="NOT_PARTNER_OWNER",
            message="Only this rescue partner's own account (or an admin) can edit this profile.",
        )

    update_data = payload.model_dump(exclude_unset=True)

    if "is_verified" in update_data and current_user.role != UserRole.ADMIN:
        raise AppError(
            status_code=403,
            code="ADMIN_ONLY_FIELD",
            message="Only an admin can change verification status.",
        )

    for field, value in update_data.items():
        setattr(partner, field, value)

    db.commit()
    db.refresh(partner)

    logger.info("Rescue partner %s updated by %s", partner.id, current_user.id)
    return partner

"""
ResourceRequest service: business logic for POST/GET/PATCH(status)/DELETE
/api/requests, kept separate from the router so it's reusable (e.g. by a
future matching engine) without going through HTTP.
"""

import logging
import uuid
from typing import Optional

from sqlalchemy import func, or_
from sqlalchemy.orm import Session, joinedload

from app.core.errors import AppError
from app.models.enums import ResourceRequestStatus, ResourceType, UrgencyLevel, UserRole
from app.models.recipient import Recipient
from app.models.resource_request import ResourceRequest, ResourceRequestStatusHistory
from app.models.user import User
from app.schemas.resource_request import ResourceRequestCreate, ResourceRequestStatusUpdate

logger = logging.getLogger(__name__)

# Which statuses a request may move to from each current status. Terminal
# statuses (REJECTED, FULFILLED, CANCELLED) map to an empty set.
ALLOWED_TRANSITIONS: dict[ResourceRequestStatus, set[ResourceRequestStatus]] = {
    ResourceRequestStatus.PENDING: {
        ResourceRequestStatus.APPROVED,
        ResourceRequestStatus.REJECTED,
        ResourceRequestStatus.CANCELLED,
    },
    ResourceRequestStatus.APPROVED: {
        ResourceRequestStatus.FULFILLED,
        ResourceRequestStatus.REJECTED,
        ResourceRequestStatus.CANCELLED,
    },
    ResourceRequestStatus.REJECTED: set(),
    ResourceRequestStatus.FULFILLED: set(),
    ResourceRequestStatus.CANCELLED: set(),
}

# CANCELLED may be set by the owning recipient (or an admin); every other
# transition (APPROVED/REJECTED/FULFILLED) is a review decision made by a
# PROVIDER or ADMIN — there's no matching engine yet to restrict *which*
# provider, so any PROVIDER can act on any pending/approved request, same
# open-marketplace model as browsing resources.
RECIPIENT_ALLOWED_TARGETS = {ResourceRequestStatus.CANCELLED}
REVIEWER_ALLOWED_TARGETS = {
    ResourceRequestStatus.APPROVED,
    ResourceRequestStatus.REJECTED,
    ResourceRequestStatus.FULFILLED,
}

# A request that's already been committed to (APPROVED) or completed
# (FULFILLED) can't be hard-deleted — cancel it instead via PATCH .../status
# if it's still APPROVED. PENDING/REJECTED/CANCELLED requests can be deleted
# outright since nothing downstream depends on them.
DELETE_LOCKED_STATUSES = {ResourceRequestStatus.APPROVED, ResourceRequestStatus.FULFILLED}


def _get_recipient_profile_or_error(db: Session, current_user: User) -> Recipient:
    recipient = db.query(Recipient).filter(Recipient.user_id == current_user.id).first()
    if recipient is None:
        raise AppError(
            status_code=400,
            code="RECIPIENT_PROFILE_REQUIRED",
            message="Complete your recipient profile (POST /api/recipients) before creating a request.",
        )
    return recipient


def _is_owner_recipient(request: ResourceRequest, current_user: User) -> bool:
    return request.recipient.user_id == current_user.id


def create_resource_request(
    db: Session, payload: ResourceRequestCreate, current_user: User
) -> ResourceRequest:
    """
    Create a resource request.

    Self-service (current_user.role == RECIPIENT): always creates the
    request for the caller's own recipient profile, regardless of any
    `recipient_id` sent in the payload. Requires that profile to already
    exist.

    Admin (current_user.role == ADMIN): must supply `recipient_id` — the
    recipient this request is being made on behalf of.

    Rejects a resource_type the recipient's profile doesn't accept
    (accepts_food/accepts_medical), and MEDICAL requests from a recipient
    that isn't medical_verified yet.
    """
    if current_user.role == UserRole.ADMIN:
        if payload.recipient_id is None:
            raise AppError(
                status_code=422,
                code="RECIPIENT_ID_REQUIRED",
                message="Admins must supply 'recipient_id' — the recipient this request is for.",
            )
        recipient = db.query(Recipient).filter(Recipient.id == payload.recipient_id).first()
        if recipient is None:
            raise AppError(status_code=404, code="RECIPIENT_NOT_FOUND", message="No recipient found with that id.")
    else:
        recipient = _get_recipient_profile_or_error(db, current_user)

    if payload.resource_type == ResourceType.FOOD and not recipient.accepts_food:
        raise AppError(
            status_code=422,
            code="RESOURCE_TYPE_NOT_ACCEPTED",
            message="This recipient profile is not set up to accept FOOD resources.",
        )
    if payload.resource_type == ResourceType.MEDICAL:
        if not recipient.accepts_medical:
            raise AppError(
                status_code=422,
                code="RESOURCE_TYPE_NOT_ACCEPTED",
                message="This recipient profile is not set up to accept MEDICAL resources.",
            )
        if not recipient.medical_verified:
            raise AppError(
                status_code=403,
                code="MEDICAL_VERIFICATION_REQUIRED",
                message="This recipient must be medical-verified before requesting MEDICAL resources.",
            )

    request = ResourceRequest(
        recipient_id=recipient.id,
        resource_type=payload.resource_type,
        requested_quantity=payload.requested_quantity,
        requesting_organization=payload.requesting_organization or recipient.organization_name,
        urgency=payload.urgency,
        needed_by=payload.needed_by,
        eligibility_requirements=payload.eligibility_requirements,
        can_self_pickup=payload.can_self_pickup,
        notes=payload.notes,
        status=ResourceRequestStatus.PENDING,
    )
    db.add(request)
    db.flush()  # assigns request.id, needed for the history row's FK

    db.add(
        ResourceRequestStatusHistory(
            request_id=request.id,
            from_status=None,
            to_status=ResourceRequestStatus.PENDING,
            changed_by_user_id=current_user.id,
        )
    )
    db.commit()
    db.refresh(request)

    logger.info("ResourceRequest %s created for recipient %s", request.id, recipient.id)
    return request


def get_resource_request_or_404(db: Session, request_id: uuid.UUID) -> ResourceRequest:
    request = (
        db.query(ResourceRequest)
        .options(
            joinedload(ResourceRequest.recipient),
            joinedload(ResourceRequest.status_history),
        )
        .filter(ResourceRequest.id == request_id)
        .first()
    )
    if request is None:
        raise AppError(status_code=404, code="RESOURCE_REQUEST_NOT_FOUND", message="Resource request not found.")
    return request


def list_resource_requests(
    db: Session,
    *,
    current_user: User,
    resource_type: Optional[ResourceType] = None,
    status_filter: Optional[ResourceRequestStatus] = None,
    recipient_id: Optional[uuid.UUID] = None,
    urgency: Optional[UrgencyLevel] = None,
    search: Optional[str] = None,
    skip: int = 0,
    limit: int = 20,
) -> tuple[list[ResourceRequest], int]:
    """
    RECIPIENTs are always scoped to their own requests, regardless of the
    `recipient_id` query param — they can't browse other recipients'
    requests. PROVIDER, RESCUE_PARTNER, and ADMIN see the full list
    (optionally filtered), matching the same open-marketplace visibility
    resources already have.
    """
    query = db.query(ResourceRequest).options(
        joinedload(ResourceRequest.recipient), joinedload(ResourceRequest.status_history)
    )

    if current_user.role == UserRole.RECIPIENT:
        own_recipient = _get_recipient_profile_or_error(db, current_user)
        query = query.filter(ResourceRequest.recipient_id == own_recipient.id)
    elif recipient_id is not None:
        query = query.filter(ResourceRequest.recipient_id == recipient_id)

    if resource_type is not None:
        query = query.filter(ResourceRequest.resource_type == resource_type)
    if status_filter is not None:
        query = query.filter(ResourceRequest.status == status_filter)
    if urgency is not None:
        query = query.filter(ResourceRequest.urgency == urgency)
    if search:
        term = f"%{search.strip()}%"
        query = query.filter(
            or_(
                ResourceRequest.requesting_organization.ilike(term),
                ResourceRequest.notes.ilike(term),
                ResourceRequest.eligibility_requirements.ilike(term),
            )
        )

    total = query.with_entities(func.count(ResourceRequest.id)).scalar() or 0
    items = query.order_by(ResourceRequest.created_at.desc()).offset(skip).limit(limit).all()

    return items, total


def update_resource_request_status(
    db: Session, request_id: uuid.UUID, payload: ResourceRequestStatusUpdate, current_user: User
) -> ResourceRequest:
    request = get_resource_request_or_404(db, request_id)

    is_owner = current_user.role != UserRole.ADMIN and _is_owner_recipient(request, current_user)
    is_reviewer = current_user.role in (UserRole.PROVIDER, UserRole.ADMIN)
    is_admin = current_user.role == UserRole.ADMIN
    target = payload.status

    if not is_admin:
        if current_user.role == UserRole.RECIPIENT:
            if not is_owner:
                raise AppError(
                    status_code=403,
                    code="NOT_REQUEST_OWNER",
                    message="Only the recipient who made this request (or an admin) can update it.",
                )
            if target not in RECIPIENT_ALLOWED_TARGETS:
                raise AppError(
                    status_code=403,
                    code="FORBIDDEN_TRANSITION",
                    message="Recipients can only cancel their own requests. "
                    "APPROVED/REJECTED/FULFILLED are set by a provider or admin reviewing the request.",
                )
        elif is_reviewer:
            if target not in REVIEWER_ALLOWED_TARGETS:
                raise AppError(
                    status_code=403,
                    code="FORBIDDEN_TRANSITION",
                    message="Providers can only approve, reject, or mark a request fulfilled. "
                    "Cancelling is done by the requesting recipient (or an admin).",
                )
        else:
            raise AppError(
                status_code=403,
                code="FORBIDDEN_ROLE",
                message="Only the requesting recipient, a provider, or an admin can change a request's status.",
            )

    current_status = request.status
    if target not in ALLOWED_TRANSITIONS.get(current_status, set()):
        raise AppError(
            status_code=409,
            code="INVALID_STATUS_TRANSITION",
            message=f"Cannot move a request from '{current_status.value}' to '{target.value}'.",
        )

    request.status = target
    db.add(
        ResourceRequestStatusHistory(
            request_id=request.id,
            from_status=current_status,
            to_status=target,
            note=payload.note,
            changed_by_user_id=current_user.id,
        )
    )
    db.commit()
    db.refresh(request)

    logger.info(
        "ResourceRequest %s moved %s -> %s by %s", request.id, current_status.value, target.value, current_user.id
    )
    return request


def delete_resource_request(db: Session, request_id: uuid.UUID, current_user: User) -> None:
    request = get_resource_request_or_404(db, request_id)

    is_owner = _is_owner_recipient(request, current_user)
    if not (is_owner or current_user.role == UserRole.ADMIN):
        raise AppError(
            status_code=403,
            code="NOT_REQUEST_OWNER",
            message="Only the recipient who made this request (or an admin) can delete it.",
        )

    if request.status in DELETE_LOCKED_STATUSES:
        raise AppError(
            status_code=409,
            code="RESOURCE_REQUEST_LOCKED",
            message=f"This request is '{request.status.value}' and can no longer be deleted. "
            "Cancel it first via PATCH .../status if it's still APPROVED.",
        )

    db.delete(request)
    db.commit()

    logger.info("ResourceRequest %s deleted by %s", request_id, current_user.id)

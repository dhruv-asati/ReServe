"""
Resource service: CRUD business logic for POST/GET/PUT/DELETE
/api/resources, kept separate from the router so it's reusable (e.g. by
the matching engine in Stage 7, or a future seed script) without going
through HTTP.
"""

import logging
import uuid
from typing import Optional

from sqlalchemy import func, or_
from sqlalchemy.orm import Session, joinedload

from app.core.errors import AppError
from app.models.allocation import Allocation
from app.models.enums import (
    AllocationStatus,
    OperationStatus,
    ResourceStatus,
    ResourceType,
    RescueRequestStatus,
    UserRole,
)
from app.models.operation import RescueOperation
from app.models.resource import Resource
from app.models.rescue_request import RescueRequest
from app.models.user import User
from app.schemas.resource import ResourceCreate, ResourceUpdate, _check_date_relationships, _validate_food_fields
from app.services import gemini_service

logger = logging.getLogger(__name__)

# Once a resource has moved this far into a rescue, it can no longer be
# freely edited or deleted by its provider — the operation already has
# commitments (a recipient, a partner, a truck en route) riding on the
# data as it stood when those commitments were made.
LOCKED_STATUSES = {
    ResourceStatus.ALLOCATED,
    ResourceStatus.IN_TRANSIT,
    ResourceStatus.DELIVERED,
}

# Non-terminal statuses on the coordination chain that hangs off a
# resource (RescueRequest -> Allocation / RescueOperation). Deletion is
# blocked whenever any of these exist for the resource, independent of
# the Resource.status check above — that check is a fast common-case
# guard, this one is the source of truth, since a resource's own status
# can in principle lag behind the state of its rescue request (e.g. a
# request still MATCHING while the resource row itself hasn't been
# flipped yet). Both are kept because deleting the parent Resource would
# cascade-delete the RescueRequest/Match/Allocation/RescueOperation rows
# beneath it (see the cascade config on those relationships) — silently
# destroying an in-flight rescue's records — so this must be checked
# *before* the delete, not relied upon to fail loudly after.
ACTIVE_REQUEST_STATUSES = {
    RescueRequestStatus.PENDING,
    RescueRequestStatus.MATCHING,
    RescueRequestStatus.MATCHED,
    RescueRequestStatus.PARTIALLY_MATCHED,
}
ACTIVE_ALLOCATION_STATUSES = {
    AllocationStatus.PENDING,
    AllocationStatus.CONFIRMED,
}
ACTIVE_OPERATION_STATUSES = {
    OperationStatus.CREATED,
    OperationStatus.MATCHING,
    OperationStatus.MATCHED,
    OperationStatus.PARTNER_ASSIGNED,
    OperationStatus.PICKUP_IN_PROGRESS,
    OperationStatus.IN_TRANSIT,
    OperationStatus.REALLOCATING,
}


def _is_owner_or_admin(resource: Resource, current_user: User) -> bool:
    return current_user.role == UserRole.ADMIN or resource.provider_id == current_user.id


def _has_active_allocation_or_operation(db: Session, resource_id: uuid.UUID) -> bool:
    """True if this resource has any rescue request, allocation, or
    operation that hasn't reached a terminal state yet."""
    has_active_request = (
        db.query(RescueRequest.id)
        .filter(
            RescueRequest.resource_id == resource_id,
            RescueRequest.status.in_(ACTIVE_REQUEST_STATUSES),
        )
        .first()
        is not None
    )
    if has_active_request:
        return True

    has_active_allocation = (
        db.query(Allocation.id)
        .join(RescueRequest, Allocation.rescue_request_id == RescueRequest.id)
        .filter(
            RescueRequest.resource_id == resource_id,
            Allocation.status.in_(ACTIVE_ALLOCATION_STATUSES),
        )
        .first()
        is not None
    )
    if has_active_allocation:
        return True

    return (
        db.query(RescueOperation.id)
        .join(RescueRequest, RescueOperation.rescue_request_id == RescueRequest.id)
        .filter(
            RescueRequest.resource_id == resource_id,
            RescueOperation.status.in_(ACTIVE_OPERATION_STATUSES),
        )
        .first()
        is not None
    )


def create_resource(db: Session, payload: ResourceCreate, current_user: User) -> Resource:
    """Create a resource owned by the current user. MEDICAL resources are always
    flagged as requiring verification, regardless of what the client sent."""
    requires_medical_verification = payload.requires_medical_verification
    if payload.resource_type == ResourceType.MEDICAL:
        requires_medical_verification = True

    resource = Resource(
        provider_id=current_user.id,
        title=payload.title,
        description=payload.description,
        resource_type=payload.resource_type,
        category=payload.category,
        quantity=payload.quantity,
        unit=payload.unit,
        status=ResourceStatus.AVAILABLE,
        urgency=payload.urgency,
        available_time=payload.available_time,
        expiry_time=payload.expiry_time,
        pickup_window_start=payload.pickup_window_start,
        pickup_window_end=payload.pickup_window_end,
        location_address=payload.location_address,
        latitude=payload.latitude,
        longitude=payload.longitude,
        image_url=payload.image_url,
        is_perishable=payload.is_perishable,
        requires_medical_verification=requires_medical_verification,
        food_category=payload.food_category,
        is_vegetarian=payload.is_vegetarian,
        preparation_time=payload.preparation_time,
        allergen_info=[a.value for a in payload.allergen_info] if payload.allergen_info else None,
        storage_requirements=payload.storage_requirements,
        packaging_info=payload.packaging_info,
    )
    db.add(resource)
    db.commit()
    db.refresh(resource)

    logger.info("Resource %s created by provider %s", resource.id, current_user.id)
    return resource


def get_resource_or_404(db: Session, resource_id: uuid.UUID) -> Resource:
    resource = (
        db.query(Resource)
        .options(joinedload(Resource.provider))
        .filter(Resource.id == resource_id)
        .first()
    )
    if resource is None:
        raise AppError(status_code=404, code="RESOURCE_NOT_FOUND", message="Resource not found.")
    return resource


def list_resources(
    db: Session,
    *,
    resource_type: Optional[ResourceType] = None,
    status_filter: Optional[ResourceStatus] = None,
    provider_id: Optional[uuid.UUID] = None,
    search: Optional[str] = None,
    skip: int = 0,
    limit: int = 20,
) -> tuple[list[Resource], int]:
    query = db.query(Resource).options(joinedload(Resource.provider))

    if resource_type is not None:
        query = query.filter(Resource.resource_type == resource_type)
    if status_filter is not None:
        query = query.filter(Resource.status == status_filter)
    if provider_id is not None:
        query = query.filter(Resource.provider_id == provider_id)
    if search:
        # Case-insensitive substring match against title OR description.
        term = f"%{search.strip()}%"
        query = query.filter(or_(Resource.title.ilike(term), Resource.description.ilike(term)))

    total = query.with_entities(func.count(Resource.id)).scalar() or 0
    items = query.order_by(Resource.created_at.desc()).offset(skip).limit(limit).all()

    return items, total


def update_resource(
    db: Session, resource_id: uuid.UUID, payload: ResourceUpdate, current_user: User
) -> Resource:
    resource = get_resource_or_404(db, resource_id)

    if not _is_owner_or_admin(resource, current_user):
        raise AppError(
            status_code=403,
            code="NOT_RESOURCE_OWNER",
            message="Only the provider who posted this resource (or an admin) can edit it.",
        )

    if resource.status in LOCKED_STATUSES:
        raise AppError(
            status_code=409,
            code="RESOURCE_LOCKED",
            message=f"This resource is already '{resource.status.value}' and can no longer be edited.",
        )

    update_data = payload.model_dump(exclude_unset=True)

    # MEDICAL resources always require verification, regardless of the
    # incoming payload — same rule as on create.
    effective_type = update_data.get("resource_type", resource.resource_type)
    if effective_type == ResourceType.MEDICAL:
        update_data["requires_medical_verification"] = True

    # Re-validate date relationships (including the food-specific
    # preparation_time) against the *merged* state (existing values for
    # anything not present in this payload). A payload that only touches
    # one of these fields can still be schema-valid on its own but
    # conflict with a value the resource already has — e.g. moving
    # pickup_window_start later than an untouched expiry_time.
    try:
        _check_date_relationships(
            available_time=update_data.get("available_time", resource.available_time),
            expiry_time=update_data.get("expiry_time", resource.expiry_time),
            pickup_window_start=update_data.get("pickup_window_start", resource.pickup_window_start),
            pickup_window_end=update_data.get("pickup_window_end", resource.pickup_window_end),
            preparation_time=update_data.get("preparation_time", resource.preparation_time),
        )
        # Same merged-state reasoning for food-field type-appropriateness:
        # resource_type can't be changed via update, but a payload that
        # only sets e.g. packaging_info still needs checking against the
        # resource's actual (unchangeable) type.
        _validate_food_fields(
            resource_type=effective_type,
            food_category=update_data.get("food_category", resource.food_category),
            is_vegetarian=update_data.get("is_vegetarian", resource.is_vegetarian),
            preparation_time=update_data.get("preparation_time", resource.preparation_time),
            allergen_info=update_data.get("allergen_info", resource.allergen_info),
            storage_requirements=update_data.get("storage_requirements", resource.storage_requirements),
            packaging_info=update_data.get("packaging_info", resource.packaging_info),
        )
    except ValueError as exc:
        raise AppError(status_code=422, code="VALIDATION_ERROR", message=str(exc))

    if update_data.get("allergen_info") is not None:
        # Stored as a JSON column of plain strings — normalize away the
        # AllergenType enum wrapper the schema layer parsed input into.
        update_data["allergen_info"] = [
            item.value if hasattr(item, "value") else item for item in update_data["allergen_info"]
        ]

    for field, value in update_data.items():
        setattr(resource, field, value)

    db.commit()
    db.refresh(resource)

    logger.info("Resource %s updated by %s", resource.id, current_user.id)
    return resource


def delete_resource(db: Session, resource_id: uuid.UUID, current_user: User) -> None:
    resource = get_resource_or_404(db, resource_id)

    if not _is_owner_or_admin(resource, current_user):
        raise AppError(
            status_code=403,
            code="NOT_RESOURCE_OWNER",
            message="Only the provider who posted this resource (or an admin) can delete it.",
        )

    if resource.status in LOCKED_STATUSES:
        raise AppError(
            status_code=409,
            code="RESOURCE_LOCKED",
            message=f"This resource is already '{resource.status.value}' and can no longer be deleted. "
            "Cancel it instead if it's still PENDING or MATCHING.",
        )

    if _has_active_allocation_or_operation(db, resource_id):
        raise AppError(
            status_code=409,
            code="RESOURCE_HAS_ACTIVE_OPERATIONS",
            message="This resource has an active rescue request, allocation, or operation in "
            "progress and cannot be deleted. Cancel the associated rescue request/operation "
            "first, or wait for it to reach a terminal state.",
        )

    db.delete(resource)
    db.commit()

    logger.info("Resource %s deleted by %s", resource_id, current_user.id)


def analyze_resource(db: Session, resource_id: uuid.UUID, current_user: User) -> Resource:
    """
    Runs Gemini structuring analysis on a resource and stores the result
    in `ai_analysis`. Restricted like update/delete — only the resource's
    own provider or an ADMIN may trigger it — and can be re-run at any
    time; each call overwrites the previous `ai_analysis` with a fresh
    one, there is no history kept of past analyses.

    Deliberately does NOT check LOCKED_STATUSES: analysis is read-only
    with respect to every field except `ai_analysis` itself, so it stays
    available even on an ALLOCATED/IN_TRANSIT/DELIVERED resource (e.g. to
    help a recipient double-check handling notes after pickup). This
    never changes `status` or touches RescueRequest/Match/Allocation —
    Gemini only analyzes and structures information; allocation decisions
    are made elsewhere, never by this function or by the AI itself.
    """
    resource = get_resource_or_404(db, resource_id)

    if not _is_owner_or_admin(resource, current_user):
        raise AppError(
            status_code=403,
            code="NOT_RESOURCE_OWNER",
            message="Only the provider who posted this resource (or an admin) can request AI analysis.",
        )

    result = gemini_service.analyze_resource(resource)

    resource.ai_analysis = result.model_dump(mode="json")
    db.commit()
    db.refresh(resource)

    logger.info("Resource %s analyzed by %s using %s", resource.id, current_user.id, result.model)
    return resource

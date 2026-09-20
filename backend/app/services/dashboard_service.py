"""
Dashboard service: read-only aggregates and feeds for the React dashboard.

Every figure comes from a live query — nothing is cached or mocked, so an
empty database honestly returns zeros and empty lists (same policy as
analytics_service). Display strings ("42 min remaining", "6 min ago",
"+164 units this week") are built here because the dashboard renders them
verbatim; see app/schemas/dashboard.py.

Nothing in this module writes to the database or can influence matching,
allocation, or any status.
"""

from datetime import datetime, timedelta, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload, selectinload

from app.models.allocation import Allocation
from app.models.enums import (
    AllocationStatus,
    OperationEventType,
    OperationStatus,
    RescueRequestStatus,
    ResourceStatus,
    PartnerType,
    RecipientType,
    UserRole,
)
from app.models.operation import OperationEvent, RescueOperation
from app.models.recipient import Recipient
from app.models.rescue_hub import RescueHub
from app.models.rescue_partner import RescuePartner
from app.models.rescue_request import RescueRequest
from app.models.resource import Resource
from app.models.user import User
from app.schemas.dashboard import (
    ActiveOperationOut,
    ActivityEventOut,
    AtRiskResourceOut,
    DashboardOverviewData,
    LatLngOut,
    NetworkLocationOut,
    NetworkOrganizationOut,
    OrgCapacityOut,
    OrgWorkloadOut,
    StatValue,
)

# A resource is "at risk" while it is still unrescued (AVAILABLE/MATCHING)
# and its rescue deadline (expiry_time) falls inside this window.
AT_RISK_WINDOW_HOURS = 6
AT_RISK_STATUSES = (ResourceStatus.AVAILABLE, ResourceStatus.MATCHING)

# Operations shown as "active": not yet closed out. DELIVERED is included
# (rather than only PLANNED/IN_TRANSIT) so a just-completed drop-off stays
# visible until it is marked COMPLETED.
ACTIVE_OPERATION_STATUSES = (OperationStatus.PLANNED, OperationStatus.IN_TRANSIT, OperationStatus.DELIVERED)
# Subset that counts towards the "Active Rescues" headline number.
IN_FLIGHT_OPERATION_STATUSES = (OperationStatus.PLANNED, OperationStatus.IN_TRANSIT)

# Allocation states that no longer count towards a recipient's share.
_INACTIVE_ALLOCATION_STATUSES = (AllocationStatus.CANCELLED, AllocationStatus.REALLOCATED)


# --------------------------------------------------------------------------
# Formatting helpers
# --------------------------------------------------------------------------


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _aware(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _quantity_text(quantity, unit: str | None) -> str:
    return f"{float(quantity):g} {unit or 'units'}".strip()


def _hours_minutes(delta: timedelta) -> str:
    total_minutes = max(int(delta.total_seconds() // 60), 0)
    hours, minutes = divmod(total_minutes, 60)
    if hours and minutes:
        return f"{hours} hr {minutes:02d} min"
    if hours:
        return f"{hours} hr"
    return f"{minutes} min"


def _countdown_text(deadline: datetime, now: datetime) -> str:
    remaining = _aware(deadline) - now
    if remaining.total_seconds() <= 0:
        return "Overdue"
    return f"{_hours_minutes(remaining)} remaining"


def _ago_text(when: datetime, now: datetime) -> str:
    elapsed = now - _aware(when)
    if elapsed.total_seconds() < 60:
        return "just now"
    if elapsed < timedelta(days=1):
        return f"{_hours_minutes(elapsed)} ago"
    return f"{elapsed.days} d ago"


def _display_name(user: User | None) -> str:
    if user is None:
        return "Unknown provider"
    return user.organization_name or user.full_name


def _resource_type(resource: Resource) -> str:
    return resource.resource_type.value.lower()


def _resource_status(status: ResourceStatus) -> str:
    """ResourceStatus -> the frontend's lowercase STATUS vocabulary."""
    return {
        ResourceStatus.AVAILABLE: "pending",
        ResourceStatus.MATCHING: "matching",
        ResourceStatus.ALLOCATED: "matched",
        ResourceStatus.IN_TRANSIT: "in_transit",
        ResourceStatus.DELIVERED: "delivered",
        ResourceStatus.EXPIRED: "expired",
        ResourceStatus.CANCELLED: "cancelled",
    }[status]


def _operation_status(operation: RescueOperation) -> str:
    """OperationStatus -> the frontend's lowercase STATUS vocabulary."""
    if operation.status == OperationStatus.PLANNED:
        return "partner_assigned" if operation.partner_id else "matched"
    return {
        OperationStatus.IN_TRANSIT: "in_transit",
        OperationStatus.DELIVERED: "delivered",
        OperationStatus.COMPLETED: "delivered",
        OperationStatus.FAILED: "failed",
    }[operation.status]


def _eta_text(operation: RescueOperation) -> str:
    # There is no ETA column on RescueOperation, so the dashboard shows the
    # lifecycle state instead of an invented time.
    return {
        OperationStatus.PLANNED: "Awaiting pickup",
        OperationStatus.IN_TRANSIT: "In transit",
        OperationStatus.DELIVERED: "Arrived",
        OperationStatus.COMPLETED: "Completed",
        OperationStatus.FAILED: "Failed",
    }[operation.status]


def _recipient_text(operation: RescueOperation) -> str:
    names: list[str] = []
    for allocation in operation.allocations:
        if allocation.status in _INACTIVE_ALLOCATION_STATUSES:
            continue
        if allocation.recipient is not None:
            names.append(allocation.recipient.organization_name)
        elif allocation.rescue_hub is not None:
            names.append(allocation.rescue_hub.name)
    if not names:
        return "Unassigned"
    if len(names) == 1:
        return names[0]
    return f"{names[0]} +{len(names) - 1} more"


def _operation_query(db: Session):
    return db.query(RescueOperation).options(
        joinedload(RescueOperation.rescue_request).joinedload(RescueRequest.resource).joinedload(Resource.provider),
        selectinload(RescueOperation.allocations).joinedload(Allocation.recipient),
        selectinload(RescueOperation.allocations).joinedload(Allocation.rescue_hub),
    )


# --------------------------------------------------------------------------
# GET /api/resources/at-risk
# --------------------------------------------------------------------------


def _at_risk_filters(now: datetime):
    return (
        Resource.status.in_(AT_RISK_STATUSES),
        Resource.expiry_time.isnot(None),
        Resource.expiry_time > now,
        Resource.expiry_time <= now + timedelta(hours=AT_RISK_WINDOW_HOURS),
    )


def _count_at_risk(db: Session, now: datetime) -> int:
    return int(db.query(func.count(Resource.id)).filter(*_at_risk_filters(now)).scalar() or 0)


def get_at_risk_resources(db: Session, limit: int = 10) -> list[AtRiskResourceOut]:
    now = _now()
    resources = (
        db.query(Resource)
        .filter(*_at_risk_filters(now))
        .order_by(Resource.expiry_time.asc())
        .limit(limit)
        .all()
    )
    return [
        AtRiskResourceOut(
            id=str(resource.id),
            resource=resource.title,
            resourceType=_resource_type(resource),
            quantity=_quantity_text(resource.quantity, resource.unit),
            deadline=_countdown_text(resource.expiry_time, now),
            urgency=resource.urgency.value.lower(),
            status=_resource_status(resource.status),
        )
        for resource in resources
    ]


# --------------------------------------------------------------------------
# GET /api/operations/active
# --------------------------------------------------------------------------


def get_active_operations(db: Session, limit: int = 10) -> list[ActiveOperationOut]:
    operations = (
        _operation_query(db)
        .filter(RescueOperation.status.in_(ACTIVE_OPERATION_STATUSES))
        .order_by(RescueOperation.updated_at.desc())
        .limit(limit)
        .all()
    )
    result = []
    for operation in operations:
        resource = operation.rescue_request.resource
        result.append(
            ActiveOperationOut(
                id=str(operation.id),
                resource=resource.title,
                resourceType=_resource_type(resource),
                quantity=_quantity_text(operation.rescue_request.requested_quantity, resource.unit),
                provider=_display_name(resource.provider),
                recipient=_recipient_text(operation),
                status=_operation_status(operation),
                eta=_eta_text(operation),
            )
        )
    return result


# --------------------------------------------------------------------------
# GET /api/dashboard/overview
# --------------------------------------------------------------------------


def get_overview(db: Session) -> DashboardOverviewData:
    now = _now()
    week_ago = now - timedelta(days=7)

    delivered = Allocation.status == AllocationStatus.DELIVERED

    rescued_total = float(
        db.query(func.coalesce(func.sum(Allocation.allocated_quantity), 0)).filter(delivered).scalar() or 0
    )
    # Allocation has no delivered_at column; updated_at is when it last
    # changed, which for a DELIVERED allocation is when it was delivered.
    rescued_this_week = float(
        db.query(func.coalesce(func.sum(Allocation.allocated_quantity), 0))
        .filter(delivered, Allocation.updated_at >= week_ago)
        .scalar()
        or 0
    )

    active_rescues = int(
        db.query(func.count(RescueOperation.id))
        .filter(RescueOperation.status.in_(IN_FLIGHT_OPERATION_STATUSES))
        .scalar()
        or 0
    )
    awaiting_match = int(
        db.query(func.count(RescueRequest.id))
        .filter(RescueRequest.status.in_((RescueRequestStatus.PENDING, RescueRequestStatus.MATCHING)))
        .scalar()
        or 0
    )

    delivered_count = int(db.query(func.count(Allocation.id)).filter(delivered).scalar() or 0)
    cancelled_count = int(
        db.query(func.count(Allocation.id)).filter(Allocation.status == AllocationStatus.CANCELLED).scalar() or 0
    )
    settled = delivered_count + cancelled_count
    success_delta = (
        f"{round(delivered_count / settled * 100)}% success rate" if settled else "No completed allocations yet"
    )

    return DashboardOverviewData(
        resourcesRescued=StatValue(
            value=round(rescued_total, 2),
            # Quantities are stored in mixed units (meals, kg, vials...), so
            # the headline is a plain unit count rather than pretending kg.
            unit="units",
            delta=f"+{rescued_this_week:g} units this week",
            tone="brand",
        ),
        activeRescues=StatValue(value=active_rescues, delta=f"{awaiting_match} awaiting match", tone="active"),
        atRiskResources=StatValue(
            value=_count_at_risk(db, now),
            delta=f"Expiring within {AT_RISK_WINDOW_HOURS} hours",
            tone="urgent",
        ),
        successfulAllocations=StatValue(value=delivered_count, delta=success_delta, tone="success"),
    )


# --------------------------------------------------------------------------
# GET /api/activity/recent
# --------------------------------------------------------------------------


def _event_presentation(event: OperationEvent) -> tuple[str, str, str]:
    """(stage, status, title) for an operation event."""
    if event.event_type == OperationEventType.REALLOCATED:
        return "reallocating", "reallocating", "Reallocated"
    if event.event_type == OperationEventType.STATUS_CHANGED:
        target = (event.event_metadata or {}).get("to")
        return {
            OperationStatus.IN_TRANSIT.value: ("pickup", "in_transit", "Pickup started"),
            OperationStatus.DELIVERED.value: ("delivered", "delivered", "Resource delivered"),
            OperationStatus.COMPLETED.value: ("completed", "delivered", "Operation completed"),
            OperationStatus.FAILED.value: ("completed", "failed", "Operation failed"),
            OperationStatus.PLANNED.value: ("assigned", "matched", "Operation planned"),
        }.get(target, ("assigned", "pending", "Operation updated"))
    if event.event_type == OperationEventType.CREATED:
        return "matched", "matched", "Operation created"
    return "assigned", "pending", "Note added"


def get_recent_activity(db: Session, limit: int = 10) -> list[ActivityEventOut]:
    now = _now()
    feed: list[tuple[datetime, ActivityEventOut]] = []

    events = (
        db.query(OperationEvent)
        .options(
            joinedload(OperationEvent.operation)
            .joinedload(RescueOperation.rescue_request)
            .joinedload(RescueRequest.resource)
            .joinedload(Resource.provider),
            joinedload(OperationEvent.operation)
            .selectinload(RescueOperation.allocations)
            .joinedload(Allocation.recipient),
            joinedload(OperationEvent.operation)
            .selectinload(RescueOperation.allocations)
            .joinedload(Allocation.rescue_hub),
        )
        .order_by(OperationEvent.created_at.desc())
        .limit(limit)
        .all()
    )
    for event in events:
        operation = event.operation
        resource = operation.rescue_request.resource
        stage, status, title = _event_presentation(event)
        description = f"{resource.title}: {_display_name(resource.provider)} \u2192 {_recipient_text(operation)}"
        if operation.status == OperationStatus.FAILED and operation.failure_reason:
            description += f" ({operation.failure_reason})"
        feed.append(
            (
                _aware(event.created_at),
                ActivityEventOut(
                    id=f"event-{event.id}",
                    stage=stage,
                    status=status,
                    title=title,
                    description=description,
                    time=_ago_text(event.created_at, now),
                    timestamp=_aware(event.created_at),
                ),
            )
        )

    recent_resources = (
        db.query(Resource)
        .options(joinedload(Resource.provider))
        .order_by(Resource.created_at.desc())
        .limit(limit)
        .all()
    )
    for resource in recent_resources:
        feed.append(
            (
                _aware(resource.created_at),
                ActivityEventOut(
                    id=f"resource-{resource.id}",
                    stage="created",
                    status="created",
                    title="Resource created",
                    description=f"{resource.title} logged by {_display_name(resource.provider)}",
                    time=_ago_text(resource.created_at, now),
                    timestamp=_aware(resource.created_at),
                ),
            )
        )

    feed.sort(key=lambda item: item[0], reverse=True)
    return [entry for _, entry in feed[:limit]]


# --------------------------------------------------------------------------
# GET /api/network/locations
# --------------------------------------------------------------------------


def get_network_locations(db: Session) -> list[NetworkLocationOut]:
    """
    Every active provider, recipient, rescue partner and hub that has
    coordinates. Rows without a latitude/longitude are skipped — they can't
    be placed on the map.
    """
    locations: list[NetworkLocationOut] = []

    providers = (
        db.query(User)
        .filter(
            User.role == UserRole.PROVIDER,
            User.is_active.is_(True),
            User.latitude.isnot(None),
            User.longitude.isnot(None),
        )
        .all()
    )
    for user in providers:
        locations.append(
            NetworkLocationOut(
                id=f"provider-{user.id}", role="provider", name=_display_name(user), lat=user.latitude, lng=user.longitude
            )
        )

    recipients = db.query(Recipient).filter(Recipient.latitude.isnot(None), Recipient.longitude.isnot(None)).all()
    for recipient in recipients:
        locations.append(
            NetworkLocationOut(
                id=f"recipient-{recipient.id}",
                role="recipient",
                name=recipient.organization_name,
                lat=recipient.latitude,
                lng=recipient.longitude,
            )
        )

    partners = (
        db.query(RescuePartner)
        .options(joinedload(RescuePartner.user))
        .filter(RescuePartner.latitude.isnot(None), RescuePartner.longitude.isnot(None))
        .all()
    )
    for partner in partners:
        locations.append(
            NetworkLocationOut(
                id=f"partner-{partner.id}",
                role="partner",
                name=partner.organization_name or _display_name(partner.user),
                lat=partner.latitude,
                lng=partner.longitude,
            )
        )

    hubs = (
        db.query(RescueHub)
        .filter(RescueHub.is_active.is_(True), RescueHub.latitude.isnot(None), RescueHub.longitude.isnot(None))
        .all()
    )
    for hub in hubs:
        locations.append(
            NetworkLocationOut(id=f"hub-{hub.id}", role="hub", name=hub.name, lat=hub.latitude, lng=hub.longitude)
        )

    return locations


# --------------------------------------------------------------------------
# GET /api/network/organizations
# --------------------------------------------------------------------------

# Load level (held / capacity) at which a hub is shown as "limited".
_HUB_LIMITED_LOAD_RATIO = 0.8


def _split_address(address: str | None) -> tuple[str, str]:
    """
    "Grand Plaza Hotel, MG Road, Bengaluru" -> ("MG Road", "Bengaluru").
    Addresses are free text, so this is best-effort: the last comma-separated
    part is the city and the one before it is the area (empty if there is none).
    """
    parts = [part.strip() for part in (address or "").split(",") if part.strip()]
    if not parts:
        return "", ""
    if len(parts) == 1:
        return "", parts[0]
    return parts[-2], parts[-1]


def _resource_types(accepts_food: bool, accepts_medical: bool) -> list[str]:
    types = []
    if accepts_food:
        types.append("food")
    if accepts_medical:
        types.append("medical")
    return types


def _verification(is_verified: bool) -> str:
    return "verified" if is_verified else "pending"


def get_network_organizations(db: Session) -> list[NetworkOrganizationOut]:
    """
    The Network Directory: recipients (NGOs / shelters / community and medical
    orgs), rescue partners and rescue hubs, in one list. Rows without
    coordinates are skipped because the directory shows every organization on
    a map. Capacity units are not stored, so they are generic ("units").
    """
    organizations: list[NetworkOrganizationOut] = []

    recipients = (
        db.query(Recipient)
        .filter(Recipient.latitude.isnot(None), Recipient.longitude.isnot(None))
        .order_by(Recipient.organization_name)
        .all()
    )
    for recipient in recipients:
        area, city = _split_address(recipient.location_address)
        org_type = "shelter" if recipient.recipient_type == RecipientType.SHELTER else "ngo"
        organizations.append(
            NetworkOrganizationOut(
                id=f"recipient-{recipient.id}",
                name=recipient.organization_name,
                type=org_type,
                area=area,
                city=city,
                position=LatLngOut(lat=recipient.latitude, lng=recipient.longitude),
                description=f"Hours: {recipient.operating_hours}" if recipient.operating_hours else "",
                resourceTypes=_resource_types(recipient.accepts_food, recipient.accepts_medical),
                capacity=(
                    OrgCapacityOut(value=recipient.capacity, unit="units", label="Intake capacity")
                    if recipient.capacity
                    else None
                ),
                availability="available" if recipient.current_availability else "unavailable",
                workload=None,
                verification=_verification(recipient.is_verified),
            )
        )

    partners = (
        db.query(RescuePartner)
        .options(joinedload(RescuePartner.user))
        .filter(RescuePartner.latitude.isnot(None), RescuePartner.longitude.isnot(None))
        .all()
    )
    for partner in partners:
        area, city = _split_address(partner.location_address)
        organizations.append(
            NetworkOrganizationOut(
                id=f"partner-{partner.id}",
                name=partner.organization_name or _display_name(partner.user),
                type="partner",
                area=area,
                city=city,
                position=LatLngOut(lat=partner.latitude, lng=partner.longitude),
                description=(
                    f"{partner.vehicle_type.capitalize()} — " if partner.vehicle_type else ""
                )
                + ("Volunteer" if partner.partner_type == PartnerType.VOLUNTEER else "Transport partner"),
                resourceTypes=_resource_types(partner.accepts_food, partner.accepts_medical),
                capacity=(
                    OrgCapacityOut(value=partner.capacity, unit="units/run", label="Load per run")
                    if partner.capacity
                    else None
                ),
                availability="available" if partner.is_available else "unavailable",
                workload=None,
                verification=_verification(partner.is_verified),
            )
        )

    hubs = (
        db.query(RescueHub)
        .filter(RescueHub.is_active.is_(True), RescueHub.latitude.isnot(None), RescueHub.longitude.isnot(None))
        .order_by(RescueHub.name)
        .all()
    )
    for hub in hubs:
        area, city = _split_address(hub.location_address)
        full = bool(hub.capacity) and hub.current_load >= hub.capacity
        limited = bool(hub.capacity) and hub.current_load >= hub.capacity * _HUB_LIMITED_LOAD_RATIO
        organizations.append(
            NetworkOrganizationOut(
                id=f"hub-{hub.id}",
                name=hub.name,
                type="hub",
                area=area,
                city=city,
                position=LatLngOut(lat=hub.latitude, lng=hub.longitude),
                description="Open 24 hours." if hub.is_24_hour else (hub.operating_hours or ""),
                resourceTypes=_resource_types(hub.accepts_food, hub.accepts_medical),
                capacity=(
                    OrgCapacityOut(value=hub.capacity, unit="units", label="Holding capacity")
                    if hub.capacity
                    else None
                ),
                availability="unavailable" if full else ("limited" if limited else "available"),
                workload=(
                    OrgWorkloadOut(active=hub.current_load, max=hub.capacity, label="Currently held")
                    if hub.capacity
                    else None
                ),
                verification=None,
            )
        )

    return organizations

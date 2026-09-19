"""
Seeds the database with clearly-labeled demo data for the ReServe final
demo: sample providers/resources, recipients, rescue partners, a rescue
hub, and rescue operations in a range of states — including the canonical
"80-meal rescue" scenario referenced in app/models/allocation.py
(80 meals -> NGO A: 50, Shelter B: 20, Rescue Hub: 10, one truck run).

Usage (from the project root, i.e. the folder containing requirements.txt,
after `alembic upgrade head`):

    python3 scripts/seed_demo_data.py

Safe to re-run: every run first deletes any previously-seeded demo data
(identified by the @demo.reserve.local email domain and the "[DEMO]" name
prefix — see "Demo labeling" below) and recreates it from scratch, so the
database never accumulates duplicate demo rows across repeated runs. It
never touches non-demo data.

Demo labeling
-------------
Nothing in the current schema has an `is_demo` flag, so demo data is made
unambiguous by convention instead (deliberately not a schema change, to
keep this a pure data-seeding script):
  - Every demo user's email ends in "@demo.reserve.local".
  - Every demo organization/resource/hub name is prefixed "[DEMO]".
All demo accounts share one password (see DEMO_PASSWORD below), printed
in the summary at the end for whoever is running the demo.
"""

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Running this file directly only puts scripts/ on sys.path, not the
# project root — so `import app` fails no matter what directory you
# launched it from. Add the project root explicitly so the import always
# works (same fix as scripts/verify_tables.py).
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import inspect  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

# Import the models package (not just the individual submodules below) so
# every ORM model is registered on Base.metadata before any relationship
# gets resolved — same convention app/models/__init__.py asks for.
import app.models  # noqa: E402,F401
from app.core.security import hash_password  # noqa: E402
from app.db.database import SessionLocal, engine  # noqa: E402
from app.models.allocation import Allocation  # noqa: E402
from app.models.enums import (  # noqa: E402
    AllocationStatus,
    FoodCategory,
    MatchCandidateType,
    MatchStatus,
    NotificationType,
    OperationEventType,
    OperationStatus,
    PartnerType,
    RecipientType,
    ResourceRequestStatus,
    ResourceStatus,
    ResourceType,
    RescueRequestStatus,
    StorageRequirement,
    UrgencyLevel,
    UserRole,
)
from app.models.match import Match  # noqa: E402
from app.models.notification import Notification  # noqa: E402
from app.models.operation import OperationEvent, RescueOperation  # noqa: E402
from app.models.recipient import Recipient  # noqa: E402
from app.models.resource import Resource  # noqa: E402
from app.models.resource_request import ResourceRequest, ResourceRequestStatusHistory  # noqa: E402
from app.models.rescue_hub import RescueHub  # noqa: E402
from app.models.rescue_partner import RescuePartner  # noqa: E402
from app.models.rescue_request import RescueRequest  # noqa: E402
from app.models.user import User  # noqa: E402

# --- Demo labeling conventions (see module docstring) ----------------------
DEMO_EMAIL_DOMAIN = "demo.reserve.local"
DEMO_TAG = "[DEMO]"
DEMO_PASSWORD = "ReserveDemo2026!"

# All timestamps are anchored to "now" so the seeded scenarios always look
# current/recent no matter when the demo is actually run.
NOW = datetime.now(timezone.utc)


def _demo_email(local_part: str) -> str:
    return f"{local_part}@{DEMO_EMAIL_DOMAIN}"


def _tag(name: str) -> str:
    return f"{DEMO_TAG} {name}"


# --- Cleanup -----------------------------------------------------------


def wipe_demo_data(db: Session) -> None:
    """
    Deletes all previously-seeded demo data so this script is safe to
    re-run. Deleting a demo User cascades (ondelete=CASCADE / relationship
    cascade="all, delete-orphan") to their resources, recipient/partner
    profile, notifications, and — transitively — every rescue_request,
    match, allocation, and rescue_operation hanging off those resources.
    RescueHub rows aren't owned by a User, so they're deleted separately
    by their "[DEMO]" name prefix.
    """
    hub_count = db.query(RescueHub).filter(RescueHub.name.like(f"{DEMO_TAG}%")).delete(
        synchronize_session=False
    )
    user_count = (
        db.query(User).filter(User.email.like(f"%@{DEMO_EMAIL_DOMAIN}")).delete(synchronize_session=False)
    )
    db.commit()
    if hub_count or user_count:
        print(f"Cleared previous demo data ({user_count} user(s), {hub_count} rescue hub(s)).")


# --- Users / profiles ----------------------------------------------------


def make_user(db: Session, *, local_part: str, role: UserRole, full_name: str, **extra) -> User:
    user = User(
        email=_demo_email(local_part),
        hashed_password=hash_password(DEMO_PASSWORD),
        full_name=full_name,
        role=role,
        is_active=True,
        **extra,
    )
    db.add(user)
    db.flush()
    return user


def make_recipient(db: Session, user: User, *, organization_name: str, **extra) -> Recipient:
    recipient = Recipient(
        user_id=user.id,
        organization_name=_tag(organization_name),
        **extra,
    )
    db.add(recipient)
    db.flush()
    return recipient


def make_partner(db: Session, user: User, *, organization_name: str | None, **extra) -> RescuePartner:
    partner = RescuePartner(
        user_id=user.id,
        organization_name=_tag(organization_name) if organization_name else None,
        **extra,
    )
    db.add(partner)
    db.flush()
    return partner


# --- Core scenario builders ------------------------------------------------


def make_resource(db: Session, provider: User, *, title: str, **extra) -> Resource:
    resource = Resource(provider_id=provider.id, title=_tag(title), **extra)
    db.add(resource)
    db.flush()
    return resource


def make_rescue_request(db: Session, resource: Resource, **extra) -> RescueRequest:
    rr = RescueRequest(resource_id=resource.id, **extra)
    db.add(rr)
    db.flush()
    return rr


def make_match(db: Session, rescue_request: RescueRequest, **extra) -> Match:
    match = Match(rescue_request_id=rescue_request.id, **extra)
    db.add(match)
    db.flush()
    return match


def make_allocation(db: Session, rescue_request: RescueRequest, **extra) -> Allocation:
    allocation = Allocation(rescue_request_id=rescue_request.id, **extra)
    db.add(allocation)
    db.flush()
    return allocation


def make_operation(db: Session, rescue_request: RescueRequest, **extra) -> RescueOperation:
    operation = RescueOperation(rescue_request_id=rescue_request.id, **extra)
    db.add(operation)
    db.flush()
    return operation


def add_event(
    db: Session, operation: RescueOperation, *, event_type: OperationEventType, description: str, **extra
) -> OperationEvent:
    event = OperationEvent(operation_id=operation.id, event_type=event_type, description=description, **extra)
    db.add(event)
    db.flush()
    return event


def make_notification(db: Session, user: User, **extra) -> Notification:
    notification = Notification(user_id=user.id, **extra)
    db.add(notification)
    db.flush()
    return notification


# --- Seeding ---------------------------------------------------------------


def seed(db: Session) -> dict:
    # --- Users --------------------------------------------------------
    admin = make_user(db, local_part="admin", role=UserRole.ADMIN, full_name="Demo Admin")

    hotel = make_user(
        db,
        local_part="provider.hotel",
        role=UserRole.PROVIDER,
        full_name="Asha Rao",
        organization_name=_tag("Grand Plaza Hotel"),
        address="MG Road, Bengaluru",
        latitude=12.9716,
        longitude=77.5946,
    )
    restaurant = make_user(
        db,
        local_part="provider.restaurant",
        role=UserRole.PROVIDER,
        full_name="Karthik Iyer",
        organization_name=_tag("Spice Garden Restaurant"),
        address="Indiranagar, Bengaluru",
        latitude=12.9784,
        longitude=77.6408,
    )
    pharmacy = make_user(
        db,
        local_part="provider.pharmacy",
        role=UserRole.PROVIDER,
        full_name="Dr. Meena Nair",
        organization_name=_tag("CareWell Pharmacy"),
        address="Jayanagar, Bengaluru",
        latitude=12.9308,
        longitude=77.5838,
    )

    ngo_a_user = make_user(
        db,
        local_part="recipient.ngo-a",
        role=UserRole.RECIPIENT,
        full_name="Farah Sheikh",
        organization_name=_tag("Hope Community Kitchen"),
    )
    shelter_b_user = make_user(
        db,
        local_part="recipient.shelter-b",
        role=UserRole.RECIPIENT,
        full_name="Daniel Thomas",
        organization_name=_tag("Sunrise Night Shelter"),
    )
    medical_recipient_user = make_user(
        db,
        local_part="recipient.medical",
        role=UserRole.RECIPIENT,
        full_name="Dr. Priya Menon",
        organization_name=_tag("Wellness Medical Aid"),
    )

    transport_partner_user = make_user(
        db,
        local_part="partner.transport",
        role=UserRole.RESCUE_PARTNER,
        full_name="Ramesh Kumar",
    )
    volunteer_partner_user = make_user(
        db,
        local_part="partner.volunteer",
        role=UserRole.RESCUE_PARTNER,
        full_name="Sara Fernandes",
    )

    # --- Profiles -------------------------------------------------------
    ngo_a = make_recipient(
        db,
        ngo_a_user,
        organization_name="Hope Community Kitchen",
        recipient_type=RecipientType.NGO,
        accepts_food=True,
        accepts_medical=False,
        capacity=100,
        current_availability=True,
        service_area_km=15,
        is_verified=True,
        location_address="12 Church Street, Bengaluru",
        latitude=12.9754,
        longitude=77.6050,
        contact_phone="+91-9876500001",
        operating_hours="6:00 AM - 10:00 PM daily",
    )
    shelter_b = make_recipient(
        db,
        shelter_b_user,
        organization_name="Sunrise Night Shelter",
        recipient_type=RecipientType.SHELTER,
        accepts_food=True,
        accepts_medical=False,
        capacity=60,
        current_availability=True,
        service_area_km=10,
        is_verified=True,
        location_address="45 Residency Road, Bengaluru",
        latitude=12.9698,
        longitude=77.6083,
        contact_phone="+91-9876500002",
        operating_hours="24 hours",
    )
    medical_recipient = make_recipient(
        db,
        medical_recipient_user,
        organization_name="Wellness Medical Aid",
        recipient_type=RecipientType.MEDICAL_ORG,
        accepts_food=False,
        accepts_medical=True,
        medical_verified=True,
        capacity=500,
        current_availability=True,
        service_area_km=25,
        is_verified=True,
        location_address="8 Hospital Road, Bengaluru",
        latitude=12.9279,
        longitude=77.5875,
        contact_phone="+91-9876500003",
        operating_hours="8:00 AM - 8:00 PM daily",
    )

    transport_partner = make_partner(
        db,
        transport_partner_user,
        organization_name="Swift Rescue Transport",
        partner_type=PartnerType.TRANSPORT_ORG,
        vehicle_type="Refrigerated van",
        capacity=150,
        is_available=True,
        accepts_food=True,
        accepts_medical=True,
        contact_phone="+91-9876500004",
        location_address="Central Depot, Bengaluru",
        latitude=12.9611,
        longitude=77.6387,
        service_radius_km=30,
        operating_hours="6:00 PM - 6:00 AM",
        is_verified=True,
        rating=4.8,
    )
    volunteer_partner = make_partner(
        db,
        volunteer_partner_user,
        organization_name=None,
        partner_type=PartnerType.VOLUNTEER,
        vehicle_type="Bike",
        capacity=20,
        is_available=True,
        accepts_food=True,
        accepts_medical=True,
        contact_phone="+91-9876500005",
        location_address="Jayanagar, Bengaluru",
        latitude=12.9308,
        longitude=77.5838,
        service_radius_km=8,
        is_verified=True,
        rating=4.6,
    )

    night_hub = RescueHub(
        name=_tag("Night Rescue Hub"),
        accepts_food=True,
        accepts_medical=False,
        is_24_hour=True,
        capacity=100,
        current_load=10,
        location_address="5 Hub Road, Bengaluru",
        latitude=12.9550,
        longitude=77.6200,
        is_active=True,
        operating_hours="24 hours",
        managed_by_user_id=admin.id,
    )
    db.add(night_hub)
    db.flush()

    # =====================================================================
    # Scenario 1 — the flagship "80-meal rescue": one hotel resource split
    # across two recipients and the night rescue hub, fully delivered.
    # This is the exact example referenced in app/models/allocation.py's
    # own docstring: 80 meals -> NGO A: 50, Shelter B: 20, Hub: 10.
    # =====================================================================
    posted_at = NOW - timedelta(hours=5)
    pickup_start = posted_at + timedelta(minutes=30)
    pickup_end = pickup_start + timedelta(minutes=90)  # the "90-minute rescue window"

    banquet_resource = make_resource(
        db,
        hotel,
        title="80 vegetarian banquet meals",
        description="Freshly prepared vegetarian banquet meals left over from a wedding reception.",
        resource_type=ResourceType.FOOD,
        category="vegetarian meals",
        quantity=80,
        unit="meals",
        status=ResourceStatus.DELIVERED,
        urgency=UrgencyLevel.HIGH,
        available_time=posted_at,
        expiry_time=pickup_end,
        pickup_window_start=pickup_start,
        pickup_window_end=pickup_end,
        location_address="Grand Plaza Hotel, MG Road, Bengaluru",
        latitude=12.9716,
        longitude=77.5946,
        is_perishable=True,
        requires_medical_verification=False,
        food_category=FoodCategory.COOKED_MEALS,
        is_vegetarian=True,
        preparation_time=posted_at - timedelta(hours=1),
        allergen_info=["MILK"],
        storage_requirements=StorageRequirement.ROOM_TEMPERATURE,
        packaging_info="Sealed foil trays, individually portioned",
    )

    banquet_request = make_rescue_request(
        db,
        banquet_resource,
        status=RescueRequestStatus.MATCHED,
        requested_quantity=80,
        urgency=UrgencyLevel.HIGH,
        deadline=pickup_end,
        notes="Full 80-meal batch — split across two recipients plus the night hub.",
    )

    match_ngo_a = make_match(
        db,
        banquet_request,
        candidate_type=MatchCandidateType.RECIPIENT,
        recipient_id=ngo_a.id,
        distance_km=3.2,
        score=0.93,
        status=MatchStatus.SELECTED,
        reasons={
            "breakdown": {"distance_score": 0.9, "capacity_fit": 1.0, "urgency_weight": 0.8},
            "passed": ["within_service_area", "accepts_food", "capacity_available", "verified"],
            "failed": [],
            "explanation": "Closest verified food recipient with capacity for the full request.",
        },
    )
    match_shelter_b = make_match(
        db,
        banquet_request,
        candidate_type=MatchCandidateType.RECIPIENT,
        recipient_id=shelter_b.id,
        distance_km=4.5,
        score=0.85,
        status=MatchStatus.SELECTED,
        reasons={
            "breakdown": {"distance_score": 0.8, "capacity_fit": 0.9, "urgency_weight": 0.8},
            "passed": ["within_service_area", "accepts_food", "capacity_available", "verified"],
            "failed": [],
            "explanation": "Second recipient brought in to absorb remaining quantity after NGO A's capacity.",
        },
    )
    match_hub = make_match(
        db,
        banquet_request,
        candidate_type=MatchCandidateType.RESCUE_HUB,
        rescue_hub_id=night_hub.id,
        distance_km=6.1,
        score=0.70,
        status=MatchStatus.SELECTED,
        reasons={
            "breakdown": {"distance_score": 0.65, "capacity_fit": 1.0, "urgency_weight": 0.8},
            "passed": ["24_hour", "accepts_food", "capacity_available"],
            "failed": [],
            "explanation": "Night hub absorbs the final 10 meals outside normal recipient hours.",
        },
    )
    # An auditable rejected candidate, to show the engine's reasoning isn't
    # just "which ones won" — a medical-only recipient was considered and
    # correctly excluded because it doesn't accept food.
    make_match(
        db,
        banquet_request,
        candidate_type=MatchCandidateType.RECIPIENT,
        recipient_id=medical_recipient.id,
        distance_km=8.4,
        score=0.10,
        status=MatchStatus.REJECTED,
        reasons={
            "breakdown": {"distance_score": 0.4, "capacity_fit": 0.0, "urgency_weight": 0.8},
            "passed": [],
            "failed": ["accepts_food"],
            "explanation": "Recipient only accepts MEDICAL resources.",
        },
    )

    banquet_operation = make_operation(
        db,
        banquet_request,
        partner_id=transport_partner.id,
        status=OperationStatus.COMPLETED,
        pickup_started_at=pickup_start,
        delivered_at=pickup_start + timedelta(minutes=45),
        completed_at=pickup_start + timedelta(minutes=60),
    )

    make_allocation(
        db,
        banquet_request,
        operation_id=banquet_operation.id,
        match_id=match_ngo_a.id,
        recipient_id=ngo_a.id,
        allocated_quantity=50,
        status=AllocationStatus.DELIVERED,
        reason="Closest verified recipient within capacity for the full request.",
    )
    make_allocation(
        db,
        banquet_request,
        operation_id=banquet_operation.id,
        match_id=match_shelter_b.id,
        recipient_id=shelter_b.id,
        allocated_quantity=20,
        status=AllocationStatus.DELIVERED,
        reason="Second recipient for remaining quantity after NGO A's capacity was reached.",
    )
    make_allocation(
        db,
        banquet_request,
        operation_id=banquet_operation.id,
        match_id=match_hub.id,
        rescue_hub_id=night_hub.id,
        allocated_quantity=10,
        status=AllocationStatus.DELIVERED,
        reason="Remaining meals routed to the 24-hour night hub within the pickup window.",
    )

    add_event(
        db,
        banquet_operation,
        event_type=OperationEventType.CREATED,
        description="Rescue operation created for the 80-meal banquet surplus.",
        created_by_user_id=admin.id,
        created_at=pickup_start - timedelta(minutes=10),
    )
    add_event(
        db,
        banquet_operation,
        event_type=OperationEventType.STATUS_CHANGED,
        description="Partner picked up all three allocations in one run.",
        event_metadata={"from": "PLANNED", "to": "IN_TRANSIT"},
        created_by_user_id=transport_partner_user.id,
        created_at=pickup_start,
    )
    add_event(
        db,
        banquet_operation,
        event_type=OperationEventType.STATUS_CHANGED,
        description="All three drop-offs (NGO A, Shelter B, Night Hub) completed.",
        event_metadata={"from": "IN_TRANSIT", "to": "DELIVERED"},
        created_by_user_id=transport_partner_user.id,
        created_at=pickup_start + timedelta(minutes=45),
    )
    add_event(
        db,
        banquet_operation,
        event_type=OperationEventType.STATUS_CHANGED,
        description="Operation closed out after delivery confirmation.",
        event_metadata={"from": "DELIVERED", "to": "COMPLETED"},
        created_by_user_id=admin.id,
        created_at=pickup_start + timedelta(minutes=60),
    )

    make_notification(
        db,
        hotel,
        notification_type=NotificationType.MATCH_FOUND,
        title="Your 80-meal donation was matched",
        message="Hope Community Kitchen, Sunrise Night Shelter, and the Night Rescue Hub will receive your meals.",
        is_read=True,
        related_operation_id=banquet_operation.id,
    )
    make_notification(
        db,
        ngo_a_user,
        notification_type=NotificationType.DELIVERY_CONFIRMED,
        title="Delivery confirmed: 50 meals",
        message="50 vegetarian meals from Grand Plaza Hotel have been delivered to Hope Community Kitchen.",
        is_read=True,
        related_operation_id=banquet_operation.id,
    )
    make_notification(
        db,
        shelter_b_user,
        notification_type=NotificationType.DELIVERY_CONFIRMED,
        title="Delivery confirmed: 20 meals",
        message="20 vegetarian meals from Grand Plaza Hotel have been delivered to Sunrise Night Shelter.",
        is_read=False,
        related_operation_id=banquet_operation.id,
    )

    # =====================================================================
    # Scenario 2 — still AVAILABLE and unmatched, for demoing the live
    # matching flow (POST /api/matching) during the demo itself.
    # =====================================================================
    veg_available_at = NOW - timedelta(minutes=20)
    make_resource(
        db,
        restaurant,
        title="40 kg fresh vegetables — daily surplus",
        description="Unsold fresh produce from today's service, still well within date.",
        resource_type=ResourceType.FOOD,
        category="raw produce",
        quantity=40,
        unit="kg",
        status=ResourceStatus.AVAILABLE,
        urgency=UrgencyLevel.MEDIUM,
        available_time=veg_available_at,
        expiry_time=veg_available_at + timedelta(hours=6),
        pickup_window_start=veg_available_at + timedelta(minutes=15),
        pickup_window_end=veg_available_at + timedelta(hours=3),
        location_address="Spice Garden Restaurant, Indiranagar, Bengaluru",
        latitude=12.9784,
        longitude=77.6408,
        is_perishable=True,
        food_category=FoodCategory.RAW_PRODUCE,
        is_vegetarian=True,
        allergen_info=["NONE"],
        storage_requirements=StorageRequirement.REFRIGERATED,
        packaging_info="Crated, unwashed",
    )

    # =====================================================================
    # Scenario 3 — a MEDICAL resource mid-delivery (IN_TRANSIT), to
    # demonstrate the medical-verification path and a live operation.
    # =====================================================================
    med_posted_at = NOW - timedelta(hours=1)
    med_resource = make_resource(
        db,
        pharmacy,
        title="200 units amoxicillin 500mg — near expiry",
        description="Unopened, in-date stock the pharmacy can no longer sell before expiry.",
        resource_type=ResourceType.MEDICAL,
        category="antibiotics",
        quantity=200,
        unit="units",
        status=ResourceStatus.IN_TRANSIT,
        urgency=UrgencyLevel.CRITICAL,
        available_time=med_posted_at,
        expiry_time=med_posted_at + timedelta(days=30),
        pickup_window_start=med_posted_at,
        pickup_window_end=med_posted_at + timedelta(hours=2),
        location_address="CareWell Pharmacy, Jayanagar, Bengaluru",
        latitude=12.9308,
        longitude=77.5838,
        is_perishable=False,
        requires_medical_verification=True,
    )
    med_request = make_rescue_request(
        db,
        med_resource,
        status=RescueRequestStatus.MATCHED,
        requested_quantity=200,
        urgency=UrgencyLevel.CRITICAL,
        deadline=med_posted_at + timedelta(hours=2),
    )
    med_match = make_match(
        db,
        med_request,
        candidate_type=MatchCandidateType.RECIPIENT,
        recipient_id=medical_recipient.id,
        distance_km=2.0,
        score=0.97,
        status=MatchStatus.SELECTED,
        reasons={
            "breakdown": {"distance_score": 0.95, "capacity_fit": 1.0, "urgency_weight": 1.0},
            "passed": ["accepts_medical", "medical_verified", "capacity_available"],
            "failed": [],
            "explanation": "Only nearby medically-verified recipient with capacity.",
        },
    )
    med_operation = make_operation(
        db,
        med_request,
        partner_id=volunteer_partner.id,
        status=OperationStatus.IN_TRANSIT,
        pickup_started_at=med_posted_at + timedelta(minutes=30),
    )
    make_allocation(
        db,
        med_request,
        operation_id=med_operation.id,
        match_id=med_match.id,
        recipient_id=medical_recipient.id,
        allocated_quantity=200,
        status=AllocationStatus.CONFIRMED,
        reason="Only nearby medically-verified recipient with capacity.",
    )
    add_event(
        db,
        med_operation,
        event_type=OperationEventType.CREATED,
        description="Rescue operation created for near-expiry medical stock.",
        created_by_user_id=admin.id,
        created_at=med_posted_at + timedelta(minutes=25),
    )
    add_event(
        db,
        med_operation,
        event_type=OperationEventType.STATUS_CHANGED,
        description="Volunteer picked up the medical stock for delivery.",
        event_metadata={"from": "PLANNED", "to": "IN_TRANSIT"},
        created_by_user_id=volunteer_partner_user.id,
        created_at=med_posted_at + timedelta(minutes=30),
    )
    make_notification(
        db,
        pharmacy,
        notification_type=NotificationType.PARTNER_ASSIGNED,
        title="Rescue partner assigned",
        message="Sara Fernandes is en route to collect your medical donation.",
        is_read=False,
        related_operation_id=med_operation.id,
    )

    # =====================================================================
    # Scenario 4 — an EXPIRED resource, to show the "missed rescue" path.
    # =====================================================================
    expired_posted_at = NOW - timedelta(days=1)
    make_resource(
        db,
        hotel,
        title="15 trays bakery items — unclaimed",
        description="Bakery surplus that went unclaimed within its pickup window.",
        resource_type=ResourceType.FOOD,
        category="bakery items",
        quantity=15,
        unit="trays",
        status=ResourceStatus.EXPIRED,
        urgency=UrgencyLevel.LOW,
        available_time=expired_posted_at,
        expiry_time=expired_posted_at + timedelta(hours=4),
        pickup_window_start=expired_posted_at + timedelta(hours=1),
        pickup_window_end=expired_posted_at + timedelta(hours=3),
        location_address="Grand Plaza Hotel, MG Road, Bengaluru",
        latitude=12.9716,
        longitude=77.5946,
        is_perishable=True,
        food_category=FoodCategory.BAKERY,
        is_vegetarian=True,
        allergen_info=["WHEAT_GLUTEN", "EGGS", "MILK"],
        storage_requirements=StorageRequirement.ROOM_TEMPERATURE,
    )

    # =====================================================================
    # Demand-side ResourceRequests — independent of the matching engine
    # (see app/models/resource_request.py), showing the recipient-initiated
    # request/review flow.
    # =====================================================================
    pending_request = ResourceRequest(
        recipient_id=ngo_a.id,
        resource_type=ResourceType.FOOD,
        requested_quantity=60,
        requesting_organization=ngo_a.organization_name,
        urgency=UrgencyLevel.MEDIUM,
        needed_by=NOW + timedelta(days=2),
        eligibility_requirements="Registered NGO serving daily meals to 100+ residents.",
        can_self_pickup=True,
        notes="Ongoing weekly need for our community kitchen.",
        status=ResourceRequestStatus.PENDING,
    )
    db.add(pending_request)
    db.flush()
    db.add(
        ResourceRequestStatusHistory(
            request_id=pending_request.id,
            from_status=None,
            to_status=ResourceRequestStatus.PENDING,
            note="Request submitted.",
            changed_by_user_id=ngo_a_user.id,
        )
    )

    approved_request = ResourceRequest(
        recipient_id=shelter_b.id,
        resource_type=ResourceType.FOOD,
        requested_quantity=30,
        requesting_organization=shelter_b.organization_name,
        urgency=UrgencyLevel.HIGH,
        needed_by=NOW + timedelta(days=1),
        eligibility_requirements="Registered night shelter, cold-weather emergency capacity.",
        can_self_pickup=False,
        notes="Approved ahead of this week's cold-weather intake.",
        status=ResourceRequestStatus.APPROVED,
    )
    db.add(approved_request)
    db.flush()
    db.add(
        ResourceRequestStatusHistory(
            request_id=approved_request.id,
            from_status=None,
            to_status=ResourceRequestStatus.PENDING,
            note="Request submitted.",
            changed_by_user_id=shelter_b_user.id,
        )
    )
    db.add(
        ResourceRequestStatusHistory(
            request_id=approved_request.id,
            from_status=ResourceRequestStatus.PENDING,
            to_status=ResourceRequestStatus.APPROVED,
            note="Approved by provider ahead of a cold-weather intake.",
            changed_by_user_id=hotel.id,
        )
    )

    db.commit()

    return {
        "admin": admin,
        "providers": [hotel, restaurant, pharmacy],
        "recipients": [ngo_a_user, shelter_b_user, medical_recipient_user],
        "partners": [transport_partner_user, volunteer_partner_user],
    }


def print_summary(created: dict) -> None:
    print("\nDemo data seeded successfully.\n")
    print(f"All demo accounts share the password: {DEMO_PASSWORD}\n")
    print(f"{'Role':<16} {'Name':<20} Email")
    print("-" * 70)
    print(f"{'ADMIN':<16} {created['admin'].full_name:<20} {created['admin'].email}")
    for u in created["providers"]:
        print(f"{'PROVIDER':<16} {u.full_name:<20} {u.email}")
    for u in created["recipients"]:
        print(f"{'RECIPIENT':<16} {u.full_name:<20} {u.email}")
    for u in created["partners"]:
        print(f"{'RESCUE_PARTNER':<16} {u.full_name:<20} {u.email}")
    print(
        "\nFlagship scenario: the 80-meal Grand Plaza Hotel donation, delivered and "
        "split NGO A (50) / Shelter B (20) / Night Rescue Hub (10) — "
        "GET /api/resources?search=80%20vegetarian or /api/operations to see it end-to-end."
    )
    print(
        "Still-open scenario for a live demo: the 40kg vegetable resource from Spice "
        "Garden Restaurant is AVAILABLE and unmatched — trigger POST /api/matching against it."
    )
    print("\nAll demo data is labeled with the \"[DEMO]\" prefix and the "
          f"@{DEMO_EMAIL_DOMAIN} email domain, and can be removed by re-running this script "
          "(it wipes its own previous output first) — it never touches non-demo data.")


def main() -> int:
    inspector = inspect(engine)
    if "users" not in set(inspector.get_table_names()):
        print(
            "The 'users' table doesn't exist yet — run `alembic upgrade head` first "
            "(see scripts/verify_tables.py to check all expected tables)."
        )
        return 1

    db = SessionLocal()
    try:
        wipe_demo_data(db)
        created = seed(db)

        # Print the summary while the database session is still open.
        print_summary(created)

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()

    return 0


if __name__ == "__main__":
    sys.exit(main())

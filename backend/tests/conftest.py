"""
Shared pytest fixtures and helpers for the resource test suite.

Requires a real Postgres test database (the project's models use
Postgres-specific column types, so SQLite is not a supported test
backend here) — point DATABASE_URL at a throwaway database before
running, e.g.:

    export DATABASE_URL=postgresql+psycopg2://postgres:postgres@localhost:5432/reserve_test
    pytest tests/ -v

Each test runs inside a transaction-per-test fixture that creates all
tables at session scope and truncates the relevant tables between tests,
so tests can run in any order without leaking state into each other.
"""

import os
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.core.security import hash_password
from app.db.database import Base, get_db
from app.main import app
from app.models.enums import (
    MatchCandidateType,
    MatchStatus,
    RecipientType,
    ResourceRequestStatus,
    ResourceStatus,
    ResourceType,
    RescueRequestStatus,
    UserRole,
)
from app.models.match import Match
from app.models.recipient import Recipient
from app.models.resource import Resource
from app.models.resource_request import ResourceRequest
from app.models.rescue_request import RescueRequest
from app.models.user import User

DEFAULT_TEST_DATABASE_URL = "postgresql+psycopg2://postgres:postgres@localhost:5432/reserve_test"

# The module docstring above tells you to point DATABASE_URL at a
# throwaway database before running. Honour it — hardcoding the URL here
# meant anyone following those instructions silently ran the suite
# (including its TRUNCATE-between-tests fixture) against whatever
# database happened to be at the default address, not the one they
# asked for.
TEST_DATABASE_URL = os.getenv("DATABASE_URL", DEFAULT_TEST_DATABASE_URL)

engine = create_engine(TEST_DATABASE_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="session", autouse=True)
def _create_tables():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(autouse=True)
def _clean_tables():
    """Truncate everything between tests so each test starts from empty tables."""
    yield
    with engine.begin() as conn:
        conn.execute(
            text(
                "TRUNCATE TABLE notifications, rescue_operations, allocations, matches, "
                "rescue_requests, resource_request_status_history, resource_requests, "
                "resources, recipients, rescue_hubs, users RESTART IDENTITY CASCADE"
            )
        )


@pytest.fixture()
def db():
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def client(db):
    def _override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def make_user(db, role=UserRole.PROVIDER, email=None) -> User:
    user = User(
        email=email or f"{uuid.uuid4()}@example.com",
        hashed_password=hash_password("Password123!"),
        full_name="Test User",
        role=role,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def login_headers(client, email: str) -> dict:
    resp = client.post("/api/auth/login", json={"email": email, "password": "Password123!"})
    assert resp.status_code == 200, resp.text
    token = resp.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


def make_resource(
    db,
    provider: User,
    status: ResourceStatus = ResourceStatus.AVAILABLE,
    resource_type: ResourceType = ResourceType.FOOD,
    **extra,
) -> Resource:
    # Every default below is popped out of **extra rather than passed
    # positionally alongside it. Hardcoding e.g. `quantity=80` and then
    # splatting `**extra` makes `make_resource(db, provider, quantity=200)`
    # raise "got multiple values for keyword argument 'quantity'" before
    # the test body ever runs — and most callers across the suite do
    # override quantity. This matches the `extra.pop(...)` convention the
    # other helpers in this module already use.
    resource = Resource(
        provider_id=provider.id,
        title=extra.pop("title", "80 vegetarian meals"),
        resource_type=resource_type,
        quantity=extra.pop("quantity", 80),
        unit=extra.pop("unit", "meals"),
        status=status,
        location_address=extra.pop("location_address", "Grand Plaza Hotel, MG Road, Bengaluru"),
        **extra,
    )
    db.add(resource)
    db.commit()
    db.refresh(resource)
    return resource


def make_rescue_request(db, resource: Resource, status: RescueRequestStatus) -> RescueRequest:
    rr = RescueRequest(
        resource_id=resource.id,
        status=status,
        requested_quantity=resource.quantity,
    )
    db.add(rr)
    db.commit()
    db.refresh(rr)
    return rr


def make_rescue_hub(db, **extra):
    from app.models.rescue_hub import RescueHub

    hub = RescueHub(
        name=extra.pop("name", "Night Rescue Hub"),
        accepts_food=extra.pop("accepts_food", True),
        accepts_medical=extra.pop("accepts_medical", False),
        location_address=extra.pop("location_address", "5 Hub Road, Bengaluru"),
        **extra,
    )
    db.add(hub)
    db.commit()
    db.refresh(hub)
    return hub


def make_match(
    db,
    rescue_request: RescueRequest,
    recipient=None,
    rescue_hub_id=None,
    candidate_type: MatchCandidateType | None = None,
    status: MatchStatus = MatchStatus.PROPOSED,
    score: float = 0.8,
    distance_km: float = 5.0,
    **extra,
) -> Match:
    if candidate_type is None:
        candidate_type = MatchCandidateType.RESCUE_HUB if rescue_hub_id else MatchCandidateType.RECIPIENT
    match = Match(
        rescue_request_id=rescue_request.id,
        candidate_type=candidate_type,
        recipient_id=recipient.id if recipient is not None else None,
        rescue_hub_id=rescue_hub_id,
        distance_km=distance_km,
        score=score,
        status=status,
        reasons=extra.pop("reasons", {"breakdown": {}, "passed": [], "failed": [], "explanation": "test match"}),
        **extra,
    )
    db.add(match)
    db.commit()
    db.refresh(match)
    return match


def make_recipient(
    db,
    user: User,
    accepts_food: bool = True,
    accepts_medical: bool = False,
    medical_verified: bool = False,
    is_verified: bool = True,
    **extra,
) -> Recipient:
    # `is_verified` (platform verification, distinct from `medical_verified`)
    # defaults to False on real recipient records and is a hard gate in the
    # matching engine (see matching_engine._score_eligibility). Tests default
    # it to True here so each test isolates the one factor it's checking
    # (capacity, availability, distance, etc.) instead of every candidate
    # being rejected for being unverified.
    recipient = Recipient(
        user_id=user.id,
        organization_name=extra.pop("organization_name", "Hope Community Shelter"),
        recipient_type=extra.pop("recipient_type", RecipientType.SHELTER),
        accepts_food=accepts_food,
        accepts_medical=accepts_medical,
        medical_verified=medical_verified,
        is_verified=is_verified,
        location_address=extra.pop("location_address", "12 Church Street, Bengaluru"),
        **extra,
    )
    db.add(recipient)
    db.commit()
    db.refresh(recipient)
    return recipient


def make_resource_request(
    db,
    recipient: Recipient,
    status: ResourceRequestStatus = ResourceRequestStatus.PENDING,
    resource_type: ResourceType = ResourceType.FOOD,
    **extra,
) -> ResourceRequest:
    from datetime import datetime, timedelta, timezone

    request = ResourceRequest(
        recipient_id=recipient.id,
        resource_type=resource_type,
        requested_quantity=extra.pop("requested_quantity", 50),
        requesting_organization=extra.pop("requesting_organization", recipient.organization_name),
        needed_by=extra.pop("needed_by", datetime.now(timezone.utc) + timedelta(days=1)),
        status=status,
        **extra,
    )
    db.add(request)
    db.commit()
    db.refresh(request)
    return request


def make_rescue_partner(
    db,
    user: "User",
    partner_type=None,
    is_available: bool = True,
    accepts_food: bool = True,
    accepts_medical: bool = False,
    is_verified: bool = True,
    **extra,
):
    """A RescuePartner profile for `user` (should have role=RESCUE_PARTNER,
    though this helper doesn't enforce that — same convention as
    make_recipient not enforcing role=RECIPIENT)."""
    from app.models.enums import PartnerType
    from app.models.rescue_partner import RescuePartner

    partner = RescuePartner(
        user_id=user.id,
        organization_name=extra.pop("organization_name", "Swift Rescue Transport"),
        partner_type=partner_type or PartnerType.TRANSPORT_ORG,
        is_available=is_available,
        accepts_food=accepts_food,
        accepts_medical=accepts_medical,
        is_verified=is_verified,
        **extra,
    )
    db.add(partner)
    db.commit()
    db.refresh(partner)
    return partner

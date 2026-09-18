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

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.core.security import hash_password
from app.db.database import Base, get_db
from app.main import app
from app.models.enums import (
    RecipientType,
    ResourceRequestStatus,
    ResourceStatus,
    ResourceType,
    RescueRequestStatus,
    UserRole,
)
from app.models.recipient import Recipient
from app.models.resource import Resource
from app.models.resource_request import ResourceRequest
from app.models.rescue_request import RescueRequest
from app.models.user import User

TEST_DATABASE_URL = "postgresql+psycopg2://postgres:postgres@localhost:5432/reserve_test"

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
                "TRUNCATE TABLE rescue_operations, allocations, matches, "
                "rescue_requests, resource_request_status_history, resource_requests, "
                "resources, recipients, users RESTART IDENTITY CASCADE"
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
    resource = Resource(
        provider_id=provider.id,
        title="80 vegetarian meals",
        resource_type=resource_type,
        quantity=80,
        unit="meals",
        status=status,
        location_address="Grand Plaza Hotel, MG Road, Bengaluru",
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


def make_recipient(
    db,
    user: User,
    accepts_food: bool = True,
    accepts_medical: bool = False,
    medical_verified: bool = False,
    **extra,
) -> Recipient:
    recipient = Recipient(
        user_id=user.id,
        organization_name=extra.pop("organization_name", "Hope Community Shelter"),
        recipient_type=extra.pop("recipient_type", RecipientType.SHELTER),
        accepts_food=accepts_food,
        accepts_medical=accepts_medical,
        medical_verified=medical_verified,
        location_address="12 Church Street, Bengaluru",
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

"""
Integration tests for POST /api/matching/{resource_id}.

Shared fixtures/helpers (db, client, make_user, login_headers,
make_resource, make_recipient) live in tests/conftest.py. Run with:

    export DATABASE_URL=postgresql+psycopg2://postgres:postgres@localhost:5432/reserve_test
    pytest tests/test_matching.py -v
"""

import uuid
from datetime import datetime, timedelta, timezone

from app.models.enums import (
    MatchStatus,
    RecipientType,
    ResourceStatus,
    ResourceType,
    RescueRequestStatus,
    UserRole,
)
from app.models.match import Match
from app.models.resource import Resource
from app.models.rescue_request import RescueRequest

from tests.conftest import login_headers, make_recipient, make_resource, make_user

MG_ROAD = dict(latitude=12.9758, longitude=77.6045)  # resource location used below
CHURCH_STREET = dict(latitude=12.9762, longitude=77.6033)  # near MG Road
MUMBAI = dict(latitude=19.0760, longitude=72.8777)  # ~840km from MG Road


def _candidate_for(candidates, recipient_id):
    return next(c for c in candidates if c["recipient"]["id"] == str(recipient_id))


class TestMatchingPermissionsAndValidation:
    def test_returns_404_for_unknown_resource(self, client, db):
        provider = make_user(db, role=UserRole.PROVIDER)
        headers = login_headers(client, provider.email)

        resp = client.post(f"/api/matching/{uuid.uuid4()}", headers=headers)

        assert resp.status_code == 404
        assert resp.json()["error"]["code"] == "RESOURCE_NOT_FOUND"

    def test_non_owner_provider_cannot_trigger_matching(self, client, db):
        owner = make_user(db, role=UserRole.PROVIDER)
        other = make_user(db, role=UserRole.PROVIDER)
        resource = make_resource(db, owner)
        headers = login_headers(client, other.email)

        resp = client.post(f"/api/matching/{resource.id}", headers=headers)

        assert resp.status_code == 403
        assert resp.json()["error"]["code"] == "NOT_RESOURCE_OWNER"

    def test_admin_can_trigger_matching_for_someone_elses_resource(self, client, db):
        owner = make_user(db, role=UserRole.PROVIDER)
        admin = make_user(db, role=UserRole.ADMIN)
        resource = make_resource(db, owner, **MG_ROAD)
        headers = login_headers(client, admin.email)

        resp = client.post(f"/api/matching/{resource.id}", headers=headers)

        assert resp.status_code == 201, resp.text
        assert resp.json()["success"] is True

    def test_already_delivered_resource_cannot_be_matched(self, client, db):
        provider = make_user(db, role=UserRole.PROVIDER)
        resource = make_resource(db, provider, status=ResourceStatus.DELIVERED)
        headers = login_headers(client, provider.email)

        resp = client.post(f"/api/matching/{resource.id}", headers=headers)

        assert resp.status_code == 409
        assert resp.json()["error"]["code"] == "RESOURCE_NOT_MATCHABLE"

    def test_expired_resource_cannot_be_matched(self, client, db):
        """Validation rule: reject expired resources — enforced up front in
        matching_service._ensure_resource_matchable, before any candidate is
        even considered."""
        provider = make_user(db, role=UserRole.PROVIDER)
        resource = make_resource(
            db, provider, expiry_time=datetime.now(timezone.utc) - timedelta(hours=1), **MG_ROAD
        )
        headers = login_headers(client, provider.email)

        resp = client.post(f"/api/matching/{resource.id}", headers=headers)

        assert resp.status_code == 409
        assert resp.json()["error"]["code"] == "RESOURCE_EXPIRED"

        # Side effect: the resource is flipped to EXPIRED so the data stays
        # consistent for anyone looking at it afterwards.
        db.refresh(resource)
        assert resource.status == ResourceStatus.EXPIRED

    def test_unauthenticated_request_is_rejected(self, client, db):
        provider = make_user(db, role=UserRole.PROVIDER)
        resource = make_resource(db, provider)

        resp = client.post(f"/api/matching/{resource.id}")

        assert resp.status_code == 401


class TestMatchingEngine:
    def test_eligible_recipient_is_returned(self, client, db):
        provider = make_user(db, role=UserRole.PROVIDER)
        resource = make_resource(db, provider, quantity=50, **MG_ROAD)

        recipient_user = make_user(db, role=UserRole.RECIPIENT)
        make_recipient(
            db,
            recipient_user,
            accepts_food=True,
            capacity=100,
            current_availability=True,
            **CHURCH_STREET,
        )
        headers = login_headers(client, provider.email)

        resp = client.post(f"/api/matching/{resource.id}", headers=headers)

        assert resp.status_code == 201, resp.text
        body = resp.json()["data"]
        assert body["resource_id"] == str(resource.id)
        assert len(body["candidates"]) == 1
        candidate = body["candidates"][0]
        assert candidate["recipient"]["organization_name"] == "Hope Community Shelter"
        assert candidate["status"] == "PROPOSED"
        assert 0.0 <= candidate["score"] <= 1.0
        assert candidate["distance_km"] is not None and candidate["distance_km"] < 5
        assert candidate["rejection_reasons"] == []

        # Side effects: resource moved to MATCHING, RescueRequest moved to
        # MATCHED (at least one proposed candidate), and a Match was persisted.
        db.refresh(resource)
        assert resource.status == ResourceStatus.MATCHING
        rr = db.query(RescueRequest).filter(RescueRequest.resource_id == resource.id).first()
        assert rr is not None
        assert rr.status == RescueRequestStatus.MATCHED
        matches = db.query(Match).filter(Match.rescue_request_id == rr.id).all()
        assert len(matches) == 1
        assert matches[0].status == MatchStatus.PROPOSED

    def test_recipient_not_accepting_resource_type_is_excluded(self, client, db):
        """Validation rule: reject incompatible resource types. Filtered out
        of the candidate pool entirely at the query level (matching_service.
        _candidate_recipients), so it never becomes a Match row at all —
        distinct from the other hard gates below, which do persist a
        REJECTED row with reasons."""
        provider = make_user(db, role=UserRole.PROVIDER)
        resource = make_resource(db, provider, resource_type=ResourceType.FOOD, **MG_ROAD)

        recipient_user = make_user(db, role=UserRole.RECIPIENT)
        make_recipient(db, recipient_user, accepts_food=False, **CHURCH_STREET)
        headers = login_headers(client, provider.email)

        resp = client.post(f"/api/matching/{resource.id}", headers=headers)

        assert resp.status_code == 201, resp.text
        assert resp.json()["data"]["candidates"] == []

    def test_medical_resource_requires_medical_verified_recipient(self, client, db):
        provider = make_user(db, role=UserRole.PROVIDER)
        resource = make_resource(db, provider, resource_type=ResourceType.MEDICAL, **MG_ROAD)

        unverified_user = make_user(db, role=UserRole.RECIPIENT, email="unverified@example.com")
        unverified = make_recipient(
            db,
            unverified_user,
            accepts_food=False,
            accepts_medical=True,
            medical_verified=False,
            recipient_type=RecipientType.MEDICAL_ORG,
            **CHURCH_STREET,
        )

        verified_user = make_user(db, role=UserRole.RECIPIENT, email="verified@example.com")
        verified = make_recipient(
            db,
            verified_user,
            accepts_food=False,
            accepts_medical=True,
            medical_verified=True,
            recipient_type=RecipientType.MEDICAL_ORG,
            organization_name="City Free Clinic",
            **CHURCH_STREET,
        )
        headers = login_headers(client, provider.email)

        resp = client.post(f"/api/matching/{resource.id}", headers=headers)

        assert resp.status_code == 201, resp.text
        candidates = resp.json()["data"]["candidates"]
        # Both accept MEDICAL resources so both enter the candidate pool;
        # only the medical-verified one clears the eligibility hard gate.
        assert len(candidates) == 2

        proposed = _candidate_for(candidates, verified.id)
        assert proposed["status"] == "PROPOSED"

        rejected = _candidate_for(candidates, unverified.id)
        assert rejected["status"] == "REJECTED"
        assert rejected["score"] == 0.0
        assert any("medical-verified" in reason for reason in rejected["rejection_reasons"])

    def test_recipient_with_zero_capacity_is_rejected(self, client, db):
        """Validation rule: check recipient capacity — zero (or negative)
        remaining capacity is a hard gate, not just a low score."""
        provider = make_user(db, role=UserRole.PROVIDER)
        resource = make_resource(db, provider, quantity=50, **MG_ROAD)

        recipient_user = make_user(db, role=UserRole.RECIPIENT)
        recipient = make_recipient(db, recipient_user, accepts_food=True, capacity=0, **CHURCH_STREET)
        headers = login_headers(client, provider.email)

        resp = client.post(f"/api/matching/{resource.id}", headers=headers)

        assert resp.status_code == 201, resp.text
        candidates = resp.json()["data"]["candidates"]
        assert len(candidates) == 1
        rejected = _candidate_for(candidates, recipient.id)
        assert rejected["status"] == "REJECTED"
        assert any("capacity" in reason for reason in rejected["rejection_reasons"])

    def test_recipient_with_partial_capacity_is_still_proposed_at_lower_score(self, client, db):
        """A recipient who can only take part of the requested quantity is
        not rejected outright (partial fulfillment is a later allocation
        concern) but does score lower than a full-coverage recipient."""
        provider = make_user(db, role=UserRole.PROVIDER)
        resource = make_resource(db, provider, quantity=200, **MG_ROAD)

        partial_user = make_user(db, role=UserRole.RECIPIENT, email="partial@example.com")
        partial = make_recipient(
            db, partial_user, accepts_food=True, capacity=50, organization_name="Small Shelter", **CHURCH_STREET
        )
        full_user = make_user(db, role=UserRole.RECIPIENT, email="full@example.com")
        full = make_recipient(
            db, full_user, accepts_food=True, capacity=200, organization_name="Large Shelter", **CHURCH_STREET
        )
        headers = login_headers(client, provider.email)

        resp = client.post(f"/api/matching/{resource.id}", headers=headers)

        assert resp.status_code == 201, resp.text
        candidates = resp.json()["data"]["candidates"]
        assert len(candidates) == 2

        partial_candidate = _candidate_for(candidates, partial.id)
        full_candidate = _candidate_for(candidates, full.id)
        assert partial_candidate["status"] == "PROPOSED"
        assert full_candidate["status"] == "PROPOSED"
        assert full_candidate["score"] > partial_candidate["score"]

    def test_unavailable_recipient_is_rejected(self, client, db):
        """Validation rule: exclude unavailable recipients — they still get
        an explained, auditable REJECTED row rather than a winning match."""
        provider = make_user(db, role=UserRole.PROVIDER)
        resource = make_resource(db, provider, **MG_ROAD)

        recipient_user = make_user(db, role=UserRole.RECIPIENT)
        recipient = make_recipient(
            db, recipient_user, accepts_food=True, current_availability=False, **CHURCH_STREET
        )
        headers = login_headers(client, provider.email)

        resp = client.post(f"/api/matching/{resource.id}", headers=headers)

        assert resp.status_code == 201, resp.text
        candidates = resp.json()["data"]["candidates"]
        assert len(candidates) == 1
        rejected = _candidate_for(candidates, recipient.id)
        assert rejected["status"] == "REJECTED"
        assert any("unavailable" in reason or "available" in reason for reason in rejected["rejection_reasons"])

    def test_recipient_outside_service_area_is_rejected(self, client, db):
        provider = make_user(db, role=UserRole.PROVIDER)
        resource = make_resource(db, provider, **MG_ROAD)

        recipient_user = make_user(db, role=UserRole.RECIPIENT)
        recipient = make_recipient(db, recipient_user, accepts_food=True, service_area_km=10, **MUMBAI)
        headers = login_headers(client, provider.email)

        resp = client.post(f"/api/matching/{resource.id}", headers=headers)

        assert resp.status_code == 201, resp.text
        candidates = resp.json()["data"]["candidates"]
        assert len(candidates) == 1
        rejected = _candidate_for(candidates, recipient.id)
        assert rejected["status"] == "REJECTED"
        assert rejected["distance_km"] > 10
        assert any("service area" in reason for reason in rejected["rejection_reasons"])

    def test_closer_recipient_ranks_above_farther_one(self, client, db):
        provider = make_user(db, role=UserRole.PROVIDER)
        resource = make_resource(db, provider, quantity=10, **MG_ROAD)

        near_user = make_user(db, role=UserRole.RECIPIENT, email="near@example.com")
        near = make_recipient(
            db, near_user, accepts_food=True, organization_name="Near Shelter", **CHURCH_STREET
        )

        far_user = make_user(db, role=UserRole.RECIPIENT, email="far@example.com")
        make_recipient(
            db,
            far_user,
            accepts_food=True,
            organization_name="Far Shelter",
            service_area_km=2000,
            **MUMBAI,
        )
        headers = login_headers(client, provider.email)

        resp = client.post(f"/api/matching/{resource.id}", headers=headers)

        assert resp.status_code == 201, resp.text
        candidates = resp.json()["data"]["candidates"]
        assert len(candidates) == 2
        assert candidates[0]["recipient"]["id"] == str(near.id)
        assert candidates[0]["score"] >= candidates[1]["score"]

    def test_no_eligible_recipients_marks_rescue_request_failed(self, client, db):
        provider = make_user(db, role=UserRole.PROVIDER)
        resource = make_resource(db, provider, **MG_ROAD)
        headers = login_headers(client, provider.email)

        resp = client.post(f"/api/matching/{resource.id}", headers=headers)

        assert resp.status_code == 201, resp.text
        body = resp.json()["data"]
        assert body["candidates"] == []
        assert body["rescue_request_status"] == "FAILED"

    def test_rerunning_matching_replaces_previous_matches(self, client, db):
        provider = make_user(db, role=UserRole.PROVIDER)
        resource = make_resource(db, provider, **MG_ROAD)

        recipient_user = make_user(db, role=UserRole.RECIPIENT)
        make_recipient(db, recipient_user, accepts_food=True, **CHURCH_STREET)
        headers = login_headers(client, provider.email)

        first = client.post(f"/api/matching/{resource.id}", headers=headers)
        second = client.post(f"/api/matching/{resource.id}", headers=headers)

        assert first.status_code == 201 and second.status_code == 201
        first_rr_id = first.json()["data"]["rescue_request_id"]
        second_rr_id = second.json()["data"]["rescue_request_id"]
        # The still-open RescueRequest is reused across re-runs, not duplicated.
        assert first_rr_id == second_rr_id
        assert db.query(RescueRequest).filter(RescueRequest.resource_id == resource.id).count() == 1

        matches = db.query(Match).filter(Match.rescue_request_id == uuid.UUID(second_rr_id)).all()
        # Re-running matching must not accumulate duplicate rows.
        assert len(matches) == 1

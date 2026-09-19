"""
Integration tests for POST/GET /api/allocations.

Shared fixtures/helpers (db, client, make_user, login_headers,
make_resource, make_recipient, make_rescue_request, make_match) live in
tests/conftest.py. A Match is created directly via make_match rather than
running the full matching engine, so these tests isolate allocation
behavior from matching behavior. Run with:

    export DATABASE_URL=postgresql+psycopg2://postgres:postgres@localhost:5432/reserve_test
    pytest tests/test_allocations.py -v
"""

import uuid

from app.models.allocation import Allocation
from app.models.enums import (
    AllocationStatus,
    MatchStatus,
    ResourceStatus,
    RescueRequestStatus,
    UserRole,
)
from app.models.match import Match

from tests.conftest import login_headers, make_match, make_recipient, make_rescue_request, make_resource, make_user


def _setup_proposed_match(db, quantity=80, recipient_capacity=None):
    provider = make_user(db, role=UserRole.PROVIDER)
    resource = make_resource(db, provider, quantity=quantity, status=ResourceStatus.MATCHING)
    rescue_request = make_rescue_request(db, resource, status=RescueRequestStatus.MATCHED)
    recipient_user = make_user(db, role=UserRole.RECIPIENT)
    recipient = make_recipient(db, recipient_user, capacity=recipient_capacity)
    match = make_match(db, rescue_request, recipient=recipient)
    return provider, resource, rescue_request, recipient, match


class TestCreateAllocationPermissionsAndValidation:
    def test_unauthenticated_request_is_rejected(self, client, db):
        _, _, _, _, match = _setup_proposed_match(db)

        resp = client.post("/api/allocations", json={"match_id": str(match.id)})

        assert resp.status_code == 401

    def test_returns_404_for_unknown_match(self, client, db):
        provider = make_user(db, role=UserRole.PROVIDER)
        headers = login_headers(client, provider.email)

        resp = client.post("/api/allocations", json={"match_id": str(uuid.uuid4())}, headers=headers)

        assert resp.status_code == 404
        assert resp.json()["error"]["code"] == "MATCH_NOT_FOUND"

    def test_non_owner_provider_cannot_allocate(self, client, db):
        _, resource, _, _, match = _setup_proposed_match(db)
        other = make_user(db, role=UserRole.PROVIDER, email="other@example.com")
        headers = login_headers(client, other.email)

        resp = client.post("/api/allocations", json={"match_id": str(match.id)}, headers=headers)

        assert resp.status_code == 403
        assert resp.json()["error"]["code"] == "NOT_RESOURCE_OWNER"

    def test_admin_can_allocate_someone_elses_resource(self, client, db):
        _, resource, _, _, match = _setup_proposed_match(db)
        admin = make_user(db, role=UserRole.ADMIN)
        headers = login_headers(client, admin.email)

        resp = client.post("/api/allocations", json={"match_id": str(match.id)}, headers=headers)

        assert resp.status_code == 201, resp.text

    def test_rejected_match_cannot_be_allocated(self, client, db):
        provider, resource, rescue_request, recipient, _ = _setup_proposed_match(db)
        rejected_match = make_match(db, rescue_request, recipient=recipient, status=MatchStatus.REJECTED)
        headers = login_headers(client, provider.email)

        resp = client.post("/api/allocations", json={"match_id": str(rejected_match.id)}, headers=headers)

        assert resp.status_code == 409
        assert resp.json()["error"]["code"] == "MATCH_NOT_ELIGIBLE"

    def test_resource_not_in_allocatable_status_is_rejected(self, client, db):
        provider = make_user(db, role=UserRole.PROVIDER)
        resource = make_resource(db, provider, status=ResourceStatus.DELIVERED)
        rescue_request = make_rescue_request(db, resource, status=RescueRequestStatus.MATCHED)
        recipient_user = make_user(db, role=UserRole.RECIPIENT)
        recipient = make_recipient(db, recipient_user)
        match = make_match(db, rescue_request, recipient=recipient)
        headers = login_headers(client, provider.email)

        resp = client.post("/api/allocations", json={"match_id": str(match.id)}, headers=headers)

        assert resp.status_code == 409
        assert resp.json()["error"]["code"] == "RESOURCE_NOT_ALLOCATABLE"


class TestCreateAllocationBehavior:
    def test_full_allocation_moves_resource_to_allocated_and_match_to_selected(self, client, db):
        provider, resource, rescue_request, recipient, match = _setup_proposed_match(db, quantity=80)
        headers = login_headers(client, provider.email)

        resp = client.post("/api/allocations", json={"match_id": str(match.id)}, headers=headers)

        assert resp.status_code == 201, resp.text
        data = resp.json()["data"]
        assert data["allocated_quantity"] == 80
        assert data["status"] == "PENDING"
        assert data["resource_remaining_quantity"] == 0
        assert data["recipient"]["id"] == str(recipient.id)

        db.refresh(resource)
        db.refresh(match)
        db.refresh(rescue_request)
        assert resource.status == ResourceStatus.ALLOCATED
        assert match.status == MatchStatus.SELECTED
        assert rescue_request.status == RescueRequestStatus.MATCHED

        allocation = db.query(Allocation).filter(Allocation.match_id == match.id).first()
        assert allocation is not None
        assert float(allocation.allocated_quantity) == 80

    def test_partial_allocation_leaves_resource_in_matching_and_request_partially_matched(self, client, db):
        provider, resource, rescue_request, recipient, match = _setup_proposed_match(db, quantity=80)
        headers = login_headers(client, provider.email)

        resp = client.post(
            "/api/allocations", json={"match_id": str(match.id), "allocated_quantity": 30}, headers=headers
        )

        assert resp.status_code == 201, resp.text
        data = resp.json()["data"]
        assert data["allocated_quantity"] == 30
        assert data["resource_remaining_quantity"] == 50

        db.refresh(resource)
        db.refresh(rescue_request)
        assert resource.status == ResourceStatus.MATCHING
        assert rescue_request.status == RescueRequestStatus.PARTIALLY_MATCHED

    def test_second_partial_allocation_can_complete_the_resource(self, client, db):
        provider, resource, rescue_request, recipient, match = _setup_proposed_match(db, quantity=80)
        headers = login_headers(client, provider.email)
        client.post("/api/allocations", json={"match_id": str(match.id), "allocated_quantity": 30}, headers=headers)

        recipient_user_2 = make_user(db, role=UserRole.RECIPIENT, email="second@example.com")
        recipient_2 = make_recipient(db, recipient_user_2, organization_name="Second Shelter")
        match_2 = make_match(db, rescue_request, recipient=recipient_2)

        resp = client.post("/api/allocations", json={"match_id": str(match_2.id)}, headers=headers)

        assert resp.status_code == 201, resp.text
        assert resp.json()["data"]["allocated_quantity"] == 50
        assert resp.json()["data"]["resource_remaining_quantity"] == 0

        db.refresh(resource)
        db.refresh(rescue_request)
        assert resource.status == ResourceStatus.ALLOCATED
        assert rescue_request.status == RescueRequestStatus.MATCHED

    def test_double_allocation_of_same_match_is_prevented(self, client, db):
        provider, resource, rescue_request, recipient, match = _setup_proposed_match(db, quantity=80)
        headers = login_headers(client, provider.email)
        first = client.post(
            "/api/allocations", json={"match_id": str(match.id), "allocated_quantity": 20}, headers=headers
        )
        assert first.status_code == 201, first.text

        second = client.post(
            "/api/allocations", json={"match_id": str(match.id), "allocated_quantity": 10}, headers=headers
        )

        assert second.status_code == 409
        assert second.json()["error"]["code"] == "MATCH_ALREADY_ALLOCATED"

    def test_double_allocation_of_same_recipient_via_new_match_is_prevented(self, client, db):
        """Even if a *different* Match row exists for the same recipient
        (e.g. after a matching re-run), they can't be allocated twice
        against the same rescue request."""
        provider, resource, rescue_request, recipient, match = _setup_proposed_match(db, quantity=80)
        headers = login_headers(client, provider.email)
        first = client.post(
            "/api/allocations", json={"match_id": str(match.id), "allocated_quantity": 20}, headers=headers
        )
        assert first.status_code == 201, first.text

        new_match_same_recipient = make_match(db, rescue_request, recipient=recipient)

        resp = client.post(
            "/api/allocations", json={"match_id": str(new_match_same_recipient.id)}, headers=headers
        )

        assert resp.status_code == 409
        assert resp.json()["error"]["code"] == "CANDIDATE_ALREADY_ALLOCATED"

    def test_allocation_exceeding_remaining_quantity_is_rejected(self, client, db):
        provider, resource, rescue_request, recipient, match = _setup_proposed_match(db, quantity=80)
        headers = login_headers(client, provider.email)

        resp = client.post(
            "/api/allocations", json={"match_id": str(match.id), "allocated_quantity": 200}, headers=headers
        )

        assert resp.status_code == 409
        assert resp.json()["error"]["code"] == "INSUFFICIENT_QUANTITY_AVAILABLE"

    def test_allocation_exceeding_recipient_capacity_is_rejected(self, client, db):
        provider, resource, rescue_request, recipient, match = _setup_proposed_match(
            db, quantity=80, recipient_capacity=50
        )
        headers = login_headers(client, provider.email)

        resp = client.post(
            "/api/allocations", json={"match_id": str(match.id), "allocated_quantity": 60}, headers=headers
        )

        assert resp.status_code == 409
        assert resp.json()["error"]["code"] == "EXCEEDS_RECIPIENT_CAPACITY"

    def test_fully_allocated_resource_rejects_further_allocation(self, client, db):
        provider, resource, rescue_request, recipient, match = _setup_proposed_match(db, quantity=80)
        headers = login_headers(client, provider.email)
        first = client.post("/api/allocations", json={"match_id": str(match.id)}, headers=headers)
        assert first.status_code == 201, first.text

        recipient_user_2 = make_user(db, role=UserRole.RECIPIENT, email="third@example.com")
        recipient_2 = make_recipient(db, recipient_user_2, organization_name="Third Shelter")
        match_2 = make_match(db, rescue_request, recipient=recipient_2)

        resp = client.post("/api/allocations", json={"match_id": str(match_2.id)}, headers=headers)

        assert resp.status_code == 409
        assert resp.json()["error"]["code"] in ("RESOURCE_FULLY_ALLOCATED", "RESOURCE_NOT_ALLOCATABLE")


class TestListAllocations:
    def test_list_returns_created_allocation(self, client, db):
        provider, resource, rescue_request, recipient, match = _setup_proposed_match(db, quantity=80)
        headers = login_headers(client, provider.email)
        client.post("/api/allocations", json={"match_id": str(match.id)}, headers=headers)

        resp = client.get("/api/allocations", headers=headers)

        assert resp.status_code == 200, resp.text
        body = resp.json()["data"]
        assert body["total"] == 1
        assert body["items"][0]["match_id"] == str(match.id)

    def test_list_filters_by_resource_id(self, client, db):
        provider, resource, rescue_request, recipient, match = _setup_proposed_match(db, quantity=80)
        headers = login_headers(client, provider.email)
        client.post("/api/allocations", json={"match_id": str(match.id)}, headers=headers)

        other_provider, other_resource, other_rr, other_recipient, other_match = _setup_proposed_match(
            db, quantity=40
        )
        other_headers = login_headers(client, other_provider.email)
        client.post("/api/allocations", json={"match_id": str(other_match.id)}, headers=other_headers)

        resp = client.get(f"/api/allocations?resource_id={resource.id}", headers=headers)

        assert resp.status_code == 200, resp.text
        body = resp.json()["data"]
        assert body["total"] == 1
        assert body["items"][0]["resource_id"] == str(resource.id)

    def test_list_filters_by_status(self, client, db):
        provider, resource, rescue_request, recipient, match = _setup_proposed_match(db, quantity=80)
        headers = login_headers(client, provider.email)
        client.post("/api/allocations", json={"match_id": str(match.id)}, headers=headers)

        resp = client.get("/api/allocations?status=CONFIRMED", headers=headers)

        assert resp.status_code == 200, resp.text
        assert resp.json()["data"]["total"] == 0

    def test_unauthenticated_list_is_rejected(self, client, db):
        resp = client.get("/api/allocations")
        assert resp.status_code == 401


class TestRescueHubAllocation:
    def test_allocation_to_a_rescue_hub_updates_its_current_load(self, client, db):
        from tests.conftest import make_rescue_hub

        provider = make_user(db, role=UserRole.PROVIDER)
        resource = make_resource(db, provider, quantity=25, status=ResourceStatus.MATCHING)
        rescue_request = make_rescue_request(db, resource, status=RescueRequestStatus.MATCHED)
        hub = make_rescue_hub(db, capacity=100, current_load=0)
        match = make_match(db, rescue_request, rescue_hub_id=hub.id)
        headers = login_headers(client, provider.email)

        resp = client.post("/api/allocations", json={"match_id": str(match.id)}, headers=headers)

        assert resp.status_code == 201, resp.text
        assert resp.json()["data"]["rescue_hub"]["id"] == str(hub.id)

        db.refresh(hub)
        assert hub.current_load == 25

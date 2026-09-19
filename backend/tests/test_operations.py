"""
Integration tests for POST/GET /api/operations and
PATCH /api/operations/{operation_id}/status.

Shared fixtures/helpers (db, client, make_user, login_headers,
make_resource, make_recipient, make_rescue_request, make_match,
make_rescue_partner) live in tests/conftest.py. An operation needs a real
Allocation underneath it, so these tests go through the actual
POST /api/allocations endpoint rather than constructing an Allocation row
directly — this suite exercises the genuine match -> allocate -> operate
-> deliver flow end to end. Run with:

    export DATABASE_URL=postgresql+psycopg2://postgres:postgres@localhost:5432/reserve_test
    pytest tests/test_operations.py -v
"""

import uuid

from app.models.enums import (
    ResourceStatus,
    RescueRequestStatus,
    UserRole,
)
from app.services.location_service import estimate_travel_duration_minutes, haversine_km

from tests.conftest import (
    login_headers,
    make_match,
    make_recipient,
    make_rescue_partner,
    make_rescue_request,
    make_resource,
    make_user,
)


def _setup_allocated_request(db, client, quantity=80, recipient_capacity=None, resource_type=None):
    """Provider + resource + rescue request + a PENDING allocation, created
    through the real matching -> allocation flow (a Match fixture stands in
    for a matching run, same as tests/test_allocations.py does)."""
    provider = make_user(db, role=UserRole.PROVIDER)
    headers = login_headers(client, provider.email)
    resource_kwargs = {"quantity": quantity, "status": ResourceStatus.MATCHING}
    if resource_type is not None:
        resource_kwargs["resource_type"] = resource_type
    resource = make_resource(db, provider, **resource_kwargs)
    rescue_request = make_rescue_request(db, resource, status=RescueRequestStatus.MATCHED)
    recipient_user = make_user(db, role=UserRole.RECIPIENT)
    recipient = make_recipient(db, recipient_user, capacity=recipient_capacity)
    match = make_match(db, rescue_request, recipient=recipient)

    alloc_resp = client.post("/api/allocations", json={"match_id": str(match.id)}, headers=headers)
    assert alloc_resp.status_code == 201, alloc_resp.text
    allocation_id = alloc_resp.json()["data"]["id"]

    return provider, headers, resource, rescue_request, recipient, allocation_id


def _create_operation(client, headers, rescue_request_id, **extra):
    payload = {"rescue_request_id": str(rescue_request_id), **extra}
    return client.post("/api/operations", json=payload, headers=headers)


class TestCreateOperation:
    def test_auto_links_active_allocations(self, db, client):
        provider, headers, resource, rescue_request, recipient, allocation_id = _setup_allocated_request(
            db, client
        )

        resp = _create_operation(client, headers, rescue_request.id)

        assert resp.status_code == 201, resp.text
        data = resp.json()["data"]
        assert data["status"] == "PLANNED"
        assert data["resource_id"] == str(resource.id)
        assert [a["id"] for a in data["allocations"]] == [allocation_id]
        assert data["partner"] is None
        assert len(data["events"]) == 1
        assert data["events"][0]["event_type"] == "CREATED"

    def test_with_explicit_allocation_ids(self, db, client):
        provider, headers, resource, rescue_request, recipient, allocation_id = _setup_allocated_request(
            db, client
        )

        resp = _create_operation(client, headers, rescue_request.id, allocation_ids=[allocation_id])

        assert resp.status_code == 201, resp.text
        assert [a["id"] for a in resp.json()["data"]["allocations"]] == [allocation_id]

    def test_with_partner_assignment(self, db, client):
        provider, headers, resource, rescue_request, recipient, allocation_id = _setup_allocated_request(
            db, client
        )
        partner_user = make_user(db, role=UserRole.RESCUE_PARTNER)
        partner = make_rescue_partner(db, partner_user, accepts_food=True)

        resp = _create_operation(client, headers, rescue_request.id, partner_id=str(partner.id))

        assert resp.status_code == 201, resp.text
        assert resp.json()["data"]["partner"]["id"] == str(partner.id)

    def test_rejects_unavailable_partner(self, db, client):
        provider, headers, resource, rescue_request, recipient, allocation_id = _setup_allocated_request(
            db, client
        )
        partner_user = make_user(db, role=UserRole.RESCUE_PARTNER)
        partner = make_rescue_partner(db, partner_user, is_available=False)

        resp = _create_operation(client, headers, rescue_request.id, partner_id=str(partner.id))

        assert resp.status_code == 409, resp.text
        assert resp.json()["error"]["code"] == "PARTNER_UNAVAILABLE"

    def test_rejects_partner_type_mismatch(self, db, client):
        provider, headers, resource, rescue_request, recipient, allocation_id = _setup_allocated_request(
            db, client
        )
        partner_user = make_user(db, role=UserRole.RESCUE_PARTNER)
        # Doesn't accept FOOD, and the default test resource is FOOD.
        partner = make_rescue_partner(db, partner_user, accepts_food=False, accepts_medical=True)

        resp = _create_operation(client, headers, rescue_request.id, partner_id=str(partner.id))

        assert resp.status_code == 409, resp.text
        assert resp.json()["error"]["code"] == "PARTNER_TYPE_MISMATCH"

    def test_requires_resource_owner_or_admin(self, db, client):
        provider, headers, resource, rescue_request, recipient, allocation_id = _setup_allocated_request(
            db, client
        )
        other = make_user(db, role=UserRole.PROVIDER, email="other-provider@example.com")
        other_headers = login_headers(client, other.email)

        resp = _create_operation(client, other_headers, rescue_request.id)

        assert resp.status_code == 403, resp.text
        assert resp.json()["error"]["code"] == "NOT_RESOURCE_OWNER"

    def test_admin_can_create_for_any_resource(self, db, client):
        provider, headers, resource, rescue_request, recipient, allocation_id = _setup_allocated_request(
            db, client
        )
        admin = make_user(db, role=UserRole.ADMIN, email="admin@example.com")
        admin_headers = login_headers(client, admin.email)

        resp = _create_operation(client, admin_headers, rescue_request.id)

        assert resp.status_code == 201, resp.text

    def test_fails_without_active_allocations(self, db, client):
        provider = make_user(db, role=UserRole.PROVIDER)
        headers = login_headers(client, provider.email)
        resource = make_resource(db, provider, status=ResourceStatus.MATCHING)
        rescue_request = make_rescue_request(db, resource, status=RescueRequestStatus.MATCHING)

        resp = _create_operation(client, headers, rescue_request.id)

        assert resp.status_code == 409, resp.text
        assert resp.json()["error"]["code"] == "NO_ACTIVE_ALLOCATIONS"

    def test_rejects_duplicate_operation_for_same_request(self, db, client):
        provider, headers, resource, rescue_request, recipient, allocation_id = _setup_allocated_request(
            db, client
        )
        first = _create_operation(client, headers, rescue_request.id)
        assert first.status_code == 201, first.text

        second = _create_operation(client, headers, rescue_request.id)

        assert second.status_code == 409, second.text
        assert second.json()["error"]["code"] == "OPERATION_ALREADY_EXISTS"

    def test_404_for_unknown_rescue_request(self, db, client):
        provider = make_user(db, role=UserRole.PROVIDER)
        headers = login_headers(client, provider.email)

        resp = _create_operation(client, headers, uuid.uuid4())

        assert resp.status_code == 404, resp.text
        assert resp.json()["error"]["code"] == "RESCUE_REQUEST_NOT_FOUND"

    def test_requires_authentication(self, db, client):
        provider, headers, resource, rescue_request, recipient, allocation_id = _setup_allocated_request(
            db, client
        )

        resp = client.post("/api/operations", json={"rescue_request_id": str(rescue_request.id)})

        assert resp.status_code == 401, resp.text


class TestListOperations:
    def test_lists_created_operations(self, db, client):
        provider, headers, resource, rescue_request, recipient, allocation_id = _setup_allocated_request(
            db, client
        )
        create_resp = _create_operation(client, headers, rescue_request.id)
        operation_id = create_resp.json()["data"]["id"]

        resp = client.get("/api/operations", headers=headers)

        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]
        assert data["total"] == 1
        assert data["items"][0]["id"] == operation_id

    def test_filters_by_status(self, db, client):
        provider, headers, resource, rescue_request, recipient, allocation_id = _setup_allocated_request(
            db, client
        )
        _create_operation(client, headers, rescue_request.id)

        planned = client.get("/api/operations", params={"status": "PLANNED"}, headers=headers)
        delivered = client.get("/api/operations", params={"status": "DELIVERED"}, headers=headers)

        assert planned.json()["data"]["total"] == 1
        assert delivered.json()["data"]["total"] == 0

    def test_filters_by_resource_id(self, db, client):
        provider, headers, resource, rescue_request, recipient, allocation_id = _setup_allocated_request(
            db, client
        )
        _create_operation(client, headers, rescue_request.id)
        other_provider, other_headers, other_resource, other_rr, _, _ = _setup_allocated_request(db, client)
        _create_operation(client, other_headers, other_rr.id)

        resp = client.get("/api/operations", params={"resource_id": str(resource.id)}, headers=headers)

        assert resp.json()["data"]["total"] == 1
        assert resp.json()["data"]["items"][0]["resource_id"] == str(resource.id)

    def test_requires_authentication(self, db, client):
        resp = client.get("/api/operations")
        assert resp.status_code == 401, resp.text


class TestListOperationEvents:
    def test_returns_events_in_chronological_order(self, db, client):
        provider, headers, resource, rescue_request, recipient, allocation_id = _setup_allocated_request(
            db, client
        )
        create_resp = _create_operation(client, headers, rescue_request.id)
        operation_id = create_resp.json()["data"]["id"]

        in_transit = client.patch(
            f"/api/operations/{operation_id}/status", json={"status": "IN_TRANSIT"}, headers=headers
        )
        assert in_transit.status_code == 200, in_transit.text
        delivered = client.patch(
            f"/api/operations/{operation_id}/status", json={"status": "DELIVERED"}, headers=headers
        )
        assert delivered.status_code == 200, delivered.text

        resp = client.get(f"/api/operations/{operation_id}/events", headers=headers)

        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]
        assert data["total"] == 3
        types = [e["event_type"] for e in data["items"]]
        assert types == ["CREATED", "STATUS_CHANGED", "STATUS_CHANGED"]
        # Chronological order: each event's timestamp is >= the previous one's.
        timestamps = [e["created_at"] for e in data["items"]]
        assert timestamps == sorted(timestamps)
        # Every field asked for is present: type, description, timestamp, user id.
        for event in data["items"]:
            assert event["event_type"]
            assert event["description"]
            assert event["created_at"]
            assert event["created_by_user_id"] == str(provider.id)

    def test_events_include_status_change_details(self, db, client):
        provider, headers, resource, rescue_request, recipient, allocation_id = _setup_allocated_request(
            db, client
        )
        create_resp = _create_operation(client, headers, rescue_request.id)
        operation_id = create_resp.json()["data"]["id"]

        client.patch(f"/api/operations/{operation_id}/status", json={"status": "IN_TRANSIT"}, headers=headers)

        resp = client.get(f"/api/operations/{operation_id}/events", headers=headers)
        status_event = resp.json()["data"]["items"][-1]
        assert status_event["event_type"] == "STATUS_CHANGED"
        assert "PLANNED" in status_event["description"]
        assert "IN_TRANSIT" in status_event["description"]

    def test_unknown_operation_returns_404(self, db, client):
        provider = make_user(db, role=UserRole.PROVIDER)
        headers = login_headers(client, provider.email)

        resp = client.get(f"/api/operations/{uuid.uuid4()}/events", headers=headers)

        assert resp.status_code == 404, resp.text

    def test_requires_authentication(self, db, client):
        provider, headers, resource, rescue_request, recipient, allocation_id = _setup_allocated_request(
            db, client
        )
        create_resp = _create_operation(client, headers, rescue_request.id)
        operation_id = create_resp.json()["data"]["id"]

        resp = client.get(f"/api/operations/{operation_id}/events")

        assert resp.status_code == 401, resp.text

    def test_any_authenticated_user_can_view(self, db, client):
        """Listing is open to any authenticated user, same as GET /api/operations."""
        provider, headers, resource, rescue_request, recipient, allocation_id = _setup_allocated_request(
            db, client
        )
        create_resp = _create_operation(client, headers, rescue_request.id)
        operation_id = create_resp.json()["data"]["id"]

        other_user = make_user(db, role=UserRole.RECIPIENT)
        other_headers = login_headers(client, other_user.email)

        resp = client.get(f"/api/operations/{operation_id}/events", headers=other_headers)

        assert resp.status_code == 200, resp.text
        assert resp.json()["data"]["total"] == 1


class TestOperationStatusLifecycle:
    def _create(self, db, client, **overrides):
        provider, headers, resource, rescue_request, recipient, allocation_id = _setup_allocated_request(
            db, client, **overrides
        )
        resp = _create_operation(client, headers, rescue_request.id)
        assert resp.status_code == 201, resp.text
        operation_id = resp.json()["data"]["id"]
        return provider, headers, resource, rescue_request, recipient, allocation_id, operation_id

    def _patch(self, client, headers, operation_id, new_status, reason=None):
        payload = {"status": new_status}
        if reason is not None:
            payload["reason"] = reason
        return client.patch(f"/api/operations/{operation_id}/status", json=payload, headers=headers)

    def test_full_happy_path_to_completed(self, db, client):
        provider, headers, resource, rescue_request, recipient, allocation_id, operation_id = self._create(
            db, client
        )

        in_transit = self._patch(client, headers, operation_id, "IN_TRANSIT")
        assert in_transit.status_code == 200, in_transit.text
        assert in_transit.json()["data"]["status"] == "IN_TRANSIT"
        assert in_transit.json()["data"]["pickup_started_at"] is not None

        delivered = self._patch(client, headers, operation_id, "DELIVERED")
        assert delivered.status_code == 200, delivered.text
        data = delivered.json()["data"]
        assert data["status"] == "DELIVERED"
        assert data["delivered_at"] is not None
        assert data["allocations"][0]["status"] == "DELIVERED"

        completed = self._patch(client, headers, operation_id, "COMPLETED")
        assert completed.status_code == 200, completed.text
        data = completed.json()["data"]
        assert data["status"] == "COMPLETED"
        assert data["completed_at"] is not None

        # Every transition (3) plus the original CREATED event = 4.
        assert len(data["events"]) == 4
        assert [e["event_type"] for e in data["events"]] == [
            "CREATED",
            "STATUS_CHANGED",
            "STATUS_CHANGED",
            "STATUS_CHANGED",
        ]

    def test_delivered_marks_allocation_and_resource_delivered(self, db, client):
        provider, headers, resource, rescue_request, recipient, allocation_id, operation_id = self._create(
            db, client
        )
        self._patch(client, headers, operation_id, "IN_TRANSIT")

        self._patch(client, headers, operation_id, "DELIVERED")

        db.refresh(resource)
        assert resource.status == ResourceStatus.DELIVERED

    def test_cannot_skip_a_status(self, db, client):
        provider, headers, resource, rescue_request, recipient, allocation_id, operation_id = self._create(
            db, client
        )

        resp = self._patch(client, headers, operation_id, "DELIVERED")

        assert resp.status_code == 409, resp.text
        assert resp.json()["error"]["code"] == "INVALID_STATUS_TRANSITION"
        assert "IN_TRANSIT" in resp.json()["error"]["message"]

    def test_setting_the_same_status_is_rejected(self, db, client):
        provider, headers, resource, rescue_request, recipient, allocation_id, operation_id = self._create(
            db, client
        )

        resp = self._patch(client, headers, operation_id, "PLANNED")

        assert resp.status_code == 409, resp.text
        assert resp.json()["error"]["code"] == "NO_STATUS_CHANGE"

    def test_failed_requires_a_reason(self, db, client):
        provider, headers, resource, rescue_request, recipient, allocation_id, operation_id = self._create(
            db, client
        )

        resp = self._patch(client, headers, operation_id, "FAILED")

        assert resp.status_code == 422, resp.text
        assert resp.json()["error"]["code"] == "FAILURE_REASON_REQUIRED"

    def test_failed_with_reason_succeeds_from_planned(self, db, client):
        provider, headers, resource, rescue_request, recipient, allocation_id, operation_id = self._create(
            db, client
        )

        resp = self._patch(client, headers, operation_id, "FAILED", reason="Vehicle breakdown")

        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]
        assert data["status"] == "FAILED"
        assert data["failure_reason"] == "Vehicle breakdown"

    def test_failed_reachable_from_in_transit(self, db, client):
        provider, headers, resource, rescue_request, recipient, allocation_id, operation_id = self._create(
            db, client
        )
        self._patch(client, headers, operation_id, "IN_TRANSIT")

        resp = self._patch(client, headers, operation_id, "FAILED", reason="Recipient unreachable")

        assert resp.status_code == 200, resp.text
        assert resp.json()["data"]["status"] == "FAILED"

    def test_failed_is_terminal(self, db, client):
        provider, headers, resource, rescue_request, recipient, allocation_id, operation_id = self._create(
            db, client
        )
        self._patch(client, headers, operation_id, "FAILED", reason="Weather")

        resp = self._patch(client, headers, operation_id, "IN_TRANSIT")

        assert resp.status_code == 409, resp.text
        assert resp.json()["error"]["code"] == "INVALID_STATUS_TRANSITION"
        assert "terminal" in resp.json()["error"]["message"].lower()

    def test_completed_is_terminal(self, db, client):
        provider, headers, resource, rescue_request, recipient, allocation_id, operation_id = self._create(
            db, client
        )
        self._patch(client, headers, operation_id, "IN_TRANSIT")
        self._patch(client, headers, operation_id, "DELIVERED")
        self._patch(client, headers, operation_id, "COMPLETED")

        resp = self._patch(client, headers, operation_id, "FAILED", reason="too late")

        assert resp.status_code == 409, resp.text

    def test_unrelated_provider_cannot_update_status(self, db, client):
        provider, headers, resource, rescue_request, recipient, allocation_id, operation_id = self._create(
            db, client
        )
        other = make_user(db, role=UserRole.PROVIDER, email="other-provider2@example.com")
        other_headers = login_headers(client, other.email)

        resp = self._patch(client, other_headers, operation_id, "IN_TRANSIT")

        assert resp.status_code == 403, resp.text
        assert resp.json()["error"]["code"] == "NOT_AUTHORIZED"

    def test_assigned_partner_can_update_status(self, db, client):
        provider, headers, resource, rescue_request, recipient, allocation_id = _setup_allocated_request(
            db, client
        )
        partner_user = make_user(db, role=UserRole.RESCUE_PARTNER)
        partner = make_rescue_partner(db, partner_user, accepts_food=True)
        create_resp = _create_operation(client, headers, rescue_request.id, partner_id=str(partner.id))
        operation_id = create_resp.json()["data"]["id"]
        partner_headers = login_headers(client, partner_user.email)

        resp = self._patch(client, partner_headers, operation_id, "IN_TRANSIT")

        assert resp.status_code == 200, resp.text

    def test_unassigned_partner_cannot_update_status(self, db, client):
        provider, headers, resource, rescue_request, recipient, allocation_id = _setup_allocated_request(
            db, client
        )
        assigned_partner_user = make_user(db, role=UserRole.RESCUE_PARTNER, email="assigned@example.com")
        assigned_partner = make_rescue_partner(db, assigned_partner_user, accepts_food=True)
        create_resp = _create_operation(
            client, headers, rescue_request.id, partner_id=str(assigned_partner.id)
        )
        operation_id = create_resp.json()["data"]["id"]

        other_partner_user = make_user(db, role=UserRole.RESCUE_PARTNER, email="other-partner@example.com")
        make_rescue_partner(db, other_partner_user, accepts_food=True)
        other_partner_headers = login_headers(client, other_partner_user.email)

        resp = self._patch(client, other_partner_headers, operation_id, "IN_TRANSIT")

        assert resp.status_code == 403, resp.text

    def test_admin_can_update_status(self, db, client):
        provider, headers, resource, rescue_request, recipient, allocation_id, operation_id = self._create(
            db, client
        )
        admin = make_user(db, role=UserRole.ADMIN, email="admin2@example.com")
        admin_headers = login_headers(client, admin.email)

        resp = self._patch(client, admin_headers, operation_id, "IN_TRANSIT")

        assert resp.status_code == 200, resp.text

    def test_requires_authentication(self, db, client):
        provider, headers, resource, rescue_request, recipient, allocation_id, operation_id = self._create(
            db, client
        )

        resp = client.patch(f"/api/operations/{operation_id}/status", json={"status": "IN_TRANSIT"})

        assert resp.status_code == 401, resp.text

    def test_404_for_unknown_operation(self, db, client):
        provider = make_user(db, role=UserRole.PROVIDER)
        headers = login_headers(client, provider.email)

        resp = self._patch(client, headers, uuid.uuid4(), "IN_TRANSIT")

        assert resp.status_code == 404, resp.text
        assert resp.json()["error"]["code"] == "OPERATION_NOT_FOUND"


# MG Road, Bengaluru (pickup) and Church Street, Bengaluru (delivery) — real,
# a few km apart, so distance/duration come out as a small positive number
# rather than 0.
_PICKUP_COORDS = {"latitude": 12.9716, "longitude": 77.5946}
_DELIVERY_COORDS = {"latitude": 12.9698, "longitude": 77.6205}


def _setup_operation_with_coords(db, client, pickup=True, delivery=True):
    """Same shape as _setup_allocated_request, but the resource/recipient
    optionally carry known coordinates so route distance/duration can be
    asserted, and an operation is already created for the rescue request."""
    provider = make_user(db, role=UserRole.PROVIDER)
    headers = login_headers(client, provider.email)
    resource_kwargs = {"status": ResourceStatus.MATCHING}
    if pickup:
        resource_kwargs.update(_PICKUP_COORDS)
    resource = make_resource(db, provider, **resource_kwargs)
    rescue_request = make_rescue_request(db, resource, status=RescueRequestStatus.MATCHED)
    recipient_user = make_user(db, role=UserRole.RECIPIENT)
    recipient_kwargs = dict(_DELIVERY_COORDS) if delivery else {}
    recipient = make_recipient(db, recipient_user, **recipient_kwargs)
    match = make_match(db, rescue_request, recipient=recipient)

    alloc_resp = client.post("/api/allocations", json={"match_id": str(match.id)}, headers=headers)
    assert alloc_resp.status_code == 201, alloc_resp.text

    create_resp = _create_operation(client, headers, rescue_request.id)
    assert create_resp.status_code == 201, create_resp.text
    operation_id = create_resp.json()["data"]["id"]

    return provider, headers, resource, rescue_request, recipient, operation_id


class TestOperationLocation:
    def test_updates_current_location(self, db, client):
        provider, headers, resource, rescue_request, recipient, operation_id = _setup_operation_with_coords(
            db, client
        )

        resp = client.patch(
            f"/api/operations/{operation_id}/location",
            json={"latitude": 12.98, "longitude": 77.60},
            headers=headers,
        )

        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]
        assert data["current_latitude"] == 12.98
        assert data["current_longitude"] == 77.60
        assert data["location_updated_at"] is not None

    def test_location_persists_on_subsequent_get(self, db, client):
        provider, headers, resource, rescue_request, recipient, operation_id = _setup_operation_with_coords(
            db, client
        )
        client.patch(
            f"/api/operations/{operation_id}/location",
            json={"latitude": 12.98, "longitude": 77.60},
            headers=headers,
        )

        resp = client.get("/api/operations", params={"rescue_request_id": str(rescue_request.id)}, headers=headers)

        item = resp.json()["data"]["items"][0]
        assert item["current_latitude"] == 12.98
        assert item["current_longitude"] == 77.60

    def test_updating_location_again_overwrites_the_previous_fix(self, db, client):
        provider, headers, resource, rescue_request, recipient, operation_id = _setup_operation_with_coords(
            db, client
        )
        client.patch(
            f"/api/operations/{operation_id}/location",
            json={"latitude": 12.98, "longitude": 77.60},
            headers=headers,
        )

        resp = client.patch(
            f"/api/operations/{operation_id}/location",
            json={"latitude": 13.00, "longitude": 77.65},
            headers=headers,
        )

        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]
        assert data["current_latitude"] == 13.00
        assert data["current_longitude"] == 77.65

    def test_route_distance_and_duration_match_location_service(self, db, client):
        provider, headers, resource, rescue_request, recipient, operation_id = _setup_operation_with_coords(
            db, client
        )

        resp = client.get("/api/operations", params={"rescue_request_id": str(rescue_request.id)}, headers=headers)
        leg = resp.json()["data"]["items"][0]["route"][0]

        expected_distance = haversine_km(
            _PICKUP_COORDS["latitude"],
            _PICKUP_COORDS["longitude"],
            _DELIVERY_COORDS["latitude"],
            _DELIVERY_COORDS["longitude"],
        )
        expected_duration = estimate_travel_duration_minutes(expected_distance)

        assert leg["target_type"] == "RECIPIENT"
        assert leg["distance_km"] == round(expected_distance, 2)
        assert leg["estimated_duration_minutes"] == round(expected_duration, 1)
        assert leg["distance_km"] > 0

    def test_route_is_null_when_coordinates_missing(self, db, client):
        provider, headers, resource, rescue_request, recipient, operation_id = _setup_operation_with_coords(
            db, client, pickup=False, delivery=False
        )

        resp = client.get("/api/operations", params={"rescue_request_id": str(rescue_request.id)}, headers=headers)
        leg = resp.json()["data"]["items"][0]["route"][0]

        assert leg["distance_km"] is None
        assert leg["estimated_duration_minutes"] is None

    def test_invalid_latitude_is_rejected(self, db, client):
        provider, headers, resource, rescue_request, recipient, operation_id = _setup_operation_with_coords(
            db, client
        )

        resp = client.patch(
            f"/api/operations/{operation_id}/location",
            json={"latitude": 200, "longitude": 77.60},
            headers=headers,
        )

        assert resp.status_code == 422, resp.text

    def test_invalid_longitude_is_rejected(self, db, client):
        provider, headers, resource, rescue_request, recipient, operation_id = _setup_operation_with_coords(
            db, client
        )

        resp = client.patch(
            f"/api/operations/{operation_id}/location",
            json={"latitude": 12.98, "longitude": -200},
            headers=headers,
        )

        assert resp.status_code == 422, resp.text

    def test_requires_authentication(self, db, client):
        provider, headers, resource, rescue_request, recipient, operation_id = _setup_operation_with_coords(
            db, client
        )

        resp = client.patch(
            f"/api/operations/{operation_id}/location", json={"latitude": 12.98, "longitude": 77.60}
        )

        assert resp.status_code == 401, resp.text

    def test_unrelated_user_cannot_update_location(self, db, client):
        provider, headers, resource, rescue_request, recipient, operation_id = _setup_operation_with_coords(
            db, client
        )
        other = make_user(db, role=UserRole.PROVIDER, email="unrelated@example.com")
        other_headers = login_headers(client, other.email)

        resp = client.patch(
            f"/api/operations/{operation_id}/location",
            json={"latitude": 12.98, "longitude": 77.60},
            headers=other_headers,
        )

        assert resp.status_code == 403, resp.text
        assert resp.json()["error"]["code"] == "NOT_AUTHORIZED"

    def test_assigned_partner_can_update_location(self, db, client):
        provider = make_user(db, role=UserRole.PROVIDER)
        headers = login_headers(client, provider.email)
        resource = make_resource(db, provider, status=ResourceStatus.MATCHING, **_PICKUP_COORDS)
        rescue_request = make_rescue_request(db, resource, status=RescueRequestStatus.MATCHED)
        recipient_user = make_user(db, role=UserRole.RECIPIENT)
        recipient = make_recipient(db, recipient_user, **_DELIVERY_COORDS)
        match = make_match(db, rescue_request, recipient=recipient)
        alloc_resp = client.post("/api/allocations", json={"match_id": str(match.id)}, headers=headers)
        assert alloc_resp.status_code == 201, alloc_resp.text

        partner_user = make_user(db, role=UserRole.RESCUE_PARTNER)
        partner = make_rescue_partner(db, partner_user, accepts_food=True)
        create_resp = _create_operation(client, headers, rescue_request.id, partner_id=str(partner.id))
        operation_id = create_resp.json()["data"]["id"]
        partner_headers = login_headers(client, partner_user.email)

        resp = client.patch(
            f"/api/operations/{operation_id}/location",
            json={"latitude": 12.98, "longitude": 77.60},
            headers=partner_headers,
        )

        assert resp.status_code == 200, resp.text

    def test_unknown_operation_returns_404(self, db, client):
        provider = make_user(db, role=UserRole.PROVIDER)
        headers = login_headers(client, provider.email)

        resp = client.patch(
            f"/api/operations/{uuid.uuid4()}/location",
            json={"latitude": 12.98, "longitude": 77.60},
            headers=headers,
        )

        assert resp.status_code == 404, resp.text
        assert resp.json()["error"]["code"] == "OPERATION_NOT_FOUND"

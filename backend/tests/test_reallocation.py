"""
Integration tests for POST /api/operations/{operation_id}/reallocate.

Shared fixtures/helpers (db, client, make_user, login_headers,
make_resource, make_recipient, make_rescue_request, make_match,
make_rescue_partner) live in tests/conftest.py. Builds the real
match -> allocate -> operate -> reallocate flow through the actual
endpoints, same convention as tests/test_operations.py. Run with:

    export DATABASE_URL=postgresql+psycopg2://postgres:postgres@localhost:5432/reserve_test
    pytest tests/test_reallocation.py -v
"""

import uuid

from app.models.allocation import Allocation
from app.models.enums import (
    AllocationStatus,
    OperationEventType,
    OperationStatus,
    ResourceStatus,
    RescueRequestStatus,
    UserRole,
)
from app.models.operation import OperationEvent

from tests.conftest import (
    login_headers,
    make_match,
    make_recipient,
    make_rescue_partner,
    make_rescue_request,
    make_resource,
    make_user,
)

MG_ROAD = dict(latitude=12.9758, longitude=77.6045)
CHURCH_STREET = dict(latitude=12.9762, longitude=77.6033)  # ~1.5km from MG Road — eligible replacement
FAR_AWAY = dict(latitude=19.0760, longitude=72.8777)  # ~840km from MG Road — Mumbai


def _setup_operation(db, client, *, with_replacement=True, quantity=80):
    """Provider + resource + rescue request + a PENDING allocation to
    `recipient`, linked into a PLANNED operation, through the real
    matching -> allocate -> operate flow. Optionally seeds a second,
    eligible recipient who should be picked up as the replacement."""
    provider = make_user(db, role=UserRole.PROVIDER)
    headers = login_headers(client, provider.email)

    resource = make_resource(db, provider, quantity=quantity, status=ResourceStatus.MATCHING, **MG_ROAD)
    rescue_request = make_rescue_request(db, resource, status=RescueRequestStatus.MATCHED)

    recipient_user = make_user(db, role=UserRole.RECIPIENT, email="original@example.com")
    recipient = make_recipient(
        db, recipient_user, organization_name="Original Shelter", current_availability=True, **CHURCH_STREET
    )
    match = make_match(db, rescue_request, recipient=recipient)

    alloc_resp = client.post(
        "/api/allocations",
        json={"match_id": str(match.id), "allocated_quantity": quantity},
        headers=headers,
    )
    assert alloc_resp.status_code == 201, alloc_resp.text
    allocation_id = alloc_resp.json()["data"]["id"]

    op_resp = client.post("/api/operations", json={"rescue_request_id": str(rescue_request.id)}, headers=headers)
    assert op_resp.status_code == 201, op_resp.text
    operation_id = op_resp.json()["data"]["id"]

    replacement = None
    if with_replacement:
        replacement_user = make_user(db, role=UserRole.RECIPIENT, email="replacement@example.com")
        replacement = make_recipient(
            db,
            replacement_user,
            organization_name="Backup NGO",
            current_availability=True,
            **CHURCH_STREET,
        )

    return provider, headers, resource, rescue_request, recipient, allocation_id, operation_id, replacement


class TestReallocationHappyPath:
    def test_finds_replacement_and_reassigns(self, db, client):
        provider, headers, resource, rescue_request, recipient, allocation_id, operation_id, replacement = (
            _setup_operation(db, client)
        )

        resp = client.post(
            f"/api/operations/{operation_id}/reallocate",
            json={"allocation_id": allocation_id, "reason": "Recipient reported unavailable"},
            headers=headers,
        )

        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]
        assert data["reallocated"] is True
        assert data["cancelled_allocation"]["id"] == allocation_id
        assert data["cancelled_allocation"]["status"] == "REALLOCATED"
        assert data["new_allocation"] is not None
        assert data["new_allocation"]["recipient"]["id"] == str(replacement.id)
        assert data["new_allocation"]["allocated_quantity"] == 80
        assert "Recipient reported unavailable" in data["new_allocation"]["reason"]

        # Original recipient flipped unavailable (that's the trigger condition modeled).
        db.refresh(recipient)
        assert recipient.current_availability is False

        # Old allocation is REALLOCATED, not silently deleted; new one is PENDING.
        old_alloc = db.query(Allocation).filter(Allocation.id == uuid.UUID(allocation_id)).first()
        assert old_alloc.status == AllocationStatus.REALLOCATED
        new_alloc = db.query(Allocation).filter(Allocation.id == uuid.UUID(data["new_allocation"]["id"])).first()
        assert new_alloc.status == AllocationStatus.PENDING
        assert new_alloc.operation_id == uuid.UUID(operation_id)

        # Operation has a REALLOCATED audit event.
        events = db.query(OperationEvent).filter(OperationEvent.operation_id == uuid.UUID(operation_id)).all()
        assert any(e.event_type == OperationEventType.REALLOCATED for e in events)

        # Resource stays fully committed (quantity fully replaced 1:1).
        db.refresh(resource)
        assert resource.status == ResourceStatus.ALLOCATED

    def test_reallocation_is_deterministic_prefers_closer_eligible_recipient(self, db, client):
        provider, headers, resource, rescue_request, recipient, allocation_id, operation_id, close_replacement = (
            _setup_operation(db, client)
        )
        # A second, farther-away eligible candidate — closer one should still win.
        far_user = make_user(db, role=UserRole.RECIPIENT, email="far@example.com")
        make_recipient(
            db,
            far_user,
            organization_name="Far NGO",
            current_availability=True,
            service_area_km=2000,
            **FAR_AWAY,
        )

        resp = client.post(
            f"/api/operations/{operation_id}/reallocate",
            json={"allocation_id": allocation_id, "reason": "Recipient unreachable"},
            headers=headers,
        )

        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]
        assert data["new_allocation"]["recipient"]["id"] == str(close_replacement.id)


class TestReallocationNoReplacement:
    def test_no_eligible_replacement_still_cancels_allocation(self, db, client):
        provider, headers, resource, rescue_request, recipient, allocation_id, operation_id, _ = _setup_operation(
            db, client, with_replacement=False
        )

        resp = client.post(
            f"/api/operations/{operation_id}/reallocate",
            json={"allocation_id": allocation_id, "reason": "Recipient closed permanently"},
            headers=headers,
        )

        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]
        assert data["reallocated"] is False
        assert data["new_allocation"] is None
        assert data["cancelled_allocation"]["status"] == "REALLOCATED"

        db.refresh(resource)
        assert resource.status == ResourceStatus.MATCHING  # quantity is unassigned again

        events = db.query(OperationEvent).filter(OperationEvent.operation_id == uuid.UUID(operation_id)).all()
        reallocation_events = [e for e in events if e.event_type == OperationEventType.REALLOCATED]
        assert len(reallocation_events) == 1
        assert "no eligible" in reallocation_events[0].description.lower()


class TestReallocationPermissionsAndValidation:
    def test_non_owner_non_partner_cannot_reallocate(self, db, client):
        provider, headers, resource, rescue_request, recipient, allocation_id, operation_id, _ = _setup_operation(
            db, client
        )
        stranger = make_user(db, role=UserRole.PROVIDER)
        stranger_headers = login_headers(client, stranger.email)

        resp = client.post(
            f"/api/operations/{operation_id}/reallocate",
            json={"allocation_id": allocation_id, "reason": "trying to interfere"},
            headers=stranger_headers,
        )

        assert resp.status_code == 403
        assert resp.json()["error"]["code"] == "NOT_AUTHORIZED"

    def test_assigned_partner_can_reallocate(self, db, client):
        provider, headers, resource, rescue_request, recipient, allocation_id, operation_id, replacement = (
            _setup_operation(db, client)
        )
        partner_user = make_user(db, role=UserRole.RESCUE_PARTNER)
        partner = make_rescue_partner(db, partner_user)
        # Assign the partner to the operation via a status update-adjacent path isn't available;
        # simplest is to set it directly and commit, mirroring how create_operation would have.
        from app.models.operation import RescueOperation

        operation = db.query(RescueOperation).filter(RescueOperation.id == uuid.UUID(operation_id)).first()
        operation.partner_id = partner.id
        db.commit()

        partner_headers = login_headers(client, partner_user.email)
        resp = client.post(
            f"/api/operations/{operation_id}/reallocate",
            json={"allocation_id": allocation_id, "reason": "Reported unavailable on pickup"},
            headers=partner_headers,
        )

        assert resp.status_code == 200, resp.text
        assert resp.json()["data"]["reallocated"] is True

    def test_returns_404_for_allocation_not_on_operation(self, db, client):
        provider, headers, resource, rescue_request, recipient, allocation_id, operation_id, _ = _setup_operation(
            db, client
        )

        resp = client.post(
            f"/api/operations/{operation_id}/reallocate",
            json={"allocation_id": str(uuid.uuid4()), "reason": "bogus allocation"},
            headers=headers,
        )

        assert resp.status_code == 404
        assert resp.json()["error"]["code"] == "ALLOCATION_NOT_FOUND_ON_OPERATION"

    def test_cannot_reallocate_already_reallocated_allocation(self, db, client):
        provider, headers, resource, rescue_request, recipient, allocation_id, operation_id, _ = _setup_operation(
            db, client
        )
        first = client.post(
            f"/api/operations/{operation_id}/reallocate",
            json={"allocation_id": allocation_id, "reason": "first reallocation"},
            headers=headers,
        )
        assert first.status_code == 200, first.text

        second = client.post(
            f"/api/operations/{operation_id}/reallocate",
            json={"allocation_id": allocation_id, "reason": "trying again on the same allocation"},
            headers=headers,
        )

        assert second.status_code == 409
        assert second.json()["error"]["code"] == "ALLOCATION_NOT_ACTIVE"

    def test_cannot_reallocate_completed_operation(self, db, client):
        provider, headers, resource, rescue_request, recipient, allocation_id, operation_id, _ = _setup_operation(
            db, client
        )
        for target_status, reason in (("IN_TRANSIT", None), ("DELIVERED", None), ("COMPLETED", None)):
            payload = {"status": target_status}
            if reason:
                payload["reason"] = reason
            step = client.patch(f"/api/operations/{operation_id}/status", json=payload, headers=headers)
            assert step.status_code == 200, step.text

        resp = client.post(
            f"/api/operations/{operation_id}/reallocate",
            json={"allocation_id": allocation_id, "reason": "too late now"},
            headers=headers,
        )

        assert resp.status_code == 409
        assert resp.json()["error"]["code"] == "OPERATION_NOT_REALLOCATABLE"

    def test_unauthenticated_request_is_rejected(self, db, client):
        provider, headers, resource, rescue_request, recipient, allocation_id, operation_id, _ = _setup_operation(
            db, client
        )

        resp = client.post(
            f"/api/operations/{operation_id}/reallocate",
            json={"allocation_id": allocation_id, "reason": "no auth"},
        )

        assert resp.status_code == 401

    def test_reason_is_required(self, db, client):
        provider, headers, resource, rescue_request, recipient, allocation_id, operation_id, _ = _setup_operation(
            db, client
        )

        resp = client.post(
            f"/api/operations/{operation_id}/reallocate",
            json={"allocation_id": allocation_id, "reason": ""},
            headers=headers,
        )

        assert resp.status_code == 422

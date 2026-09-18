"""
Integration tests for DELETE /api/resources/{resource_id}.

Shared fixtures/helpers (db, client, make_user, login_headers,
make_resource, make_rescue_request) live in tests/conftest.py. Run with:

    export DATABASE_URL=postgresql+psycopg2://postgres:postgres@localhost:5432/reserve_test
    pytest tests/test_resource_delete.py -v
"""

import uuid

import pytest

from app.models.allocation import Allocation
from app.models.enums import (
    AllocationStatus,
    OperationStatus,
    ResourceStatus,
    RescueRequestStatus,
    UserRole,
)
from app.models.operation import RescueOperation
from app.models.resource import Resource

from tests.conftest import login_headers, make_resource, make_rescue_request, make_user


class TestDeleteResourcePermissions:
    def test_owner_can_delete_their_own_resource(self, client, db):
        provider = make_user(db, role=UserRole.PROVIDER)
        resource = make_resource(db, provider)
        headers = login_headers(client, provider.email)

        resp = client.delete(f"/api/resources/{resource.id}", headers=headers)

        assert resp.status_code == 200, resp.text
        assert resp.json()["success"] is True
        assert db.query(Resource).filter(Resource.id == resource.id).first() is None

    def test_admin_can_delete_someone_elses_resource(self, client, db):
        provider = make_user(db, role=UserRole.PROVIDER)
        admin = make_user(db, role=UserRole.ADMIN)
        resource = make_resource(db, provider)
        headers = login_headers(client, admin.email)

        resp = client.delete(f"/api/resources/{resource.id}", headers=headers)

        assert resp.status_code == 200, resp.text
        assert db.query(Resource).filter(Resource.id == resource.id).first() is None

    def test_non_owner_provider_cannot_delete(self, client, db):
        owner = make_user(db, role=UserRole.PROVIDER)
        other = make_user(db, role=UserRole.PROVIDER)
        resource = make_resource(db, owner)
        headers = login_headers(client, other.email)

        resp = client.delete(f"/api/resources/{resource.id}", headers=headers)

        assert resp.status_code == 403
        assert resp.json()["error"]["code"] == "NOT_RESOURCE_OWNER"
        assert db.query(Resource).filter(Resource.id == resource.id).first() is not None

    def test_recipient_role_cannot_delete_someone_elses_resource(self, client, db):
        owner = make_user(db, role=UserRole.PROVIDER)
        recipient = make_user(db, role=UserRole.RECIPIENT)
        resource = make_resource(db, owner)
        headers = login_headers(client, recipient.email)

        resp = client.delete(f"/api/resources/{resource.id}", headers=headers)

        assert resp.status_code == 403
        assert resp.json()["error"]["code"] == "NOT_RESOURCE_OWNER"

    def test_delete_requires_authentication(self, client, db):
        provider = make_user(db, role=UserRole.PROVIDER)
        resource = make_resource(db, provider)

        resp = client.delete(f"/api/resources/{resource.id}")

        assert resp.status_code == 401


class TestDeleteResourceMissing:
    def test_missing_resource_returns_404(self, client, db):
        provider = make_user(db, role=UserRole.PROVIDER)
        headers = login_headers(client, provider.email)

        resp = client.delete(f"/api/resources/{uuid.uuid4()}", headers=headers)

        assert resp.status_code == 404
        assert resp.json()["error"]["code"] == "RESOURCE_NOT_FOUND"

    def test_malformed_resource_id_returns_422(self, client, db):
        provider = make_user(db, role=UserRole.PROVIDER)
        headers = login_headers(client, provider.email)

        resp = client.delete("/api/resources/not-a-uuid", headers=headers)

        assert resp.status_code == 422

    def test_deleting_twice_returns_404_the_second_time(self, client, db):
        provider = make_user(db, role=UserRole.PROVIDER)
        resource = make_resource(db, provider)
        headers = login_headers(client, provider.email)

        first = client.delete(f"/api/resources/{resource.id}", headers=headers)
        second = client.delete(f"/api/resources/{resource.id}", headers=headers)

        assert first.status_code == 200
        assert second.status_code == 404


class TestDeleteResourceLockedByOwnStatus:
    @pytest.mark.parametrize(
        "status", [ResourceStatus.ALLOCATED, ResourceStatus.IN_TRANSIT, ResourceStatus.DELIVERED]
    )
    def test_locked_statuses_block_deletion(self, client, db, status):
        provider = make_user(db, role=UserRole.PROVIDER)
        resource = make_resource(db, provider, status=status)
        headers = login_headers(client, provider.email)

        resp = client.delete(f"/api/resources/{resource.id}", headers=headers)

        assert resp.status_code == 409
        assert resp.json()["error"]["code"] == "RESOURCE_LOCKED"
        assert db.query(Resource).filter(Resource.id == resource.id).first() is not None

    def test_admin_is_also_blocked_by_locked_status(self, client, db):
        provider = make_user(db, role=UserRole.PROVIDER)
        admin = make_user(db, role=UserRole.ADMIN)
        resource = make_resource(db, provider, status=ResourceStatus.IN_TRANSIT)
        headers = login_headers(client, admin.email)

        resp = client.delete(f"/api/resources/{resource.id}", headers=headers)

        assert resp.status_code == 409
        assert resp.json()["error"]["code"] == "RESOURCE_LOCKED"

    @pytest.mark.parametrize("status", [ResourceStatus.AVAILABLE, ResourceStatus.CANCELLED, ResourceStatus.EXPIRED])
    def test_non_locked_statuses_with_no_history_can_be_deleted(self, client, db, status):
        provider = make_user(db, role=UserRole.PROVIDER)
        resource = make_resource(db, provider, status=status)
        headers = login_headers(client, provider.email)

        resp = client.delete(f"/api/resources/{resource.id}", headers=headers)

        assert resp.status_code == 200, resp.text


class TestDeleteResourceActiveRescueChain:
    """
    Resource.status is the fast common-case guard, but a resource's own
    status can in principle lag behind its RescueRequest/Allocation/
    RescueOperation state. These tests hold the resource's own status at
    AVAILABLE/MATCHING (i.e. NOT one of the LOCKED_STATUSES) while giving
    it non-terminal history downstream, to prove the deeper check catches
    what the status-only check would miss.
    """

    @pytest.mark.parametrize(
        "rr_status",
        [
            RescueRequestStatus.PENDING,
            RescueRequestStatus.MATCHING,
            RescueRequestStatus.MATCHED,
            RescueRequestStatus.PARTIALLY_MATCHED,
        ],
    )
    def test_active_rescue_request_blocks_deletion(self, client, db, rr_status):
        provider = make_user(db, role=UserRole.PROVIDER)
        resource = make_resource(db, provider, status=ResourceStatus.AVAILABLE)
        make_rescue_request(db, resource, rr_status)
        headers = login_headers(client, provider.email)

        resp = client.delete(f"/api/resources/{resource.id}", headers=headers)

        assert resp.status_code == 409
        assert resp.json()["error"]["code"] == "RESOURCE_HAS_ACTIVE_OPERATIONS"
        assert db.query(Resource).filter(Resource.id == resource.id).first() is not None

    @pytest.mark.parametrize("alloc_status", [AllocationStatus.PENDING, AllocationStatus.CONFIRMED])
    def test_active_allocation_blocks_deletion(self, client, db, alloc_status):
        provider = make_user(db, role=UserRole.PROVIDER)
        resource = make_resource(db, provider, status=ResourceStatus.MATCHING)
        rr = make_rescue_request(db, resource, RescueRequestStatus.MATCHED)
        allocation = Allocation(
            rescue_request_id=rr.id,
            recipient_id=None,
            rescue_hub_id=None,
            allocated_quantity=resource.quantity,
            status=alloc_status,
        )
        # allocation_target_xor requires exactly one of recipient/hub set;
        # a fixed dummy recipient isn't needed for this check since we
        # only exercise the resource-deletion guard, but the DB
        # constraint must still be satisfied to insert the row.
        allocation.rescue_hub_id = uuid.uuid4()
        db.add(allocation)
        db.commit()
        headers = login_headers(client, provider.email)

        resp = client.delete(f"/api/resources/{resource.id}", headers=headers)

        assert resp.status_code == 409
        assert resp.json()["error"]["code"] == "RESOURCE_HAS_ACTIVE_OPERATIONS"

    @pytest.mark.parametrize(
        "op_status",
        [
            OperationStatus.CREATED,
            OperationStatus.MATCHED,
            OperationStatus.PARTNER_ASSIGNED,
            OperationStatus.PICKUP_IN_PROGRESS,
            OperationStatus.REALLOCATING,
        ],
    )
    def test_active_operation_blocks_deletion(self, client, db, op_status):
        provider = make_user(db, role=UserRole.PROVIDER)
        resource = make_resource(db, provider, status=ResourceStatus.MATCHING)
        rr = make_rescue_request(db, resource, RescueRequestStatus.MATCHED)
        operation = RescueOperation(rescue_request_id=rr.id, status=op_status)
        db.add(operation)
        db.commit()
        headers = login_headers(client, provider.email)

        resp = client.delete(f"/api/resources/{resource.id}", headers=headers)

        assert resp.status_code == 409
        assert resp.json()["error"]["code"] == "RESOURCE_HAS_ACTIVE_OPERATIONS"

    def test_only_terminal_history_can_still_be_deleted(self, client, db):
        provider = make_user(db, role=UserRole.PROVIDER)
        resource = make_resource(db, provider, status=ResourceStatus.CANCELLED)
        rr = make_rescue_request(db, resource, RescueRequestStatus.CANCELLED)
        allocation = Allocation(
            rescue_request_id=rr.id,
            rescue_hub_id=uuid.uuid4(),
            allocated_quantity=resource.quantity,
            status=AllocationStatus.CANCELLED,
        )
        db.add(allocation)
        operation = RescueOperation(rescue_request_id=rr.id, status=OperationStatus.CANCELLED)
        db.add(operation)
        db.commit()
        headers = login_headers(client, provider.email)

        resp = client.delete(f"/api/resources/{resource.id}", headers=headers)

        assert resp.status_code == 200, resp.text


class TestExistingCrudStillWorks:
    """Smoke tests that POST/GET/PUT weren't broken by the delete changes."""

    def test_create_list_get_update_still_work(self, client, db):
        provider = make_user(db, role=UserRole.PROVIDER)
        headers = login_headers(client, provider.email)

        create_resp = client.post(
            "/api/resources",
            headers=headers,
            json={
                "title": "50 sandwiches",
                "resource_type": "FOOD",
                "quantity": 50,
                "unit": "sandwiches",
                "location_address": "Test Kitchen, Bengaluru",
            },
        )
        assert create_resp.status_code == 201, create_resp.text
        resource_id = create_resp.json()["data"]["id"]

        list_resp = client.get("/api/resources", headers=headers)
        assert list_resp.status_code == 200
        assert list_resp.json()["data"]["total"] >= 1

        get_resp = client.get(f"/api/resources/{resource_id}", headers=headers)
        assert get_resp.status_code == 200
        assert get_resp.json()["data"]["title"] == "50 sandwiches"

        update_resp = client.put(
            f"/api/resources/{resource_id}", headers=headers, json={"quantity": 60}
        )
        assert update_resp.status_code == 200
        assert update_resp.json()["data"]["quantity"] == 60

        delete_resp = client.delete(f"/api/resources/{resource_id}", headers=headers)
        assert delete_resp.status_code == 200

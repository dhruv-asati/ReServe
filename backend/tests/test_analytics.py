"""
Integration tests for GET /api/analytics/overview.

Shared fixtures/helpers (db, client, make_user, login_headers,
make_resource, make_recipient, make_rescue_request, make_match) live in
tests/conftest.py. Allocation/RescueOperation rows that don't need the
full match->allocate->operate flow are constructed directly via the ORM
here, same convention as tests/test_operations.py uses for its own
one-off fixtures. Run with:

    export DATABASE_URL=postgresql+psycopg2://postgres:postgres@localhost:5432/reserve_test
    pytest tests/test_analytics.py -v
"""

import uuid

from app.models.allocation import Allocation
from app.models.enums import (
    AllocationStatus,
    OperationStatus,
    ResourceStatus,
    RescueRequestStatus,
    UserRole,
)
from app.models.operation import RescueOperation

from tests.conftest import login_headers, make_match, make_recipient, make_rescue_request, make_resource, make_user


def _get_overview(client, headers):
    resp = client.get("/api/analytics/overview", headers=headers)
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]


def _make_operation(db, rescue_request, status: OperationStatus) -> RescueOperation:
    operation = RescueOperation(rescue_request_id=rescue_request.id, status=status)
    db.add(operation)
    db.commit()
    db.refresh(operation)
    return operation


def _make_allocation(db, rescue_request, recipient, status: AllocationStatus, quantity: float) -> Allocation:
    allocation = Allocation(
        rescue_request_id=rescue_request.id,
        recipient_id=recipient.id,
        allocated_quantity=quantity,
        status=status,
    )
    db.add(allocation)
    db.commit()
    db.refresh(allocation)
    return allocation


class TestAnalyticsOverviewBasics:
    def test_requires_authentication(self, db, client):
        resp = client.get("/api/analytics/overview")
        assert resp.status_code == 401

    def test_empty_platform_returns_zeros(self, db, client):
        user = make_user(db, role=UserRole.ADMIN)
        headers = login_headers(client, user.email)

        data = _get_overview(client, headers)

        assert data["total_resources"] == 0
        assert data["available_resources"] == 0
        assert data["allocated_resources"] == 0
        assert data["completed_operations"] == 0
        assert data["pending_operations"] == 0
        assert data["total_quantity_rescued"] == 0
        assert "generated_at" in data


class TestAnalyticsResourceCounts:
    def test_counts_resources_by_status(self, db, client):
        provider = make_user(db, role=UserRole.PROVIDER)
        headers = login_headers(client, provider.email)

        make_resource(db, provider, status=ResourceStatus.AVAILABLE)
        make_resource(db, provider, status=ResourceStatus.AVAILABLE)
        make_resource(db, provider, status=ResourceStatus.ALLOCATED)
        make_resource(db, provider, status=ResourceStatus.DELIVERED)
        make_resource(db, provider, status=ResourceStatus.CANCELLED)

        data = _get_overview(client, headers)

        assert data["total_resources"] == 5
        assert data["available_resources"] == 2
        assert data["allocated_resources"] == 1
        # DELIVERED/CANCELLED resources still count toward the total but not
        # toward either of the two status-specific buckets requested.
        assert data["available_resources"] + data["allocated_resources"] < data["total_resources"]


class TestAnalyticsOperationCounts:
    def test_counts_operations_by_status(self, db, client):
        provider = make_user(db, role=UserRole.PROVIDER)
        headers = login_headers(client, provider.email)

        statuses = [
            OperationStatus.PLANNED,
            OperationStatus.PLANNED,
            OperationStatus.IN_TRANSIT,
            OperationStatus.DELIVERED,
            OperationStatus.COMPLETED,
            OperationStatus.COMPLETED,
            OperationStatus.FAILED,
        ]
        for status in statuses:
            resource = make_resource(db, provider)
            rescue_request = make_rescue_request(db, resource, status=RescueRequestStatus.MATCHED)
            _make_operation(db, rescue_request, status)

        data = _get_overview(client, headers)

        assert data["pending_operations"] == 2  # PLANNED
        assert data["completed_operations"] == 2  # COMPLETED
        # IN_TRANSIT/DELIVERED/FAILED are neither "pending" nor "completed" here.


class TestAnalyticsQuantityRescued:
    def test_sums_only_delivered_allocations(self, db, client):
        provider = make_user(db, role=UserRole.PROVIDER)
        headers = login_headers(client, provider.email)
        resource = make_resource(db, provider, quantity=200)
        rescue_request = make_rescue_request(db, resource, status=RescueRequestStatus.MATCHED)
        recipient_user = make_user(db, role=UserRole.RECIPIENT)
        recipient = make_recipient(db, recipient_user)

        _make_allocation(db, rescue_request, recipient, AllocationStatus.DELIVERED, 30)
        _make_allocation(db, rescue_request, recipient, AllocationStatus.DELIVERED, 20)
        _make_allocation(db, rescue_request, recipient, AllocationStatus.PENDING, 15)
        _make_allocation(db, rescue_request, recipient, AllocationStatus.CONFIRMED, 25)
        _make_allocation(db, rescue_request, recipient, AllocationStatus.CANCELLED, 10)
        _make_allocation(db, rescue_request, recipient, AllocationStatus.REALLOCATED, 5)

        data = _get_overview(client, headers)

        assert data["total_quantity_rescued"] == 50  # only the two DELIVERED rows: 30 + 20


class TestAnalyticsEndToEndFlow:
    def test_reflects_real_delivery_through_the_full_flow(self, db, client):
        """Goes through the genuine post -> match -> allocate -> operate ->
        deliver flow via the real endpoints, and checks the overview
        reflects it — not a synthetic fixture."""
        provider = make_user(db, role=UserRole.PROVIDER)
        headers = login_headers(client, provider.email)

        resource = make_resource(db, provider, quantity=80, status=ResourceStatus.MATCHING)
        rescue_request = make_rescue_request(db, resource, status=RescueRequestStatus.MATCHED)
        recipient_user = make_user(db, role=UserRole.RECIPIENT)
        recipient = make_recipient(db, recipient_user)
        match = make_match(db, rescue_request, recipient=recipient)

        before = _get_overview(client, headers)

        alloc_resp = client.post("/api/allocations", json={"match_id": str(match.id)}, headers=headers)
        assert alloc_resp.status_code == 201, alloc_resp.text

        after_allocation = _get_overview(client, headers)
        assert after_allocation["allocated_resources"] == before["allocated_resources"] + 1
        assert after_allocation["total_quantity_rescued"] == before["total_quantity_rescued"]  # not delivered yet

        op_resp = client.post("/api/operations", json={"rescue_request_id": str(rescue_request.id)}, headers=headers)
        assert op_resp.status_code == 201, op_resp.text
        operation_id = op_resp.json()["data"]["id"]

        after_operation = _get_overview(client, headers)
        assert after_operation["pending_operations"] == before["pending_operations"] + 1  # PLANNED

        client.patch(f"/api/operations/{operation_id}/status", json={"status": "IN_TRANSIT"}, headers=headers)
        deliver_resp = client.patch(
            f"/api/operations/{operation_id}/status", json={"status": "DELIVERED"}, headers=headers
        )
        assert deliver_resp.status_code == 200, deliver_resp.text

        after_delivery = _get_overview(client, headers)
        assert after_delivery["total_quantity_rescued"] == before["total_quantity_rescued"] + 80
        assert after_delivery["pending_operations"] == before["pending_operations"]  # moved on from PLANNED

        complete_resp = client.patch(
            f"/api/operations/{operation_id}/status", json={"status": "COMPLETED"}, headers=headers
        )
        assert complete_resp.status_code == 200, complete_resp.text

        after_completion = _get_overview(client, headers)
        assert after_completion["completed_operations"] == before["completed_operations"] + 1

"""
Integration tests for the dashboard feeds:

    GET /api/dashboard/overview
    GET /api/resources/at-risk
    GET /api/operations/active
    GET /api/activity/recent
    GET /api/network/locations
    GET /api/network/organizations

Shared fixtures/helpers live in tests/conftest.py. Run with:

    export DATABASE_URL=postgresql+psycopg2://postgres:postgres@localhost:5432/reserve_test
    pytest tests/test_dashboard.py -v
"""

from datetime import datetime, timedelta, timezone

import pytest

from app.models.allocation import Allocation
from app.models.enums import (
    AllocationStatus,
    OperationStatus,
    RescueRequestStatus,
    ResourceStatus,
    UserRole,
)
from app.models.operation import RescueOperation

from tests.conftest import (
    login_headers,
    make_recipient,
    make_rescue_hub,
    make_rescue_request,
    make_resource,
    make_user,
)

DASHBOARD_ENDPOINTS = [
    "/api/dashboard/overview",
    "/api/resources/at-risk",
    "/api/operations/active",
    "/api/activity/recent",
    "/api/network/locations",
    "/api/network/organizations",
]


def _get(client, path, headers):
    resp = client.get(path, headers=headers)
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]


@pytest.mark.parametrize("path", DASHBOARD_ENDPOINTS)
def test_requires_authentication(db, client, path):
    assert client.get(path).status_code == 401


class TestEmptyPlatform:
    def test_overview_is_all_zeros(self, db, client):
        headers = login_headers(client, make_user(db, role=UserRole.ADMIN).email)

        data = _get(client, "/api/dashboard/overview", headers)

        assert data["resourcesRescued"]["value"] == 0
        assert data["activeRescues"]["value"] == 0
        assert data["atRiskResources"]["value"] == 0
        assert data["successfulAllocations"]["value"] == 0

    @pytest.mark.parametrize(
        "path",
        ["/api/resources/at-risk", "/api/operations/active", "/api/activity/recent", "/api/network/locations"],
    )
    def test_list_feeds_are_empty(self, db, client, path):
        headers = login_headers(client, make_user(db, role=UserRole.ADMIN).email)
        assert _get(client, path, headers) == []


class TestAtRisk:
    def test_route_is_not_captured_by_resource_id(self, db, client):
        # Regression: declared after GET /{resource_id}, "at-risk" was parsed
        # as a UUID and rejected with 422.
        headers = login_headers(client, make_user(db, role=UserRole.ADMIN).email)
        assert client.get("/api/resources/at-risk", headers=headers).status_code == 200

    def test_only_unrescued_resources_expiring_soon(self, db, client):
        provider = make_user(db, role=UserRole.PROVIDER)
        headers = login_headers(client, provider.email)
        now = datetime.now(timezone.utc)

        soon = make_resource(db, provider, title="Soon", expiry_time=now + timedelta(hours=2))
        make_resource(db, provider, title="Far away", expiry_time=now + timedelta(hours=48))
        make_resource(db, provider, title="Already past", expiry_time=now - timedelta(hours=1))
        make_resource(
            db, provider, title="Allocated", status=ResourceStatus.ALLOCATED, expiry_time=now + timedelta(hours=2)
        )
        make_resource(db, provider, title="No deadline")

        items = _get(client, "/api/resources/at-risk", headers)

        assert [item["resource"] for item in items] == ["Soon"]
        assert items[0]["id"] == str(soon.id)
        assert items[0]["resourceType"] == "food"
        assert items[0]["deadline"].endswith("remaining")
        assert _get(client, "/api/dashboard/overview", headers)["atRiskResources"]["value"] == 1


class TestActiveOperationsAndOverview:
    def _operation(self, db, status, allocation_status=AllocationStatus.CONFIRMED):
        provider = make_user(db, role=UserRole.PROVIDER)
        provider.organization_name = "Grand Plaza Hotel"
        db.commit()
        resource = make_resource(db, provider, title="Dinner buffet", quantity=40, unit="meals")
        rescue_request = make_rescue_request(db, resource, RescueRequestStatus.MATCHED)
        recipient = make_recipient(
            db, make_user(db, role=UserRole.RECIPIENT), organization_name="Hope Shelter", latitude=12.9, longitude=77.6
        )
        operation = RescueOperation(rescue_request_id=rescue_request.id, status=status)
        db.add(operation)
        db.flush()
        db.add(
            Allocation(
                rescue_request_id=rescue_request.id,
                operation_id=operation.id,
                recipient_id=recipient.id,
                allocated_quantity=40,
                status=allocation_status,
            )
        )
        db.commit()
        return operation

    def test_active_operation_shape(self, db, client):
        operation = self._operation(db, OperationStatus.IN_TRANSIT)
        headers = login_headers(client, make_user(db, role=UserRole.ADMIN).email)

        items = _get(client, "/api/operations/active", headers)

        assert len(items) == 1
        assert items[0] == {
            "id": str(operation.id),
            "resource": "Dinner buffet",
            "resourceType": "food",
            "quantity": "40 meals",
            "provider": "Grand Plaza Hotel",
            "recipient": "Hope Shelter",
            "status": "in_transit",
            "eta": "In transit",
        }

    def test_completed_operations_are_not_active(self, db, client):
        self._operation(db, OperationStatus.COMPLETED)
        headers = login_headers(client, make_user(db, role=UserRole.ADMIN).email)
        assert _get(client, "/api/operations/active", headers) == []

    def test_overview_counts_delivered_and_in_flight(self, db, client):
        self._operation(db, OperationStatus.DELIVERED, AllocationStatus.DELIVERED)
        self._operation(db, OperationStatus.PLANNED)
        headers = login_headers(client, make_user(db, role=UserRole.ADMIN).email)

        data = _get(client, "/api/dashboard/overview", headers)

        assert data["resourcesRescued"]["value"] == 40
        assert data["activeRescues"]["value"] == 1  # only the PLANNED one is in flight
        assert data["successfulAllocations"]["value"] == 1
        assert data["successfulAllocations"]["delta"] == "100% success rate"


class TestActivityAndNetwork:
    def test_activity_includes_newly_created_resource(self, db, client):
        provider = make_user(db, role=UserRole.PROVIDER)
        make_resource(db, provider, title="Bakery surplus")
        headers = login_headers(client, provider.email)

        items = _get(client, "/api/activity/recent", headers)

        assert len(items) == 1
        assert items[0]["stage"] == "created"
        assert items[0]["time"] == "just now"
        assert "Bakery surplus" in items[0]["description"]

    def test_network_locations_skip_rows_without_coordinates(self, db, client):
        make_recipient(db, make_user(db, role=UserRole.RECIPIENT), organization_name="Placed", latitude=1.5, longitude=2.5)
        make_recipient(db, make_user(db, role=UserRole.RECIPIENT), organization_name="Unplaced")
        make_rescue_hub(db, name="Night Hub", latitude=3.5, longitude=4.5)
        headers = login_headers(client, make_user(db, role=UserRole.ADMIN).email)

        items = _get(client, "/api/network/locations", headers)

        by_role = {item["role"]: item for item in items}
        assert sorted(by_role) == ["hub", "recipient"]
        assert by_role["recipient"]["name"] == "Placed"
        assert (by_role["hub"]["lat"], by_role["hub"]["lng"]) == (3.5, 4.5)

    def test_network_organizations_match_directory_shape(self, db, client):
        make_recipient(
            db,
            make_user(db, role=UserRole.RECIPIENT),
            organization_name="Hope Shelter",
            location_address="12 Church Street, Bengaluru",
            latitude=12.97,
            longitude=77.6,
            capacity=40,
        )
        make_recipient(db, make_user(db, role=UserRole.RECIPIENT), organization_name="Unplaced")
        make_rescue_hub(db, name="Night Hub", latitude=13.0, longitude=77.5, capacity=100, current_load=90)
        headers = login_headers(client, make_user(db, role=UserRole.ADMIN).email)

        items = _get(client, "/api/network/organizations", headers)

        by_type = {item["type"]: item for item in items}
        assert sorted(by_type) == ["hub", "shelter"]  # unplaced recipient skipped

        shelter = by_type["shelter"]
        assert shelter["name"] == "Hope Shelter"
        assert (shelter["area"], shelter["city"]) == ("12 Church Street", "Bengaluru")
        assert shelter["position"] == {"lat": 12.97, "lng": 77.6}
        assert shelter["resourceTypes"] == ["food"]
        assert shelter["capacity"]["value"] == 40
        assert shelter["availability"] == "available"
        assert shelter["verification"] == "verified"

        hub = by_type["hub"]
        assert hub["availability"] == "limited"  # 90 / 100 held
        assert hub["workload"] == {"active": 90, "max": 100, "label": "Currently held"}
        assert hub["verification"] is None

"""
Integration tests for the two analytics breakdown endpoints:

    GET /api/analytics/trends
    GET /api/analytics/resource-types

Shared fixtures/helpers (db, client, make_user, login_headers,
make_resource, make_recipient, make_rescue_request) live in
tests/conftest.py. Allocation/RescueOperation rows are constructed
directly via the ORM, same convention as tests/test_analytics.py. Run
with:

    export DATABASE_URL=postgresql+psycopg2://postgres:postgres@localhost:5432/reserve_test
    pytest tests/test_analytics_trends.py -v

Rows are backdated by writing created_at/delivered_at/completed_at
explicitly — every timestamp written here is timezone-aware UTC, matching
how the service buckets days, so these tests don't depend on the database
server's own timezone setting.
"""

from datetime import datetime, timedelta, timezone

from app.models.allocation import Allocation
from app.models.enums import (
    AllocationStatus,
    OperationStatus,
    ResourceStatus,
    ResourceType,
    RescueRequestStatus,
    UserRole,
)
from app.models.operation import RescueOperation

from tests.conftest import login_headers, make_recipient, make_rescue_request, make_resource, make_user


def _get(client, headers, path):
    resp = client.get(path, headers=headers)
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]


def _backdate(db, obj, days_ago: int, field: str = "created_at"):
    """Move a row's timestamp `days_ago` days into the past (UTC)."""
    setattr(obj, field, datetime.now(timezone.utc) - timedelta(days=days_ago))
    db.commit()
    db.refresh(obj)
    return obj


def _make_operation(db, rescue_request, status: OperationStatus) -> RescueOperation:
    operation = RescueOperation(rescue_request_id=rescue_request.id, status=status)
    db.add(operation)
    db.commit()
    db.refresh(operation)
    return operation


def _make_allocation(db, rescue_request, recipient, status, quantity, operation=None) -> Allocation:
    allocation = Allocation(
        rescue_request_id=rescue_request.id,
        recipient_id=recipient.id,
        allocated_quantity=quantity,
        status=status,
        operation_id=operation.id if operation is not None else None,
    )
    db.add(allocation)
    db.commit()
    db.refresh(allocation)
    return allocation


# ---------------------------------------------------------------------------
# GET /api/analytics/trends
# ---------------------------------------------------------------------------


class TestTrendsBasics:
    def test_requires_authentication(self, db, client):
        assert client.get("/api/analytics/trends").status_code == 401

    def test_empty_platform_returns_zero_filled_window(self, db, client):
        user = make_user(db, role=UserRole.ADMIN)
        headers = login_headers(client, user.email)

        data = _get(client, headers, "/api/analytics/trends")

        assert data["window_days"] == 14
        assert len(data["daily"]) == 14
        assert data["total_resources_posted"] == 0
        assert data["total_quantity_posted"] == 0
        assert data["total_operations_started"] == 0
        assert data["total_operations_completed"] == 0
        assert data["total_quantity_delivered"] == 0
        # Zero-filled, not omitted — a client can chart this directly.
        assert all(point["resources_posted"] == 0 for point in data["daily"])

    def test_window_is_contiguous_and_ordered_oldest_first(self, db, client):
        user = make_user(db, role=UserRole.ADMIN)
        headers = login_headers(client, user.email)

        data = _get(client, headers, "/api/analytics/trends?days=30")

        days = [point["day"] for point in data["daily"]]
        assert len(days) == 30 == data["window_days"]
        assert days == sorted(days)
        assert len(set(days)) == 30  # no duplicate buckets
        assert days[0] == data["start_day"]
        assert days[-1] == data["end_day"]

    def test_rejects_out_of_range_days(self, db, client):
        user = make_user(db, role=UserRole.ADMIN)
        headers = login_headers(client, user.email)

        assert client.get("/api/analytics/trends?days=0", headers=headers).status_code == 422
        assert client.get("/api/analytics/trends?days=91", headers=headers).status_code == 422


class TestTrendsResourceActivity:
    def test_buckets_resources_by_day_posted(self, db, client):
        provider = make_user(db, role=UserRole.PROVIDER)
        headers = login_headers(client, provider.email)

        _backdate(db, make_resource(db, provider, quantity=10), 0)
        _backdate(db, make_resource(db, provider, quantity=20), 2)
        _backdate(db, make_resource(db, provider, quantity=30), 2)

        data = _get(client, headers, "/api/analytics/trends?days=7")
        by_day = {point["day"]: point for point in data["daily"]}

        today = data["end_day"]
        two_days_ago = data["daily"][-3]["day"]

        assert by_day[today]["resources_posted"] == 1
        assert by_day[today]["quantity_posted"] == 10
        assert by_day[two_days_ago]["resources_posted"] == 2
        assert by_day[two_days_ago]["quantity_posted"] == 50
        assert data["total_resources_posted"] == 3
        assert data["total_quantity_posted"] == 60

    def test_excludes_activity_older_than_the_window(self, db, client):
        provider = make_user(db, role=UserRole.PROVIDER)
        headers = login_headers(client, provider.email)

        _backdate(db, make_resource(db, provider, quantity=10), 1)
        _backdate(db, make_resource(db, provider, quantity=999), 40)  # well outside a 7-day window

        data = _get(client, headers, "/api/analytics/trends?days=7")

        assert data["total_resources_posted"] == 1
        assert data["total_quantity_posted"] == 10

    def test_totals_equal_the_sum_of_the_daily_series(self, db, client):
        provider = make_user(db, role=UserRole.PROVIDER)
        headers = login_headers(client, provider.email)

        for days_ago in (0, 1, 1, 3, 5):
            _backdate(db, make_resource(db, provider, quantity=7), days_ago)

        data = _get(client, headers, "/api/analytics/trends?days=14")

        assert data["total_resources_posted"] == sum(p["resources_posted"] for p in data["daily"])
        assert data["total_quantity_posted"] == sum(p["quantity_posted"] for p in data["daily"])


class TestTrendsOperationActivity:
    def test_counts_operations_started_and_completed_separately(self, db, client):
        provider = make_user(db, role=UserRole.PROVIDER)
        headers = login_headers(client, provider.email)

        # Started 3 days ago, completed today — the two must land in
        # different buckets, not both on created_at.
        resource = make_resource(db, provider)
        rescue_request = make_rescue_request(db, resource, status=RescueRequestStatus.MATCHED)
        operation = _make_operation(db, rescue_request, OperationStatus.COMPLETED)
        operation.completed_at = datetime.now(timezone.utc)
        db.commit()
        _backdate(db, operation, 3)

        data = _get(client, headers, "/api/analytics/trends?days=7")
        by_day = {point["day"]: point for point in data["daily"]}

        assert by_day[data["daily"][-4]["day"]]["operations_started"] == 1
        assert by_day[data["end_day"]]["operations_completed"] == 1
        assert data["total_operations_started"] == 1
        assert data["total_operations_completed"] == 1

    def test_operation_without_completed_at_is_not_counted_as_completed(self, db, client):
        provider = make_user(db, role=UserRole.PROVIDER)
        headers = login_headers(client, provider.email)

        resource = make_resource(db, provider)
        rescue_request = make_rescue_request(db, resource, status=RescueRequestStatus.MATCHED)
        _make_operation(db, rescue_request, OperationStatus.PLANNED)

        data = _get(client, headers, "/api/analytics/trends?days=7")

        assert data["total_operations_started"] == 1
        assert data["total_operations_completed"] == 0

    def test_delivered_quantity_buckets_by_operation_delivery_day(self, db, client):
        provider = make_user(db, role=UserRole.PROVIDER)
        headers = login_headers(client, provider.email)
        recipient = make_recipient(db, make_user(db, role=UserRole.RECIPIENT))

        resource = make_resource(db, provider, quantity=100)
        rescue_request = make_rescue_request(db, resource, status=RescueRequestStatus.MATCHED)
        operation = _make_operation(db, rescue_request, OperationStatus.DELIVERED)
        operation.delivered_at = datetime.now(timezone.utc) - timedelta(days=1)
        db.commit()

        _make_allocation(db, rescue_request, recipient, AllocationStatus.DELIVERED, 40, operation)
        # Not delivered — must not be counted.
        _make_allocation(db, rescue_request, recipient, AllocationStatus.PENDING, 25, operation)

        data = _get(client, headers, "/api/analytics/trends?days=7")
        yesterday = data["daily"][-2]["day"]
        by_day = {point["day"]: point for point in data["daily"]}

        assert by_day[yesterday]["quantity_delivered"] == 40
        assert data["total_quantity_delivered"] == 40


# ---------------------------------------------------------------------------
# GET /api/analytics/resource-types
# ---------------------------------------------------------------------------


class TestResourceTypeStats:
    def test_requires_authentication(self, db, client):
        assert client.get("/api/analytics/resource-types").status_code == 401

    def test_empty_platform_lists_every_type_zero_filled(self, db, client):
        user = make_user(db, role=UserRole.ADMIN)
        headers = login_headers(client, user.email)

        data = _get(client, headers, "/api/analytics/resource-types")

        assert data["total_resources"] == 0
        types = {row["resource_type"]: row for row in data["by_resource_type"]}
        # Every type is present even with nothing posted — a real zero,
        # not a missing key.
        assert set(types) == {t.value for t in ResourceType}
        for row in types.values():
            assert row["resource_count"] == 0
            assert row["total_quantity"] == 0
            assert row["share_percent"] == 0
            assert row["quantity_rescued"] == 0

    def test_counts_and_quantities_split_by_type(self, db, client):
        provider = make_user(db, role=UserRole.PROVIDER)
        headers = login_headers(client, provider.email)

        make_resource(db, provider, resource_type=ResourceType.FOOD, quantity=10)
        make_resource(db, provider, resource_type=ResourceType.FOOD, quantity=20)
        make_resource(db, provider, resource_type=ResourceType.FOOD, quantity=30)
        make_resource(db, provider, resource_type=ResourceType.MEDICAL, quantity=5)

        data = _get(client, headers, "/api/analytics/resource-types")
        types = {row["resource_type"]: row for row in data["by_resource_type"]}

        assert data["total_resources"] == 4
        assert types["FOOD"]["resource_count"] == 3
        assert types["FOOD"]["total_quantity"] == 60
        assert types["FOOD"]["share_percent"] == 75.0
        assert types["MEDICAL"]["resource_count"] == 1
        assert types["MEDICAL"]["total_quantity"] == 5
        assert types["MEDICAL"]["share_percent"] == 25.0
        # Shares are a percentage of the same total.
        assert sum(row["share_percent"] for row in data["by_resource_type"]) == 100.0

    def test_status_breakdown_per_type(self, db, client):
        provider = make_user(db, role=UserRole.PROVIDER)
        headers = login_headers(client, provider.email)

        make_resource(db, provider, status=ResourceStatus.AVAILABLE)
        make_resource(db, provider, status=ResourceStatus.AVAILABLE)
        make_resource(db, provider, status=ResourceStatus.ALLOCATED)
        make_resource(db, provider, status=ResourceStatus.DELIVERED)
        make_resource(db, provider, status=ResourceStatus.CANCELLED)
        make_resource(db, provider, resource_type=ResourceType.MEDICAL, status=ResourceStatus.ALLOCATED)

        data = _get(client, headers, "/api/analytics/resource-types")
        types = {row["resource_type"]: row for row in data["by_resource_type"]}

        assert types["FOOD"]["available_count"] == 2
        assert types["FOOD"]["allocated_count"] == 1
        assert types["FOOD"]["delivered_count"] == 1
        # CANCELLED counts toward the type total but no status bucket here.
        assert types["FOOD"]["resource_count"] == 5
        assert types["MEDICAL"]["allocated_count"] == 1
        assert types["MEDICAL"]["available_count"] == 0

    def test_quantity_rescued_counts_only_delivered_allocations(self, db, client):
        provider = make_user(db, role=UserRole.PROVIDER)
        headers = login_headers(client, provider.email)
        recipient = make_recipient(db, make_user(db, role=UserRole.RECIPIENT))

        food = make_resource(db, provider, resource_type=ResourceType.FOOD, quantity=200)
        food_request = make_rescue_request(db, food, status=RescueRequestStatus.MATCHED)
        _make_allocation(db, food_request, recipient, AllocationStatus.DELIVERED, 30)
        _make_allocation(db, food_request, recipient, AllocationStatus.DELIVERED, 20)
        _make_allocation(db, food_request, recipient, AllocationStatus.PENDING, 15)
        _make_allocation(db, food_request, recipient, AllocationStatus.CANCELLED, 10)

        medical = make_resource(db, provider, resource_type=ResourceType.MEDICAL, quantity=100)
        medical_request = make_rescue_request(db, medical, status=RescueRequestStatus.MATCHED)
        _make_allocation(db, medical_request, recipient, AllocationStatus.DELIVERED, 7)

        data = _get(client, headers, "/api/analytics/resource-types")
        types = {row["resource_type"]: row for row in data["by_resource_type"]}

        assert types["FOOD"]["quantity_rescued"] == 50  # 30 + 20 only
        assert types["MEDICAL"]["quantity_rescued"] == 7

    def test_agrees_with_the_overview_endpoint(self, db, client):
        """The two endpoints compute the same underlying facts different
        ways; they must not disagree."""
        provider = make_user(db, role=UserRole.PROVIDER)
        headers = login_headers(client, provider.email)
        recipient = make_recipient(db, make_user(db, role=UserRole.RECIPIENT))

        make_resource(db, provider, resource_type=ResourceType.FOOD, status=ResourceStatus.AVAILABLE)
        make_resource(db, provider, resource_type=ResourceType.MEDICAL, status=ResourceStatus.ALLOCATED)
        resource = make_resource(db, provider, quantity=80)
        rescue_request = make_rescue_request(db, resource, status=RescueRequestStatus.MATCHED)
        _make_allocation(db, rescue_request, recipient, AllocationStatus.DELIVERED, 80)

        by_type = _get(client, headers, "/api/analytics/resource-types")
        overview = _get(client, headers, "/api/analytics/overview")

        assert by_type["total_resources"] == overview["total_resources"]
        assert sum(row["available_count"] for row in by_type["by_resource_type"]) == overview[
            "available_resources"
        ]
        assert sum(row["allocated_count"] for row in by_type["by_resource_type"]) == overview[
            "allocated_resources"
        ]
        assert sum(row["quantity_rescued"] for row in by_type["by_resource_type"]) == overview[
            "total_quantity_rescued"
        ]

"""
Integration tests for in-app notifications:

    GET   /api/notifications
    PATCH /api/notifications/{notification_id}/read

plus the four events that raise them (allocation confirmed, operation
assigned, reallocation, operation failed).

Shared fixtures/helpers (db, client, make_user, login_headers,
make_resource, make_recipient, make_rescue_request, make_match,
make_rescue_partner) live in tests/conftest.py. Builds the real
match -> allocate -> operate flow through the actual endpoints, same
convention as tests/test_reallocation.py. Run with:

    export DATABASE_URL=postgresql+psycopg2://postgres:postgres@localhost:5432/reserve_test
    pytest tests/test_notifications.py -v
"""

import uuid

from app.models.enums import (
    NotificationType,
    ResourceStatus,
    RescueRequestStatus,
    UserRole,
)
from app.models.notification import Notification

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
CHURCH_STREET = dict(latitude=12.9762, longitude=77.6033)  # ~1.5km away — eligible


def _notifications_for(db, user) -> list[Notification]:
    return (
        db.query(Notification)
        .filter(Notification.user_id == user.id)
        .order_by(Notification.created_at.asc())
        .all()
    )


def _types_for(db, user) -> set:
    return {n.notification_type for n in _notifications_for(db, user)}


def _setup_allocation(db, client, *, quantity=80):
    """Provider + resource + rescue request + recipient + PROPOSED match,
    then a real allocation through POST /api/allocations."""
    provider = make_user(db, role=UserRole.PROVIDER)
    headers = login_headers(client, provider.email)

    resource = make_resource(db, provider, quantity=quantity, status=ResourceStatus.MATCHING, **MG_ROAD)
    rescue_request = make_rescue_request(db, resource, status=RescueRequestStatus.MATCHED)

    recipient_user = make_user(db, role=UserRole.RECIPIENT, email="recipient@example.com")
    recipient = make_recipient(
        db, recipient_user, organization_name="Hope Shelter", current_availability=True, **CHURCH_STREET
    )
    match = make_match(db, rescue_request, recipient=recipient)

    resp = client.post(
        "/api/allocations",
        json={"match_id": str(match.id), "allocated_quantity": quantity},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text

    return provider, headers, resource, rescue_request, recipient_user, recipient, resp.json()["data"]["id"]


class TestAllocationConfirmedNotifications:
    def test_recipient_and_provider_are_both_notified(self, db, client):
        provider, _, _, _, recipient_user, _, _ = _setup_allocation(db, client)

        assert NotificationType.MATCH_FOUND in _types_for(db, recipient_user)
        assert NotificationType.MATCH_FOUND in _types_for(db, provider)

    def test_message_names_the_quantity_and_resource(self, db, client):
        _, _, resource, _, recipient_user, _, _ = _setup_allocation(db, client, quantity=40)

        messages = [n.message for n in _notifications_for(db, recipient_user)]
        assert any("40" in m and resource.title in m for m in messages), messages

    def test_notifications_start_unread(self, db, client):
        _, _, _, _, recipient_user, _, _ = _setup_allocation(db, client)

        assert all(n.is_read is False for n in _notifications_for(db, recipient_user))

    def test_hub_allocation_notifies_provider_without_failing(self, db, client):
        """A RescueHub has no owning user, so only the provider is
        notified — the allocation must still succeed."""
        from tests.conftest import make_rescue_hub

        provider = make_user(db, role=UserRole.PROVIDER)
        headers = login_headers(client, provider.email)
        resource = make_resource(db, provider, quantity=50, status=ResourceStatus.MATCHING, **MG_ROAD)
        rescue_request = make_rescue_request(db, resource, status=RescueRequestStatus.MATCHED)
        hub = make_rescue_hub(db)
        match = make_match(db, rescue_request, rescue_hub_id=hub.id)

        resp = client.post("/api/allocations", json={"match_id": str(match.id)}, headers=headers)

        assert resp.status_code == 201, resp.text
        assert NotificationType.MATCH_FOUND in _types_for(db, provider)


class TestOperationAssignedNotifications:
    def test_partner_and_provider_notified_on_assignment(self, db, client):
        provider, headers, _, rescue_request, _, _, _ = _setup_allocation(db, client)
        partner_user = make_user(db, role=UserRole.RESCUE_PARTNER, email="partner@example.com")
        partner = make_rescue_partner(db, partner_user)

        resp = client.post(
            "/api/operations",
            json={"rescue_request_id": str(rescue_request.id), "partner_id": str(partner.id)},
            headers=headers,
        )
        assert resp.status_code == 201, resp.text

        assert NotificationType.PARTNER_ASSIGNED in _types_for(db, partner_user)
        assert NotificationType.PARTNER_ASSIGNED in _types_for(db, provider)

    def test_notification_links_to_the_operation(self, db, client):
        _, headers, _, rescue_request, _, _, _ = _setup_allocation(db, client)
        partner_user = make_user(db, role=UserRole.RESCUE_PARTNER, email="partner2@example.com")
        partner = make_rescue_partner(db, partner_user)

        resp = client.post(
            "/api/operations",
            json={"rescue_request_id": str(rescue_request.id), "partner_id": str(partner.id)},
            headers=headers,
        )
        operation_id = resp.json()["data"]["id"]

        notifications = _notifications_for(db, partner_user)
        assert notifications
        assert str(notifications[0].related_operation_id) == operation_id

    def test_no_partner_assigned_raises_no_partner_notification(self, db, client):
        provider, headers, _, rescue_request, _, _, _ = _setup_allocation(db, client)
        before = len(_notifications_for(db, provider))

        resp = client.post(
            "/api/operations", json={"rescue_request_id": str(rescue_request.id)}, headers=headers
        )
        assert resp.status_code == 201, resp.text

        after = _notifications_for(db, provider)
        assert len(after) == before
        assert NotificationType.PARTNER_ASSIGNED not in {n.notification_type for n in after}


class TestReallocationNotifications:
    def _setup_with_replacement(self, db, client):
        provider, headers, resource, rescue_request, recipient_user, recipient, allocation_id = _setup_allocation(
            db, client
        )
        replacement_user = make_user(db, role=UserRole.RECIPIENT, email="backup@example.com")
        replacement = make_recipient(
            db, replacement_user, organization_name="Backup NGO", current_availability=True, **CHURCH_STREET
        )
        op_resp = client.post(
            "/api/operations", json={"rescue_request_id": str(rescue_request.id)}, headers=headers
        )
        assert op_resp.status_code == 201, op_resp.text
        return (
            provider,
            headers,
            recipient_user,
            replacement_user,
            allocation_id,
            op_resp.json()["data"]["id"],
        )

    def test_old_new_recipient_and_provider_all_notified(self, db, client):
        provider, headers, old_user, new_user, allocation_id, operation_id = self._setup_with_replacement(
            db, client
        )

        resp = client.post(
            f"/api/operations/{operation_id}/reallocate",
            json={"allocation_id": allocation_id, "reason": "Recipient became unreachable."},
            headers=headers,
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["data"]["reallocated"] is True

        assert NotificationType.REALLOCATION in _types_for(db, old_user)
        assert NotificationType.REALLOCATION in _types_for(db, new_user)
        assert NotificationType.REALLOCATION in _types_for(db, provider)

    def test_reason_is_included_for_the_displaced_recipient(self, db, client):
        _, headers, old_user, _, allocation_id, operation_id = self._setup_with_replacement(db, client)
        reason = "Recipient became unreachable."

        client.post(
            f"/api/operations/{operation_id}/reallocate",
            json={"allocation_id": allocation_id, "reason": reason},
            headers=headers,
        )

        messages = [
            n.message for n in _notifications_for(db, old_user)
            if n.notification_type == NotificationType.REALLOCATION
        ]
        assert any(reason in m for m in messages), messages

    def test_no_replacement_still_notifies_old_recipient_and_provider(self, db, client):
        provider, headers, _, rescue_request, recipient_user, _, allocation_id = _setup_allocation(db, client)
        op_resp = client.post(
            "/api/operations", json={"rescue_request_id": str(rescue_request.id)}, headers=headers
        )
        operation_id = op_resp.json()["data"]["id"]

        resp = client.post(
            f"/api/operations/{operation_id}/reallocate",
            json={"allocation_id": allocation_id, "reason": "No longer able to receive."},
            headers=headers,
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["data"]["reallocated"] is False

        assert NotificationType.REALLOCATION in _types_for(db, recipient_user)
        assert NotificationType.REALLOCATION in _types_for(db, provider)


class TestOperationFailedNotifications:
    def test_provider_partner_and_recipient_are_notified(self, db, client):
        provider, headers, _, rescue_request, recipient_user, _, _ = _setup_allocation(db, client)
        partner_user = make_user(db, role=UserRole.RESCUE_PARTNER, email="failpartner@example.com")
        partner = make_rescue_partner(db, partner_user)

        op_resp = client.post(
            "/api/operations",
            json={"rescue_request_id": str(rescue_request.id), "partner_id": str(partner.id)},
            headers=headers,
        )
        operation_id = op_resp.json()["data"]["id"]

        resp = client.patch(
            f"/api/operations/{operation_id}/status",
            json={"status": "FAILED", "reason": "Vehicle breakdown."},
            headers=headers,
        )
        assert resp.status_code == 200, resp.text

        assert NotificationType.OPERATION_UPDATE in _types_for(db, provider)
        assert NotificationType.OPERATION_UPDATE in _types_for(db, partner_user)
        assert NotificationType.OPERATION_UPDATE in _types_for(db, recipient_user)

    def test_failure_reason_is_in_the_message(self, db, client):
        provider, headers, _, rescue_request, _, _, _ = _setup_allocation(db, client)
        op_resp = client.post(
            "/api/operations", json={"rescue_request_id": str(rescue_request.id)}, headers=headers
        )
        operation_id = op_resp.json()["data"]["id"]

        client.patch(
            f"/api/operations/{operation_id}/status",
            json={"status": "FAILED", "reason": "Vehicle breakdown."},
            headers=headers,
        )

        messages = [
            n.message for n in _notifications_for(db, provider)
            if n.notification_type == NotificationType.OPERATION_UPDATE
        ]
        assert any("Vehicle breakdown." in m for m in messages), messages

    def test_successful_delivery_raises_no_failure_notification(self, db, client):
        provider, headers, _, rescue_request, _, _, _ = _setup_allocation(db, client)
        op_resp = client.post(
            "/api/operations", json={"rescue_request_id": str(rescue_request.id)}, headers=headers
        )
        operation_id = op_resp.json()["data"]["id"]

        client.patch(f"/api/operations/{operation_id}/status", json={"status": "IN_TRANSIT"}, headers=headers)
        client.patch(f"/api/operations/{operation_id}/status", json={"status": "DELIVERED"}, headers=headers)

        assert NotificationType.OPERATION_UPDATE not in _types_for(db, provider)


class TestOperationCompletedNotifications:
    def _run_to_completed(self, db, client, headers, operation_id):
        in_transit = client.patch(f"/api/operations/{operation_id}/status", json={"status": "IN_TRANSIT"}, headers=headers)
        assert in_transit.status_code == 200, in_transit.text
        delivered = client.patch(f"/api/operations/{operation_id}/status", json={"status": "DELIVERED"}, headers=headers)
        assert delivered.status_code == 200, delivered.text
        completed = client.patch(f"/api/operations/{operation_id}/status", json={"status": "COMPLETED"}, headers=headers)
        assert completed.status_code == 200, completed.text
        return completed

    def test_provider_and_recipient_notified_on_completion(self, db, client):
        provider, headers, _, rescue_request, recipient_user, _, _ = _setup_allocation(db, client)
        partner_user = make_user(db, role=UserRole.RESCUE_PARTNER, email="completepartner@example.com")
        partner = make_rescue_partner(db, partner_user)

        op_resp = client.post(
            "/api/operations",
            json={"rescue_request_id": str(rescue_request.id), "partner_id": str(partner.id)},
            headers=headers,
        )
        assert op_resp.status_code == 201, op_resp.text
        operation_id = op_resp.json()["data"]["id"]

        self._run_to_completed(db, client, headers, operation_id)

        assert NotificationType.DELIVERY_CONFIRMED in _types_for(db, provider)
        assert NotificationType.DELIVERY_CONFIRMED in _types_for(db, partner_user)
        assert NotificationType.DELIVERY_CONFIRMED in _types_for(db, recipient_user)

    def test_message_names_the_resource(self, db, client):
        provider, headers, resource, rescue_request, _, _, _ = _setup_allocation(db, client)
        op_resp = client.post(
            "/api/operations", json={"rescue_request_id": str(rescue_request.id)}, headers=headers
        )
        operation_id = op_resp.json()["data"]["id"]

        self._run_to_completed(db, client, headers, operation_id)

        messages = [
            n.message for n in _notifications_for(db, provider)
            if n.notification_type == NotificationType.DELIVERY_CONFIRMED
        ]
        assert any(resource.title in m for m in messages), messages

    def test_notification_links_to_the_operation(self, db, client):
        provider, headers, _, rescue_request, _, _, _ = _setup_allocation(db, client)
        op_resp = client.post(
            "/api/operations", json={"rescue_request_id": str(rescue_request.id)}, headers=headers
        )
        operation_id = op_resp.json()["data"]["id"]

        self._run_to_completed(db, client, headers, operation_id)

        completed_notifications = [
            n for n in _notifications_for(db, provider)
            if n.notification_type == NotificationType.DELIVERY_CONFIRMED
        ]
        assert completed_notifications
        assert str(completed_notifications[0].related_operation_id) == operation_id

    def test_no_notification_before_completed(self, db, client):
        provider, headers, _, rescue_request, _, _, _ = _setup_allocation(db, client)
        op_resp = client.post(
            "/api/operations", json={"rescue_request_id": str(rescue_request.id)}, headers=headers
        )
        operation_id = op_resp.json()["data"]["id"]

        client.patch(f"/api/operations/{operation_id}/status", json={"status": "IN_TRANSIT"}, headers=headers)
        client.patch(f"/api/operations/{operation_id}/status", json={"status": "DELIVERED"}, headers=headers)

        assert NotificationType.DELIVERY_CONFIRMED not in _types_for(db, provider)


class TestListNotifications:
    def test_requires_authentication(self, db, client):
        assert client.get("/api/notifications").status_code == 401

    def test_returns_only_the_callers_own_notifications(self, db, client):
        _, _, _, _, recipient_user, _, _ = _setup_allocation(db, client)
        recipient_headers = login_headers(client, recipient_user.email)

        resp = client.get("/api/notifications", headers=recipient_headers)

        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]
        assert data["total"] >= 1
        # Every returned row belongs to this user — a provider-targeted
        # notification for the same allocation must not leak through.
        own_ids = {str(n.id) for n in _notifications_for(db, recipient_user)}
        assert {item["id"] for item in data["items"]} <= own_ids

    def test_unread_count_is_reported(self, db, client):
        _, _, _, _, recipient_user, _, _ = _setup_allocation(db, client)
        headers = login_headers(client, recipient_user.email)

        data = client.get("/api/notifications", headers=headers).json()["data"]

        assert data["unread_count"] == data["total"]

    def test_filters_by_is_read(self, db, client):
        _, _, _, _, recipient_user, _, _ = _setup_allocation(db, client)
        headers = login_headers(client, recipient_user.email)

        unread = client.get("/api/notifications?is_read=false", headers=headers).json()["data"]
        read = client.get("/api/notifications?is_read=true", headers=headers).json()["data"]

        assert unread["total"] >= 1
        assert read["total"] == 0

    def test_filters_by_type(self, db, client):
        _, _, _, _, recipient_user, _, _ = _setup_allocation(db, client)
        headers = login_headers(client, recipient_user.email)

        resp = client.get("/api/notifications?type=MATCH_FOUND", headers=headers)

        assert resp.status_code == 200, resp.text
        assert all(i["notification_type"] == "MATCH_FOUND" for i in resp.json()["data"]["items"])

    def test_pagination_reports_has_more(self, db, client):
        _, _, _, _, recipient_user, _, _ = _setup_allocation(db, client)
        headers = login_headers(client, recipient_user.email)

        data = client.get("/api/notifications?limit=1", headers=headers).json()["data"]

        assert len(data["items"]) <= 1
        assert data["has_more"] == (data["total"] > 1)

    def test_user_with_no_notifications_gets_empty_list(self, db, client):
        bystander = make_user(db, role=UserRole.PROVIDER, email="bystander@example.com")
        headers = login_headers(client, bystander.email)

        data = client.get("/api/notifications", headers=headers).json()["data"]

        assert data["total"] == 0
        assert data["items"] == []
        assert data["unread_count"] == 0


class TestMarkNotificationRead:
    def test_requires_authentication(self, db, client):
        resp = client.patch(f"/api/notifications/{uuid.uuid4()}/read")
        assert resp.status_code == 401

    def test_marks_own_notification_read(self, db, client):
        _, _, _, _, recipient_user, _, _ = _setup_allocation(db, client)
        headers = login_headers(client, recipient_user.email)
        notification = _notifications_for(db, recipient_user)[0]

        resp = client.patch(f"/api/notifications/{notification.id}/read", headers=headers)

        assert resp.status_code == 200, resp.text
        assert resp.json()["data"]["is_read"] is True

    def test_unread_count_drops_after_marking_read(self, db, client):
        _, _, _, _, recipient_user, _, _ = _setup_allocation(db, client)
        headers = login_headers(client, recipient_user.email)
        before = client.get("/api/notifications", headers=headers).json()["data"]["unread_count"]
        notification = _notifications_for(db, recipient_user)[0]

        client.patch(f"/api/notifications/{notification.id}/read", headers=headers)

        after = client.get("/api/notifications", headers=headers).json()["data"]["unread_count"]
        assert after == before - 1

    def test_marking_twice_is_idempotent(self, db, client):
        _, _, _, _, recipient_user, _, _ = _setup_allocation(db, client)
        headers = login_headers(client, recipient_user.email)
        notification = _notifications_for(db, recipient_user)[0]

        first = client.patch(f"/api/notifications/{notification.id}/read", headers=headers)
        second = client.patch(f"/api/notifications/{notification.id}/read", headers=headers)

        assert first.status_code == 200
        assert second.status_code == 200, second.text
        assert second.json()["data"]["is_read"] is True

    def test_cannot_mark_someone_elses_notification(self, db, client):
        _, _, _, _, recipient_user, _, _ = _setup_allocation(db, client)
        notification = _notifications_for(db, recipient_user)[0]
        stranger = make_user(db, role=UserRole.PROVIDER, email="stranger@example.com")
        headers = login_headers(client, stranger.email)

        resp = client.patch(f"/api/notifications/{notification.id}/read", headers=headers)

        assert resp.status_code == 403
        assert resp.json()["error"]["code"] == "NOT_NOTIFICATION_OWNER"

    def test_admin_can_mark_any_notification(self, db, client):
        _, _, _, _, recipient_user, _, _ = _setup_allocation(db, client)
        notification = _notifications_for(db, recipient_user)[0]
        admin = make_user(db, role=UserRole.ADMIN, email="admin@example.com")
        headers = login_headers(client, admin.email)

        resp = client.patch(f"/api/notifications/{notification.id}/read", headers=headers)

        assert resp.status_code == 200, resp.text

    def test_unknown_id_returns_404(self, db, client):
        user = make_user(db, role=UserRole.PROVIDER, email="nobody@example.com")
        headers = login_headers(client, user.email)

        resp = client.patch(f"/api/notifications/{uuid.uuid4()}/read", headers=headers)

        assert resp.status_code == 404
        assert resp.json()["error"]["code"] == "NOTIFICATION_NOT_FOUND"

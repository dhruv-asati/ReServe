"""
Tests for the ResourceRequest system: POST/GET/PATCH(status)/DELETE
/api/requests. See tests/conftest.py for fixtures — requires a real
Postgres test database (same as the rest of this suite).
"""

from datetime import datetime, timedelta, timezone

from app.models.enums import ResourceRequestStatus, ResourceType, UserRole

from .conftest import login_headers, make_recipient, make_resource_request, make_user


def _future_iso(days=2):
    return (datetime.now(timezone.utc) + timedelta(days=days)).isoformat()


def _recipient_and_headers(db, client, **recipient_kwargs):
    user = make_user(db, role=UserRole.RECIPIENT, email=f"recipient+{id(recipient_kwargs)}@example.com")
    recipient = make_recipient(db, user, **recipient_kwargs)
    headers = login_headers(client, user.email)
    return user, recipient, headers


# --- Create -----------------------------------------------------------


def test_recipient_can_create_request(db, client):
    _, recipient, headers = _recipient_and_headers(db, client)

    resp = client.post(
        "/api/requests",
        headers=headers,
        json={
            "resource_type": "FOOD",
            "requested_quantity": 50,
            "urgency": "HIGH",
            "needed_by": _future_iso(),
            "eligibility_requirements": "Nut-free only.",
            "can_self_pickup": True,
            "notes": "Van available.",
        },
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()["data"]
    assert body["status"] == "PENDING"
    assert body["recipient_id"] == str(recipient.id)
    assert body["requesting_organization"] == recipient.organization_name
    # Creation appends the initial PENDING entry to status history.
    assert len(body["status_history"]) == 1
    assert body["status_history"][0]["to_status"] == "PENDING"
    assert body["status_history"][0]["from_status"] is None


def test_provider_cannot_create_request(db, client):
    provider = make_user(db, role=UserRole.PROVIDER)
    headers = login_headers(client, provider.email)

    resp = client.post(
        "/api/requests",
        headers=headers,
        json={"resource_type": "FOOD", "requested_quantity": 10, "needed_by": _future_iso()},
    )
    assert resp.status_code == 403


def test_create_rejects_past_deadline(db, client):
    _, _, headers = _recipient_and_headers(db, client)

    resp = client.post(
        "/api/requests",
        headers=headers,
        json={
            "resource_type": "FOOD",
            "requested_quantity": 10,
            "needed_by": (datetime.now(timezone.utc) - timedelta(days=1)).isoformat(),
        },
    )
    assert resp.status_code == 422


def test_create_rejects_non_positive_quantity(db, client):
    _, _, headers = _recipient_and_headers(db, client)

    resp = client.post(
        "/api/requests",
        headers=headers,
        json={"resource_type": "FOOD", "requested_quantity": 0, "needed_by": _future_iso()},
    )
    assert resp.status_code == 422


def test_create_rejects_unaccepted_resource_type(db, client):
    # Recipient profile only accepts FOOD by default.
    _, _, headers = _recipient_and_headers(db, client, accepts_food=True, accepts_medical=False)

    resp = client.post(
        "/api/requests",
        headers=headers,
        json={"resource_type": "MEDICAL", "requested_quantity": 10, "needed_by": _future_iso()},
    )
    assert resp.status_code == 422


def test_create_rejects_medical_without_verification(db, client):
    _, _, headers = _recipient_and_headers(
        db, client, accepts_food=True, accepts_medical=True, medical_verified=False
    )

    resp = client.post(
        "/api/requests",
        headers=headers,
        json={"resource_type": "MEDICAL", "requested_quantity": 10, "needed_by": _future_iso()},
    )
    assert resp.status_code == 403


def test_create_without_recipient_profile_fails(db, client):
    user = make_user(db, role=UserRole.RECIPIENT)
    headers = login_headers(client, user.email)

    resp = client.post(
        "/api/requests",
        headers=headers,
        json={"resource_type": "FOOD", "requested_quantity": 10, "needed_by": _future_iso()},
    )
    assert resp.status_code == 400


# --- List / Get ---------------------------------------------------------


def test_recipient_only_sees_own_requests(db, client):
    _, recipient_a, headers_a = _recipient_and_headers(db, client)
    _, recipient_b, _ = _recipient_and_headers(db, client)

    make_resource_request(db, recipient_a)
    make_resource_request(db, recipient_b)

    resp = client.get("/api/requests", headers=headers_a)
    assert resp.status_code == 200
    body = resp.json()["data"]
    assert body["total"] == 1
    assert body["items"][0]["recipient_id"] == str(recipient_a.id)


def test_provider_sees_all_requests(db, client):
    _, recipient_a, _ = _recipient_and_headers(db, client)
    _, recipient_b, _ = _recipient_and_headers(db, client)
    make_resource_request(db, recipient_a)
    make_resource_request(db, recipient_b)

    provider = make_user(db, role=UserRole.PROVIDER)
    headers = login_headers(client, provider.email)

    resp = client.get("/api/requests", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["data"]["total"] == 2


def test_get_missing_request_404(db, client):
    provider = make_user(db, role=UserRole.PROVIDER)
    headers = login_headers(client, provider.email)

    resp = client.get("/api/requests/00000000-0000-0000-0000-000000000000", headers=headers)
    assert resp.status_code == 404


def test_filter_by_status_and_type(db, client):
    _, recipient, headers = _recipient_and_headers(db, client, accepts_medical=True, medical_verified=True)
    make_resource_request(db, recipient, status=ResourceRequestStatus.PENDING, resource_type=ResourceType.FOOD)
    make_resource_request(db, recipient, status=ResourceRequestStatus.CANCELLED, resource_type=ResourceType.MEDICAL)

    resp = client.get("/api/requests?status=PENDING&resource_type=FOOD", headers=headers)
    assert resp.status_code == 200
    body = resp.json()["data"]
    assert body["total"] == 1
    assert body["items"][0]["status"] == "PENDING"


# --- Status transitions (update / cancel) --------------------------------


def test_provider_can_approve_then_fulfill(db, client):
    _, recipient, _ = _recipient_and_headers(db, client)
    request = make_resource_request(db, recipient)

    provider = make_user(db, role=UserRole.PROVIDER)
    provider_headers = login_headers(client, provider.email)

    resp = client.patch(
        f"/api/requests/{request.id}/status",
        headers=provider_headers,
        json={"status": "APPROVED", "note": "We can cover this."},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["data"]["status"] == "APPROVED"

    resp = client.patch(
        f"/api/requests/{request.id}/status",
        headers=provider_headers,
        json={"status": "FULFILLED"},
    )
    assert resp.status_code == 200
    body = resp.json()["data"]
    assert body["status"] == "FULFILLED"
    # PENDING (creation) -> APPROVED -> FULFILLED
    assert [h["to_status"] for h in body["status_history"]] == ["PENDING", "APPROVED", "FULFILLED"]


def test_recipient_cannot_approve_own_request(db, client):
    _, recipient, headers = _recipient_and_headers(db, client)
    request = make_resource_request(db, recipient)

    resp = client.patch(
        f"/api/requests/{request.id}/status",
        headers=headers,
        json={"status": "APPROVED"},
    )
    assert resp.status_code == 403


def test_recipient_can_cancel_own_pending_request(db, client):
    _, recipient, headers = _recipient_and_headers(db, client)
    request = make_resource_request(db, recipient)

    resp = client.patch(
        f"/api/requests/{request.id}/status",
        headers=headers,
        json={"status": "CANCELLED"},
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["status"] == "CANCELLED"


def test_recipient_cannot_cancel_others_request(db, client):
    _, recipient_a, _ = _recipient_and_headers(db, client)
    _, _, headers_b = _recipient_and_headers(db, client)
    request = make_resource_request(db, recipient_a)

    resp = client.patch(
        f"/api/requests/{request.id}/status",
        headers=headers_b,
        json={"status": "CANCELLED"},
    )
    assert resp.status_code == 403


def test_provider_cannot_cancel_request(db, client):
    _, recipient, _ = _recipient_and_headers(db, client)
    request = make_resource_request(db, recipient)

    provider = make_user(db, role=UserRole.PROVIDER)
    provider_headers = login_headers(client, provider.email)

    resp = client.patch(
        f"/api/requests/{request.id}/status",
        headers=provider_headers,
        json={"status": "CANCELLED"},
    )
    assert resp.status_code == 403


def test_cannot_transition_from_terminal_status(db, client):
    _, recipient, _ = _recipient_and_headers(db, client)
    request = make_resource_request(db, recipient, status=ResourceRequestStatus.REJECTED)

    provider = make_user(db, role=UserRole.PROVIDER)
    provider_headers = login_headers(client, provider.email)

    resp = client.patch(
        f"/api/requests/{request.id}/status",
        headers=provider_headers,
        json={"status": "APPROVED"},
    )
    assert resp.status_code == 409


def test_admin_can_cancel_any_request(db, client):
    _, recipient, _ = _recipient_and_headers(db, client)
    request = make_resource_request(db, recipient)

    admin = make_user(db, role=UserRole.ADMIN)
    admin_headers = login_headers(client, admin.email)

    resp = client.patch(
        f"/api/requests/{request.id}/status",
        headers=admin_headers,
        json={"status": "CANCELLED"},
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["status"] == "CANCELLED"


# --- Delete --------------------------------------------------------------


def test_owner_can_delete_pending_request(db, client):
    _, recipient, headers = _recipient_and_headers(db, client)
    request = make_resource_request(db, recipient)

    resp = client.delete(f"/api/requests/{request.id}", headers=headers)
    assert resp.status_code == 200

    resp = client.get(f"/api/requests/{request.id}", headers=headers)
    assert resp.status_code == 404


def test_cannot_delete_approved_request(db, client):
    _, recipient, headers = _recipient_and_headers(db, client)
    request = make_resource_request(db, recipient, status=ResourceRequestStatus.APPROVED)

    resp = client.delete(f"/api/requests/{request.id}", headers=headers)
    assert resp.status_code == 409


def test_other_recipient_cannot_delete_request(db, client):
    _, recipient_a, _ = _recipient_and_headers(db, client)
    _, _, headers_b = _recipient_and_headers(db, client)
    request = make_resource_request(db, recipient_a)

    resp = client.delete(f"/api/requests/{request.id}", headers=headers_b)
    assert resp.status_code == 403

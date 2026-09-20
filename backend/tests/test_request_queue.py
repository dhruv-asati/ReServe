"""
Integration tests for the Rescue Requests page queues:

    GET /api/requests/incoming
    GET /api/requests/outgoing
    GET /api/requests/completed

Regression: declared after GET /api/requests/{request_id}, these paths were
parsed as a UUID and rejected with 422. Run with:

    export DATABASE_URL=postgresql+psycopg2://postgres:postgres@localhost:5432/reserve_test
    pytest tests/test_request_queue.py -v
"""

import pytest

from app.models.enums import ResourceRequestStatus, ResourceType, UserRole

from tests.conftest import login_headers, make_recipient, make_resource_request, make_user

QUEUE_PATHS = ["/api/requests/incoming", "/api/requests/outgoing", "/api/requests/completed"]


def _get(client, path, headers):
    resp = client.get(path, headers=headers)
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]


@pytest.mark.parametrize("path", QUEUE_PATHS)
def test_requires_authentication(db, client, path):
    assert client.get(path).status_code == 401


@pytest.mark.parametrize("path", QUEUE_PATHS)
def test_not_captured_by_request_id_route(db, client, path):
    headers = login_headers(client, make_user(db, role=UserRole.ADMIN).email)
    assert _get(client, path, headers) == []


class TestRecipientView:
    def test_outgoing_is_own_open_requests_and_completed_is_own_final_ones(self, db, client):
        user = make_user(db, role=UserRole.RECIPIENT)
        mine = make_recipient(db, user, organization_name="Hope Shelter")
        other = make_recipient(db, make_user(db, role=UserRole.RECIPIENT), organization_name="Other Org")
        headers = login_headers(client, user.email)

        pending = make_resource_request(db, mine, status=ResourceRequestStatus.PENDING, requested_quantity=25)
        make_resource_request(db, mine, status=ResourceRequestStatus.APPROVED)
        make_resource_request(db, mine, status=ResourceRequestStatus.FULFILLED)
        make_resource_request(db, other, status=ResourceRequestStatus.PENDING)  # someone else's

        outgoing = _get(client, "/api/requests/outgoing", headers)
        assert len(outgoing) == 2
        assert {row["status"] for row in outgoing} == {"pending", "matched"}
        row = next(r for r in outgoing if r["id"] == str(pending.id))
        assert row["resourceType"] == "food"
        assert row["quantity"] == "25 units"
        assert row["recipient"] == "Hope Shelter"
        assert row["location"] == "12 Church Street, Bengaluru"
        assert row["deadline"].startswith("Tomorrow")

        completed = _get(client, "/api/requests/completed", headers)
        assert [r["status"] for r in completed] == ["delivered"]

        # Recipients never see other organizations' requests.
        assert _get(client, "/api/requests/incoming", headers) == []


class TestProviderView:
    def test_incoming_is_everyone_elses_open_requests(self, db, client):
        provider = make_user(db, role=UserRole.PROVIDER)
        headers = login_headers(client, provider.email)
        recipient = make_recipient(db, make_user(db, role=UserRole.RECIPIENT), organization_name="Hope Shelter")

        make_resource_request(db, recipient, status=ResourceRequestStatus.PENDING, resource_type=ResourceType.MEDICAL)
        make_resource_request(db, recipient, status=ResourceRequestStatus.REJECTED)
        make_resource_request(db, recipient, status=ResourceRequestStatus.CANCELLED)

        incoming = _get(client, "/api/requests/incoming", headers)
        assert [(r["status"], r["resourceType"]) for r in incoming] == [("pending", "medical")]

        # A provider has no recipient profile, so nothing is "outgoing".
        assert _get(client, "/api/requests/outgoing", headers) == []

        # Rejected shows as "cancelled" — the frontend has no rejected status.
        completed = _get(client, "/api/requests/completed", headers)
        assert sorted(r["status"] for r in completed) == ["cancelled", "cancelled"]

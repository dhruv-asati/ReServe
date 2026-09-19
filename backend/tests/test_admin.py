"""
Integration tests for admin endpoints:

    GET   /api/admin/users
    PATCH /api/admin/partners/{partner_id}/verify
    PATCH /api/admin/recipients/{recipient_id}/verify

Shared fixtures/helpers (db, client, make_user, login_headers,
make_recipient, make_rescue_partner) live in tests/conftest.py. Run with:

    export DATABASE_URL=postgresql+psycopg2://postgres:postgres@localhost:5432/reserve_test
    pytest tests/test_admin.py -v
"""

import uuid

from app.models.enums import UserRole

from tests.conftest import login_headers, make_recipient, make_rescue_partner, make_user


class TestListUsersAuthorization:
    def test_requires_authentication(self, db, client):
        resp = client.get("/api/admin/users")
        assert resp.status_code == 401

    def test_non_admin_is_forbidden(self, db, client):
        provider = make_user(db, role=UserRole.PROVIDER)
        headers = login_headers(client, provider.email)

        resp = client.get("/api/admin/users", headers=headers)

        assert resp.status_code == 403
        assert resp.json()["error"]["code"] == "FORBIDDEN_ROLE"

    def test_recipient_is_forbidden(self, db, client):
        recipient_user = make_user(db, role=UserRole.RECIPIENT)
        headers = login_headers(client, recipient_user.email)

        resp = client.get("/api/admin/users", headers=headers)

        assert resp.status_code == 403

    def test_admin_is_allowed(self, db, client):
        admin = make_user(db, role=UserRole.ADMIN)
        headers = login_headers(client, admin.email)

        resp = client.get("/api/admin/users", headers=headers)

        assert resp.status_code == 200, resp.text


class TestListUsersContent:
    def test_lists_every_role(self, db, client):
        admin = make_user(db, role=UserRole.ADMIN)
        headers = login_headers(client, admin.email)
        provider = make_user(db, role=UserRole.PROVIDER, email="provider@example.com")

        data = client.get("/api/admin/users", headers=headers).json()["data"]

        ids = {item["id"] for item in data["items"]}
        assert str(admin.id) in ids
        assert str(provider.id) in ids

    def test_never_exposes_password_hash(self, db, client):
        admin = make_user(db, role=UserRole.ADMIN)
        headers = login_headers(client, admin.email)
        make_user(db, role=UserRole.PROVIDER, email="secret@example.com")

        data = client.get("/api/admin/users", headers=headers).json()["data"]

        raw = str(data)
        assert "hashed_password" not in raw

    def test_filters_by_role(self, db, client):
        admin = make_user(db, role=UserRole.ADMIN)
        headers = login_headers(client, admin.email)
        make_user(db, role=UserRole.PROVIDER, email="prov1@example.com")
        make_user(db, role=UserRole.RECIPIENT, email="rec1@example.com")

        data = client.get("/api/admin/users?role=PROVIDER", headers=headers).json()["data"]

        assert data["total"] >= 1
        assert all(item["role"] == "PROVIDER" for item in data["items"])

    def test_filters_by_is_active(self, db, client):
        admin = make_user(db, role=UserRole.ADMIN)
        headers = login_headers(client, admin.email)
        inactive = make_user(db, role=UserRole.PROVIDER, email="inactive@example.com")
        inactive.is_active = False
        db.commit()

        data = client.get("/api/admin/users?is_active=false", headers=headers).json()["data"]

        ids = {item["id"] for item in data["items"]}
        assert str(inactive.id) in ids
        assert all(item["is_active"] is False for item in data["items"])

    def test_search_matches_email(self, db, client):
        admin = make_user(db, role=UserRole.ADMIN)
        headers = login_headers(client, admin.email)
        target = make_user(db, role=UserRole.PROVIDER, email="findme-unique@example.com")

        data = client.get("/api/admin/users?search=findme-unique", headers=headers).json()["data"]

        ids = {item["id"] for item in data["items"]}
        assert str(target.id) in ids

    def test_pagination_reports_has_more(self, db, client):
        admin = make_user(db, role=UserRole.ADMIN)
        headers = login_headers(client, admin.email)
        for i in range(3):
            make_user(db, role=UserRole.PROVIDER, email=f"page{i}@example.com")

        data = client.get("/api/admin/users?limit=1", headers=headers).json()["data"]

        assert len(data["items"]) <= 1
        assert data["has_more"] == (data["total"] > 1)


class TestListUsersVerificationSnapshot:
    def test_provider_has_null_verification_fields(self, db, client):
        admin = make_user(db, role=UserRole.ADMIN)
        headers = login_headers(client, admin.email)
        provider = make_user(db, role=UserRole.PROVIDER, email="noverify@example.com")

        data = client.get("/api/admin/users?role=PROVIDER", headers=headers).json()["data"]
        item = next(i for i in data["items"] if i["id"] == str(provider.id))

        assert item["verification_profile_id"] is None
        assert item["is_verified"] is None

    def test_recipient_without_profile_has_null_verification_fields(self, db, client):
        admin = make_user(db, role=UserRole.ADMIN)
        headers = login_headers(client, admin.email)
        recipient_user = make_user(db, role=UserRole.RECIPIENT, email="noprofile@example.com")

        data = client.get("/api/admin/users?role=RECIPIENT", headers=headers).json()["data"]
        item = next(i for i in data["items"] if i["id"] == str(recipient_user.id))

        assert item["verification_profile_id"] is None
        assert item["is_verified"] is None

    def test_recipient_with_profile_shows_verification_state(self, db, client):
        admin = make_user(db, role=UserRole.ADMIN)
        headers = login_headers(client, admin.email)
        recipient_user = make_user(db, role=UserRole.RECIPIENT, email="hasprofile@example.com")
        recipient = make_recipient(db, recipient_user, is_verified=False)

        data = client.get("/api/admin/users?role=RECIPIENT", headers=headers).json()["data"]
        item = next(i for i in data["items"] if i["id"] == str(recipient_user.id))

        assert item["verification_profile_id"] == str(recipient.id)
        assert item["is_verified"] is False

    def test_partner_with_profile_shows_verification_state(self, db, client):
        admin = make_user(db, role=UserRole.ADMIN)
        headers = login_headers(client, admin.email)
        partner_user = make_user(db, role=UserRole.RESCUE_PARTNER, email="haspartner@example.com")
        partner = make_rescue_partner(db, partner_user, is_verified=False)

        data = client.get("/api/admin/users?role=RESCUE_PARTNER", headers=headers).json()["data"]
        item = next(i for i in data["items"] if i["id"] == str(partner_user.id))

        assert item["verification_profile_id"] == str(partner.id)
        assert item["is_verified"] is False


class TestVerifyPartner:
    def test_unauthenticated_verify_is_rejected(self, db, client):
        partner_user = make_user(db, role=UserRole.RESCUE_PARTNER)
        partner = make_rescue_partner(db, partner_user, is_verified=False)

        resp = client.patch(f"/api/admin/partners/{partner.id}/verify")

        assert resp.status_code == 401

    def test_non_admin_cannot_verify(self, db, client):
        partner_user = make_user(db, role=UserRole.RESCUE_PARTNER, email="p1@example.com")
        partner = make_rescue_partner(db, partner_user, is_verified=False)
        other_partner_user = make_user(db, role=UserRole.RESCUE_PARTNER, email="p2@example.com")
        headers = login_headers(client, other_partner_user.email)

        resp = client.patch(f"/api/admin/partners/{partner.id}/verify", headers=headers)

        assert resp.status_code == 403
        assert resp.json()["error"]["code"] == "FORBIDDEN_ROLE"

        db.refresh(partner)
        assert partner.is_verified is False  # untouched by the rejected call

    def test_admin_verifies_with_empty_body(self, db, client):
        admin = make_user(db, role=UserRole.ADMIN)
        headers = login_headers(client, admin.email)
        partner_user = make_user(db, role=UserRole.RESCUE_PARTNER, email="p3@example.com")
        partner = make_rescue_partner(db, partner_user, is_verified=False)

        resp = client.patch(f"/api/admin/partners/{partner.id}/verify", headers=headers)

        assert resp.status_code == 200, resp.text
        assert resp.json()["data"]["is_verified"] is True

    def test_admin_can_revoke_verification(self, db, client):
        admin = make_user(db, role=UserRole.ADMIN)
        headers = login_headers(client, admin.email)
        partner_user = make_user(db, role=UserRole.RESCUE_PARTNER, email="p4@example.com")
        partner = make_rescue_partner(db, partner_user, is_verified=True)

        resp = client.patch(
            f"/api/admin/partners/{partner.id}/verify", json={"is_verified": False}, headers=headers
        )

        assert resp.status_code == 200, resp.text
        assert resp.json()["data"]["is_verified"] is False

    def test_verifying_twice_is_idempotent(self, db, client):
        admin = make_user(db, role=UserRole.ADMIN)
        headers = login_headers(client, admin.email)
        partner_user = make_user(db, role=UserRole.RESCUE_PARTNER, email="p5@example.com")
        partner = make_rescue_partner(db, partner_user, is_verified=False)

        first = client.patch(f"/api/admin/partners/{partner.id}/verify", headers=headers)
        second = client.patch(f"/api/admin/partners/{partner.id}/verify", headers=headers)

        assert first.status_code == 200
        assert second.status_code == 200, second.text
        assert second.json()["data"]["is_verified"] is True

    def test_unknown_partner_returns_404(self, db, client):
        admin = make_user(db, role=UserRole.ADMIN)
        headers = login_headers(client, admin.email)

        resp = client.patch(f"/api/admin/partners/{uuid.uuid4()}/verify", headers=headers)

        assert resp.status_code == 404
        assert resp.json()["error"]["code"] == "PARTNER_NOT_FOUND"

    def test_verifying_a_partner_does_not_affect_other_partners(self, db, client):
        admin = make_user(db, role=UserRole.ADMIN)
        headers = login_headers(client, admin.email)
        user_a = make_user(db, role=UserRole.RESCUE_PARTNER, email="a@example.com")
        user_b = make_user(db, role=UserRole.RESCUE_PARTNER, email="b@example.com")
        partner_a = make_rescue_partner(db, user_a, is_verified=False)
        partner_b = make_rescue_partner(db, user_b, is_verified=False)

        client.patch(f"/api/admin/partners/{partner_a.id}/verify", headers=headers)

        db.refresh(partner_b)
        assert partner_b.is_verified is False


class TestVerifyRecipient:
    def test_unauthenticated_verify_is_rejected(self, db, client):
        recipient_user = make_user(db, role=UserRole.RECIPIENT)
        recipient = make_recipient(db, recipient_user, is_verified=False)

        resp = client.patch(f"/api/admin/recipients/{recipient.id}/verify")

        assert resp.status_code == 401

    def test_non_admin_cannot_verify(self, db, client):
        recipient_user = make_user(db, role=UserRole.RECIPIENT, email="r1@example.com")
        recipient = make_recipient(db, recipient_user, is_verified=False)
        other_recipient_user = make_user(db, role=UserRole.RECIPIENT, email="r2@example.com")
        headers = login_headers(client, other_recipient_user.email)

        resp = client.patch(f"/api/admin/recipients/{recipient.id}/verify", headers=headers)

        assert resp.status_code == 403
        assert resp.json()["error"]["code"] == "FORBIDDEN_ROLE"

        db.refresh(recipient)
        assert recipient.is_verified is False

    def test_admin_verifies_with_empty_body(self, db, client):
        admin = make_user(db, role=UserRole.ADMIN)
        headers = login_headers(client, admin.email)
        recipient_user = make_user(db, role=UserRole.RECIPIENT, email="r3@example.com")
        recipient = make_recipient(db, recipient_user, is_verified=False)

        resp = client.patch(f"/api/admin/recipients/{recipient.id}/verify", headers=headers)

        assert resp.status_code == 200, resp.text
        assert resp.json()["data"]["is_verified"] is True

    def test_admin_can_revoke_verification(self, db, client):
        admin = make_user(db, role=UserRole.ADMIN)
        headers = login_headers(client, admin.email)
        recipient_user = make_user(db, role=UserRole.RECIPIENT, email="r4@example.com")
        recipient = make_recipient(db, recipient_user, is_verified=True)

        resp = client.patch(
            f"/api/admin/recipients/{recipient.id}/verify", json={"is_verified": False}, headers=headers
        )

        assert resp.status_code == 200, resp.text
        assert resp.json()["data"]["is_verified"] is False

    def test_verifying_twice_is_idempotent(self, db, client):
        admin = make_user(db, role=UserRole.ADMIN)
        headers = login_headers(client, admin.email)
        recipient_user = make_user(db, role=UserRole.RECIPIENT, email="r5@example.com")
        recipient = make_recipient(db, recipient_user, is_verified=False)

        first = client.patch(f"/api/admin/recipients/{recipient.id}/verify", headers=headers)
        second = client.patch(f"/api/admin/recipients/{recipient.id}/verify", headers=headers)

        assert first.status_code == 200
        assert second.status_code == 200, second.text
        assert second.json()["data"]["is_verified"] is True

    def test_unknown_recipient_returns_404(self, db, client):
        admin = make_user(db, role=UserRole.ADMIN)
        headers = login_headers(client, admin.email)

        resp = client.patch(f"/api/admin/recipients/{uuid.uuid4()}/verify", headers=headers)

        assert resp.status_code == 404
        assert resp.json()["error"]["code"] == "RECIPIENT_NOT_FOUND"

    def test_medical_verified_is_untouched(self, db, client):
        """Platform verification (`is_verified`) and medical verification
        (`medical_verified`) are separate flags — this endpoint only
        controls the former."""
        admin = make_user(db, role=UserRole.ADMIN)
        headers = login_headers(client, admin.email)
        recipient_user = make_user(db, role=UserRole.RECIPIENT, email="r6@example.com")
        recipient = make_recipient(db, recipient_user, is_verified=False, medical_verified=False)

        client.patch(f"/api/admin/recipients/{recipient.id}/verify", headers=headers)

        db.refresh(recipient)
        assert recipient.is_verified is True
        assert recipient.medical_verified is False

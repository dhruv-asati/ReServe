"""
Security-focused tests for authentication, role assignment, and ownership.

    POST /api/auth/register
    POST /api/auth/login
    GET  /api/auth/me
    POST /api/auth/refresh
    PUT  /api/users/me
    GET  /api/users/{user_id}
    DELETE /api/uploads/{file_id}

Covers the fixes from the basic security review:
- Self-registration can no longer request the ADMIN role (privilege escalation).
- Tokens signed with a different secret / wrong type / malformed are rejected.
- A user can never read or modify another user's data.
- Password hashes are never returned in any response.

Shared fixtures/helpers (db, client, make_user, login_headers) live in
tests/conftest.py. Run with:

    export DATABASE_URL=postgresql+psycopg2://postgres:postgres@localhost:5432/reserve_test
    pytest tests/test_auth_security.py -v
"""

import uuid

from jose import jwt

from app.core.config import get_settings
from app.core.security import create_access_token, hash_password
from app.models.enums import UserRole
from app.models.user import User

from tests.conftest import login_headers, make_user


class TestRegistrationCannotEscalatePrivilege:
    def test_register_with_admin_role_is_rejected(self, db, client):
        """A public, unauthenticated register call must never be able to mint an ADMIN account."""
        resp = client.post(
            "/api/auth/register",
            json={
                "email": "wannabe-admin@example.com",
                "password": "StrongPassword123",
                "full_name": "Eve",
                "role": "ADMIN",
            },
        )

        assert resp.status_code == 422
        # No user should have been created at all.
        assert db.query(User).filter(User.email == "wannabe-admin@example.com").first() is None

    def test_register_with_each_normal_role_still_works(self, db, client):
        for role in ("PROVIDER", "RECIPIENT", "RESCUE_PARTNER"):
            resp = client.post(
                "/api/auth/register",
                json={
                    "email": f"{role.lower()}@example.com",
                    "password": "StrongPassword123",
                    "full_name": "Test User",
                    "role": role,
                },
            )
            assert resp.status_code == 201, resp.text
            assert resp.json()["data"]["role"] == role

    def test_register_response_never_includes_password_hash(self, db, client):
        resp = client.post(
            "/api/auth/register",
            json={
                "email": "no-hash-leak@example.com",
                "password": "StrongPassword123",
                "full_name": "Test User",
                "role": "PROVIDER",
            },
        )
        assert resp.status_code == 201
        body = resp.json()["data"]
        assert "password" not in body
        assert "hashed_password" not in body


class TestLoginAndMeDoNotLeakSecrets:
    def test_login_response_never_includes_password_hash(self, db, client):
        make_user(db, role=UserRole.PROVIDER, email="leak-check@example.com")
        resp = client.post(
            "/api/auth/login",
            json={"email": "leak-check@example.com", "password": "Password123!"},
        )
        assert resp.status_code == 200
        assert "hashed_password" not in resp.json()["data"]["user"]

    def test_me_response_never_includes_password_hash(self, db, client):
        user = make_user(db, role=UserRole.PROVIDER)
        headers = login_headers(client, user.email)
        resp = client.get("/api/auth/me", headers=headers)
        assert resp.status_code == 200
        assert "hashed_password" not in resp.json()["data"]


class TestTokenValidation:
    def test_request_without_token_is_rejected(self, db, client):
        resp = client.get("/api/auth/me")
        assert resp.status_code == 401

    def test_token_signed_with_wrong_secret_is_rejected(self, db, client):
        user = make_user(db, role=UserRole.PROVIDER)
        forged = jwt.encode(
            {"sub": str(user.id), "type": "access"}, "some-other-secret", algorithm="HS256"
        )
        resp = client.get("/api/auth/me", headers={"Authorization": f"Bearer {forged}"})
        assert resp.status_code == 401

    def test_refresh_token_cannot_be_used_as_access_token(self, db, client):
        user = make_user(db, role=UserRole.PROVIDER)
        headers = login_headers(client, user.email)
        refresh_token = client.post(
            "/api/auth/login", json={"email": user.email, "password": "Password123!"}
        ).json()["data"]["refresh_token"]

        resp = client.get("/api/auth/me", headers={"Authorization": f"Bearer {refresh_token}"})
        assert resp.status_code == 401

    def test_deactivated_user_token_is_rejected(self, db, client):
        user = make_user(db, role=UserRole.PROVIDER)
        token = create_access_token(subject=str(user.id))
        user.is_active = False
        db.commit()

        resp = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 403

    def test_token_for_deleted_user_is_rejected(self, db, client):
        token = create_access_token(subject=str(uuid.uuid4()))
        resp = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 401


class TestUserOwnershipCannotBeBypassed:
    def test_cannot_view_another_users_profile(self, db, client):
        victim = make_user(db, role=UserRole.PROVIDER)
        attacker = make_user(db, role=UserRole.RECIPIENT)
        headers = login_headers(client, attacker.email)

        resp = client.get(f"/api/users/{victim.id}", headers=headers)

        assert resp.status_code == 403

    def test_admin_can_view_any_profile(self, db, client):
        victim = make_user(db, role=UserRole.PROVIDER)
        admin = make_user(db, role=UserRole.ADMIN)
        headers = login_headers(client, admin.email)

        resp = client.get(f"/api/users/{victim.id}", headers=headers)

        assert resp.status_code == 200

    def test_profile_update_cannot_set_role_or_active_status(self, db, client):
        """
        UserProfileUpdate intentionally has no `role`/`is_active` fields, so
        extra keys in the request body must be silently ignored rather than
        applied — a user must not be able to self-promote via PUT /me.
        """
        user = make_user(db, role=UserRole.PROVIDER)
        headers = login_headers(client, user.email)

        resp = client.put(
            "/api/users/me",
            headers=headers,
            json={"full_name": "Still Just A Provider", "role": "ADMIN", "is_active": False},
        )

        assert resp.status_code == 200
        assert resp.json()["data"]["role"] == "PROVIDER"
        db.refresh(user)
        assert user.role == UserRole.PROVIDER
        assert user.is_active is True


class TestUploadOwnership:
    def test_cannot_delete_another_users_upload(self, db, client):
        owner = make_user(db, role=UserRole.PROVIDER)
        attacker = make_user(db, role=UserRole.PROVIDER)
        headers = login_headers(client, attacker.email)

        file_id = f"{owner.id.hex}__{uuid.uuid4().hex}.jpg"
        resp = client.delete(f"/api/uploads/{file_id}", headers=headers)

        assert resp.status_code == 403

    def test_path_traversal_file_id_is_rejected(self, db, client):
        user = make_user(db, role=UserRole.PROVIDER)
        headers = login_headers(client, user.email)

        resp = client.delete("/api/uploads/..%2F..%2F..%2Fetc%2Fpasswd", headers=headers)

        assert resp.status_code == 404


class TestProductionSecretEnforcement:
    def test_default_jwt_secret_rejected_outside_development(self, monkeypatch):
        from app.core.config import Settings

        monkeypatch.setenv("ENVIRONMENT", "production")
        monkeypatch.setenv("JWT_SECRET", "CHANGE_ME_IN_PRODUCTION")
        monkeypatch.setenv("DATABASE_URL", get_settings().DATABASE_URL)

        try:
            Settings()
        except Exception as exc:
            assert "JWT_SECRET" in str(exc)
        else:
            raise AssertionError("Settings() should have rejected the default JWT_SECRET in production")

    def test_strong_jwt_secret_accepted_in_production(self, monkeypatch):
        from app.core.config import Settings

        monkeypatch.setenv("ENVIRONMENT", "production")
        monkeypatch.setenv("JWT_SECRET", "a" * 40)
        monkeypatch.setenv("DATABASE_URL", get_settings().DATABASE_URL)

        Settings()  # should not raise

    def test_default_jwt_secret_still_allowed_in_development(self, monkeypatch):
        from app.core.config import Settings

        monkeypatch.setenv("ENVIRONMENT", "development")
        monkeypatch.setenv("JWT_SECRET", "CHANGE_ME_IN_PRODUCTION")
        monkeypatch.setenv("DATABASE_URL", get_settings().DATABASE_URL)

        Settings()  # should not raise

"""
Tests for POST /api/uploads/resource-image and DELETE /api/uploads/{file_id}.

These exercise the local-disk storage backend specifically (no Supabase
credentials configured in the test environment), which is the code path
exercised by `.env.example`'s defaults and by anyone running this test
suite without a Supabase project set up.

Shared fixtures (db, client, make_user, login_headers) live in
tests/conftest.py. Run with:

    export DATABASE_URL=postgresql+psycopg2://postgres:postgres@localhost:5432/reserve_test
    pytest tests/test_uploads.py -v
"""

import io

from app.core.config import get_settings
from app.models.enums import UserRole

from tests.conftest import login_headers, make_user

# Smallest possible valid file for each accepted format — just enough
# bytes for storage_service.sniff_image_extension() to recognize them.
PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"\x00" * 16
JPEG_BYTES = b"\xff\xd8\xff" + b"\x00" * 16
GIF_BYTES = b"GIF89a" + b"\x00" * 16
WEBP_BYTES = b"RIFF" + b"\x00\x00\x00\x00" + b"WEBP" + b"\x00" * 16
NOT_AN_IMAGE_BYTES = b"this is definitely not an image, just plain text bytes"


def _upload(client, headers, content: bytes, filename: str = "photo.png", content_type: str = "image/png"):
    return client.post(
        "/api/uploads/resource-image",
        headers=headers,
        files={"file": (filename, io.BytesIO(content), content_type)},
    )


class TestUploadResourceImage:
    def test_provider_can_upload_png(self, client, db):
        provider = make_user(db, role=UserRole.PROVIDER)
        headers = login_headers(client, provider.email)

        resp = _upload(client, headers, PNG_BYTES)

        assert resp.status_code == 201, resp.text
        data = resp.json()["data"]
        assert data["content_type"] == "image/png"
        assert data["size_bytes"] == len(PNG_BYTES)
        assert data["url"].startswith("http")
        assert data["file_id"].endswith(".png")
        # File id is owner-prefixed and matches the uploading provider.
        assert data["file_id"].startswith(provider.id.hex + "__")

    def test_accepts_jpeg_gif_and_webp(self, client, db):
        provider = make_user(db, role=UserRole.PROVIDER)
        headers = login_headers(client, provider.email)

        for content, filename, ctype, expected_ext in (
            (JPEG_BYTES, "photo.jpg", "image/jpeg", ".jpg"),
            (GIF_BYTES, "photo.gif", "image/gif", ".gif"),
            (WEBP_BYTES, "photo.webp", "image/webp", ".webp"),
        ):
            resp = _upload(client, headers, content, filename, ctype)
            assert resp.status_code == 201, resp.text
            assert resp.json()["data"]["file_id"].endswith(expected_ext)

    def test_rejects_non_image_content(self, client, db):
        """A file is judged by its actual bytes, not by the filename or
        the declared Content-Type — both are attacker-controlled."""
        provider = make_user(db, role=UserRole.PROVIDER)
        headers = login_headers(client, provider.email)

        resp = _upload(
            client, headers, NOT_AN_IMAGE_BYTES, filename="totally-a-photo.png", content_type="image/png"
        )

        assert resp.status_code == 422, resp.text
        assert resp.json()["error"]["code"] == "UNSUPPORTED_FILE_TYPE"

    def test_rejects_empty_file(self, client, db):
        provider = make_user(db, role=UserRole.PROVIDER)
        headers = login_headers(client, provider.email)

        resp = _upload(client, headers, b"")

        assert resp.status_code == 422, resp.text
        assert resp.json()["error"]["code"] == "EMPTY_FILE"

    def test_rejects_file_over_size_limit(self, client, db):
        provider = make_user(db, role=UserRole.PROVIDER)
        headers = login_headers(client, provider.email)

        max_bytes = get_settings().MAX_UPLOAD_FILE_SIZE_MB * 1024 * 1024
        oversized = PNG_BYTES + b"\x00" * max_bytes

        resp = _upload(client, headers, oversized)

        assert resp.status_code == 413, resp.text
        assert resp.json()["error"]["code"] == "FILE_TOO_LARGE"

    def test_recipient_cannot_upload_resource_image(self, client, db):
        """Only PROVIDER/ADMIN accounts may upload — same restriction as
        creating a resource in the first place."""
        recipient = make_user(db, role=UserRole.RECIPIENT)
        headers = login_headers(client, recipient.email)

        resp = _upload(client, headers, PNG_BYTES)

        assert resp.status_code == 403, resp.text
        assert resp.json()["error"]["code"] == "FORBIDDEN_ROLE"

    def test_upload_requires_authentication(self, client):
        resp = client.post(
            "/api/uploads/resource-image",
            files={"file": ("photo.png", io.BytesIO(PNG_BYTES), "image/png")},
        )
        assert resp.status_code == 401, resp.text

    def test_uploaded_image_url_is_usable_as_resource_image_url(self, client, db):
        """The url an upload returns should be accepted straight back by
        POST /api/resources' image_url field."""
        provider = make_user(db, role=UserRole.PROVIDER)
        headers = login_headers(client, provider.email)

        upload_resp = _upload(client, headers, PNG_BYTES)
        assert upload_resp.status_code == 201, upload_resp.text
        image_url = upload_resp.json()["data"]["url"]

        resource_resp = client.post(
            "/api/resources",
            headers=headers,
            json={
                "title": "80 vegetarian meals",
                "resource_type": "FOOD",
                "quantity": 80,
                "unit": "meals",
                "location_address": "Grand Plaza Hotel, MG Road, Bengaluru",
                "image_url": image_url,
            },
        )
        assert resource_resp.status_code == 201, resource_resp.text
        assert resource_resp.json()["data"]["image_url"] == image_url


class TestDeleteUploadedFile:
    def test_uploader_can_delete_own_file(self, client, db):
        provider = make_user(db, role=UserRole.PROVIDER)
        headers = login_headers(client, provider.email)
        file_id = _upload(client, headers, PNG_BYTES).json()["data"]["file_id"]

        resp = client.delete(f"/api/uploads/{file_id}", headers=headers)

        assert resp.status_code == 200, resp.text
        assert resp.json()["success"] is True

    def test_other_provider_cannot_delete_someone_elses_file(self, client, db):
        owner = make_user(db, role=UserRole.PROVIDER, email="owner@example.com")
        owner_headers = login_headers(client, owner.email)
        file_id = _upload(client, owner_headers, PNG_BYTES).json()["data"]["file_id"]

        other = make_user(db, role=UserRole.PROVIDER, email="other@example.com")
        other_headers = login_headers(client, other.email)

        resp = client.delete(f"/api/uploads/{file_id}", headers=other_headers)

        assert resp.status_code == 403, resp.text
        assert resp.json()["error"]["code"] == "NOT_FILE_OWNER"

    def test_admin_can_delete_any_file(self, client, db):
        owner = make_user(db, role=UserRole.PROVIDER, email="owner2@example.com")
        owner_headers = login_headers(client, owner.email)
        file_id = _upload(client, owner_headers, PNG_BYTES).json()["data"]["file_id"]

        admin = make_user(db, role=UserRole.ADMIN, email="admin@example.com")
        admin_headers = login_headers(client, admin.email)

        resp = client.delete(f"/api/uploads/{file_id}", headers=admin_headers)

        assert resp.status_code == 200, resp.text

    def test_delete_rejects_malformed_file_id(self, client, db):
        """A file_id that doesn't match the expected pattern (including any
        attempt at path traversal) is rejected before it ever reaches the
        storage backend."""
        provider = make_user(db, role=UserRole.PROVIDER)
        headers = login_headers(client, provider.email)

        resp = client.delete("/api/uploads/../../etc/passwd", headers=headers)

        assert resp.status_code == 404, resp.text

    def test_delete_requires_authentication(self, client, db):
        provider = make_user(db, role=UserRole.PROVIDER)
        headers = login_headers(client, provider.email)
        file_id = _upload(client, headers, PNG_BYTES).json()["data"]["file_id"]

        resp = client.delete(f"/api/uploads/{file_id}")

        assert resp.status_code == 401, resp.text

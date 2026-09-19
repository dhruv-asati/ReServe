"""
Tests for the SMTP email companion to in-app notifications
(app/services/email_service.py + notification_service._send_email_safely).

Two layers, tested separately:

  1. email_service.send_email() itself — unit-tested with `smtplib.SMTP`
     monkeypatched, so no real network/mail server is ever touched.

  2. notification_service's email wiring — integration-tested through the
     real allocation/operation/reallocation endpoints, with
     `email_service.is_configured`/`send_email` monkeypatched (the same
     pattern tests/test_resource_analysis.py uses for
     `gemini_service.call_gemini_model`). This is the "mock emails during
     testing" requirement: no test in this suite ever opens a real SMTP
     connection, since SMTP_HOST/SMTP_FROM_EMAIL are unset in the test
     environment by default and every email-path test here monkeypatches
     the send function instead of relying on real settings.

Run with:

    export DATABASE_URL=postgresql+psycopg2://postgres:postgres@localhost:5432/reserve_test
    pytest tests/test_email_notifications.py -v
"""

import smtplib

from app.core.config import get_settings
from app.models.enums import ResourceStatus, RescueRequestStatus, UserRole
from app.services import email_service

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
CHURCH_STREET = dict(latitude=12.9762, longitude=77.6033)


def _setup_allocation(db, client, *, quantity=80):
    provider = make_user(db, role=UserRole.PROVIDER)
    headers = login_headers(client, provider.email)

    resource = make_resource(db, provider, quantity=quantity, status=ResourceStatus.MATCHING, **MG_ROAD)
    rescue_request = make_rescue_request(db, resource, status=RescueRequestStatus.MATCHED)

    recipient_user = make_user(db, role=UserRole.RECIPIENT, email="emailrecipient@example.com")
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
    allocation_id = resp.json()["data"]["id"]

    return provider, headers, resource, rescue_request, recipient_user, recipient, allocation_id


class _RecordingSender:
    """Records every (to, subject, body) send_email() was called with."""

    def __init__(self, succeed: bool = True, exc: Exception | None = None):
        self.calls: list[tuple[str, str, str]] = []
        self._succeed = succeed
        self._exc = exc

    def __call__(self, to: str, subject: str, body: str) -> bool:
        self.calls.append((to, subject, body))
        if self._exc is not None:
            raise self._exc
        return self._succeed


def _mock_email_configured(monkeypatch, succeed: bool = True, exc: Exception | None = None) -> _RecordingSender:
    """Pretends SMTP is configured and replaces the real send with a
    recording double — no network call is ever made."""
    sender = _RecordingSender(succeed=succeed, exc=exc)
    monkeypatch.setattr(email_service, "is_configured", lambda: True)
    monkeypatch.setattr(email_service, "send_email", sender)
    return sender


# --- Unit tests: email_service.send_email() itself --------------------------


class TestEmailServiceUnit:
    def test_not_configured_by_default(self):
        # Test settings never set SMTP_HOST/SMTP_FROM_EMAIL.
        assert email_service.is_configured() is False

    def test_send_email_skips_and_returns_false_when_unconfigured(self, monkeypatch):
        monkeypatch.setattr(email_service, "is_configured", lambda: False)
        result = email_service.send_email(to="x@example.com", subject="Hi", body="Body")
        assert result is False

    def test_send_email_uses_smtp_when_configured(self, monkeypatch):
        monkeypatch.setattr(email_service, "is_configured", lambda: True)
        settings = get_settings()
        monkeypatch.setattr(settings, "SMTP_HOST", "smtp.example.com")
        monkeypatch.setattr(settings, "SMTP_PORT", 587)
        monkeypatch.setattr(settings, "SMTP_FROM_EMAIL", "noreply@reserve.example")
        monkeypatch.setattr(settings, "SMTP_USERNAME", "user")
        monkeypatch.setattr(settings, "SMTP_PASSWORD", "pass")
        monkeypatch.setattr(settings, "SMTP_USE_TLS", True)
        monkeypatch.setattr(email_service, "get_settings", lambda: settings)

        calls = {}

        class _FakeSMTP:
            def __init__(self, host, port, timeout=10):
                calls["host"] = host
                calls["port"] = port

            def __enter__(self):
                return self

            def __exit__(self, *exc):
                return False

            def starttls(self):
                calls["starttls"] = True

            def login(self, user, password):
                calls["login"] = (user, password)

            def send_message(self, message):
                calls["sent"] = (message["To"], message["Subject"])

        monkeypatch.setattr(smtplib, "SMTP", _FakeSMTP)

        result = email_service.send_email(to="someone@example.com", subject="Test subject", body="Test body")

        assert result is True
        assert calls["host"] == "smtp.example.com"
        assert calls["starttls"] is True
        assert calls["login"] == ("user", "pass")
        assert calls["sent"] == ("someone@example.com", "Test subject")

    def test_send_email_returns_false_on_smtp_error(self, monkeypatch):
        monkeypatch.setattr(email_service, "is_configured", lambda: True)
        settings = get_settings()
        monkeypatch.setattr(settings, "SMTP_HOST", "smtp.example.com")
        monkeypatch.setattr(settings, "SMTP_FROM_EMAIL", "noreply@reserve.example")
        monkeypatch.setattr(email_service, "get_settings", lambda: settings)

        class _FailingSMTP:
            def __init__(self, host, port, timeout=10):
                raise ConnectionRefusedError("no mail server here")

        monkeypatch.setattr(smtplib, "SMTP", _FailingSMTP)

        # Must not raise — a broken mail server is reported as a plain
        # False, never an exception escaping this function.
        result = email_service.send_email(to="someone@example.com", subject="Test", body="Test")
        assert result is False


# --- Integration tests: notification_service wiring -------------------------


class TestEmailNotConfiguredByDefault:
    def test_allocation_does_not_attempt_email_when_unconfigured(self, db, client, monkeypatch):
        def _boom(*args, **kwargs):
            raise AssertionError("send_email should never be called when SMTP isn't configured")

        monkeypatch.setattr(email_service, "send_email", _boom)
        # is_configured() is left at its real (False-by-default) behavior.
        _setup_allocation(db, client)  # would raise via _boom if email were attempted


class TestAllocationConfirmedEmail:
    def test_sends_email_to_recipient_and_provider(self, db, client, monkeypatch):
        sender = _mock_email_configured(monkeypatch)
        provider, _, resource, _, recipient_user, _, _ = _setup_allocation(db, client)

        recipients_emailed = {to for to, _, _ in sender.calls}
        assert provider.email in recipients_emailed
        assert recipient_user.email in recipients_emailed

    def test_email_body_mentions_the_resource(self, db, client, monkeypatch):
        sender = _mock_email_configured(monkeypatch)
        _, _, resource, _, _, _, _ = _setup_allocation(db, client)

        assert any(resource.title in body for _, _, body in sender.calls)


class TestOperationAssignedEmail:
    def test_sends_email_to_partner_and_provider(self, db, client, monkeypatch):
        sender = _mock_email_configured(monkeypatch)
        provider, headers, _, rescue_request, _, _, _ = _setup_allocation(db, client)
        partner_user = make_user(db, role=UserRole.RESCUE_PARTNER, email="emailpartner@example.com")
        partner = make_rescue_partner(db, partner_user)

        sender.calls.clear()  # isolate this event from the allocation email above
        resp = client.post(
            "/api/operations",
            json={"rescue_request_id": str(rescue_request.id), "partner_id": str(partner.id)},
            headers=headers,
        )
        assert resp.status_code == 201, resp.text

        recipients_emailed = {to for to, _, _ in sender.calls}
        assert partner_user.email in recipients_emailed
        assert provider.email in recipients_emailed


class TestOperationCompletedEmail:
    def test_sends_email_on_completion(self, db, client, monkeypatch):
        sender = _mock_email_configured(monkeypatch)
        provider, headers, _, rescue_request, recipient_user, _, _ = _setup_allocation(db, client)

        op_resp = client.post(
            "/api/operations", json={"rescue_request_id": str(rescue_request.id)}, headers=headers
        )
        operation_id = op_resp.json()["data"]["id"]

        sender.calls.clear()
        client.patch(f"/api/operations/{operation_id}/status", json={"status": "IN_TRANSIT"}, headers=headers)
        client.patch(f"/api/operations/{operation_id}/status", json={"status": "DELIVERED"}, headers=headers)
        completed = client.patch(
            f"/api/operations/{operation_id}/status", json={"status": "COMPLETED"}, headers=headers
        )
        assert completed.status_code == 200, completed.text

        recipients_emailed = {to for to, _, _ in sender.calls}
        assert provider.email in recipients_emailed
        assert recipient_user.email in recipients_emailed


class TestOperationFailedEmail:
    def test_sends_email_to_everyone_still_waiting(self, db, client, monkeypatch):
        sender = _mock_email_configured(monkeypatch)
        provider, headers, _, rescue_request, recipient_user, _, _ = _setup_allocation(db, client)
        partner_user = make_user(db, role=UserRole.RESCUE_PARTNER, email="emailfailpartner@example.com")
        partner = make_rescue_partner(db, partner_user)

        op_resp = client.post(
            "/api/operations",
            json={"rescue_request_id": str(rescue_request.id), "partner_id": str(partner.id)},
            headers=headers,
        )
        operation_id = op_resp.json()["data"]["id"]

        sender.calls.clear()
        resp = client.patch(
            f"/api/operations/{operation_id}/status",
            json={"status": "FAILED", "reason": "Vehicle breakdown."},
            headers=headers,
        )
        assert resp.status_code == 200, resp.text

        recipients_emailed = {to for to, _, _ in sender.calls}
        assert provider.email in recipients_emailed
        assert partner_user.email in recipients_emailed
        assert recipient_user.email in recipients_emailed
        assert any("Vehicle breakdown." in body for _, _, body in sender.calls)


class TestReallocationEmail:
    def test_sends_email_to_old_and_new_recipient(self, db, client, monkeypatch):
        provider, headers, resource, rescue_request, recipient_user, recipient, allocation_id = _setup_allocation(db, client)
        # A second, eligible recipient for the reallocation engine to pick
        # up automatically — same convention as tests/test_reallocation.py.
        replacement_user = make_user(db, role=UserRole.RECIPIENT, email="emailbackup@example.com")
        make_recipient(
            db, replacement_user, organization_name="Backup NGO", current_availability=True, **CHURCH_STREET
        )
        op_resp = client.post(
            "/api/operations", json={"rescue_request_id": str(rescue_request.id)}, headers=headers
        )
        assert op_resp.status_code == 201, op_resp.text
        operation_id = op_resp.json()["data"]["id"]

        sender = _mock_email_configured(monkeypatch)
        resp = client.post(
            f"/api/operations/{operation_id}/reallocate",
            json={"allocation_id": allocation_id, "reason": "No longer available."},
            headers=headers,
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["data"]["reallocated"] is True

        recipients_emailed = {to for to, _, _ in sender.calls}
        assert recipient_user.email in recipients_emailed  # the one who lost the allocation
        assert replacement_user.email in recipients_emailed  # the one who gained it
        assert provider.email in recipients_emailed


class TestEmailFailureIsSafe:
    def test_broken_mail_server_does_not_break_allocation(self, db, client, monkeypatch):
        """send_email() raising must never surface as a failed request —
        the in-app Notification row is still the source of truth."""
        sender = _mock_email_configured(monkeypatch, exc=smtplib.SMTPConnectError(421, "down"))

        # _setup_allocation asserts a 201 internally; if the email failure
        # leaked out as an unhandled exception, this would fail instead.
        provider, _, _, _, recipient_user, _, _ = _setup_allocation(db, client)

        assert sender.calls  # email really was attempted, not just skipped

        from app.models.notification import Notification

        rows = db.query(Notification).filter(Notification.user_id == recipient_user.id).all()
        assert rows, "the in-app notification must still be written even though the email failed"

    def test_broken_mail_server_does_not_break_operation_status_update(self, db, client, monkeypatch):
        provider, headers, _, rescue_request, _, _, _ = _setup_allocation(db, client)
        partner_user = make_user(db, role=UserRole.RESCUE_PARTNER, email="emailboom@example.com")
        partner = make_rescue_partner(db, partner_user)

        op_resp = client.post(
            "/api/operations",
            json={"rescue_request_id": str(rescue_request.id), "partner_id": str(partner.id)},
            headers=headers,
        )
        assert op_resp.status_code == 201, op_resp.text
        operation_id = op_resp.json()["data"]["id"]

        _mock_email_configured(monkeypatch, exc=OSError("network unreachable"))

        resp = client.patch(
            f"/api/operations/{operation_id}/status",
            json={"status": "FAILED", "reason": "Vehicle breakdown."},
            headers=headers,
        )
        assert resp.status_code == 200, resp.text

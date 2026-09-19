"""
Email service: sends basic transactional email notifications over SMTP.

Split into two functions specifically so tests never need a real SMTP
server or network access:

    is_configured() -> bool                    # whether SMTP settings are present
    send_email(to, subject, body) -> bool       # the ONLY function that talks to SMTP

A test monkeypatches `email_service.is_configured` and `email_service.send_email`
(the same pattern gemini_service.py uses for `call_gemini_model`) to a
canned True/False and a recording double — see tests/test_email_notifications.py.

This module never raises. `send_email` catches every SMTP/socket error
itself and returns False; notification_service also wraps its call to
this module in its own try/except as a second line of defense. Email is
always best-effort: a broken or misconfigured mail server must never
turn an otherwise-successful allocation, assignment, reallocation, or
operation status change into a failed request. There is no retry queue
or background worker here — this is a synchronous, best-effort send,
which is the deliberate scope for now (no SMS either — see
notification_service.py).
"""

import logging
import smtplib
from email.message import EmailMessage

from app.core.config import get_settings

logger = logging.getLogger(__name__)


def is_configured() -> bool:
    """
    True once both SMTP_HOST and SMTP_FROM_EMAIL are set. Checked before
    every send so an environment that never configured SMTP (local dev,
    CI, the test suite) never attempts a network connection at all.
    """
    settings = get_settings()
    return bool(settings.SMTP_HOST and settings.SMTP_FROM_EMAIL)


def send_email(to: str, subject: str, body: str) -> bool:
    """
    Sends one plain-text email. Returns True on success, False on any
    failure — bad credentials, connection refused, DNS failure, timeout,
    or SMTP not being configured at all. Never raises.
    """
    settings = get_settings()

    if not is_configured():
        logger.debug("SMTP not configured (SMTP_HOST/SMTP_FROM_EMAIL unset) — skipping email to %s.", to)
        return False

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = settings.SMTP_FROM_EMAIL
    message["To"] = to
    message.set_content(body)

    try:
        # A short, fixed timeout so a hung/unreachable mail server fails
        # fast rather than stalling the request that triggered this email.
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10) as server:
            if settings.SMTP_USE_TLS:
                server.starttls()
            if settings.SMTP_USERNAME:
                server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
            server.send_message(message)
        return True
    except (smtplib.SMTPException, OSError) as exc:
        # OSError covers socket-level failures (connection refused, DNS,
        # timeout) that aren't smtplib.SMTPException subclasses.
        logger.warning("Failed to send email to %s: %s", to, exc)
        return False

"""
Notification service.

Two halves:

  1. `list_for_user` / `mark_read` — the business logic behind
     GET /api/notifications and PATCH /api/notifications/{id}/read.

  2. `notify_*` emitters — called by allocation_service, operation_service,
     and reallocation_service when the event they already handle happens.

Transaction policy for the emitters: they only ever `db.add(...)`, never
`db.commit()`. The caller commits, so a notification is written in the same
transaction as the thing it describes. That means there is no window where
an allocation exists but its notification silently didn't get written (or
vice versa) — they land together or not at all.

Recipient-resolution policy: every notification targets a `users.id`, so the
emitters translate domain objects into the user behind them —
`Recipient.user_id` for a recipient org, `RescuePartner.user_id` for a
partner, `Resource.provider_id` for the provider. A target that doesn't
resolve to a user (most often an allocation made to a RescueHub, which has
no owning user account) is skipped rather than raising: a missing
notification must never fail the rescue operation that triggered it.

Email: every in-app notification `_add()` writes also gets a best-effort
companion email via app/services/email_service.py, gated on
email_service.is_configured() (empty SMTP_HOST/SMTP_FROM_EMAIL in
Settings — the default — means no email is ever attempted, which is what
keeps this a no-op in tests and any environment without SMTP set up). A
failed or misconfigured send is caught and logged, never raised — the
in-app Notification row this module already writes is the source of
truth, and email is purely additive. No SMS yet.

Five events raise notifications: allocation confirmed, partner assigned,
operation completed, operation failed, and reallocation. No new
NotificationType values were needed for four of them — they're mapped
onto the existing enum (see app/models/enums.py); the fifth
(operation completed) uses DELIVERY_CONFIRMED, which was already defined
in that enum but unused until now.
"""

import logging
import uuid
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models.enums import NotificationType, UserRole
from app.models.notification import Notification
from app.models.user import User
from app.services import email_service

logger = logging.getLogger(__name__)


def _add(
    db: Session,
    *,
    user_id: Optional[uuid.UUID],
    notification_type: NotificationType,
    title: str,
    message: str,
    related_operation_id: Optional[uuid.UUID] = None,
) -> Optional[Notification]:
    """
    Queues one notification on the current transaction. Returns None (and
    writes nothing) when there's no user to notify — see the
    recipient-resolution policy in the module docstring.
    """
    if user_id is None:
        return None

    notification = Notification(
        user_id=user_id,
        notification_type=notification_type,
        title=title,
        message=message,
        is_read=False,
        related_operation_id=related_operation_id,
    )
    db.add(notification)

    _send_email_safely(db, user_id=user_id, subject=title, body=message)

    return notification


def _send_email_safely(db: Session, *, user_id: uuid.UUID, subject: str, body: str) -> None:
    """
    Best-effort email companion to the in-app notification `_add()` just
    queued. Never raises and never affects the DB transaction's
    outcome — a broken or misconfigured mail server must never turn a
    successful allocation/assignment/reallocation/status-change into a
    failed request.

    Skipped entirely — no query, no network call — when SMTP isn't
    configured (email_service.is_configured() is False), which is the
    default in local dev, CI, and the test suite.
    """
    if not email_service.is_configured():
        return

    try:
        to_email = db.query(User.email).filter(User.id == user_id).scalar()
        if not to_email:
            return
        email_service.send_email(to=to_email, subject=subject, body=body)
    except Exception:  # noqa: BLE001 - email is always best-effort, never allowed to break the caller
        logger.warning("Unexpected error sending email notification to user %s", user_id, exc_info=True)


def _resource_label(resource) -> str:
    """Short human-readable identifier for a resource, used in messages."""
    return resource.title


# --- Event emitters ---------------------------------------------------------


def notify_allocation_confirmed(db: Session, *, allocation, resource, recipient=None, hub=None) -> None:
    """
    An allocation has been committed: a slice of `resource` is now reserved
    for a specific recipient (or rescue hub).

    Notifies the recipient's own account that resources are coming their
    way, and the provider that their surplus has been successfully
    committed. A hub allocation only notifies the provider, since a
    RescueHub is admin-managed and has no single owning user.
    """
    quantity = float(allocation.allocated_quantity)
    label = _resource_label(resource)

    if recipient is not None:
        _add(
            db,
            user_id=recipient.user_id,
            notification_type=NotificationType.MATCH_FOUND,
            title="Resources allocated to you",
            message=(
                f"{quantity:g} {resource.unit} of '{label}' has been allocated to "
                f"{recipient.organization_name}. A rescue operation will be arranged to deliver it."
            ),
        )

    target_name = recipient.organization_name if recipient is not None else (hub.name if hub is not None else "a rescue hub")
    _add(
        db,
        user_id=resource.provider_id,
        notification_type=NotificationType.MATCH_FOUND,
        title="Your resource was allocated",
        message=f"{quantity:g} {resource.unit} of '{label}' has been allocated to {target_name}.",
    )


def notify_operation_assigned(db: Session, *, operation, partner, resource) -> None:
    """
    A rescue partner has been assigned to an operation. Notifies the
    partner (they're the one who has to go and collect it) and the
    provider (so they know who to expect at pickup).
    """
    label = _resource_label(resource)
    partner_name = partner.organization_name or "A rescue partner"

    _add(
        db,
        user_id=partner.user_id,
        notification_type=NotificationType.PARTNER_ASSIGNED,
        title="You've been assigned a rescue operation",
        message=(
            f"You're assigned to collect '{label}' from {resource.location_address}. "
            f"The operation is currently {operation.status.value}."
        ),
        related_operation_id=operation.id,
    )

    _add(
        db,
        user_id=resource.provider_id,
        notification_type=NotificationType.PARTNER_ASSIGNED,
        title="A rescue partner was assigned",
        message=f"{partner_name} has been assigned to collect '{label}'.",
        related_operation_id=operation.id,
    )


def notify_operation_completed(db: Session, *, operation, resource, recipient_user_ids=()) -> None:
    """
    An operation has reached COMPLETED — the final sign-off after delivery
    (allocations were already marked DELIVERED at the DELIVERED step).
    Notifies the provider, the assigned partner (if any), and every
    recipient whose allocation was actually delivered on this operation.

    Uses NotificationType.DELIVERY_CONFIRMED — defined in the enum from
    the start but unused until this event existed to raise it.

    Targets are de-duplicated, same as notify_operation_failed.
    """
    label = _resource_label(resource)
    message = f"The rescue operation for '{label}' has been completed successfully."

    targets: list[Optional[uuid.UUID]] = [resource.provider_id]
    if operation.partner is not None:
        targets.append(operation.partner.user_id)
    targets.extend(recipient_user_ids)

    seen: set[uuid.UUID] = set()
    for user_id in targets:
        if user_id is None or user_id in seen:
            continue
        seen.add(user_id)
        _add(
            db,
            user_id=user_id,
            notification_type=NotificationType.DELIVERY_CONFIRMED,
            title="Rescue operation completed",
            message=message,
            related_operation_id=operation.id,
        )


def notify_reallocation(
    db: Session, *, operation, resource, old_recipient, new_recipient=None, quantity: float = 0.0, reason: str = ""
) -> None:
    """
    An allocation was reallocated away from `old_recipient` — either to
    `new_recipient`, or to nobody if the matching engine found no eligible
    replacement.

    Notifies the recipient who lost the allocation, the one who gained it
    (if any), and the provider whose resource moved.
    """
    label = _resource_label(resource)

    _add(
        db,
        user_id=old_recipient.user_id,
        notification_type=NotificationType.REALLOCATION,
        title="Your allocation was reassigned",
        message=(
            f"The allocation of '{label}' to {old_recipient.organization_name} has been cancelled "
            f"and reassigned. Reason: {reason}"
        ),
        related_operation_id=operation.id,
    )

    if new_recipient is not None:
        _add(
            db,
            user_id=new_recipient.user_id,
            notification_type=NotificationType.REALLOCATION,
            title="Resources reassigned to you",
            message=(
                f"{quantity:g} {resource.unit} of '{label}' has been reassigned to "
                f"{new_recipient.organization_name} after the original recipient became unavailable."
            ),
            related_operation_id=operation.id,
        )
        provider_message = (
            f"'{label}' was reassigned from {old_recipient.organization_name} to "
            f"{new_recipient.organization_name}. Reason: {reason}"
        )
    else:
        provider_message = (
            f"'{label}' was cancelled from {old_recipient.organization_name} and no eligible "
            f"replacement recipient was found. Reason: {reason}"
        )

    _add(
        db,
        user_id=resource.provider_id,
        notification_type=NotificationType.REALLOCATION,
        title="Your resource was reallocated",
        message=provider_message,
        related_operation_id=operation.id,
    )


def notify_operation_failed(db: Session, *, operation, resource, reason: str, recipient_user_ids=()) -> None:
    """
    An operation has moved to FAILED. Notifies the provider, the assigned
    partner (if any), and every recipient still holding a live allocation
    on it — all of them were expecting this rescue to happen.

    Targets are de-duplicated, so a user who is somehow two parties to the
    same operation gets one notification rather than several.
    """
    label = _resource_label(resource)
    message = f"The rescue operation for '{label}' has failed. Reason: {reason}"

    targets: list[Optional[uuid.UUID]] = [resource.provider_id]
    if operation.partner is not None:
        targets.append(operation.partner.user_id)
    targets.extend(recipient_user_ids)

    seen: set[uuid.UUID] = set()
    for user_id in targets:
        if user_id is None or user_id in seen:
            continue
        seen.add(user_id)
        _add(
            db,
            user_id=user_id,
            notification_type=NotificationType.OPERATION_UPDATE,
            title="Rescue operation failed",
            message=message,
            related_operation_id=operation.id,
        )


# --- Query / mutation for the API layer -------------------------------------


def list_for_user(
    db: Session,
    current_user: User,
    *,
    is_read: Optional[bool] = None,
    notification_type: Optional[NotificationType] = None,
    skip: int = 0,
    limit: int = 20,
) -> tuple[list[Notification], int, int]:
    """
    Returns (items, total, unread_count) for the caller's own
    notifications, newest first.

    `unread_count` deliberately ignores both the `is_read` filter and
    pagination — it's the badge number, so it has to reflect every unread
    notification the user has, not just the current page.
    """
    conditions = [Notification.user_id == current_user.id]
    if is_read is not None:
        conditions.append(Notification.is_read.is_(is_read))
    if notification_type is not None:
        conditions.append(Notification.notification_type == notification_type)

    total = db.query(func.count(Notification.id)).filter(*conditions).scalar() or 0

    unread_count = (
        db.query(func.count(Notification.id))
        .filter(Notification.user_id == current_user.id, Notification.is_read.is_(False))
        .scalar()
        or 0
    )

    items = (
        db.query(Notification)
        .filter(*conditions)
        .order_by(Notification.created_at.desc(), Notification.id.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )

    return items, int(total), int(unread_count)


def get_notification_or_404(db: Session, notification_id: uuid.UUID) -> Notification:
    notification = db.query(Notification).filter(Notification.id == notification_id).first()
    if notification is None:
        raise AppError(
            status_code=404, code="NOTIFICATION_NOT_FOUND", message="Notification not found."
        )
    return notification


def mark_read(db: Session, notification_id: uuid.UUID, current_user: User) -> Notification:
    """
    Marks one notification read. Only its own recipient (or an ADMIN) may
    do so. Idempotent — marking an already-read notification is a success,
    not a 409, so a client retrying doesn't have to special-case it.
    """
    notification = get_notification_or_404(db, notification_id)

    if notification.user_id != current_user.id and current_user.role != UserRole.ADMIN:
        raise AppError(
            status_code=403,
            code="NOT_NOTIFICATION_OWNER",
            message="You can only update your own notifications.",
        )

    if not notification.is_read:
        notification.is_read = True
        db.commit()
        db.refresh(notification)

    return notification

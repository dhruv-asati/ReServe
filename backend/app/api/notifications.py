"""
Notification endpoints:

    GET   /api/notifications
    PATCH /api/notifications/{notification_id}/read

Both require authentication and are scoped to the caller's own
notifications — there is no way to read or mark someone else's. Listing is
filtered by user_id in the service layer rather than by a permission check,
so another user's notifications are invisible rather than forbidden.

Notifications are never created through the API. They're raised as a side
effect of allocations, operation assignment, reallocation, and operation
failure — see app/services/notification_service.py.
"""

import logging
import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.database import get_db
from app.models.enums import NotificationType
from app.models.user import User
from app.schemas.common import SuccessResponse
from app.schemas.notification import NotificationListData, NotificationOut
from app.services import notification_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/notifications", tags=["Notifications"])


@router.get(
    "",
    response_model=SuccessResponse[NotificationListData],
    summary="List my notifications",
    description=(
        "Returns the authenticated user's own notifications, newest first. Optionally filter by "
        "read state (`is_read`) or type. `unread_count` in the response is the user's total "
        "unread count, independent of the filter and pagination, so it can drive a badge without "
        "a second request."
    ),
)
def list_notifications(
    is_read: bool | None = Query(default=None, description="Filter by read state. Omit for all."),
    notification_type: NotificationType | None = Query(default=None, alias="type"),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    items, total, unread_count = notification_service.list_for_user(
        db,
        current_user,
        is_read=is_read,
        notification_type=notification_type,
        skip=skip,
        limit=limit,
    )
    data = NotificationListData(
        items=[NotificationOut.model_validate(item) for item in items],
        total=total,
        skip=skip,
        limit=limit,
        has_more=skip + len(items) < total,
        unread_count=unread_count,
    )
    return SuccessResponse(data=data, message=f"Found {total} notification(s), {unread_count} unread.")


@router.patch(
    "/{notification_id}/read",
    response_model=SuccessResponse[NotificationOut],
    summary="Mark a notification as read",
    description=(
        "Marks one of the caller's own notifications as read. Idempotent — marking an "
        "already-read notification succeeds and returns it unchanged. Returns 403 if the "
        "notification belongs to someone else."
    ),
)
def mark_notification_read(
    notification_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    notification = notification_service.mark_read(db, notification_id, current_user)
    return SuccessResponse(
        data=NotificationOut.model_validate(notification), message="Notification marked as read."
    )

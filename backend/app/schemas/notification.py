"""
Pydantic schemas for:

    GET   /api/notifications
    PATCH /api/notifications/{notification_id}/read

A Notification is always scoped to exactly one user (see
app/models/notification.py). There is deliberately no create schema here:
notifications are never created by a client request — they're raised by the
allocation/operation/reallocation services as a side effect of the events
they already handle (see app/services/notification_service.py).
"""

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import NotificationType


class NotificationOut(BaseModel):
    id: uuid.UUID
    notification_type: NotificationType
    title: str
    message: str
    is_read: bool

    related_operation_id: Optional[uuid.UUID] = Field(
        default=None,
        description="The RescueOperation this notification refers to, when there is one. Null for "
        "events that happen before an operation exists (e.g. an allocation being confirmed).",
    )

    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class NotificationListData(BaseModel):
    items: list[NotificationOut]
    total: int
    skip: int
    limit: int
    has_more: bool
    unread_count: int = Field(
        description="Total unread notifications for this user, ignoring the is_read filter and "
        "pagination — so a client can render a badge without a second request."
    )

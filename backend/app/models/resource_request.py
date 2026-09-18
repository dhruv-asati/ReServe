"""
ResourceRequest and ResourceRequestStatusHistory models.

A ResourceRequest is a RECIPIENT's demand-side ask — "we need 50 meals by
6pm" — independent of any specific Resource a provider has posted. This is
deliberately a separate concept from RescueRequest (see
app/models/rescue_request.py), which is the matching engine's supply-side
coordination record tied to one specific Resource. The two aren't linked
yet; matching a ResourceRequest to actual Resources/RescueRequests is
matching-engine work for a later stage.

Every status change is appended to ResourceRequestStatusHistory, mirroring
the OperationEvent audit-log pattern used for RescueOperation — an
append-only log, never edited, so "who approved/rejected/cancelled this
and when" is always reconstructable.
"""

import uuid
from datetime import datetime
from typing import List, Optional, TYPE_CHECKING

from sqlalchemy import DateTime, Boolean, Enum, ForeignKey, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base
from app.models.enums import ResourceRequestStatus, ResourceType, UrgencyLevel
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.recipient import Recipient
    from app.models.user import User


class ResourceRequest(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "resource_requests"

    recipient_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("recipients.id", ondelete="CASCADE"), nullable=False, index=True
    )

    resource_type: Mapped[ResourceType] = mapped_column(
        Enum(ResourceType, name="resource_type", values_callable=lambda e: [m.value for m in e]),
        nullable=False,
        index=True,
    )
    requested_quantity: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)

    # Snapshot of the recipient's org name at request time, not a live
    # reference — captured explicitly since a request should keep saying
    # who it was for even if the recipient's profile name changes later.
    requesting_organization: Mapped[str] = mapped_column(String(255), nullable=False)

    urgency: Mapped[UrgencyLevel] = mapped_column(
        Enum(UrgencyLevel, name="urgency_level", values_callable=lambda e: [m.value for m in e]),
        nullable=False,
        default=UrgencyLevel.MEDIUM,
    )
    needed_by: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    eligibility_requirements: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    can_self_pickup: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    status: Mapped[ResourceRequestStatus] = mapped_column(
        Enum(
            ResourceRequestStatus,
            name="resource_request_status",
            values_callable=lambda e: [m.value for m in e],
        ),
        nullable=False,
        default=ResourceRequestStatus.PENDING,
        index=True,
    )

    # --- Relationships ---
    recipient: Mapped["Recipient"] = relationship("Recipient", back_populates="resource_requests")
    status_history: Mapped[List["ResourceRequestStatusHistory"]] = relationship(
        "ResourceRequestStatusHistory",
        back_populates="request",
        cascade="all, delete-orphan",
        order_by="ResourceRequestStatusHistory.created_at",
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<ResourceRequest id={self.id} status={self.status}>"


class ResourceRequestStatusHistory(Base, UUIDPrimaryKeyMixin):
    """
    Append-only audit log for a ResourceRequest's status changes. No
    `updated_at` on purpose — entries are never edited, only added.
    """

    __tablename__ = "resource_request_status_history"

    request_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("resource_requests.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # Null only for the initial row created alongside the request itself
    # (there is no "from" status before PENDING).
    from_status: Mapped[Optional[ResourceRequestStatus]] = mapped_column(
        Enum(
            ResourceRequestStatus,
            name="resource_request_status",
            values_callable=lambda e: [m.value for m in e],
        ),
        nullable=True,
    )
    to_status: Mapped[ResourceRequestStatus] = mapped_column(
        Enum(
            ResourceRequestStatus,
            name="resource_request_status",
            values_callable=lambda e: [m.value for m in e],
        ),
        nullable=False,
    )
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Null when the request was raised by the system rather than a
    # specific user action (not currently used, but keeps this row
    # consistent with OperationEvent.created_by_user_id).
    changed_by_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # --- Relationships ---
    request: Mapped["ResourceRequest"] = relationship("ResourceRequest", back_populates="status_history")
    changed_by: Mapped[Optional["User"]] = relationship("User", back_populates="resource_request_status_changes")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<ResourceRequestStatusHistory request_id={self.request_id} to={self.to_status}>"

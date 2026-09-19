"""
RescueOperation and OperationEvent models.

A RescueOperation is the execution of a RescueRequest end-to-end: one
rescue partner, one status lifecycle, and one or more Allocations (e.g. a
single truck run that drops meals at both NGO A and Shelter B). Every
state change — including dynamic reallocation — is appended to its
OperationEvent log, which is what lets the API "explain the old and new
allocation" after a reallocation happens.
"""

import uuid
from datetime import datetime
from typing import List, Optional, TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, JSON, Text, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base
from app.models.enums import OperationEventType, OperationStatus
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.allocation import Allocation
    from app.models.rescue_partner import RescuePartner
    from app.models.rescue_request import RescueRequest
    from app.models.user import User


class RescueOperation(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "rescue_operations"

    rescue_request_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("rescue_requests.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )
    partner_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("rescue_partners.id", ondelete="SET NULL"), nullable=True
    )

    status: Mapped[OperationStatus] = mapped_column(
        Enum(OperationStatus, name="operation_status", values_callable=lambda e: [m.value for m in e]),
        nullable=False,
        default=OperationStatus.PLANNED,
        index=True,
    )

    pickup_started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    delivered_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    # Set when status transitions to FAILED; explains what went wrong
    # (e.g. "recipient no longer reachable", "vehicle breakdown").
    failure_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Latest known position of whoever is executing this operation (set via
    # PATCH /api/operations/{operation_id}/location). Only the most recent
    # fix is kept — this is a "where is it now" pointer, not a location
    # history/trail, so it's plain columns rather than its own table.
    current_latitude: Mapped[Optional[float]] = mapped_column(nullable=True)
    current_longitude: Mapped[Optional[float]] = mapped_column(nullable=True)
    location_updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # --- Relationships ---
    rescue_request: Mapped["RescueRequest"] = relationship("RescueRequest", back_populates="operation")
    partner: Mapped[Optional["RescuePartner"]] = relationship("RescuePartner", back_populates="operations")
    allocations: Mapped[List["Allocation"]] = relationship("Allocation", back_populates="operation")
    events: Mapped[List["OperationEvent"]] = relationship(
        "OperationEvent",
        back_populates="operation",
        cascade="all, delete-orphan",
        order_by="OperationEvent.created_at",
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<RescueOperation id={self.id} status={self.status}>"


class OperationEvent(Base, UUIDPrimaryKeyMixin):
    """
    Append-only audit log for a RescueOperation. No `updated_at` on purpose —
    events are never edited, only added.
    """

    __tablename__ = "operation_events"

    operation_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("rescue_operations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    event_type: Mapped[OperationEventType] = mapped_column(
        Enum(
            OperationEventType,
            name="operation_event_type",
            values_callable=lambda e: [m.value for m in e],
        ),
        nullable=False,
        index=True,
    )
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Structured payload for events that need it, e.g. a REALLOCATED event
    # storing {"old_allocation": {...}, "new_allocation": {...}}.
    event_metadata: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Null when the event was raised by the system (e.g. automatic
    # reallocation) rather than a specific user action.
    created_by_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # --- Relationships ---
    operation: Mapped["RescueOperation"] = relationship("RescueOperation", back_populates="events")
    created_by: Mapped[Optional["User"]] = relationship("User", back_populates="triggered_events")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<OperationEvent id={self.id} type={self.event_type}>"

"""
RescueRequest model.

A RescueRequest is the coordination record created for a Resource once it
needs to be rescued — this is what the matching engine actually operates
on. Separating it from Resource keeps "what was posted" distinct from
"what's being actively matched/allocated right now", and lets urgency or
requested quantity be adjusted at request time without mutating the
original resource post.
"""

import uuid
from datetime import datetime
from typing import List, Optional, TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, Numeric, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base
from app.models.enums import RescueRequestStatus, UrgencyLevel
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.allocation import Allocation
    from app.models.match import Match
    from app.models.operation import RescueOperation
    from app.models.resource import Resource


class RescueRequest(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "rescue_requests"

    resource_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("resources.id", ondelete="CASCADE"), nullable=False, index=True
    )

    status: Mapped[RescueRequestStatus] = mapped_column(
        Enum(
            RescueRequestStatus,
            name="rescue_request_status",
            values_callable=lambda e: [m.value for m in e],
        ),
        nullable=False,
        default=RescueRequestStatus.PENDING,
        index=True,
    )

    # Snapshot of what needs to be rescued at request time — normally equal
    # to the resource's quantity, but can be lower if this is a follow-up
    # request for a partially-rescued resource.
    requested_quantity: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    urgency: Mapped[UrgencyLevel] = mapped_column(
        Enum(UrgencyLevel, name="urgency_level", values_callable=lambda e: [m.value for m in e]),
        nullable=False,
        default=UrgencyLevel.MEDIUM,
    )
    deadline: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # --- Relationships ---
    resource: Mapped["Resource"] = relationship("Resource", back_populates="rescue_requests")
    matches: Mapped[List["Match"]] = relationship(
        "Match", back_populates="rescue_request", cascade="all, delete-orphan"
    )
    allocations: Mapped[List["Allocation"]] = relationship(
        "Allocation", back_populates="rescue_request", cascade="all, delete-orphan"
    )
    operation: Mapped[Optional["RescueOperation"]] = relationship(
        "RescueOperation",
        back_populates="rescue_request",
        uselist=False,
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<RescueRequest id={self.id} status={self.status}>"

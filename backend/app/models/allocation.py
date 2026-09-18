"""
Allocation model.

An Allocation is a confirmed slice of a RescueRequest's quantity committed
to a specific Recipient or RescueHub (never both) — e.g. "NGO A -> 50",
"Shelter B -> 20", "Rescue Hub -> 10" from the same 80-meal resource.
Allocations are what dynamic reallocation actually creates, cancels, and
replaces when a recipient becomes unavailable mid-operation.
"""

import uuid
from typing import Optional, TYPE_CHECKING

from sqlalchemy import CheckConstraint, Enum, ForeignKey, Numeric, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base
from app.models.enums import AllocationStatus
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.match import Match
    from app.models.operation import RescueOperation
    from app.models.recipient import Recipient
    from app.models.rescue_hub import RescueHub
    from app.models.rescue_request import RescueRequest


class Allocation(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "allocations"
    __table_args__ = (
        CheckConstraint(
            "(recipient_id IS NOT NULL AND rescue_hub_id IS NULL) OR "
            "(recipient_id IS NULL AND rescue_hub_id IS NOT NULL)",
            name="allocation_target_xor",
        ),
    )

    rescue_request_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("rescue_requests.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # Set once a RescueOperation exists to execute this allocation.
    operation_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("rescue_operations.id", ondelete="SET NULL"), nullable=True
    )
    # The Match this allocation originated from, if any (traceability back
    # to the engine's original reasoning).
    match_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("matches.id", ondelete="SET NULL"), nullable=True
    )

    recipient_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("recipients.id", ondelete="CASCADE"), nullable=True
    )
    rescue_hub_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("rescue_hubs.id", ondelete="CASCADE"), nullable=True
    )

    allocated_quantity: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    status: Mapped[AllocationStatus] = mapped_column(
        Enum(AllocationStatus, name="allocation_status", values_callable=lambda e: [m.value for m in e]),
        nullable=False,
        default=AllocationStatus.PENDING,
        index=True,
    )

    # Human-readable explanation, e.g. "Closest available recipient within
    # capacity" or "Reallocated after NGO A became unavailable".
    reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # --- Relationships ---
    rescue_request: Mapped["RescueRequest"] = relationship("RescueRequest", back_populates="allocations")
    operation: Mapped[Optional["RescueOperation"]] = relationship(
        "RescueOperation", back_populates="allocations"
    )
    match: Mapped[Optional["Match"]] = relationship("Match")
    recipient: Mapped[Optional["Recipient"]] = relationship("Recipient", back_populates="allocations")
    rescue_hub: Mapped[Optional["RescueHub"]] = relationship("RescueHub", back_populates="allocations")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Allocation id={self.id} qty={self.allocated_quantity} status={self.status}>"

"""
Match model.

A Match is one candidate pairing the matching engine considered for a
RescueRequest — either a Recipient or a RescueHub, never both. Storing
every candidate (not just the winner) is what makes the engine's decisions
transparent and auditable: `reasons` holds the machine-readable factors
(distance, capacity fit, urgency weight, availability, etc.) that produced
`score`, and `status` records whether this candidate was ultimately
selected for an Allocation.
"""

import uuid
from typing import Optional, TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    Enum,
    Float,
    ForeignKey,
    JSON,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base
from app.models.enums import MatchCandidateType, MatchStatus
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.recipient import Recipient
    from app.models.rescue_hub import RescueHub
    from app.models.rescue_request import RescueRequest


class Match(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "matches"
    __table_args__ = (
        CheckConstraint(
            "(recipient_id IS NOT NULL AND rescue_hub_id IS NULL) OR "
            "(recipient_id IS NULL AND rescue_hub_id IS NOT NULL)",
            name="match_candidate_target_xor",
        ),
    )

    rescue_request_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("rescue_requests.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    candidate_type: Mapped[MatchCandidateType] = mapped_column(
        Enum(
            MatchCandidateType,
            name="match_candidate_type",
            values_callable=lambda e: [m.value for m in e],
        ),
        nullable=False,
    )
    recipient_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("recipients.id", ondelete="CASCADE"), nullable=True
    )
    rescue_hub_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("rescue_hubs.id", ondelete="CASCADE"), nullable=True
    )

    distance_km: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    # Overall ranking score computed by the matching engine (higher = better fit).
    score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    status: Mapped[MatchStatus] = mapped_column(
        Enum(MatchStatus, name="match_status", values_callable=lambda e: [m.value for m in e]),
        nullable=False,
        default=MatchStatus.PROPOSED,
        index=True,
    )

    # Structured, machine-readable breakdown of why this candidate scored
    # the way it did, e.g.:
    # {"distance_score": 0.8, "capacity_fit": 1.0, "urgency_weight": 0.6,
    #  "available": true, "notes": "within capacity, 4km away"}
    reasons: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # --- Relationships ---
    rescue_request: Mapped["RescueRequest"] = relationship("RescueRequest", back_populates="matches")
    recipient: Mapped[Optional["Recipient"]] = relationship("Recipient", back_populates="matches")
    rescue_hub: Mapped[Optional["RescueHub"]] = relationship("RescueHub", back_populates="matches")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Match id={self.id} type={self.candidate_type} score={self.score} status={self.status}>"

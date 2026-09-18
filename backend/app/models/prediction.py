"""
Prediction model.

Stores a predicted-surplus record (PREDICT -> PREPARE -> RESCUE). For the
hackathon these are generated from seeded/demo historical data —
`is_simulated` exists specifically so the API and frontend can always
label this output as simulated rather than presenting it as a live
statistical guarantee.
"""

import uuid
from datetime import date as date_type
from typing import Optional, TYPE_CHECKING

from sqlalchemy import Boolean, Date, Enum, Float, ForeignKey, JSON, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base
from app.models.enums import ResourceType
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.user import User


class Prediction(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "predictions"

    # Null = a platform-wide prediction rather than one scoped to a
    # specific provider.
    provider_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True
    )

    resource_type: Mapped[ResourceType] = mapped_column(
        Enum(ResourceType, name="resource_type", values_callable=lambda e: [m.value for m in e]),
        nullable=False,
    )
    predicted_date: Mapped[date_type] = mapped_column(Date, nullable=False, index=True)

    expected_quantity_min: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    expected_quantity_max: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)

    # Free-text description of the expected time window, e.g. "9-11 PM",
    # kept as a string rather than two datetimes since it's a recurring
    # daily pattern rather than a single instant.
    expected_time_window: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    confidence: Mapped[float] = mapped_column(Float, nullable=False)  # 0.0 - 1.0
    recommended_preparation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Always True for the hackathon build — surfaced explicitly in the API
    # response so simulated predictions are never confused with real ones.
    is_simulated: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # The historical/demo series the prediction was derived from, e.g.
    # {"Monday": 65, "Tuesday": 72, ...}, kept for transparency/debugging.
    based_on_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # --- Relationships ---
    provider: Mapped[Optional["User"]] = relationship("User")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Prediction id={self.id} date={self.predicted_date} simulated={self.is_simulated}>"

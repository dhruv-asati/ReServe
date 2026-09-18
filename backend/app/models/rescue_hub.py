"""
RescueHub model.

A RescueHub is a temporary/standing location that can receive resources
when normal recipients are unavailable or unreachable in time — e.g. a
night rescue hub used in the late-night scenario. Not tied to a single
User the way Recipient/RescuePartner are; typically admin-managed.
"""

import uuid
from typing import List, Optional, TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.allocation import Allocation
    from app.models.match import Match
    from app.models.user import User


class RescueHub(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "rescue_hubs"

    name: Mapped[str] = mapped_column(String(255), nullable=False)

    accepts_food: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    accepts_medical: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    # Whether this hub can receive resources outside normal daytime hours —
    # directly relevant to the late-night rescue scenario.
    is_24_hour: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    capacity: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    current_load: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    location_address: Mapped[str] = mapped_column(String(500), nullable=False)
    latitude: Mapped[Optional[float]] = mapped_column(nullable=True)
    longitude: Mapped[Optional[float]] = mapped_column(nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    operating_hours: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    managed_by_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    # --- Relationships ---
    managed_by: Mapped[Optional["User"]] = relationship("User")
    allocations: Mapped[List["Allocation"]] = relationship("Allocation", back_populates="rescue_hub")
    matches: Mapped[List["Match"]] = relationship("Match", back_populates="rescue_hub")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<RescueHub id={self.id} name={self.name!r}>"

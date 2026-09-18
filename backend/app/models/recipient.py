"""
Recipient model.

A Recipient is the profile record for an organization that can receive
rescued resources — an NGO, shelter, community organization, or an
authorized medical recipient organization. One-to-one with a User whose
role is RECIPIENT.
"""

import uuid
from typing import List, Optional, TYPE_CHECKING

from sqlalchemy import Boolean, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base
from app.models.enums import RecipientType
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.allocation import Allocation
    from app.models.match import Match
    from app.models.resource_request import ResourceRequest
    from app.models.user import User


class Recipient(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "recipients"

    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )

    organization_name: Mapped[str] = mapped_column(String(255), nullable=False)
    recipient_type: Mapped[RecipientType] = mapped_column(
        Enum(RecipientType, name="recipient_type", values_callable=lambda e: [m.value for m in e]),
        nullable=False,
    )

    accepts_food: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    accepts_medical: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    # Required before any MEDICAL allocation can be made to this recipient.
    medical_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Max quantity this recipient can take in a single rescue, used by the
    # matching engine as a hard capacity constraint.
    capacity: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    current_availability: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)

    # How far this recipient is willing/able to have resources delivered
    # from, in kilometers. Distinct from `medical_verified` below —
    # general platform verification (identity/legitimacy), not a
    # medical-eligibility check.
    service_area_km: Mapped[Optional[float]] = mapped_column(nullable=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    location_address: Mapped[str] = mapped_column(String(500), nullable=False)
    latitude: Mapped[Optional[float]] = mapped_column(nullable=True)
    longitude: Mapped[Optional[float]] = mapped_column(nullable=True)

    contact_phone: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    operating_hours: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # --- Relationships ---
    user: Mapped["User"] = relationship("User", back_populates="recipient_profile")
    allocations: Mapped[List["Allocation"]] = relationship("Allocation", back_populates="recipient")
    matches: Mapped[List["Match"]] = relationship("Match", back_populates="recipient")
    resource_requests: Mapped[List["ResourceRequest"]] = relationship(
        "ResourceRequest", back_populates="recipient", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Recipient id={self.id} org={self.organization_name!r}>"

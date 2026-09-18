"""
RescuePartner model.

A RescuePartner is the profile record for whoever physically moves a
resource from provider to recipient/hub — a volunteer, transport partner,
or organization. One-to-one with a User whose role is RESCUE_PARTNER.
"""

import uuid
from typing import List, Optional, TYPE_CHECKING

from sqlalchemy import Boolean, Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base
from app.models.enums import PartnerType
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.operation import RescueOperation
    from app.models.user import User


class RescuePartner(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "rescue_partners"

    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )

    # Relevant mainly for ORGANIZATION/TRANSPORT_ORG partner types — a lone
    # VOLUNTEER typically leaves this blank.
    organization_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    partner_type: Mapped[PartnerType] = mapped_column(
        Enum(PartnerType, name="partner_type", values_callable=lambda e: [m.value for m in e]),
        nullable=False,
    )
    # Free-text transportation capability, e.g. "bike", "van", "refrigerated truck".
    vehicle_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    # Max quantity this partner can carry in one trip, used as a pickup
    # feasibility constraint by the matching/allocation engine.
    capacity: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    is_available: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)

    accepts_food: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    accepts_medical: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    contact_phone: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    location_address: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    latitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    longitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    # How far from their base location this partner is willing to travel —
    # the partner-side equivalent of Recipient.service_area_km.
    service_radius_km: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    operating_hours: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # General platform verification (identity/legitimacy) — distinct from
    # any resource-type-specific eligibility check.
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    rating: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # --- Relationships ---
    user: Mapped["User"] = relationship("User", back_populates="partner_profile")
    operations: Mapped[List["RescueOperation"]] = relationship(
        "RescueOperation", back_populates="partner"
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<RescuePartner id={self.id} type={self.partner_type} available={self.is_available}>"

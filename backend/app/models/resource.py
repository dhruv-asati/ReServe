"""
Resource model.

A Resource is a unit of surplus (food or medical) posted by a provider
(hotel, restaurant, hospital, pharmacy, etc.) that needs to be rescued
before it expires. It carries everything the matching engine needs:
quantity, urgency, expiry/pickup deadlines, and location.
"""

import uuid
from datetime import datetime
from typing import List, Optional, TYPE_CHECKING

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base
from app.models.enums import (
    FoodCategory,
    ResourceStatus,
    ResourceType,
    StorageRequirement,
    UrgencyLevel,
)
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.rescue_request import RescueRequest
    from app.models.user import User


class Resource(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "resources"

    provider_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    resource_type: Mapped[ResourceType] = mapped_column(
        Enum(ResourceType, name="resource_type", values_callable=lambda e: [m.value for m in e]),
        nullable=False,
        index=True,
    )
    # Free-text subtype, e.g. "vegetarian meals", "antibiotics", "IV fluids"
    category: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)

    quantity: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    unit: Mapped[str] = mapped_column(String(30), nullable=False, default="units")

    status: Mapped[ResourceStatus] = mapped_column(
        Enum(ResourceStatus, name="resource_status", values_callable=lambda e: [m.value for m in e]),
        nullable=False,
        default=ResourceStatus.AVAILABLE,
        index=True,
    )
    urgency: Mapped[UrgencyLevel] = mapped_column(
        Enum(UrgencyLevel, name="urgency_level", values_callable=lambda e: [m.value for m in e]),
        nullable=False,
        default=UrgencyLevel.MEDIUM,
    )

    # When the resource actually becomes ready/available (e.g. "food is
    # packed and ready from 9pm"). Distinct from pickup_window_start, which
    # is the window a rescue partner is expected to arrive within.
    available_time: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Rescue deadline: after this point the resource is no longer usable.
    expiry_time: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    # Optional narrower pickup window within the expiry deadline
    # (e.g. the "90-minute rescue window" late-night scenario).
    pickup_window_start: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    pickup_window_end: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    location_address: Mapped[str] = mapped_column(String(500), nullable=False)
    latitude: Mapped[Optional[float]] = mapped_column(nullable=True)
    longitude: Mapped[Optional[float]] = mapped_column(nullable=True)

    image_url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)

    is_perishable: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    # True for MEDICAL resources by default at the service layer — stricter
    # eligibility/verification checks are enforced in the matching engine.
    requires_medical_verification: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Raw structured output from Gemini (Stage 5), validated by Pydantic
    # before being stored. Nullable until a resource has been analyzed.
    ai_analysis: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # --- Food-specific fields ---
    # All nullable and meaningful only when resource_type == FOOD; the
    # service/schema layer rejects them being set on MEDICAL resources.
    # Free-text subtype of FOOD, distinct from the generic `category`
    # column above (which is used for both FOOD and MEDICAL).
    food_category: Mapped[Optional[FoodCategory]] = mapped_column(
        Enum(FoodCategory, name="food_category", values_callable=lambda e: [m.value for m in e]),
        nullable=True,
    )
    is_vegetarian: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    # When the food was actually prepared/cooked — distinct from
    # available_time (when it becomes ready for pickup) and expiry_time
    # (the rescue deadline).
    preparation_time: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    # List of AllergenType values, e.g. ["MILK", "TREE_NUTS"], or ["NONE"]
    # for a resource explicitly confirmed allergen-free. Validated against
    # the AllergenType enum at the Pydantic layer.
    allergen_info: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    storage_requirements: Mapped[Optional[StorageRequirement]] = mapped_column(
        Enum(StorageRequirement, name="storage_requirement", values_callable=lambda e: [m.value for m in e]),
        nullable=True,
    )
    # Free-text, e.g. "sealed containers", "individually wrapped".
    packaging_info: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # --- Relationships ---
    provider: Mapped["User"] = relationship("User", back_populates="resources")
    rescue_requests: Mapped[List["RescueRequest"]] = relationship(
        "RescueRequest", back_populates="resource", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Resource id={self.id} title={self.title!r} status={self.status}>"

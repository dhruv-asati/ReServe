"""
User model.

A User is the login/identity record for everyone on the platform —
providers, recipients, rescue partners, and admins. Recipient- and
RescuePartner-specific data lives in their own profile tables (one-to-one
with User) rather than being crammed into this table, since only some
users need that extra profile information.
"""

from typing import List, Optional
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Enum, Float, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base
from app.models.enums import UserRole
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.notification import Notification
    from app.models.operation import OperationEvent
    from app.models.recipient import Recipient
    from app.models.resource import Resource
    from app.models.resource_request import ResourceRequestStatusHistory
    from app.models.rescue_partner import RescuePartner


class User(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role", values_callable=lambda e: [m.value for m in e]),
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # --- Profile fields ---
    # Generic enough to apply to any role (a provider's hotel, a
    # recipient's NGO, a rescue partner's transport org), so these live
    # directly on User rather than being duplicated across the
    # role-specific profile tables.
    organization_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    organization_description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    profile_image_url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    address: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    latitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    longitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # --- Relationships ---
    resources: Mapped[List["Resource"]] = relationship(
        "Resource", back_populates="provider", cascade="all, delete-orphan"
    )
    recipient_profile: Mapped[Optional["Recipient"]] = relationship(
        "Recipient", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    partner_profile: Mapped[Optional["RescuePartner"]] = relationship(
        "RescuePartner", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    notifications: Mapped[List["Notification"]] = relationship(
        "Notification", back_populates="user", cascade="all, delete-orphan"
    )
    triggered_events: Mapped[List["OperationEvent"]] = relationship(
        "OperationEvent", back_populates="created_by"
    )
    resource_request_status_changes: Mapped[List["ResourceRequestStatusHistory"]] = relationship(
        "ResourceRequestStatusHistory", back_populates="changed_by"
    )

    def __repr__(self) -> str:  # pragma: no cover - debugging convenience
        return f"<User id={self.id} email={self.email!r} role={self.role}>"

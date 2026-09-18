"""
Notification model.

A simple per-user notification record — e.g. "your resource was matched",
"a recipient became unavailable and we reallocated", "delivery confirmed".
Kept deliberately simple for the hackathon: no delivery channels/read
receipts beyond a single is_read flag.
"""

import uuid
from typing import Optional, TYPE_CHECKING

from sqlalchemy import Boolean, Enum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base
from app.models.enums import NotificationType
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.operation import RescueOperation
    from app.models.user import User


class Notification(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "notifications"

    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    notification_type: Mapped[NotificationType] = mapped_column(
        Enum(
            NotificationType, name="notification_type", values_callable=lambda e: [m.value for m in e]
        ),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)

    related_operation_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("rescue_operations.id", ondelete="SET NULL"), nullable=True
    )

    # --- Relationships ---
    user: Mapped["User"] = relationship("User", back_populates="notifications")
    operation: Mapped[Optional["RescueOperation"]] = relationship("RescueOperation")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Notification id={self.id} type={self.notification_type} read={self.is_read}>"

"""
User profile service: business logic backing

    GET /api/users/me
    PUT /api/users/me
    GET /api/users/{user_id}

kept separate from the router for the same reason as resource_service —
reusable without going through HTTP, and it's where the ownership/role
checks live so both routes enforce them consistently.
"""

import logging
import uuid

from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.user import UserProfileUpdate

logger = logging.getLogger(__name__)


def get_user_or_404(db: Session, user_id: uuid.UUID) -> User:
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise AppError(status_code=404, code="USER_NOT_FOUND", message="User not found.")
    return user


def get_user_profile(db: Session, user_id: uuid.UUID, current_user: User) -> User:
    """
    Enforces: a user may always view their own profile; viewing someone
    else's profile is restricted to ADMIN.
    """
    if user_id != current_user.id and current_user.role != UserRole.ADMIN:
        raise AppError(
            status_code=403,
            code="FORBIDDEN",
            message="Only admins can view another user's profile.",
        )
    return get_user_or_404(db, user_id)


def update_own_profile(db: Session, current_user: User, payload: UserProfileUpdate) -> User:
    """Updates only the fields provided; a user can only ever update their own profile."""
    update_data = payload.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        setattr(current_user, field, value)

    db.commit()
    db.refresh(current_user)

    logger.info("User %s updated their profile", current_user.id)
    return current_user

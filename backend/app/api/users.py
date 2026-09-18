"""
User profile endpoints:

    GET /api/users/me
    PUT /api/users/me
    GET /api/users/{user_id}

All endpoints require authentication. Users can update only their own
profile via PUT /me. Viewing another user's profile via GET
/{user_id} is restricted to ADMIN accounts; every authenticated user
can view their own profile that way too. Responses never include
`hashed_password` or any other auth internals — `UserProfileOut` only
lists the fields meant to be public.
"""

import logging
import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.database import get_db
from app.models.user import User
from app.schemas.common import SuccessResponse
from app.schemas.user import UserProfileOut, UserProfileUpdate
from app.services import user_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/users", tags=["Users"])


@router.get(
    "/me",
    response_model=SuccessResponse[UserProfileOut],
    summary="Get my profile",
    description="Returns the full profile of the currently authenticated user.",
)
def get_my_profile(current_user: User = Depends(get_current_user)):
    return SuccessResponse(
        data=UserProfileOut.model_validate(current_user),
        message="Profile retrieved successfully.",
    )


@router.put(
    "/me",
    response_model=SuccessResponse[UserProfileOut],
    summary="Update my profile",
    description="Updates the currently authenticated user's own profile. Only the fields "
    "provided are changed. Users may only ever update their own profile — there is no way to "
    "target another user's id here. `latitude` and `longitude` must be provided together.",
)
def update_my_profile(
    payload: UserProfileUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    user = user_service.update_own_profile(db, current_user, payload)
    return SuccessResponse(
        data=UserProfileOut.model_validate(user),
        message="Profile updated successfully.",
    )


@router.get(
    "/{user_id}",
    response_model=SuccessResponse[UserProfileOut],
    summary="Get a user's profile by id",
    description="Returns another user's profile. Restricted to ADMIN accounts — non-admins get "
    "a 403 unless `user_id` is their own (in which case, use /api/users/me instead).",
)
def get_user_profile(
    user_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    user = user_service.get_user_profile(db, user_id, current_user)
    return SuccessResponse(
        data=UserProfileOut.model_validate(user),
        message="Profile retrieved successfully.",
    )

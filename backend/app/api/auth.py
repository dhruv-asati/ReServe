"""
Auth endpoints:

    POST /api/auth/register
    POST /api/auth/login
    GET  /api/auth/me
    POST /api/auth/refresh
"""

import logging

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.database import get_db
from app.models.user import User
from app.schemas.auth import LoginRequest, RefreshedTokenData, RefreshRequest, RegisterRequest, TokenData, UserPublic
from app.schemas.common import SuccessResponse
from app.services import auth_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/auth", tags=["Auth"])


@router.post(
    "/register",
    response_model=SuccessResponse[UserPublic],
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
    description="Creates a new account. `role` must be one of PROVIDER, RECIPIENT, or "
    "RESCUE_PARTNER — ADMIN accounts cannot be self-registered and must be created "
    "out-of-band. Passwords are hashed with bcrypt before storage. Fails with 409 if the "
    "email is already registered.",
)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    user = auth_service.register_user(db, payload)
    return SuccessResponse(
        data=UserPublic.model_validate(user),
        message="User registered successfully.",
    )


@router.post(
    "/login",
    response_model=SuccessResponse[TokenData],
    summary="Log in",
    description="Exchanges email + password for an access token and a refresh token. Pass the "
    "`access_token` as 'Authorization: Bearer <token>' on subsequent requests — in Swagger, "
    "click the 'Authorize' button and paste the token there. Keep the `refresh_token` to get a "
    "new access token via /api/auth/refresh once the access token expires.",
)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    token_data = auth_service.authenticate_user(db, payload)
    return SuccessResponse(data=token_data, message="Login successful.")


@router.get(
    "/me",
    response_model=SuccessResponse[UserPublic],
    summary="Get the current authenticated user",
    description="Requires a valid access token. Returns the profile of whoever the token belongs to.",
)
def get_me(current_user: User = Depends(get_current_user)):
    return SuccessResponse(
        data=UserPublic.model_validate(current_user),
        message="Current user retrieved successfully.",
    )


@router.post(
    "/refresh",
    response_model=SuccessResponse[RefreshedTokenData],
    summary="Get a new access token",
    description="Exchanges a valid refresh token (from /login) for a new access/refresh token "
    "pair — use this once the access token expires instead of logging in again. Rejects access "
    "tokens presented here (they're not interchangeable with refresh tokens).",
)
def refresh(payload: RefreshRequest, db: Session = Depends(get_db)):
    token_data = auth_service.refresh_access_token(db, payload.refresh_token)
    return SuccessResponse(data=token_data, message="Token refreshed successfully.")

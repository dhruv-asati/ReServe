"""
Auth service: the business logic behind register/login/refresh, kept
separate from the API router so it's independently testable and reusable
(e.g. by a future seed-data script that needs to create users).
"""

import logging
import uuid

from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.user import User
from app.schemas.auth import LoginRequest, RefreshedTokenData, RegisterRequest, TokenData, UserPublic

logger = logging.getLogger(__name__)


def get_user_by_email(db: Session, email: str) -> User | None:
    return db.query(User).filter(User.email == email.lower()).first()


def register_user(db: Session, payload: RegisterRequest) -> User:
    """Create a new user. Raises AppError(409) if the email is already registered."""
    existing = get_user_by_email(db, payload.email)
    if existing is not None:
        raise AppError(
            status_code=409,
            code="EMAIL_ALREADY_REGISTERED",
            message="An account with this email already exists.",
        )

    user = User(
        email=payload.email.lower(),
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name,
        phone=payload.phone,
        role=payload.role,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    logger.info("Registered new user %s with role %s", user.email, user.role)
    return user


def _issue_token_pair(user: User) -> tuple[str, str]:
    """Mint a fresh (access_token, refresh_token) pair for a user."""
    access_token = create_access_token(subject=str(user.id), extra_claims={"role": user.role.value})
    refresh_token = create_refresh_token(subject=str(user.id))
    return access_token, refresh_token


def authenticate_user(db: Session, payload: LoginRequest) -> TokenData:
    """
    Verify credentials and issue an access/refresh token pair.

    Raises AppError(401) for any invalid-credentials case. Deliberately
    uses the same error code/message whether the email doesn't exist or
    the password is wrong, so login attempts can't be used to enumerate
    which emails are registered.
    """
    user = get_user_by_email(db, payload.email)
    if user is None or not verify_password(payload.password, user.hashed_password):
        raise AppError(
            status_code=401,
            code="INVALID_CREDENTIALS",
            message="Incorrect email or password.",
        )

    if not user.is_active:
        raise AppError(
            status_code=403,
            code="ACCOUNT_INACTIVE",
            message="This account has been deactivated.",
        )

    access_token, refresh_token = _issue_token_pair(user)

    logger.info("User %s logged in", user.email)
    return TokenData(
        access_token=access_token,
        refresh_token=refresh_token,
        user=UserPublic.model_validate(user),
    )


def refresh_access_token(db: Session, refresh_token: str) -> RefreshedTokenData:
    """
    Exchange a valid, unexpired refresh token for a new access/refresh
    pair.

    Note on rotation: a new refresh token is issued each call, and clients
    should discard the old one and use the new one going forward. However,
    since tokens here are stateless JWTs (no server-side token store), the
    OLD refresh token technically remains valid until its own expiry if
    someone were to reuse it — this implementation does not detect or
    block reuse of a rotated-out refresh token. True revocation would need
    a persisted token/session table (e.g. tracking issued refresh-token
    ids and their revoked/used status), which is a reasonable next step
    but was left out here to keep the schema hackathon-practical.

    Always re-fetches the user from the database rather than trusting
    anything from the old token, so a refresh can't be used to "lock in"
    a role or active-status the user no longer has.
    """
    payload = decode_token(refresh_token, expected_type="refresh")
    if payload is None or "sub" not in payload:
        raise AppError(
            status_code=401,
            code="INVALID_REFRESH_TOKEN",
            message="This refresh token is invalid, expired, or not a refresh token. Please log in again.",
        )

    try:
        user_id = uuid.UUID(payload["sub"])
    except (ValueError, TypeError):
        raise AppError(
            status_code=401, code="INVALID_REFRESH_TOKEN", message="This refresh token is malformed."
        )

    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise AppError(status_code=401, code="USER_NOT_FOUND", message="This account no longer exists.")

    if not user.is_active:
        raise AppError(
            status_code=403, code="ACCOUNT_INACTIVE", message="This account has been deactivated."
        )

    access_token, new_refresh_token = _issue_token_pair(user)

    logger.info("Issued refreshed token pair for user %s", user.email)
    return RefreshedTokenData(access_token=access_token, refresh_token=new_refresh_token)

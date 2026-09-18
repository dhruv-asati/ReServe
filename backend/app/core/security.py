"""
Security utilities: password hashing and JWT encoding/decoding.

Kept separate from the auth service/router so any other part of the
backend (or a future admin script) can hash a password or verify a token
without importing the auth API layer.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Literal, Optional

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# bcrypt is the standard choice for password hashing: slow by design
# (resistant to brute force) and battle-tested.
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

TokenType = Literal["access", "refresh"]


def hash_password(plain_password: str) -> str:
    """Hash a plaintext password for storage. Never store plaintext passwords."""
    return pwd_context.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Check a plaintext password against a stored bcrypt hash."""
    return pwd_context.verify(plain_password, hashed_password)


def _create_token(subject: str, token_type: TokenType, expires_minutes: int,
                   extra_claims: Optional[dict[str, Any]] = None) -> str:
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=expires_minutes)

    to_encode: dict[str, Any] = {
        "sub": subject,
        "type": token_type,
        "iat": now,
        "exp": expire,
    }
    if extra_claims:
        to_encode.update(extra_claims)

    return jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def create_access_token(subject: str, extra_claims: Optional[dict[str, Any]] = None) -> str:
    """
    Create a signed JWT access token (short-lived — JWT_ACCESS_TOKEN_EXPIRE_MINUTES).

    `subject` is the user's id (stored in the standard `sub` claim).
    `extra_claims` can carry non-sensitive, non-secret data useful for
    authorization checks without a DB round trip (e.g. role). Every access
    token carries `"type": "access"` so it can never be mistaken for — or
    misused as — a refresh token.
    """
    return _create_token(
        subject, "access", settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES, extra_claims
    )


def create_refresh_token(subject: str) -> str:
    """
    Create a signed JWT refresh token (long-lived — JWT_REFRESH_TOKEN_EXPIRE_MINUTES).

    Deliberately carries no role/permission claims — POST /api/auth/refresh
    re-fetches the user from the database before issuing a new access
    token, so a refresh token can't be used to "lock in" a role a user no
    longer has (e.g. after an admin deactivates the account).
    """
    return _create_token(subject, "refresh", settings.JWT_REFRESH_TOKEN_EXPIRE_MINUTES)


def decode_token(token: str, expected_type: Optional[TokenType] = None) -> Optional[dict[str, Any]]:
    """
    Decode and verify a JWT (access or refresh).

    Returns the decoded claims dict, or None if the token is invalid,
    malformed, expired, or — when `expected_type` is given — of the wrong
    type (e.g. a refresh token presented where an access token is
    required, or vice versa). Never raises to the caller — callers should
    treat None as "unauthenticated"/"invalid".
    """
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
    except JWTError as exc:
        logger.info("JWT decode failed: %s", exc)
        return None

    if expected_type is not None and payload.get("type") != expected_type:
        logger.info(
            "JWT type mismatch: expected %r, got %r", expected_type, payload.get("type")
        )
        return None

    return payload

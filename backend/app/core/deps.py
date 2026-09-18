"""
Authentication/authorization dependencies.

`get_current_user` protects any endpoint that needs a logged-in user —
just add `current_user: User = Depends(get_current_user)` to the route
signature. `require_roles(...)` builds on top of it for endpoints that
also need to restrict *which* roles may call them (used starting with the
resource/matching/operations stages).
"""

import uuid

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.core.security import decode_token
from app.db.database import get_db
from app.models.enums import UserRole
from app.models.user import User

# HTTPBearer renders as a simple "Authorize" -> paste-your-token field in
# Swagger UI, which fits a JSON-body login endpoint better than the
# OAuth2 password-flow form Swagger otherwise expects.
bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None:
        raise AppError(
            status_code=401,
            code="NOT_AUTHENTICATED",
            message="Missing bearer token. Log in via /api/auth/login and pass the access token "
            "as 'Authorization: Bearer <token>'.",
        )

    payload = decode_token(credentials.credentials, expected_type="access")
    if payload is None or "sub" not in payload:
        raise AppError(
            status_code=401,
            code="INVALID_TOKEN",
            message="The provided token is invalid, expired, or not an access token. "
            "Please log in again, or use /api/auth/refresh if you have a refresh token.",
        )

    try:
        user_id = uuid.UUID(payload["sub"])
    except (ValueError, TypeError):
        raise AppError(status_code=401, code="INVALID_TOKEN", message="The provided token is malformed.")

    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise AppError(status_code=401, code="USER_NOT_FOUND", message="This account no longer exists.")

    if not user.is_active:
        raise AppError(
            status_code=403, code="ACCOUNT_INACTIVE", message="This account has been deactivated."
        )

    return user


def require_roles(*allowed_roles: UserRole):
    """
    Dependency factory for role-restricted endpoints, e.g.:

        @router.post("/resources")
        def create_resource(
            current_user: User = Depends(require_roles(UserRole.PROVIDER, UserRole.ADMIN)),
        ):
            ...
    """

    def _dependency(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise AppError(
                status_code=403,
                code="FORBIDDEN_ROLE",
                message=f"This action requires one of the following roles: "
                f"{', '.join(r.value for r in allowed_roles)}.",
            )
        return current_user

    return _dependency

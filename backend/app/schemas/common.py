"""
Shared response envelope schemas.

Every endpoint in ReServe responds with one of these two shapes so frontend
error handling can be generic instead of per-endpoint:

Success:
    {"success": true, "data": {...}, "message": "..."}

Error:
    {"success": false, "error": {"code": "...", "message": "..."}}
"""

from typing import Any, Generic, Optional, TypeVar
from uuid import UUID

from pydantic import BaseModel, ConfigDict

T = TypeVar("T")


class ErrorDetail(BaseModel):
    code: str
    message: str


class SuccessResponse(BaseModel, Generic[T]):
    success: bool = True
    data: Optional[T] = None
    message: str = ""


class ErrorResponse(BaseModel):
    success: bool = False
    error: ErrorDetail


class HealthData(BaseModel):
    status: str
    environment: str
    version: str
    database_connected: bool


class OwnerSummary(BaseModel):
    """
    Minimal, safe user info embedded in a recipient/partner response — the
    account behind the profile, never including the password hash or any
    other auth internals. Distinct from resource.ProviderSummary only in
    including `email`, since recipient/partner directories are meant to
    be contactable by other authenticated users coordinating a rescue.
    """

    id: UUID
    full_name: str
    email: str
    phone: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


# Generic dict-based success response, handy for endpoints that don't
# (yet) have a dedicated Pydantic model for their payload.
class GenericSuccessResponse(BaseModel):
    success: bool = True
    data: dict[str, Any]
    message: str = ""

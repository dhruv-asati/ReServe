"""
Pydantic schemas for admin endpoints:

    GET   /api/admin/users
    PATCH /api/admin/partners/{partner_id}/verify
    PATCH /api/admin/recipients/{recipient_id}/verify

All three are restricted to ADMIN accounts (see app/core/deps.require_roles
and app/api/admin.py). Verifying a partner or recipient sets the same
`is_verified` column PUT /api/recipients/{id} and PUT /api/partners/{id}
already expose to admins (see app/schemas/recipient.py and
app/schemas/rescue_partner.py) — this just gives that one action its own
purpose-built route instead of requiring a full profile PUT to flip a flag.
"""

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import UserRole


class VerificationUpdate(BaseModel):
    is_verified: bool = Field(
        default=True,
        description="True to verify this profile, false to revoke a previous verification. "
        "Defaults to true, so an empty PATCH body verifies.",
    )

    model_config = ConfigDict(json_schema_extra={"example": {"is_verified": True}})


class AdminUserOut(BaseModel):
    """
    A user as seen by an admin. Never includes `hashed_password` or any
    other auth internal — same discipline as UserProfileOut in
    app/schemas/user.py, this schema lists only the fields meant to be
    exposed, and is always built explicitly (never via model_validate on
    the raw ORM object) precisely so a new column added to User later
    can't leak through here by accident.
    """

    id: uuid.UUID
    email: str
    full_name: str
    phone: Optional[str] = None
    role: UserRole
    is_active: bool
    organization_name: Optional[str] = None
    created_at: datetime

    verification_profile_id: Optional[uuid.UUID] = Field(
        default=None,
        description="This user's Recipient or RescuePartner profile id — pass it to the matching "
        "PATCH /api/admin/recipients/{id}/verify or /api/admin/partners/{id}/verify endpoint. "
        "Null if the user hasn't created that profile yet, or their role carries no platform "
        "verification (PROVIDER, ADMIN).",
    )
    is_verified: Optional[bool] = Field(
        default=None,
        description="Whether that profile is currently verified. Null under the same conditions "
        "as verification_profile_id.",
    )


class AdminUserListData(BaseModel):
    items: list[AdminUserOut]
    total: int
    skip: int
    limit: int
    has_more: bool

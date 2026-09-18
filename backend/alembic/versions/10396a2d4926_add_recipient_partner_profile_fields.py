"""add recipient and rescue partner profile fields

Revision ID: 10396a2d4926
Revises: a1c3e7f92b6d
Create Date: 2026-09-18 06:00:00.000000

- `recipients`: adds `service_area_km` (Float) and `is_verified` (Boolean,
  default False) — general platform verification, distinct from the
  existing resource-type-specific `medical_verified`.
- `rescue_partners`: adds `organization_name`, `contact_phone`,
  `location_address`, `accepts_food`, `accepts_medical`,
  `operating_hours`, `is_verified`; renames `current_latitude` /
  `current_longitude` to `latitude` / `longitude` for consistency with
  every other location-bearing table (Resource, Recipient) — these were
  never used for live GPS tracking, just the partner's base location.

All new columns are nullable (or boolean with a server default), so this
is a safe additive change for existing rows.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "10396a2d4926"
down_revision: Union[str, None] = "a1c3e7f92b6d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- recipients ---
    op.add_column("recipients", sa.Column("service_area_km", sa.Float(), nullable=True))
    op.add_column(
        "recipients",
        sa.Column("is_verified", sa.Boolean(), nullable=False, server_default=sa.false()),
    )

    # --- rescue_partners ---
    op.add_column("rescue_partners", sa.Column("organization_name", sa.String(255), nullable=True))
    op.add_column("rescue_partners", sa.Column("contact_phone", sa.String(30), nullable=True))
    op.add_column("rescue_partners", sa.Column("location_address", sa.String(500), nullable=True))
    op.add_column(
        "rescue_partners",
        sa.Column("accepts_food", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.add_column(
        "rescue_partners",
        sa.Column("accepts_medical", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column("rescue_partners", sa.Column("operating_hours", sa.Text(), nullable=True))
    op.add_column(
        "rescue_partners",
        sa.Column("is_verified", sa.Boolean(), nullable=False, server_default=sa.false()),
    )

    op.alter_column("rescue_partners", "current_latitude", new_column_name="latitude")
    op.alter_column("rescue_partners", "current_longitude", new_column_name="longitude")


def downgrade() -> None:
    op.alter_column("rescue_partners", "longitude", new_column_name="current_longitude")
    op.alter_column("rescue_partners", "latitude", new_column_name="current_latitude")

    op.drop_column("rescue_partners", "is_verified")
    op.drop_column("rescue_partners", "operating_hours")
    op.drop_column("rescue_partners", "accepts_medical")
    op.drop_column("rescue_partners", "accepts_food")
    op.drop_column("rescue_partners", "location_address")
    op.drop_column("rescue_partners", "contact_phone")
    op.drop_column("rescue_partners", "organization_name")

    op.drop_column("recipients", "is_verified")
    op.drop_column("recipients", "service_area_km")

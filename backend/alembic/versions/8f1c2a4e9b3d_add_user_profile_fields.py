"""add user profile fields

Revision ID: 8f1c2a4e9b3d
Revises: 34a01cac6ded
Create Date: 2026-09-17 00:00:00.000000

Adds profile-management columns to `users`: organization_name,
organization_description, profile_image_url, address, latitude,
longitude. All nullable, so this is a safe additive change for existing
rows.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "8f1c2a4e9b3d"
down_revision: Union[str, None] = "34a01cac6ded"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("organization_name", sa.String(255), nullable=True))
    op.add_column("users", sa.Column("organization_description", sa.Text(), nullable=True))
    op.add_column("users", sa.Column("profile_image_url", sa.String(1000), nullable=True))
    op.add_column("users", sa.Column("address", sa.String(500), nullable=True))
    op.add_column("users", sa.Column("latitude", sa.Float(), nullable=True))
    op.add_column("users", sa.Column("longitude", sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "longitude")
    op.drop_column("users", "latitude")
    op.drop_column("users", "address")
    op.drop_column("users", "profile_image_url")
    op.drop_column("users", "organization_description")
    op.drop_column("users", "organization_name")

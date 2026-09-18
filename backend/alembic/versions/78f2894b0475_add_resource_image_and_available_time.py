"""add resource image_url and available_time

Revision ID: 78f2894b0475
Revises: 8f1c2a4e9b3d
Create Date: 2026-09-17 00:00:00.000000

Adds two columns to `resources`:

- `image_url` (String(1000), nullable) — matches the style of
  `users.profile_image_url` added in the previous migration.
- `available_time` (DateTime(timezone=True), nullable) — when the
  resource actually becomes ready/available, distinct from
  `pickup_window_start` (when a partner is expected to arrive).

Both nullable, so this is a safe additive change for existing rows.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "78f2894b0475"
down_revision: Union[str, None] = "8f1c2a4e9b3d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("resources", sa.Column("image_url", sa.String(1000), nullable=True))
    op.add_column(
        "resources", sa.Column("available_time", sa.DateTime(timezone=True), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("resources", "available_time")
    op.drop_column("resources", "image_url")

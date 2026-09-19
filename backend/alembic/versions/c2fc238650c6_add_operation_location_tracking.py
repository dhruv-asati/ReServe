"""add operation location tracking

Adds three columns to rescue_operations so the latest known position of
whoever is executing an operation can be stored and served back:

    current_latitude, current_longitude   -- the latest GPS fix
    location_updated_at                   -- when that fix was recorded

Set via the new PATCH /api/operations/{operation_id}/location endpoint
(app/services/operation_service.update_location). Only the most recent
fix is kept, so this is purely additive/nullable columns — no history
table, no data migration needed for existing rows.

Revision ID: c2fc238650c6
Revises: e2f5a9c1d834
Create Date: 2025-03-01 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c2fc238650c6"
down_revision: Union[str, None] = "e2f5a9c1d834"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("rescue_operations", sa.Column("current_latitude", sa.Float(), nullable=True))
    op.add_column("rescue_operations", sa.Column("current_longitude", sa.Float(), nullable=True))
    op.add_column(
        "rescue_operations", sa.Column("location_updated_at", sa.DateTime(timezone=True), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("rescue_operations", "location_updated_at")
    op.drop_column("rescue_operations", "current_longitude")
    op.drop_column("rescue_operations", "current_latitude")

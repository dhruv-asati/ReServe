"""add REALLOCATED operation event type

Adds OperationEventType.REALLOCATED, used by
POST /api/operations/{operation_id}/reallocate to log the cancel ->
find-replacement -> reassign flow when a recipient becomes unavailable
mid-operation. Purely additive — no data migration needed.

Revision ID: e2f5a9c1d834
Revises: c7b19e2f5a4d
Create Date: 2025-02-01 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e2f5a9c1d834"
down_revision: Union[str, None] = "c7b19e2f5a4d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ADD VALUE can't run inside the transaction Alembic normally wraps
    # each migration in, so it needs its own autocommit block (same
    # pattern as the STATUS_CHANGED addition in c7b19e2f5a4d).
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE operation_event_type ADD VALUE IF NOT EXISTS 'REALLOCATED'")


def downgrade() -> None:
    # Postgres has no DROP VALUE for enums, so operation_event_type keeps
    # REALLOCATED even on downgrade — harmless (an unused label), same
    # accepted limitation noted in c7b19e2f5a4d for STATUS_CHANGED.
    pass

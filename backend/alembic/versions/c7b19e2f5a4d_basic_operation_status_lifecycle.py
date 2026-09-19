"""basic operation status lifecycle

Collapses OperationStatus down to the basic 5-value lifecycle used by the
operations stage (PLANNED, IN_TRANSIT, DELIVERED, COMPLETED, FAILED),
remapping every existing row's old value onto the closest new one. Also
adds OperationEventType.STATUS_CHANGED (used by every PATCH
/api/operations/{operation_id}/status call), and two new columns on
rescue_operations: completed_at and failure_reason.

Revision ID: c7b19e2f5a4d
Revises: 8d13ac9db247
Create Date: 2025-01-01 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "c7b19e2f5a4d"
down_revision: Union[str, None] = "8d13ac9db247"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

OLD_TO_NEW_STATUS = {
    "CREATED": "PLANNED",
    "MATCHING": "PLANNED",
    "MATCHED": "PLANNED",
    "PARTNER_ASSIGNED": "PLANNED",
    "PICKUP_IN_PROGRESS": "PLANNED",
    "IN_TRANSIT": "IN_TRANSIT",
    "DELIVERED": "DELIVERED",
    "REALLOCATING": "IN_TRANSIT",
    "CANCELLED": "FAILED",
    "EXPIRED": "FAILED",
}

# Reverse mapping used by downgrade(). Lossy for COMPLETED/FAILED (no
# exact old equivalent), so downgrade maps them to the closest old status
# rather than attempting to recover which specific old sub-state a row
# was actually in.
NEW_TO_OLD_STATUS = {
    "PLANNED": "CREATED",
    "IN_TRANSIT": "IN_TRANSIT",
    "DELIVERED": "DELIVERED",
    "COMPLETED": "DELIVERED",
    "FAILED": "CANCELLED",
}


def upgrade() -> None:
    # --- operation_status: CREATED/MATCHING/.../EXPIRED (10 values) -> ---
    # --- PLANNED/IN_TRANSIT/DELIVERED/COMPLETED/FAILED (5 values)   -----
    op.execute("ALTER TYPE operation_status RENAME TO operation_status_old")

    new_status_enum = postgresql.ENUM(
        "PLANNED", "IN_TRANSIT", "DELIVERED", "COMPLETED", "FAILED", name="operation_status"
    )
    new_status_enum.create(op.get_bind())

    op.execute("ALTER TABLE rescue_operations ALTER COLUMN status DROP DEFAULT")

    case_sql = " ".join(
        f"WHEN '{old}' THEN '{new}'" for old, new in OLD_TO_NEW_STATUS.items()
    )
    op.execute(
        f"""
        ALTER TABLE rescue_operations
        ALTER COLUMN status TYPE operation_status
        USING (CASE status::text {case_sql} END)::operation_status
        """
    )
    op.execute("ALTER TABLE rescue_operations ALTER COLUMN status SET DEFAULT 'PLANNED'")
    op.execute("DROP TYPE operation_status_old")

    # --- operation_event_type: add STATUS_CHANGED -------------------------
    # ADD VALUE can't run inside the transaction Alembic normally wraps
    # each migration in, so it needs its own autocommit block.
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE operation_event_type ADD VALUE IF NOT EXISTS 'STATUS_CHANGED'")

    # --- rescue_operations: new columns ------------------------------------
    op.add_column("rescue_operations", sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("rescue_operations", sa.Column("failure_reason", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("rescue_operations", "failure_reason")
    op.drop_column("rescue_operations", "completed_at")

    # Postgres has no DROP VALUE for enums, so operation_event_type keeps
    # STATUS_CHANGED even on downgrade — harmless (an unused label), and
    # the standard accepted limitation for additive enum migrations.

    op.execute("ALTER TYPE operation_status RENAME TO operation_status_new")

    old_status_enum = postgresql.ENUM(
        "CREATED",
        "MATCHING",
        "MATCHED",
        "PARTNER_ASSIGNED",
        "PICKUP_IN_PROGRESS",
        "IN_TRANSIT",
        "DELIVERED",
        "REALLOCATING",
        "CANCELLED",
        "EXPIRED",
        name="operation_status",
    )
    old_status_enum.create(op.get_bind())

    op.execute("ALTER TABLE rescue_operations ALTER COLUMN status DROP DEFAULT")

    case_sql = " ".join(
        f"WHEN '{new}' THEN '{old}'" for new, old in NEW_TO_OLD_STATUS.items()
    )
    op.execute(
        f"""
        ALTER TABLE rescue_operations
        ALTER COLUMN status TYPE operation_status
        USING (CASE status::text {case_sql} END)::operation_status
        """
    )
    op.execute("ALTER TABLE rescue_operations ALTER COLUMN status SET DEFAULT 'CREATED'")
    op.execute("DROP TYPE operation_status_new")

"""add resource requests

Revision ID: 8d13ac9db247
Revises: 10396a2d4926
Create Date: 2026-09-18 00:00:00.000000

Creates `resource_requests` (a RECIPIENT's demand-side ask, independent
of any specific Resource — see app/models/resource_request.py for why
this is deliberately separate from `rescue_requests`) and
`resource_request_status_history` (its append-only status audit log,
mirroring `operation_events`), plus the `resource_request_status`
Postgres enum type. Follows the same hand-authored style as
34a01cac6ded (re-declaring a shared enum per column, no explicit type
drop on downgrade — consistent with how that migration handles
`urgency_level` being reused across `resources` and `rescue_requests`).
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "8d13ac9db247"
down_revision: Union[str, None] = "10396a2d4926"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ---------------------------------------------------------------
    # resource_requests
    # ---------------------------------------------------------------
    op.create_table(
        "resource_requests",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "recipient_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("recipients.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "resource_type",
            sa.Enum("FOOD", "MEDICAL", name="resource_type"),
            nullable=False,
        ),
        sa.Column("requested_quantity", sa.Numeric(10, 2), nullable=False),
        sa.Column("requesting_organization", sa.String(255), nullable=False),
        sa.Column(
            "urgency",
            sa.Enum("LOW", "MEDIUM", "HIGH", "CRITICAL", name="urgency_level"),
            nullable=False,
            server_default="MEDIUM",
        ),
        sa.Column("needed_by", sa.DateTime(timezone=True), nullable=False),
        sa.Column("eligibility_requirements", sa.Text(), nullable=True),
        sa.Column("can_self_pickup", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "status",
            sa.Enum("PENDING", "APPROVED", "REJECTED", "FULFILLED", "CANCELLED", name="resource_request_status"),
            nullable=False,
            server_default="PENDING",
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_resource_requests_recipient_id", "resource_requests", ["recipient_id"])
    op.create_index("ix_resource_requests_resource_type", "resource_requests", ["resource_type"])
    op.create_index("ix_resource_requests_status", "resource_requests", ["status"])

    # ---------------------------------------------------------------
    # resource_request_status_history
    # ---------------------------------------------------------------
    op.create_table(
        "resource_request_status_history",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "request_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("resource_requests.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "from_status",
            sa.Enum("PENDING", "APPROVED", "REJECTED", "FULFILLED", "CANCELLED", name="resource_request_status"),
            nullable=True,
        ),
        sa.Column(
            "to_status",
            sa.Enum("PENDING", "APPROVED", "REJECTED", "FULFILLED", "CANCELLED", name="resource_request_status"),
            nullable=False,
        ),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column(
            "changed_by_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index(
        "ix_resource_request_status_history_request_id", "resource_request_status_history", ["request_id"]
    )


def downgrade() -> None:
    op.drop_table("resource_request_status_history")
    op.drop_table("resource_requests")

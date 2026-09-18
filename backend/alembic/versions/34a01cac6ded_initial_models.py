"""initial models

Revision ID: 34a01cac6ded
Revises:
Create Date: 2026-09-17 00:00:00.000000

Creates all 12 core tables (users, resources, recipients, rescue_partners,
rescue_hubs, rescue_requests, matches, allocations, rescue_operations,
operation_events, notifications, predictions) plus their Postgres enum
types, foreign keys, indexes, and check constraints.

Hand-authored to match app/models/ exactly, so a future
`alembic revision --autogenerate` run against this schema should produce
no diff. Tables are created in FK-dependency order; downgrade() drops them
in reverse.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "34a01cac6ded"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ---------------------------------------------------------------
    # users
    # ---------------------------------------------------------------
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("phone", sa.String(30), nullable=True),
        sa.Column(
            "role",
            sa.Enum(
                "PROVIDER", "RECIPIENT", "RESCUE_PARTNER", "ADMIN", name="user_role"
            ),
            nullable=False,
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    # ---------------------------------------------------------------
    # resources
    # ---------------------------------------------------------------
    op.create_table(
        "resources",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "provider_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "resource_type",
            sa.Enum("FOOD", "MEDICAL", name="resource_type"),
            nullable=False,
        ),
        sa.Column("category", sa.String(120), nullable=True),
        sa.Column("quantity", sa.Numeric(10, 2), nullable=False),
        sa.Column("unit", sa.String(30), nullable=False, server_default="units"),
        sa.Column(
            "status",
            sa.Enum(
                "AVAILABLE",
                "MATCHING",
                "ALLOCATED",
                "IN_TRANSIT",
                "DELIVERED",
                "EXPIRED",
                "CANCELLED",
                name="resource_status",
            ),
            nullable=False,
            server_default="AVAILABLE",
        ),
        sa.Column(
            "urgency",
            sa.Enum("LOW", "MEDIUM", "HIGH", "CRITICAL", name="urgency_level"),
            nullable=False,
            server_default="MEDIUM",
        ),
        sa.Column("expiry_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("pickup_window_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("pickup_window_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("location_address", sa.String(500), nullable=False),
        sa.Column("latitude", sa.Float(), nullable=True),
        sa.Column("longitude", sa.Float(), nullable=True),
        sa.Column("is_perishable", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "requires_medical_verification", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
        sa.Column("ai_analysis", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_resources_provider_id", "resources", ["provider_id"])
    op.create_index("ix_resources_resource_type", "resources", ["resource_type"])
    op.create_index("ix_resources_status", "resources", ["status"])

    # ---------------------------------------------------------------
    # recipients
    # ---------------------------------------------------------------
    op.create_table(
        "recipients",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("organization_name", sa.String(255), nullable=False),
        sa.Column(
            "recipient_type",
            sa.Enum(
                "NGO", "SHELTER", "COMMUNITY_ORG", "MEDICAL_ORG", name="recipient_type"
            ),
            nullable=False,
        ),
        sa.Column("accepts_food", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("accepts_medical", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("medical_verified", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("capacity", sa.Integer(), nullable=True),
        sa.Column("current_availability", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("location_address", sa.String(500), nullable=False),
        sa.Column("latitude", sa.Float(), nullable=True),
        sa.Column("longitude", sa.Float(), nullable=True),
        sa.Column("contact_phone", sa.String(30), nullable=True),
        sa.Column("operating_hours", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_recipients_user_id", "recipients", ["user_id"], unique=True)
    op.create_index("ix_recipients_current_availability", "recipients", ["current_availability"])

    # ---------------------------------------------------------------
    # rescue_partners
    # ---------------------------------------------------------------
    op.create_table(
        "rescue_partners",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column(
            "partner_type",
            sa.Enum("VOLUNTEER", "TRANSPORT_ORG", "ORGANIZATION", name="partner_type"),
            nullable=False,
        ),
        sa.Column("vehicle_type", sa.String(100), nullable=True),
        sa.Column("capacity", sa.Integer(), nullable=True),
        sa.Column("is_available", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("current_latitude", sa.Float(), nullable=True),
        sa.Column("current_longitude", sa.Float(), nullable=True),
        sa.Column("service_radius_km", sa.Float(), nullable=True),
        sa.Column("rating", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_rescue_partners_user_id", "rescue_partners", ["user_id"], unique=True)
    op.create_index("ix_rescue_partners_is_available", "rescue_partners", ["is_available"])

    # ---------------------------------------------------------------
    # rescue_hubs
    # ---------------------------------------------------------------
    op.create_table(
        "rescue_hubs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("accepts_food", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("accepts_medical", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_24_hour", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("capacity", sa.Integer(), nullable=True),
        sa.Column("current_load", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("location_address", sa.String(500), nullable=False),
        sa.Column("latitude", sa.Float(), nullable=True),
        sa.Column("longitude", sa.Float(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("operating_hours", sa.Text(), nullable=True),
        sa.Column(
            "managed_by_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_rescue_hubs_is_active", "rescue_hubs", ["is_active"])

    # ---------------------------------------------------------------
    # rescue_requests
    # ---------------------------------------------------------------
    op.create_table(
        "rescue_requests",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "resource_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("resources.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum(
                "PENDING",
                "MATCHING",
                "MATCHED",
                "PARTIALLY_MATCHED",
                "FAILED",
                "CANCELLED",
                "EXPIRED",
                name="rescue_request_status",
            ),
            nullable=False,
            server_default="PENDING",
        ),
        sa.Column("requested_quantity", sa.Numeric(10, 2), nullable=False),
        sa.Column(
            "urgency",
            sa.Enum("LOW", "MEDIUM", "HIGH", "CRITICAL", name="urgency_level"),
            nullable=False,
            server_default="MEDIUM",
        ),
        sa.Column("deadline", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_rescue_requests_resource_id", "rescue_requests", ["resource_id"])
    op.create_index("ix_rescue_requests_status", "rescue_requests", ["status"])

    # ---------------------------------------------------------------
    # matches
    # ---------------------------------------------------------------
    op.create_table(
        "matches",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "rescue_request_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("rescue_requests.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "candidate_type",
            sa.Enum("RECIPIENT", "RESCUE_HUB", name="match_candidate_type"),
            nullable=False,
        ),
        sa.Column(
            "recipient_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("recipients.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column(
            "rescue_hub_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("rescue_hubs.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("distance_km", sa.Float(), nullable=True),
        sa.Column("score", sa.Float(), nullable=True),
        sa.Column(
            "status",
            sa.Enum("PROPOSED", "SELECTED", "REJECTED", "EXPIRED", name="match_status"),
            nullable=False,
            server_default="PROPOSED",
        ),
        sa.Column("reasons", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "(recipient_id IS NOT NULL AND rescue_hub_id IS NULL) OR "
            "(recipient_id IS NULL AND rescue_hub_id IS NOT NULL)",
            name="match_candidate_target_xor",
        ),
    )
    op.create_index("ix_matches_rescue_request_id", "matches", ["rescue_request_id"])
    op.create_index("ix_matches_status", "matches", ["status"])

    # ---------------------------------------------------------------
    # rescue_operations
    # ---------------------------------------------------------------
    op.create_table(
        "rescue_operations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "rescue_request_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("rescue_requests.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column(
            "partner_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("rescue_partners.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "status",
            sa.Enum(
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
            ),
            nullable=False,
            server_default="CREATED",
        ),
        sa.Column("pickup_started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_rescue_operations_rescue_request_id", "rescue_operations", ["rescue_request_id"], unique=True
    )
    op.create_index("ix_rescue_operations_status", "rescue_operations", ["status"])

    # ---------------------------------------------------------------
    # allocations
    # ---------------------------------------------------------------
    op.create_table(
        "allocations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "rescue_request_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("rescue_requests.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "operation_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("rescue_operations.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "match_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("matches.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "recipient_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("recipients.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column(
            "rescue_hub_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("rescue_hubs.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("allocated_quantity", sa.Numeric(10, 2), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "PENDING", "CONFIRMED", "REALLOCATED", "CANCELLED", "DELIVERED", name="allocation_status"
            ),
            nullable=False,
            server_default="PENDING",
        ),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "(recipient_id IS NOT NULL AND rescue_hub_id IS NULL) OR "
            "(recipient_id IS NULL AND rescue_hub_id IS NOT NULL)",
            name="allocation_target_xor",
        ),
    )
    op.create_index("ix_allocations_rescue_request_id", "allocations", ["rescue_request_id"])
    op.create_index("ix_allocations_status", "allocations", ["status"])

    # ---------------------------------------------------------------
    # operation_events
    # ---------------------------------------------------------------
    op.create_table(
        "operation_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "operation_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("rescue_operations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "event_type",
            sa.Enum(
                "CREATED",
                "MATCHING_STARTED",
                "MATCHED",
                "PARTNER_ASSIGNED",
                "PICKUP_STARTED",
                "IN_TRANSIT",
                "DELIVERED",
                "REALLOCATION_TRIGGERED",
                "REALLOCATED",
                "CANCELLED",
                "EXPIRED",
                "NOTE",
                name="operation_event_type",
            ),
            nullable=False,
        ),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("event_metadata", sa.JSON(), nullable=True),
        sa.Column(
            "created_by_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_operation_events_operation_id", "operation_events", ["operation_id"])
    op.create_index("ix_operation_events_event_type", "operation_events", ["event_type"])

    # ---------------------------------------------------------------
    # notifications
    # ---------------------------------------------------------------
    op.create_table(
        "notifications",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "notification_type",
            sa.Enum(
                "MATCH_FOUND",
                "PARTNER_ASSIGNED",
                "OPERATION_UPDATE",
                "REALLOCATION",
                "DELIVERY_CONFIRMED",
                "SYSTEM",
                name="notification_type",
            ),
            nullable=False,
        ),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("is_read", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column(
            "related_operation_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("rescue_operations.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_notifications_user_id", "notifications", ["user_id"])
    op.create_index("ix_notifications_is_read", "notifications", ["is_read"])

    # ---------------------------------------------------------------
    # predictions
    # ---------------------------------------------------------------
    op.create_table(
        "predictions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "provider_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column(
            "resource_type",
            sa.Enum("FOOD", "MEDICAL", name="resource_type"),
            nullable=False,
        ),
        sa.Column("predicted_date", sa.Date(), nullable=False),
        sa.Column("expected_quantity_min", sa.Numeric(10, 2), nullable=False),
        sa.Column("expected_quantity_max", sa.Numeric(10, 2), nullable=False),
        sa.Column("expected_time_window", sa.String(100), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("recommended_preparation", sa.Text(), nullable=True),
        sa.Column("is_simulated", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("based_on_data", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_predictions_provider_id", "predictions", ["provider_id"])
    op.create_index("ix_predictions_predicted_date", "predictions", ["predicted_date"])


def downgrade() -> None:
    # Reverse dependency order.
    op.drop_table("predictions")
    op.drop_table("notifications")
    op.drop_table("operation_events")
    op.drop_table("allocations")
    op.drop_table("rescue_operations")
    op.drop_table("matches")
    op.drop_table("rescue_requests")
    op.drop_table("rescue_hubs")
    op.drop_table("rescue_partners")
    op.drop_table("recipients")
    op.drop_table("resources")
    op.drop_table("users")

    # Drop enum types explicitly (op.drop_table does not drop the Postgres
    # ENUM types it used, since other tables/columns could still reference
    # them).
    bind = op.get_bind()
    for enum_name in (
        "user_role",
        "resource_type",
        "resource_status",
        "urgency_level",
        "recipient_type",
        "partner_type",
        "rescue_request_status",
        "match_candidate_type",
        "match_status",
        "allocation_status",
        "operation_status",
        "operation_event_type",
        "notification_type",
    ):
        sa.Enum(name=enum_name).drop(bind, checkfirst=True)

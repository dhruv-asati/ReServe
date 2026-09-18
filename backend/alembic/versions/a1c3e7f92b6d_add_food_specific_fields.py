"""add food-specific fields to resources

Revision ID: a1c3e7f92b6d
Revises: 78f2894b0475
Create Date: 2026-09-18 00:00:00.000000

Adds six columns to `resources`, all nullable so this is a safe additive
change for existing rows:

- `food_category` (new `food_category` enum) — food subtype, distinct
  from the existing free-text `category` column.
- `is_vegetarian` (Boolean)
- `preparation_time` (DateTime(timezone=True)) — when the food was
  prepared/cooked.
- `allergen_info` (JSON) — list of allergen tags, e.g. ["MILK", "SOY"].
- `storage_requirements` (new `storage_requirement` enum)
- `packaging_info` (String(500))

All six are meaningful only for FOOD resources; the schema/service layer
(not the database) rejects them being set on MEDICAL resources, so no
CHECK constraint is added here.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "a1c3e7f92b6d"
down_revision: Union[str, None] = "78f2894b0475"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

food_category_enum = postgresql.ENUM(
    "COOKED_MEALS",
    "RAW_PRODUCE",
    "BAKERY",
    "DAIRY",
    "GRAINS_CEREALS",
    "PACKAGED_SNACKS",
    "BEVERAGES",
    "FROZEN_FOOD",
    "CANNED_GOODS",
    "OTHER",
    name="food_category",
)

storage_requirement_enum = postgresql.ENUM(
    "REFRIGERATED",
    "FROZEN",
    "ROOM_TEMPERATURE",
    "DRY_STORAGE",
    name="storage_requirement",
)


def upgrade() -> None:
    bind = op.get_bind()
    # Postgres ENUM types must exist before a column can reference them;
    # checkfirst=True keeps this migration idempotent/re-runnable.
    food_category_enum.create(bind, checkfirst=True)
    storage_requirement_enum.create(bind, checkfirst=True)

    op.add_column(
        "resources",
        sa.Column("food_category", food_category_enum, nullable=True),
    )
    op.add_column("resources", sa.Column("is_vegetarian", sa.Boolean(), nullable=True))
    op.add_column(
        "resources", sa.Column("preparation_time", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column("resources", sa.Column("allergen_info", sa.JSON(), nullable=True))
    op.add_column(
        "resources",
        sa.Column("storage_requirements", storage_requirement_enum, nullable=True),
    )
    op.add_column("resources", sa.Column("packaging_info", sa.String(500), nullable=True))


def downgrade() -> None:
    op.drop_column("resources", "packaging_info")
    op.drop_column("resources", "storage_requirements")
    op.drop_column("resources", "allergen_info")
    op.drop_column("resources", "preparation_time")
    op.drop_column("resources", "is_vegetarian")
    op.drop_column("resources", "food_category")

    bind = op.get_bind()
    storage_requirement_enum.drop(bind, checkfirst=True)
    food_category_enum.drop(bind, checkfirst=True)

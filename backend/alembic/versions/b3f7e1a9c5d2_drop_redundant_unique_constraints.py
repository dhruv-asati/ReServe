"""drop redundant unique constraints already covered by unique indexes

Revision ID: b3f7e1a9c5d2
Revises: c2fc238650c6
Create Date: 2026-09-19 00:00:00.000000

`alembic check` flagged three unique constraints as "removed" relative to
the current models:

    recipients_user_id_key                    on recipients.user_id
    rescue_partners_user_id_key               on rescue_partners.user_id
    rescue_operations_rescue_request_id_key   on rescue_operations.rescue_request_id

This is NOT a sign the models lost `unique=True` -- they never did.
Recipient.user_id, RescuePartner.user_id, and
RescueOperation.rescue_request_id all still declare `unique=True,
index=True` together, matching the one-to-one relationships they're meant
to enforce (Recipient<->User, RescuePartner<->User,
RescueOperation<->RescueRequest -- see those models' docstrings and their
scalar `Optional[...]` relationships on both sides).

The `unique=True, index=True` combination is SQLAlchemy's documented
shorthand for "generate a single UNIQUE INDEX for this column" (Column
docs: "...if index is True as well, indicates that a unique index should
be created for this column" -- no separate UniqueConstraint is added in
that case). `users.email` uses this exact combination and was migrated
correctly back in 34a01cac6ded: that raw column has no `unique=True` of
its own, only the follow-up `op.create_index("ix_users_email", ...,
unique=True)` -- one DB object, matching the model, and `alembic check`
has never flagged it.

The three columns here were migrated inconsistently in 34a01cac6ded: the
raw `sa.Column(...)` calls were *also* given `unique=True` directly,
which Postgres turns into its own standalone UNIQUE CONSTRAINT
(auto-named `<table>_<column>_key`) as part of CREATE TABLE -- in
addition to the follow-up `op.create_index(..., unique=True)` used for
every other unique+indexed column in that migration. That left two
redundant objects enforcing the same uniqueness on the live database,
where the model (and everywhere else in this codebase) only asks for
one.

This migration removes only the three redundant constraint objects. It
does not touch `ix_recipients_user_id`, `ix_rescue_partners_user_id`, or
`ix_rescue_operations_rescue_request_id` -- the unique indexes created
alongside them in 34a01cac6ded -- so the underlying one-to-one
relationships stay fully enforced at the database level throughout, with
no gap.
"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b3f7e1a9c5d2"
down_revision: Union[str, None] = "c2fc238650c6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# (constraint name, table, columns) -- each is a duplicate of an existing
# unique index of the same shape (ix_recipients_user_id,
# ix_rescue_partners_user_id, ix_rescue_operations_rescue_request_id
# respectively), which is left untouched by this migration.
_REDUNDANT_UNIQUE_CONSTRAINTS = [
    ("recipients_user_id_key", "recipients", ["user_id"]),
    ("rescue_partners_user_id_key", "rescue_partners", ["user_id"]),
    ("rescue_operations_rescue_request_id_key", "rescue_operations", ["rescue_request_id"]),
]


def upgrade() -> None:
    for name, table, _columns in _REDUNDANT_UNIQUE_CONSTRAINTS:
        op.drop_constraint(name, table, type_="unique")


def downgrade() -> None:
    for name, table, columns in _REDUNDANT_UNIQUE_CONSTRAINTS:
        op.create_unique_constraint(name, table, columns)

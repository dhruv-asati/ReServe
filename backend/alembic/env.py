"""
Alembic environment script.

Wired to pull the database URL from app.core.config.Settings (so it always
matches .env / DATABASE_URL) and to autogenerate migrations against
app.db.database.Base.metadata.

The database URL is deliberately kept OUT of alembic.ini / Config's
set_main_option(): Python's configparser treats "%" as the start of
interpolation syntax (like "%(name)s"), and a URL-encoded password
(e.g. containing "%40" for "@") will crash with
"invalid interpolation syntax" if passed through it. Instead, the URL is
built once here and handed directly to context.configure()/create_engine(),
bypassing configparser entirely.
"""

from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine, pool

from app.db.database import Base, _build_database_url

# Importing app.models registers every ORM model on Base.metadata so
# autogenerate can see the full schema.
import app.models  # noqa: F401

# Alembic Config object, provides access to values in alembic.ini
config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

# Built once, used directly below — never passed through
# config.set_main_option()/config.get_section(), which would run it
# through configparser's %-interpolation.
DATABASE_URL = _build_database_url()


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (generates SQL without a live DB connection)."""
    context.configure(
        url=DATABASE_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode (connects directly to the database)."""
    connectable = create_engine(DATABASE_URL, poolclass=pool.NullPool)

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

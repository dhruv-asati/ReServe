"""
SQLAlchemy database setup: engine, session factory, and declarative base.

This module intentionally does NOT create any tables or define any models —
that's for the "Database models" stage. It only wires up the connection.
"""

import logging
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()


def _build_database_url() -> str:
    """
    Returns DATABASE_URL as-is, except for one convenience: if it points at
    a Supabase host and doesn't already specify `sslmode`, `sslmode=require`
    is added automatically. Supabase's Postgres requires SSL, and forgetting
    this is a common source of confusing connection errors.
    """
    url = settings.DATABASE_URL
    parsed = urlparse(url)

    if "supabase.co" in (parsed.hostname or ""):
        query = dict(parse_qsl(parsed.query))
        if "sslmode" not in query:
            query["sslmode"] = "require"
            parsed = parsed._replace(query=urlencode(query))
            url = urlunparse(parsed)

    return url


# pool_pre_ping=True checks connections are alive before handing them out,
# which avoids "server closed the connection unexpectedly" errors after
# idle periods — cheap insurance for a Postgres-backed API, and especially
# useful with Supabase's pooled connection (which recycles idle connections
# more aggressively than a locally-run Postgres would).
engine = create_engine(
    _build_database_url(),
    pool_pre_ping=True,
    echo=False,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """Base class that all ORM models will inherit from (added in a later stage)."""

    pass


def get_db():
    """
    FastAPI dependency that yields a database session and guarantees it is
    closed afterwards, even if the request raises.

    Usage in a route:
        @router.get("/things")
        def list_things(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def check_database_connection() -> bool:
    """
    Attempt a lightweight connection check against the configured database.

    Returns True if the connection succeeds, False otherwise. Used by the
    health endpoint to report DB status without ever raising to the caller.
    """
    try:
        with engine.connect() as connection:
            connection.exec_driver_sql("SELECT 1")
        return True
    except Exception as exc:  # noqa: BLE001 - we deliberately want to catch anything here
        logger.warning("Database connectivity check failed: %s", exc)
        return False

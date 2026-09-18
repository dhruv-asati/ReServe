"""
Verifies that every expected ReServe table exists in the configured
database. Run this after `alembic upgrade head`.

Usage (from the project root, i.e. the folder containing requirements.txt):
    python3 scripts/verify_tables.py
"""

import sys
from pathlib import Path

# Running this file directly (`python3 scripts/verify_tables.py`) only puts
# scripts/ on sys.path, not the project root — so `import app` fails no
# matter what directory you launched it from. Add the project root
# (this file's parent's parent) explicitly so the import always works.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import inspect

from app.db.database import engine

EXPECTED_TABLES = {
    "users",
    "resources",
    "recipients",
    "rescue_partners",
    "rescue_hubs",
    "rescue_requests",
    "matches",
    "allocations",
    "rescue_operations",
    "operation_events",
    "notifications",
    "predictions",
}


def main() -> int:
    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())

    missing = EXPECTED_TABLES - existing_tables
    extra = existing_tables - EXPECTED_TABLES - {"alembic_version"}

    print(f"Found {len(existing_tables)} table(s) in the database.\n")

    for table in sorted(EXPECTED_TABLES):
        status = "OK" if table in existing_tables else "MISSING"
        print(f"  [{status:^7}] {table}")

    if missing:
        print(f"\nMissing tables: {sorted(missing)}")
    if extra:
        print(f"\nUnexpected extra tables (not necessarily a problem): {sorted(extra)}")

    if not missing:
        print("\nAll expected ReServe tables are present.")
        return 0
    else:
        print("\nSome tables are missing — did you run `alembic upgrade head`?")
        return 1


if __name__ == "__main__":
    sys.exit(main())

"""
Shows (and optionally clears) what's in the database, using the same
DATABASE_URL as the backend — no Supabase SQL editor needed.

Run from the backend folder (the one containing requirements.txt), with the
venv active:

    python scripts/clear_data.py             # dry run: just print row counts
    python scripts/clear_data.py --demo      # delete only the seeded [DEMO] data
    python scripts/clear_data.py --all       # delete ALL activity (resources, requests,
                                             # matches, allocations, operations,
                                             # notifications) but keep every user,
                                             # recipient, partner and hub account

Deleting is irreversible, so --demo / --all ask you to type "yes" first
(pass --yes to skip the prompt).
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from sqlalchemy import text  # noqa: E402

from app.db.database import SessionLocal  # noqa: E402
from seed_demo_data import DEMO_EMAIL_DOMAIN, DEMO_TAG, wipe_demo_data  # noqa: E402

COUNTS = [
    ("users (all)", "select count(*) from users"),
    ("users (demo)", f"select count(*) from users where email like '%@{DEMO_EMAIL_DOMAIN}'"),
    ("rescue hubs (demo)", f"select count(*) from rescue_hubs where name like '{DEMO_TAG}%'"),
    ("resources", "select count(*) from resources"),
    ("rescue requests", "select count(*) from rescue_requests"),
    ("allocations", "select count(*) from allocations"),
    ("operations", "select count(*) from rescue_operations"),
    ("notifications", "select count(*) from notifications"),
]

# Everything that represents activity rather than accounts. CASCADE also
# clears tables that reference these (e.g. operation_events).
ACTIVITY_TABLES = (
    "notifications, rescue_operations, allocations, matches, rescue_requests, "
    "resource_request_status_history, resource_requests, resources"
)


def print_counts(db, title):
    print(f"\n{title}")
    for label, sql in COUNTS:
        print(f"  {label:<20} {db.execute(text(sql)).scalar()}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--demo", action="store_true", help="delete only the seeded [DEMO] data")
    mode.add_argument("--all", action="store_true", help="delete all activity, keep accounts")
    parser.add_argument("--yes", action="store_true", help="skip the confirmation prompt")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        print_counts(db, "Current database contents:")

        if not (args.demo or args.all):
            print("\nDry run only. Re-run with --demo or --all to delete.")
            return 0

        what = "the seeded [DEMO] data" if args.demo else "ALL resources, requests, matches, allocations, operations and notifications"
        if not args.yes and input(f"\nThis will permanently delete {what}. Type 'yes' to continue: ").strip() != "yes":
            print("Cancelled; nothing was deleted.")
            return 1

        if args.demo:
            wipe_demo_data(db)
        else:
            db.execute(text(f"TRUNCATE TABLE {ACTIVITY_TABLES} RESTART IDENTITY CASCADE"))
            db.commit()

        print_counts(db, "After clearing:")
        return 0
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())

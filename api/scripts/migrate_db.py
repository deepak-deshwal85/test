#!/usr/bin/env python3
"""Apply incremental SQL migrations to an existing RelayDesk database.

Usage:
  cd api
  uv run python scripts/migrate_db.py

  # All migrations in scripts/db/migrate_*.sql (sorted by name):
  uv run python scripts/migrate_db.py --all

  # Through RDS tunnel (repo root):
  $env:RDS_DB_PASSWORD = "your-password"
  python infra/scripts/migrate_database.py --use-tunnel
"""
from __future__ import annotations

import argparse
import asyncio
import sys

import asyncpg

from db_runner import (
    DB_DIR,
    load_env,
    resolve_database_url,
    run_sql_file,
    to_asyncpg_dsn,
)

DEFAULT_MIGRATION = "migrate_consumer_campaign.sql"


async def _run(*, database_url: str, migration_files: list[str]) -> None:
    dsn = to_asyncpg_dsn(database_url)
    connection = await asyncpg.connect(dsn)
    try:
        for name in migration_files:
            path = DB_DIR / name
            if not path.is_file():
                raise FileNotFoundError(f"Migration not found: {path}")
            count = await run_sql_file(connection, path)
            print(f"Applied {name} ({count} statements)")
    finally:
        await connection.close()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Apply SQL migrations to RelayDesk PostgreSQL."
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Run every scripts/db/migrate_*.sql file in sorted order.",
    )
    parser.add_argument(
        "--file",
        default=DEFAULT_MIGRATION,
        help=f"Migration file under scripts/db/ (default: {DEFAULT_MIGRATION}).",
    )
    args = parser.parse_args()

    if args.all:
        migration_files = sorted(p.name for p in DB_DIR.glob("migrate_*.sql"))
        if not migration_files:
            print("No migrate_*.sql files found.", file=sys.stderr)
            return 1
    else:
        migration_files = [args.file]

    load_env()
    try:
        database_url = resolve_database_url()
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    try:
        asyncio.run(_run(database_url=database_url, migration_files=migration_files))
    except Exception as exc:
        print(f"Migration failed: {exc}", file=sys.stderr)
        return 1

    print("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Drop all tables, recreate schema, and load Deepak bootstrap seed data.

Destructive — deletes every row in all RelayDesk tables, then inserts:
  - clients: deepakdeshwal85@gmail.com, deepakdeshwal85@yahoo.com
  - shared business phone: 911171366880
  - voice agent configs with Cal.com settings for both clients
  - dummy consumers, call jobs, and call summaries

Usage:
  cd api
  uv run python scripts/bootstrap_db.py --yes

  # Through RDS tunnel (repo root, tunnel must be running):
  $env:RDS_DB_PASSWORD = "your-password"
  python infra/scripts/bootstrap_database.py --use-tunnel --yes
"""
from __future__ import annotations

import argparse
import asyncio
import sys

import asyncpg
from db_runner import (
    DB_DIR,
    apply_schema,
    drop_schema,
    load_env,
    resolve_database_url,
    run_sql_file,
    to_asyncpg_dsn,
)

SEED_FILE = "seed_deepak.sql"


async def _run(*, database_url: str) -> None:
    dsn = to_asyncpg_dsn(database_url)
    connection = await asyncpg.connect(dsn)
    try:
        await drop_schema(connection)
        await apply_schema(connection)
        seed_path = DB_DIR / SEED_FILE
        count = await run_sql_file(connection, seed_path)
        print(f"Applied seed data ({count} statements) from {seed_path.name}")
    finally:
        await connection.close()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Drop, recreate, and seed RelayDesk PostgreSQL for Deepak dev data."
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Required confirmation — this deletes all application data.",
    )
    args = parser.parse_args()

    if not args.yes:
        print(
            "Refusing to run without --yes. This drops all tables and reloads seed data.",
            file=sys.stderr,
        )
        return 1

    load_env()
    try:
        database_url = resolve_database_url()
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    print("WARNING: Dropping all RelayDesk tables, recreating schema, loading Deepak seed.")
    try:
        asyncio.run(_run(database_url=database_url))
    except Exception as exc:
        print(f"Bootstrap failed: {exc}", file=sys.stderr)
        return 1

    print("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

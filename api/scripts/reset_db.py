#!/usr/bin/env python3
"""Drop all RelayDesk tables and recreate schema (+ optional seed data).

Destructive — deletes every row in clients, customers, and call_jobs.

Usage:
  cd api
  uv run python scripts/reset_db.py --yes
  uv run python scripts/reset_db.py --yes --schema-only

  # Through SSM tunnel (from repo root):
  $env:RDS_DB_PASSWORD = "your-password"
  python infra/scripts/reset_database.py --use-tunnel --yes
"""
from __future__ import annotations

import argparse
import asyncio
import sys

import asyncpg
from db_runner import (
    apply_schema,
    apply_seed,
    drop_schema,
    load_env,
    resolve_database_url,
    to_asyncpg_dsn,
)


async def _run(*, database_url: str, schema: bool, seed: bool) -> None:
    dsn = to_asyncpg_dsn(database_url)
    connection = await asyncpg.connect(dsn)
    try:
        await drop_schema(connection)
        if schema:
            await apply_schema(connection)
        if seed:
            await apply_seed(connection)
    finally:
        await connection.close()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Drop and recreate RelayDesk PostgreSQL tables."
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Required confirmation — this deletes all application data.",
    )
    parser.add_argument(
        "--schema-only",
        action="store_true",
        help="Recreate empty tables only (no dummy seed rows).",
    )
    args = parser.parse_args()

    if not args.yes:
        print(
            "Refusing to run without --yes. This drops clients, customers, and call_jobs.",
            file=sys.stderr,
        )
        return 1

    run_schema = True
    run_seed = not args.schema_only

    load_env()
    try:
        database_url = resolve_database_url()
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    print("WARNING: Dropping all RelayDesk tables and recreating schema.")
    try:
        asyncio.run(
            _run(
                database_url=database_url,
                schema=run_schema,
                seed=run_seed,
            )
        )
    except Exception as exc:
        print(f"Database reset failed: {exc}", file=sys.stderr)
        return 1

    print("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

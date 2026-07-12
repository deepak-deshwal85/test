#!/usr/bin/env python3
"""Apply a single SQL migration file to the configured DATABASE_URL."""
from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

SCRIPT_PATH = Path(__file__).resolve()
SCRIPTS_DIR = SCRIPT_PATH.parent
REPO_ROOT = SCRIPTS_DIR.parents[1]
API_DIR = REPO_ROOT / "api"


async def _run(migration_path: Path) -> None:
    import asyncpg

    sys.path.insert(0, str(SCRIPTS_DIR))
    from db_runner import load_env, resolve_database_url, run_sql_file, to_asyncpg_dsn

    load_env()
    database_url = resolve_database_url()
    connection = await asyncpg.connect(to_asyncpg_dsn(database_url))
    try:
        count = await run_sql_file(connection, migration_path)
        print(f"Applied migration ({count} statements) from {migration_path.name}")
    finally:
        await connection.close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Apply one SQL migration file.")
    parser.add_argument(
        "migration",
        nargs="?",
        default="migrate_add_voice_agent_schedules.sql",
        help="SQL file name under infra/scripts/db/ (default: migrate_add_voice_agent_schedules.sql)",
    )
    args = parser.parse_args(argv)

    migration_path = SCRIPTS_DIR / "db" / args.migration
    if not migration_path.is_file():
        print(f"Migration file not found: {migration_path}", file=sys.stderr)
        return 1

    try:
        asyncio.run(_run(migration_path))
    except Exception as exc:
        print(f"Migration failed: {exc}", file=sys.stderr)
        return 1

    print("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

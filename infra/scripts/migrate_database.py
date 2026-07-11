#!/usr/bin/env python3
"""Run api/scripts/migrate_db.py against RDS (via tunnel or DATABASE_URL).

Examples:
  $env:RDS_DB_PASSWORD = "your-password"
  python infra/scripts/migrate_database.py --use-tunnel

  python infra/scripts/migrate_database.py --use-tunnel --all
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path
from urllib.parse import quote_plus

REPO_ROOT = Path(__file__).resolve().parents[2]
API_DIR = REPO_ROOT / "api"
MIGRATE_SCRIPT = API_DIR / "scripts" / "migrate_db.py"
TUNNEL_HOST = "127.0.0.1"
TUNNEL_PORT = 15432


def build_tunnel_database_url(*, password: str, username: str, db_name: str) -> str:
    encoded = quote_plus(password)
    return (
        f"postgresql+asyncpg://{username}:{encoded}"
        f"@{TUNNEL_HOST}:{TUNNEL_PORT}/{db_name}"
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Apply RelayDesk PostgreSQL migrations."
    )
    parser.add_argument(
        "--database-url",
        default=os.getenv("DATABASE_URL", "").strip(),
    )
    parser.add_argument("--use-tunnel", action="store_true")
    parser.add_argument(
        "--username",
        default=os.getenv("RDS_MASTER_USERNAME", "relaydesk_admin"),
    )
    parser.add_argument(
        "--db-name",
        default=os.getenv("RDS_DATABASE_NAME", "relaydesk"),
    )
    parser.add_argument(
        "--password",
        default=os.getenv("RDS_DB_PASSWORD", "").strip(),
    )
    parser.add_argument("--all", action="store_true")
    parser.add_argument(
        "--file",
        default="migrate_customer_campaign.sql",
        help="Migration file under api/scripts/db/.",
    )
    args = parser.parse_args()

    database_url = args.database_url
    if args.use_tunnel:
        if not args.password:
            print(
                "Set RDS_DB_PASSWORD or pass --password when using --use-tunnel.",
                file=sys.stderr,
            )
            return 1
        database_url = build_tunnel_database_url(
            password=args.password,
            username=args.username,
            db_name=args.db_name,
        )

    if not database_url:
        print("Provide --database-url, set DATABASE_URL, or use --use-tunnel.", file=sys.stderr)
        return 1

    cmd = ["uv", "run", "python", str(MIGRATE_SCRIPT)]
    if args.all:
        cmd.append("--all")
    else:
        cmd.extend(["--file", args.file])

    env = os.environ.copy()
    env["DATABASE_URL"] = database_url
    return subprocess.run(cmd, cwd=str(API_DIR), env=env).returncode


if __name__ == "__main__":
    raise SystemExit(main())

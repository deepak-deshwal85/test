#!/usr/bin/env python3
"""Drop and recreate RelayDesk PostgreSQL tables (via api/scripts/reset_db.py).

Examples:
  $env:RDS_DB_PASSWORD = "your-password"
  python infra/scripts/reset_database.py --use-tunnel --yes

  python infra/scripts/reset_database.py --database-url "postgresql+asyncpg://..." --yes
  python infra/scripts/reset_database.py --use-tunnel --yes --schema-only
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
RESET_SCRIPT = API_DIR / "scripts" / "reset_db.py"
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
        description="Drop and recreate RelayDesk PostgreSQL schema and seed data."
    )
    parser.add_argument(
        "--database-url",
        default=os.getenv("DATABASE_URL", "").strip(),
        help="PostgreSQL URL (or set DATABASE_URL).",
    )
    parser.add_argument(
        "--use-tunnel",
        action="store_true",
        help=f"Build URL for localhost:{TUNNEL_PORT} SSM tunnel.",
    )
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
        help="RDS password (or set RDS_DB_PASSWORD).",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Required — confirms destructive drop of all application tables.",
    )
    parser.add_argument("--schema-only", action="store_true")
    args = parser.parse_args()

    if not args.yes:
        print("Pass --yes to confirm drop and recreate.", file=sys.stderr)
        return 1

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

    cmd = ["uv", "run", "python", str(RESET_SCRIPT), "--yes"]
    if args.schema_only:
        cmd.append("--schema-only")

    env = os.environ.copy()
    env["DATABASE_URL"] = database_url
    result = subprocess.run(cmd, cwd=str(API_DIR), env=env)
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())

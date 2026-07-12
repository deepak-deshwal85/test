#!/usr/bin/env python3
"""Store a client's business phone number in PostgreSQL.

Used by infra/scripts/approve_cognito_user.py (via `uv run` from api/).

Usage:
  cd api
  uv run python ../infra/scripts/set_client_business_phone.py \\
    --email client@example.com \\
    --business-phone +911171366880
"""
from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_API_SRC = _REPO_ROOT / "api" / "src"
if str(_API_SRC) not in sys.path:
    sys.path.insert(0, str(_API_SRC))

from app.core.config import Settings
from app.db.postgres.client_repository import ClientRepository
from app.db.postgres.session import dispose_engine, get_session_factory, init_engine


async def _run(*, email: str, business_phone: str, database_url: str) -> None:
    settings = Settings(database_url=database_url)
    init_engine(settings)
    session_factory = get_session_factory()
    try:
        async with session_factory() as session:
            repository = ClientRepository(session)
            client = await repository.set_business_phone(
                client_email_id=email,
                client_business_phone_number=business_phone,
            )
            print(
                f"Stored business phone {client.client_business_phone_number!r} "
                f"for client {client.client_email_id!r}"
            )
    finally:
        await dispose_engine()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Set client_business_phone_number for a client email."
    )
    parser.add_argument("--email", required=True)
    parser.add_argument("--business-phone", required=True)
    args = parser.parse_args()

    import os

    database_url = os.getenv("DATABASE_URL", "").strip()
    if not database_url:
        print(
            "DATABASE_URL is required. Set it in the environment.",
            file=sys.stderr,
        )
        return 1

    email = args.email.strip().lower()
    business_phone = args.business_phone.strip()
    if not email or "@" not in email:
        print("invalid --email", file=sys.stderr)
        return 1
    if not business_phone:
        print("invalid --business-phone", file=sys.stderr)
        return 1

    try:
        asyncio.run(
            _run(
                email=email,
                business_phone=business_phone,
                database_url=database_url,
            )
        )
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

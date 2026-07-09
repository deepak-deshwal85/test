#!/usr/bin/env python3
"""Add guest-clients to Cognito users who have no RelayDesk role yet.

Use once after deploying the post-confirmation Lambda, for users who signed up
before automatic guest assignment existed.

Usage:
  python infra/scripts/backfill_guest_clients.py --dry-run
  python infra/scripts/backfill_guest_clients.py --profile relaydesk-admin --region ap-south-1
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

RELAYDESK_ROLE_GROUPS = (
    "guest-clients",
    "approved-clients",
    "relaydesk-admins",
)
DEFAULT_GUEST_GROUP = "guest-clients"


def aws_cmd(profile: str | None, region: str, *args: str) -> list[str]:
    cmd = ["aws", *args, "--region", region, "--output", "json"]
    if profile:
        cmd.extend(["--profile", profile])
    return cmd


def run_json(cmd: list[str]) -> dict:
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return json.loads(result.stdout or "{}")


def terraform_output(terraform_dir: Path, name: str) -> str | None:
    result = subprocess.run(
        ["terraform", "output", "-raw", name],
        cwd=str(terraform_dir),
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return None
    value = result.stdout.strip()
    return value or None


def list_users(profile: str | None, region: str, user_pool_id: str) -> list[dict]:
    users: list[dict] = []
    token: str | None = None
    while True:
        cmd = aws_cmd(
            profile,
            region,
            "cognito-idp",
            "list-users",
            "--user-pool-id",
            user_pool_id,
            "--limit",
            "60",
        )
        if token:
            cmd.extend(["--pagination-token", token])
        payload = run_json(cmd)
        users.extend(payload.get("Users") or [])
        token = payload.get("PaginationToken")
        if not token:
            break
    return users


def user_groups(profile: str | None, region: str, user_pool_id: str, username: str) -> set[str]:
    payload = run_json(
        aws_cmd(
            profile,
            region,
            "cognito-idp",
            "admin-list-groups-for-user",
            "--user-pool-id",
            user_pool_id,
            "--username",
            username,
        )
    )
    return {group["GroupName"] for group in payload.get("Groups") or []}


def add_to_guest(
    profile: str | None,
    region: str,
    user_pool_id: str,
    username: str,
    *,
    guest_group: str,
    dry_run: bool,
) -> None:
    if dry_run:
        print(f"[dry-run] would add {username!r} to {guest_group!r}")
        return
    subprocess.run(
        aws_cmd(
            profile,
            region,
            "cognito-idp",
            "admin-add-user-to-group",
            "--user-pool-id",
            user_pool_id,
            "--username",
            username,
            "--group-name",
            guest_group,
        ),
        check=True,
    )
    print(f"added {username!r} to {guest_group!r}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Backfill guest-clients for users without a RelayDesk role."
    )
    parser.add_argument("--region", default="ap-south-1")
    parser.add_argument("--profile", default=os.getenv("AWS_PROFILE"))
    parser.add_argument(
        "--user-pool-id",
        help="Cognito user pool ID (default: terraform output cognito_user_pool_id)",
    )
    parser.add_argument("--group", default=DEFAULT_GUEST_GROUP)
    parser.add_argument(
        "--terraform-dir",
        default="infra/terraform",
        help="Terraform directory for default pool ID lookup",
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    user_pool_id = args.user_pool_id or terraform_output(
        Path(args.terraform_dir).resolve(), "cognito_user_pool_id"
    )
    if not user_pool_id:
        print("Could not resolve user pool ID.", file=sys.stderr)
        return 1

    updated = 0
    skipped = 0
    for user in list_users(args.profile, args.region, user_pool_id):
        username = user.get("Username")
        if not username:
            continue
        groups = user_groups(args.profile, args.region, user_pool_id, str(username))
        if groups.intersection(RELAYDESK_ROLE_GROUPS):
            skipped += 1
            continue
        add_to_guest(
            args.profile,
            args.region,
            user_pool_id,
            str(username),
            guest_group=args.group,
            dry_run=args.dry_run,
        )
        updated += 1

    print(f"done: added={updated} skipped={skipped}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except subprocess.CalledProcessError as exc:
        print(f"aws command failed: {exc.stderr or exc}", file=sys.stderr)
        raise SystemExit(exc.returncode) from exc

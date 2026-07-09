#!/usr/bin/env python3
"""Assign a RelayDesk Cognito role group to a user by email.

Users must have signed in at least once (native or Google SSO) so Cognito has
created their user record. The script removes the user from other RelayDesk
role groups before adding the requested one.

When approving to approved-clients or relaydesk-admins, --business-phone is
required and stored on the client's profile in PostgreSQL.

Roles:
  guest-clients      — default for new SSO sign-ups (view-only; no Cognito group required)
  approved-clients   — upload/delete knowledge-base documents
  relaydesk-admins   — full console and API access

Usage:
  python infra/scripts/approve_cognito_user.py --email you@example.com --role relaydesk-admins --business-phone +911171366880
  python infra/scripts/approve_cognito_user.py --email you@example.com --role approved-clients --business-phone +911171366880
  python infra/scripts/approve_cognito_user.py --email you@example.com --role guest-clients
  python infra/scripts/approve_cognito_user.py --email you@example.com --revoke
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

ROLES_REQUIRING_BUSINESS_PHONE = frozenset({"approved-clients", "relaydesk-admins"})


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


def find_username_by_email(
    *,
    profile: str | None,
    region: str,
    user_pool_id: str,
    email: str,
) -> str:
    payload = run_json(
        aws_cmd(
            profile,
            region,
            "cognito-idp",
            "list-users",
            "--user-pool-id",
            user_pool_id,
            "--filter",
            f'email = "{email}"',
        )
    )
    users = payload.get("Users") or []
    if not users:
        raise RuntimeError(
            f"No Cognito user found for email {email!r}. "
            "Ask them to sign in once via SSO, then retry."
        )
    if len(users) > 1:
        usernames = [user.get("Username", "") for user in users]
        raise RuntimeError(
            f"Multiple Cognito users match email {email!r}: {usernames}"
        )
    username = users[0].get("Username")
    if not username:
        raise RuntimeError(f"Cognito user for {email!r} has no Username")
    return str(username)


def remove_from_role_groups(
    *,
    profile: str | None,
    region: str,
    user_pool_id: str,
    username: str,
    dry_run: bool,
) -> None:
    for group_name in RELAYDESK_ROLE_GROUPS:
        if dry_run:
            print(f"[dry-run] would remove {username!r} from {group_name!r}")
            continue
        subprocess.run(
            aws_cmd(
                profile,
                region,
                "cognito-idp",
                "admin-remove-user-from-group",
                "--user-pool-id",
                user_pool_id,
                "--username",
                username,
                "--group-name",
                group_name,
            ),
            check=False,
        )


def set_group_membership(
    *,
    profile: str | None,
    region: str,
    user_pool_id: str,
    username: str,
    group_name: str,
    revoke: bool,
    dry_run: bool,
) -> None:
    if revoke:
        if dry_run:
            print(
                f"[dry-run] would revoke all RelayDesk roles for {username!r} "
                f"(pool {user_pool_id})"
            )
            return
        remove_from_role_groups(
            profile=profile,
            region=region,
            user_pool_id=user_pool_id,
            username=username,
            dry_run=False,
        )
        print(f"Revoked RelayDesk roles for {username!r}")
        return

    if dry_run:
        print(
            f"[dry-run] would assign {username!r} to {group_name!r} "
            f"(pool {user_pool_id})"
        )
        return

    remove_from_role_groups(
        profile=profile,
        region=region,
        user_pool_id=user_pool_id,
        username=username,
        dry_run=False,
    )
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
            group_name,
        ),
        check=True,
    )
    print(f"Assigned {username!r} to group {group_name!r}")


def upsert_client_business_phone(*, email: str, business_phone: str) -> None:
    database_url = os.getenv("DATABASE_URL", "").strip()
    if not database_url:
        raise RuntimeError(
            "DATABASE_URL is required to store the client business phone number. "
            "Set it in the environment or use infra/scripts/set_database_url_from_rds.py."
        )

    repo_root = Path(__file__).resolve().parents[2]
    api_dir = repo_root / "api"
    helper = api_dir / "scripts" / "set_client_business_phone.py"
    if not helper.is_file():
        raise RuntimeError(f"Missing helper script: {helper}")

    env = os.environ.copy()
    env["DATABASE_URL"] = database_url
    result = subprocess.run(
        [
            "uv",
            "run",
            "python",
            str(helper),
            "--email",
            email,
            "--business-phone",
            business_phone,
        ],
        cwd=str(api_dir),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.stdout.strip():
        print(result.stdout.strip())
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "unknown error").strip()
        raise RuntimeError(f"Failed to store business phone in database:\n{detail}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Assign or revoke a RelayDesk Cognito role for a user by email."
    )
    parser.add_argument("--email", required=True, help="User email in Cognito")
    parser.add_argument(
        "--role",
        choices=RELAYDESK_ROLE_GROUPS,
        default="relaydesk-admins",
        help="RelayDesk role group to assign (default: relaydesk-admins)",
    )
    parser.add_argument(
        "--business-phone",
        help="Client business phone number (required for approved-clients and relaydesk-admins)",
    )
    parser.add_argument("--region", default="ap-south-1")
    parser.add_argument(
        "--profile",
        default=os.getenv("AWS_PROFILE"),
        help="AWS CLI profile (or set AWS_PROFILE).",
    )
    parser.add_argument(
        "--user-pool-id",
        help="Cognito user pool ID (default: terraform output cognito_user_pool_id)",
    )
    parser.add_argument(
        "--terraform-dir",
        default="infra/terraform",
        help="Path to Terraform directory for default pool ID lookup",
    )
    parser.add_argument(
        "--revoke",
        action="store_true",
        help="Remove the user from all RelayDesk role groups",
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    email = args.email.strip().lower()
    if not email or "@" not in email:
        print("invalid --email", file=sys.stderr)
        return 1

    if not args.revoke and args.role in ROLES_REQUIRING_BUSINESS_PHONE:
        business_phone = (args.business_phone or "").strip()
        if not business_phone:
            print(
                "--business-phone is required when assigning "
                f"{args.role!r}",
                file=sys.stderr,
            )
            return 1

    user_pool_id = args.user_pool_id
    if not user_pool_id:
        user_pool_id = terraform_output(Path(args.terraform_dir).resolve(), "cognito_user_pool_id")
    if not user_pool_id:
        print(
            "Could not resolve user pool ID. Pass --user-pool-id or run from a "
            "configured terraform directory.",
            file=sys.stderr,
        )
        return 1

    username = find_username_by_email(
        profile=args.profile,
        region=args.region,
        user_pool_id=user_pool_id,
        email=email,
    )
    set_group_membership(
        profile=args.profile,
        region=args.region,
        user_pool_id=user_pool_id,
        username=username,
        group_name=args.role,
        revoke=args.revoke,
        dry_run=args.dry_run,
    )
    if (
        not args.revoke
        and not args.dry_run
        and args.role in ROLES_REQUIRING_BUSINESS_PHONE
    ):
        upsert_client_business_phone(
            email=email,
            business_phone=args.business_phone.strip(),
        )
        print(f"Tell {email} to sign out and sign in again to refresh access.")
    elif not args.revoke and not args.dry_run:
        print(f"Tell {email} to sign out and sign in again to refresh access.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except subprocess.CalledProcessError as exc:
        print(f"aws command failed: {exc.stderr or exc}", file=sys.stderr)
        raise SystemExit(exc.returncode) from exc
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1) from exc

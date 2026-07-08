#!/usr/bin/env python3
"""Sync Cognito voice M2M client secret from Terraform state into SSM.

The voice-agent ECS task reads /relaydesk/prod/voice-agent/COGNITO_CLIENT_SECRET.
That parameter uses lifecycle ignore_changes in Terraform, so it can drift if the
Cognito app client was recreated or the placeholder value was never updated.
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path


def terraform_state_show(terraform_dir: Path, resource: str) -> str:
    result = subprocess.run(
        ["terraform", "state", "show", resource],
        cwd=str(terraform_dir),
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout


def parse_client_secret(state_text: str) -> str:
    match = re.search(r'^\s*client_secret\s*=\s*"(.*)"\s*$', state_text, re.MULTILINE)
    if not match:
        raise RuntimeError("Could not find client_secret in terraform state")
    secret = match.group(1)
    if not secret or secret == "CHANGEME":
        raise RuntimeError("client_secret in terraform state is empty or placeholder")
    return secret


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Sync Cognito voice M2M client secret from Terraform state to SSM."
    )
    parser.add_argument(
        "--terraform-dir",
        default="infra/terraform",
        help="Path to Terraform directory (default: infra/terraform)",
    )
    parser.add_argument("--region", default="ap-south-1")
    parser.add_argument(
        "--profile",
        default=os.getenv("AWS_PROFILE"),
        help="AWS CLI profile (or set AWS_PROFILE).",
    )
    parser.add_argument("--project", default="relaydesk")
    parser.add_argument("--environment", default="prod")
    parser.add_argument(
        "--resource",
        default="aws_cognito_user_pool_client.voice_m2m[0]",
        help="Terraform resource address for the voice M2M Cognito client.",
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    terraform_dir = Path(args.terraform_dir).resolve()
    state_text = terraform_state_show(terraform_dir, args.resource)
    client_secret = parse_client_secret(state_text)
    ssm_name = f"/{args.project}/{args.environment}/voice-agent/COGNITO_CLIENT_SECRET"

    if args.dry_run:
        print(f"[dry-run] would set {ssm_name} (secret length={len(client_secret)})")
        return 0

    cmd = [
        "aws",
        "ssm",
        "put-parameter",
        "--name",
        ssm_name,
        "--value",
        client_secret,
        "--type",
        "SecureString",
        "--overwrite",
        "--region",
        args.region,
    ]
    if args.profile:
        cmd.extend(["--profile", args.profile])

    subprocess.run(cmd, check=True)
    print(f"set {ssm_name}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except subprocess.CalledProcessError as exc:
        print(f"command failed: {exc}", file=sys.stderr)
        raise SystemExit(exc.returncode) from exc
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1) from exc

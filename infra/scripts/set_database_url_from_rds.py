#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from urllib.parse import quote_plus


def terraform_output(terraform_dir: Path) -> dict[str, object]:
    result = subprocess.run(
        ["terraform", "output", "-json"],
        cwd=str(terraform_dir),
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(result.stdout)


def get_output_value(outputs: dict[str, object], key: str) -> str:
    value_obj = outputs.get(key)
    if not isinstance(value_obj, dict):
        raise RuntimeError(f"Missing terraform output: {key}")
    value = value_obj.get("value")
    if not value:
        raise RuntimeError(f"Terraform output {key} is empty")
    if not isinstance(value, (str, int)):
        raise RuntimeError(f"Terraform output {key} has unsupported type")
    return str(value)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build DATABASE_URL from RDS terraform outputs and upload to SSM."
    )
    parser.add_argument(
        "--terraform-dir",
        default="infra/terraform",
        help="Path to Terraform directory (default: infra/terraform)",
    )
    parser.add_argument("--region", default="ap-south-1")
    parser.add_argument("--project", default="relaydesk")
    parser.add_argument("--environment", default="prod")
    parser.add_argument(
        "--password",
        default=os.getenv("RDS_DB_PASSWORD", ""),
        help="RDS master password (or set RDS_DB_PASSWORD env var).",
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if not args.password:
        print("Provide --password or set RDS_DB_PASSWORD.", file=sys.stderr)
        return 1

    terraform_dir = Path(args.terraform_dir).resolve()
    outputs = terraform_output(terraform_dir)
    endpoint = get_output_value(outputs, "rds_endpoint")
    db_name = get_output_value(outputs, "rds_database_name")
    username = get_output_value(outputs, "rds_master_username")
    port = get_output_value(outputs, "rds_port")

    encoded_password = quote_plus(args.password)
    database_url = (
        f"postgresql+asyncpg://{username}:{encoded_password}@{endpoint}:{port}/{db_name}"
    )
    ssm_name = f"/{args.project}/{args.environment}/api/DATABASE_URL"

    if args.dry_run:
        print(f"[dry-run] would set {ssm_name}")
        print(database_url)
        return 0

    subprocess.run(
        [
            "aws",
            "ssm",
            "put-parameter",
            "--name",
            ssm_name,
            "--value",
            database_url,
            "--type",
            "SecureString",
            "--overwrite",
            "--region",
            args.region,
        ],
        check=True,
    )
    print(f"set {ssm_name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

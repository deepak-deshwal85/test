#!/usr/bin/env python3
"""Upload RelayDesk ECS secrets to AWS SSM Parameter Store.

Reads infra/scripts/env.properties (KEY=VALUE) and optional api/.env + voice-agent/.env
fallbacks, then runs aws ssm put-parameter for each Terraform-managed secret.

Usage:
  python infra/scripts/sync_ssm_parameters.py --dry-run
  python infra/scripts/sync_ssm_parameters.py --region ap-south-1
  python infra/scripts/sync_ssm_parameters.py --from-local-env
  python infra/scripts/sync_ssm_parameters.py --write-env-properties
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = Path(__file__).resolve().parent
DEFAULT_PROPERTIES = SCRIPTS_DIR / "env.properties"

API_SECRET_KEYS = [
    "OPENAI_API_KEY",
    "DATABASE_URL",
    "QDRANT_API_KEY",
    "QDRANT_CLUSTER_ENDPOINT",
    "LIVEKIT_URL",
    "LIVEKIT_API_KEY",
    "LIVEKIT_API_SECRET",
    "LIVEKIT_SIP_OUTBOUND_TRUNK_ID",
]

VOICE_AGENT_SECRET_KEYS = [
    "LIVEKIT_URL",
    "LIVEKIT_API_KEY",
    "LIVEKIT_API_SECRET",
    "XAI_API_KEY",
    "DEEPGRAM_API_KEY",
    "CARTESIA_API_KEY",
    "CALCOM_API_KEY",
    "COGNITO_CLIENT_SECRET",
]

UI_SECRET_KEYS = [
    "AUTH_SECRET",
    "COGNITO_CLIENT_SECRET",
]


def parse_env_file(path: Path) -> dict[str, str]:
    if not path.is_file():
        return {}

    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.lower().startswith("export "):
            line = line[7:].strip()
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
            value = value[1:-1]
        if key:
            values[key] = value
    return values


def merge_sources(*sources: dict[str, str]) -> dict[str, str]:
    merged: dict[str, str] = {}
    for source in sources:
        merged.update(source)
    return merged


def ssm_name(prefix: str, key: str) -> str:
    return f"{prefix.rstrip('/')}/{key}"


def validate_database_url(value: str) -> None:
    parsed = urlparse(value)
    if parsed.scheme != "postgresql+asyncpg":
        raise ValueError(
            "DATABASE_URL must start with postgresql+asyncpg://"
        )
    if not parsed.hostname or not parsed.path or parsed.path == "/":
        raise ValueError("DATABASE_URL is missing host or database name.")


def put_parameter(
    *,
    name: str,
    value: str,
    region: str,
    profile: str | None,
    dry_run: bool,
) -> None:
    if dry_run:
        print(f"[dry-run] would set {name}")
        return

    cmd = [
        "aws",
        "ssm",
        "put-parameter",
        "--name",
        name,
        "--value",
        value,
        "--type",
        "SecureString",
        "--overwrite",
        "--region",
        region,
    ]
    if profile:
        cmd.extend(["--profile", profile])

    subprocess.run(cmd, check=True)
    print(f"set {name}")


def write_env_properties(path: Path, values: dict[str, str]) -> None:
    all_keys = sorted(
        set(API_SECRET_KEYS) | set(VOICE_AGENT_SECRET_KEYS) | set(UI_SECRET_KEYS)
    )
    lines = [
        "# RelayDesk SSM source file — do not commit (see env.properties.example)",
        "# Used by: python infra/scripts/sync_ssm_parameters.py",
        "",
    ]
    for key in all_keys:
        value = values.get(key, "")
        if value:
            lines.append(f"{key}={value}")
        else:
            lines.append(f"# {key}=")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {path}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync RelayDesk secrets to AWS SSM.")
    parser.add_argument(
        "--properties",
        type=Path,
        default=DEFAULT_PROPERTIES,
        help=f"Properties file (default: {DEFAULT_PROPERTIES})",
    )
    parser.add_argument("--api-env", type=Path, default=REPO_ROOT / "api" / ".env")
    parser.add_argument(
        "--voice-env", type=Path, default=REPO_ROOT / "voice-agent" / ".env"
    )
    parser.add_argument(
        "--ui-env", type=Path, default=REPO_ROOT / "ui" / ".env.local"
    )
    parser.add_argument(
        "--from-local-env",
        action="store_true",
        help="Merge api/.env and voice-agent/.env into properties lookup",
    )
    parser.add_argument(
        "--write-env-properties",
        action="store_true",
        help="Build env.properties from local .env files (no AWS calls)",
    )
    parser.add_argument("--project", default="relaydesk")
    parser.add_argument("--environment", default="prod")
    parser.add_argument("--region", default="ap-south-1")
    parser.add_argument(
        "--profile",
        default=None,
        help="AWS CLI profile (or set AWS_PROFILE in the environment)",
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    properties = parse_env_file(args.properties)
    if args.from_local_env or args.write_env_properties:
        properties = merge_sources(
            parse_env_file(args.api_env),
            parse_env_file(args.voice_env),
            parse_env_file(args.ui_env),
            properties,
        )

    if args.write_env_properties:
        write_env_properties(args.properties, properties)
        return 0

    if not properties:
        print(
            f"No values found. Create {args.properties} or pass --from-local-env.",
            file=sys.stderr,
        )
        return 1

    api_prefix = f"/{args.project}/{args.environment}/api"
    voice_prefix = f"/{args.project}/{args.environment}/voice-agent"
    ui_prefix = f"/{args.project}/{args.environment}/ui"

    missing: list[str] = []
    errors = 0

    for key in API_SECRET_KEYS:
        value = properties.get(key, "").strip()
        if not value:
            missing.append(f"{api_prefix}/{key}")
            continue
        if key == "DATABASE_URL":
            try:
                validate_database_url(value)
            except ValueError as exc:
                errors += 1
                print(f"invalid {api_prefix}/{key}: {exc}", file=sys.stderr)
                continue
        try:
            put_parameter(
                name=ssm_name(api_prefix, key),
                value=value,
                region=args.region,
                profile=args.profile,
                dry_run=args.dry_run,
            )
        except subprocess.CalledProcessError:
            errors += 1
            print(f"failed {api_prefix}/{key}", file=sys.stderr)

    for key in VOICE_AGENT_SECRET_KEYS:
        value = properties.get(key, "").strip()
        if not value:
            missing.append(f"{voice_prefix}/{key}")
            continue
        try:
            put_parameter(
                name=ssm_name(voice_prefix, key),
                value=value,
                region=args.region,
                profile=args.profile,
                dry_run=args.dry_run,
            )
        except subprocess.CalledProcessError:
            errors += 1
            print(f"failed {voice_prefix}/{key}", file=sys.stderr)

    for key in UI_SECRET_KEYS:
        value = properties.get(key, "").strip()
        if not value:
            missing.append(f"{ui_prefix}/{key}")
            continue
        try:
            put_parameter(
                name=ssm_name(ui_prefix, key),
                value=value,
                region=args.region,
                profile=args.profile,
                dry_run=args.dry_run,
            )
        except subprocess.CalledProcessError:
            errors += 1
            print(f"failed {ui_prefix}/{key}", file=sys.stderr)

    if missing:
        print("\nMissing values (not uploaded):", file=sys.stderr)
        for name in missing:
            print(f"  - {name}", file=sys.stderr)

    if errors:
        return 1
    if missing and not args.dry_run:
        print(
            "\nSome parameters were skipped. Add keys to env.properties and re-run.",
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

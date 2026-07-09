#!/usr/bin/env python3
"""Build and deploy API, UI, and voice-agent to ECS (one command).

Runs deploy_api.py, deploy_ui.py, and deploy_voice_agent.py in sequence.

Usage (from repo root):
  python infra/scripts/deploy_all.py
  python infra/scripts/deploy_all.py --only api,ui
  python infra/scripts/deploy_all.py --dry-run

Windows double-click:
  infra/scripts/deploy_all.bat
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
DEPLOY_ORDER = ("api", "ui", "voice-agent")
SCRIPT_NAMES = {
    "api": "deploy_api.py",
    "ui": "deploy_ui.py",
    "voice-agent": "deploy_voice_agent.py",
}


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build and deploy API, UI, and voice-agent to ECS"
    )
    parser.add_argument(
        "--only",
        help="Comma-separated services to deploy: api, ui, voice-agent (default: all)",
    )
    parser.add_argument("--profile", default=None)
    parser.add_argument("--region", default="ap-south-1")
    parser.add_argument("--image-tag", default="latest")
    parser.add_argument("--terraform-dir", default="infra/terraform")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--build-only", action="store_true")
    parser.add_argument("--skip-deploy", action="store_true")
    args = parser.parse_args()

    if args.only:
        selected = [part.strip() for part in args.only.split(",") if part.strip()]
        unknown = [name for name in selected if name not in SCRIPT_NAMES]
        if unknown:
            print(f"Unknown service(s): {', '.join(unknown)}", file=sys.stderr)
            return 1
        services = [name for name in DEPLOY_ORDER if name in selected]
    else:
        services = list(DEPLOY_ORDER)

    shared_args: list[str] = []
    if args.profile:
        shared_args.extend(["--profile", args.profile])
    shared_args.extend(["--region", args.region])
    shared_args.extend(["--image-tag", args.image_tag])
    shared_args.extend(["--terraform-dir", args.terraform_dir])
    if args.dry_run:
        shared_args.append("--dry-run")
    if args.build_only:
        shared_args.append("--build-only")
    if args.skip_deploy:
        shared_args.append("--skip-deploy")

    for service in services:
        script = SCRIPT_DIR / SCRIPT_NAMES[service]
        cmd = [sys.executable, str(script), *shared_args]
        print(f"\n{'=' * 60}\nRunning {script.name}\n{'=' * 60}")
        result = subprocess.run(cmd)
        if result.returncode != 0:
            print(f"\n✗ {service} deploy failed", file=sys.stderr)
            return result.returncode

    print("\n✓ All selected services deployed successfully")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

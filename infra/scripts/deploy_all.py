#!/usr/bin/env python3
"""Build and deploy API, UI, and voice-agent to ECS.

Default: parallel deploy (new terminal per service on Windows, wait for all).

Usage (from repo root):
  python infra/scripts/deploy_all.py
  python infra/scripts/deploy_all.py --only api,ui
  python infra/scripts/deploy_all.py --sequential
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


def _build_cmd(service: str, shared_args: list[str]) -> list[str]:
    script = SCRIPT_DIR / SCRIPT_NAMES[service]
    return [sys.executable, str(script), *shared_args]


def _deploy_sequential(services: list[str], shared_args: list[str]) -> int:
    for service in services:
        cmd = _build_cmd(service, shared_args)
        print(f"\n{'=' * 60}\nRunning {SCRIPT_NAMES[service]}\n{'=' * 60}")
        result = subprocess.run(cmd)
        if result.returncode != 0:
            print(f"\n✗ {service} deploy failed", file=sys.stderr)
            return result.returncode
    return 0


def _deploy_parallel(
    services: list[str],
    shared_args: list[str],
    *,
    new_terminal: bool,
    wait: bool,
) -> int:
    procs: list[tuple[str, subprocess.Popen[bytes] | subprocess.Popen[str]]] = []

    for service in services:
        cmd = _build_cmd(service, shared_args)
        label = SCRIPT_NAMES[service]

        if new_terminal and sys.platform == "win32":
            print(f"→ Opening new terminal for {service} ({label})")
            proc = subprocess.Popen(
                cmd,
                creationflags=subprocess.CREATE_NEW_CONSOLE,
            )
        else:
            print(f"→ Starting {service} in background ({label})")
            proc = subprocess.Popen(cmd)

        procs.append((service, proc))

    if not wait:
        print(
            "\nDeploy started in parallel. "
            + (
                "Check each terminal window for progress."
                if new_terminal and sys.platform == "win32"
                else "Processes running in background."
            )
        )
        return 0

    failed: list[str] = []
    for service, proc in procs:
        code = proc.wait()
        if code != 0:
            failed.append(service)
            print(f"✗ {service} deploy failed (exit {code})", file=sys.stderr)
        else:
            print(f"✓ {service} deploy finished")

    return 1 if failed else 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build and deploy API, UI, and voice-agent to ECS (parallel by default)"
    )
    parser.add_argument(
        "--only",
        help="Comma-separated services to deploy: api, ui, voice-agent (default: all)",
    )
    parser.add_argument(
        "--sequential",
        action="store_true",
        help="Deploy one service at a time in this terminal (old behavior)",
    )
    parser.add_argument(
        "--no-wait",
        action="store_true",
        help="Start parallel deploys and exit without waiting for completion",
    )
    parser.add_argument(
        "--no-new-terminal",
        action="store_true",
        help="Run parallel deploys in this terminal instead of new windows",
    )
    parser.add_argument("--profile", default=None)
    parser.add_argument("--region", default="ap-south-1")
    parser.add_argument(
        "--image-tag",
        default=None,
        help="ECR tag for all services (default: api/ui=latest, voice-agent=v1)",
    )
    parser.add_argument(
        "--fast",
        action="store_true",
        help="Fast dev deploy (downtime OK): stop tasks, single push, BuildKit",
    )
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
    if args.image_tag:
        shared_args.extend(["--image-tag", args.image_tag])
    shared_args.extend(["--terraform-dir", args.terraform_dir])
    if args.dry_run:
        shared_args.append("--dry-run")
    if args.build_only:
        shared_args.append("--build-only")
    if args.skip_deploy:
        shared_args.append("--skip-deploy")
    if args.fast:
        shared_args.append("--fast")

    if args.sequential:
        code = _deploy_sequential(services, shared_args)
    else:
        code = _deploy_parallel(
            services,
            shared_args,
            new_terminal=not args.no_new_terminal,
            wait=not args.no_wait,
        )

    if code == 0:
        print("\n✓ All selected services deployed successfully")
    return code


if __name__ == "__main__":
    raise SystemExit(main())

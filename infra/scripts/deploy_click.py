#!/usr/bin/env python3
"""Interactive AWS deploy launcher (double-click friendly).

Double-click:
  infra/scripts/deploy_click.bat

Or from repo root:
  python infra/scripts/deploy_click.py
  python infra/scripts/deploy_click.py --only api
  python infra/scripts/deploy_click.py --only api,ui --safe

With no arguments, shows a numbered menu and runs deploy_all.py.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[1]
DEPLOY_ALL = SCRIPT_DIR / "deploy_all.py"

MENU_OPTIONS: list[tuple[str, list[str]]] = [
    ("Deploy all services (fast, parallel)", []),
    ("Deploy API only", ["--only", "api"]),
    ("Deploy UI only", ["--only", "ui"]),
    ("Deploy voice-agent only", ["--only", "voice-agent"]),
    ("Deploy API + UI", ["--only", "api,ui"]),
    ("Deploy all (safe / zero-downtime rolling)", ["--safe"]),
    ("Dry run - all services", ["--dry-run"]),
    ("Build only - all services (no push/deploy)", ["--build-only"]),
]


def _pause_on_windows() -> None:
    if sys.platform == "win32" and sys.stdin.isatty():
        try:
            input("\nPress Enter to close...")
        except EOFError:
            pass


def _run_deploy(extra_args: list[str]) -> int:
    cmd = [sys.executable, str(DEPLOY_ALL), *extra_args]
    print(f"\n-> {' '.join(cmd)}\n")
    result = subprocess.run(cmd, cwd=str(REPO_ROOT))
    return result.returncode


def _pick_from_menu() -> list[str] | None:
    print()
    print("RelayDesk AWS Deploy")
    print("=" * 40)
    print()
    for index, (label, _) in enumerate(MENU_OPTIONS, start=1):
        print(f"  {index}. {label}")
    print("  0. Exit")
    print()

    while True:
        try:
            choice = input(f"Choose [1-{len(MENU_OPTIONS)}]: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nCancelled.")
            return None

        if choice in {"", "1"}:
            return MENU_OPTIONS[0][1]
        if choice == "0":
            return None
        if choice.isdigit():
            index = int(choice)
            if 1 <= index <= len(MENU_OPTIONS):
                return MENU_OPTIONS[index - 1][1]
        print(f"Invalid choice: {choice!r}. Try again.")


def main(argv: list[str] | None = None) -> int:
    args = list(argv if argv is not None else sys.argv[1:])

    if args:
        return _run_deploy(args)

    selected = _pick_from_menu()
    if selected is None:
        return 0

    code = _run_deploy(selected)
    if code == 0:
        print("\nDeploy finished successfully")
    else:
        print(f"\nDeploy failed (exit {code})", file=sys.stderr)
    _pause_on_windows()
    return code


if __name__ == "__main__":
    raise SystemExit(main())

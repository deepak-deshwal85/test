#!/usr/bin/env python3
"""Build RelayDesk UI Docker image, push to ECR, and redeploy ECS.

Mirrors the steps in ui/README.md § "Docker build, push to ECR, update ECS".

Usage (from repo root):
  python infra/scripts/deploy_ui.py
  python infra/scripts/deploy_ui.py --profile relaydesk-admin --image-tag latest
  python infra/scripts/deploy_ui.py --dry-run
  python infra/scripts/deploy_ui.py --build-only
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from deploy_common import main_for_service

if __name__ == "__main__":
    raise SystemExit(
        main_for_service(
            "ui",
            "Build and deploy RelayDesk UI to ECS",
        )
    )

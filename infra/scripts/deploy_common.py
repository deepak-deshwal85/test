#!/usr/bin/env python3
"""Shared helpers for RelayDesk Docker → ECR → ECS deploy scripts."""
from __future__ import annotations

import argparse
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class DeployTarget:
    name: str
    docker_context: str
    local_image: str
    ecr_output: str
    ecs_service_output: str


DEPLOY_TARGETS: dict[str, DeployTarget] = {
    "api": DeployTarget(
        name="api",
        docker_context="api",
        local_image="relaydesk-api:latest",
        ecr_output="ecr_api_repository_url",
        ecs_service_output="ecs_service_api_name",
    ),
    "ui": DeployTarget(
        name="ui",
        docker_context="ui",
        local_image="relaydesk-ui:latest",
        ecr_output="ecr_ui_repository_url",
        ecs_service_output="ecs_service_ui_name",
    ),
    "voice-agent": DeployTarget(
        name="voice-agent",
        docker_context="voice-agent",
        local_image="relaydesk-voice:latest",
        ecr_output="ecr_voice_agent_repository_url",
        ecs_service_output="ecs_service_voice_agent_name",
    ),
}

DEFAULT_IMAGE_TAGS: dict[str, str] = {
    "api": "latest",
    "ui": "latest",
    "voice-agent": "v1",
}


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def aws_env() -> dict[str, str]:
    """Disable AWS CLI pager (avoids less/'press q' on long JSON output)."""
    import os

    env = os.environ.copy()
    env["AWS_PAGER"] = ""
    env["AWS_CLI_AUTO_PROMPT"] = "off"
    return env


def terraform_output(terraform_dir: Path, name: str) -> str:
    result = subprocess.run(
        ["terraform", "output", "-raw", name],
        cwd=str(terraform_dir),
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        stderr = (result.stderr or result.stdout or "").strip()
        raise RuntimeError(
            f"terraform output -raw {name!r} failed in {terraform_dir}: {stderr}"
        )
    value = result.stdout.strip()
    if not value or value == "null":
        raise RuntimeError(f"Terraform output {name!r} is empty")
    return value


def run_step(
    cmd: list[str],
    *,
    cwd: Path | None = None,
    dry_run: bool = False,
    env: dict[str, str] | None = None,
) -> None:
    label = " ".join(cmd)
    print(f"\n→ {label}")
    if dry_run:
        print("[dry-run] skipped")
        return
    result = subprocess.run(cmd, cwd=str(cwd) if cwd else None, env=env)
    if result.returncode != 0:
        raise RuntimeError(f"Command failed ({result.returncode}): {label}")


def add_deploy_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--profile",
        default=None,
        help="AWS CLI profile (default: AWS_PROFILE or relaydesk-admin)",
    )
    parser.add_argument("--region", default="ap-south-1")
    parser.add_argument(
        "--image-tag",
        default=None,
        help="ECR image tag (default: latest for api/ui, v1 for voice-agent)",
    )
    parser.add_argument(
        "--terraform-dir",
        default="infra/terraform",
        help="Path to Terraform directory",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print commands without executing",
    )
    parser.add_argument(
        "--build-only",
        action="store_true",
        help="Docker build only (no ECR login, push, or ECS deploy)",
    )
    parser.add_argument(
        "--skip-deploy",
        action="store_true",
        help="Build and push to ECR but do not force ECS redeployment",
    )
    parser.add_argument(
        "--fast",
        action="store_true",
        help=(
            "Fast dev deploy (downtime OK): BuildKit cache, single ECR push, "
            "stop running tasks before redeploy"
        ),
    )


def resolve_profile(explicit: str | None) -> str:
    import os

    return explicit or os.getenv("AWS_PROFILE") or os.getenv("PROFILE_NAME") or "relaydesk-admin"


def resolve_image_tag(service_key: str, explicit: str | None) -> str:
    if explicit:
        return explicit
    return DEFAULT_IMAGE_TAGS.get(service_key, "latest")


def docker_build_env(*, fast: bool) -> dict[str, str]:
    import os

    env = os.environ.copy()
    if fast:
        env["DOCKER_BUILDKIT"] = "1"
    return env


def list_running_task_arns(
    *,
    cluster: str,
    service: str,
    profile: str,
    region: str,
    dry_run: bool,
) -> list[str]:
    if dry_run:
        return []
    result = subprocess.run(
        [
            "aws",
            "ecs",
            "list-tasks",
            "--cluster",
            cluster,
            "--service-name",
            service,
            "--desired-status",
            "RUNNING",
            "--profile",
            profile,
            "--region",
            region,
            "--no-cli-pager",
            "--output",
            "json",
            "--query",
            "taskArns",
        ],
        capture_output=True,
        text=True,
        env=aws_env(),
        check=True,
    )
    import json

    task_arns = json.loads(result.stdout or "[]")
    return [str(arn) for arn in task_arns if arn]


def stop_running_tasks(
    *,
    cluster: str,
    service: str,
    profile: str,
    region: str,
    dry_run: bool,
) -> None:
    task_arns = list_running_task_arns(
        cluster=cluster,
        service=service,
        profile=profile,
        region=region,
        dry_run=dry_run,
    )
    if not task_arns:
        print(f"  no running tasks for {service}")
        return
    print(f"  stopping {len(task_arns)} running task(s) for {service}")
    for task_arn in task_arns:
        run_step(
            [
                "aws",
                "ecs",
                "stop-task",
                "--cluster",
                cluster,
                "--task",
                task_arn,
                "--reason",
                "fast deploy",
                "--profile",
                profile,
                "--region",
                region,
                "--no-cli-pager",
            ],
            dry_run=dry_run,
            env=aws_env(),
        )


def deploy_service(
    target: DeployTarget,
    *,
    profile: str,
    region: str,
    image_tag: str,
    terraform_dir: Path,
    dry_run: bool = False,
    build_only: bool = False,
    skip_deploy: bool = False,
    fast: bool = False,
) -> None:
    root = repo_root()
    context_path = root / target.docker_context
    if not context_path.is_dir():
        raise RuntimeError(f"Docker context not found: {context_path}")

    tf_dir = terraform_dir if terraform_dir.is_absolute() else root / terraform_dir

    print(f"=== Deploy {target.name} ===")
    print(f"  repo root:     {root}")
    print(f"  docker context:{context_path}")
    print(f"  profile:       {profile}")
    print(f"  region:        {region}")
    print(f"  image tag:     {image_tag}")
    if fast:
        print("  mode:          fast (downtime OK)")

    account_id = terraform_output(tf_dir, "aws_account_id")
    ecr_url = terraform_output(tf_dir, target.ecr_output)
    cluster = terraform_output(tf_dir, "ecs_cluster_name")
    service = terraform_output(tf_dir, target.ecs_service_output)

    print(f"  ECR:           {ecr_url}")
    print(f"  ECS:           {cluster} / {service}")

    registry = f"{account_id}.dkr.ecr.{region}.amazonaws.com"

    run_step(
        ["docker", "build", "-t", target.local_image, str(context_path)],
        cwd=root,
        dry_run=dry_run,
        env=docker_build_env(fast=fast),
    )

    if build_only:
        print(f"\n✓ {target.name} image built ({target.local_image})")
        return

    login_cmd = [
        "aws",
        "ecr",
        "get-login-password",
        "--profile",
        profile,
        "--region",
        region,
        "--no-cli-pager",
    ]
    print(f"\n→ ECR login ({registry})")
    if dry_run:
        print("[dry-run] skipped ECR login")
    else:
        login = subprocess.run(
            login_cmd,
            capture_output=True,
            text=True,
            check=True,
            env=aws_env(),
        )
        docker_login = subprocess.run(
            [
                "docker",
                "login",
                "--username",
                "AWS",
                "--password-stdin",
                registry,
            ],
            input=login.stdout,
            text=True,
        )
        if docker_login.returncode != 0:
            raise RuntimeError("docker login to ECR failed")

    tagged = f"{ecr_url}:{image_tag}"
    latest = f"{ecr_url}:latest"
    run_step(["docker", "tag", target.local_image, tagged], dry_run=dry_run)
    run_step(["docker", "push", tagged], dry_run=dry_run)
    if not fast and image_tag != "latest":
        run_step(["docker", "tag", target.local_image, latest], dry_run=dry_run)
        run_step(["docker", "push", latest], dry_run=dry_run)

    if skip_deploy:
        print(f"\n✓ {target.name} pushed to ECR (ECS deploy skipped)")
        return

    if fast:
        print(f"\n→ Fast deploy: stopping old {target.name} tasks")
        stop_running_tasks(
            cluster=cluster,
            service=service,
            profile=profile,
            region=region,
            dry_run=dry_run,
        )

    run_step(
        [
            "aws",
            "ecs",
            "update-service",
            "--cluster",
            cluster,
            "--service",
            service,
            "--force-new-deployment",
            "--profile",
            profile,
            "--region",
            region,
            "--no-cli-pager",
            "--output",
            "json",
            "--query",
            "service.{name:serviceName,status:status,desired:desiredCount,running:runningCount,deployment:deployments[0].rolloutState}",
        ],
        dry_run=dry_run,
        env=aws_env(),
    )
    print(f"\n✓ {target.name} deployed ({tagged})")


def main_for_service(service_key: str, description: str) -> int:
    target = DEPLOY_TARGETS[service_key]
    parser = argparse.ArgumentParser(description=description)
    add_deploy_args(parser)
    args = parser.parse_args()

    try:
        deploy_service(
            target,
            profile=resolve_profile(args.profile),
            region=args.region,
            image_tag=resolve_image_tag(service_key, args.image_tag),
            terraform_dir=Path(args.terraform_dir),
            dry_run=args.dry_run,
            build_only=args.build_only,
            skip_deploy=args.skip_deploy,
            fast=args.fast,
        )
    except (RuntimeError, subprocess.CalledProcessError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    return 0

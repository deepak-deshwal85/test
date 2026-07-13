#!/usr/bin/env python3
"""Destroy and/or reprovision RelayDesk AWS infrastructure with no manual steps.

Orchestrates existing scripts: terraform, sync_ssm_parameters, rds_tunnel,
bootstrap_db, and deploy_all.

Prerequisites (must exist before running):
  - api/.env, ui/.env, voice-agent/.env with vendor API keys
  - RDS_DB_PASSWORD env var (or --password) — used for Terraform + RDS bootstrap
  - terraform, aws, docker, and uv on PATH
  - AWS CLI profile configured (--profile or AWS_PROFILE)

Examples (from repo root):
  # Full teardown then rebuild (DB wiped + Deepak seed):
  python infra/scripts/rebuild_infra.py rebuild --yes --profile relaydesk-admin

  # Destroy only:
  python infra/scripts/rebuild_infra.py destroy --yes --profile relaydesk-admin

  # Provision after terraform apply was run separately:
  python infra/scripts/rebuild_infra.py provision --profile relaydesk-admin

  # Dry run (print steps only):
  python infra/scripts/rebuild_infra.py rebuild --yes --dry-run
"""
from __future__ import annotations

import argparse
import contextlib
import json
import os
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[1]
DEFAULT_TERRAFORM_DIR = REPO_ROOT / "infra" / "terraform"
TUNNEL_HOST = "127.0.0.1"
TUNNEL_PORT = 15432
VOICE_COGNITO_TF_RESOURCE = "aws_cognito_user_pool_client.voice_m2m[0]"

SESSION_MANAGER_PLUGIN_WIN = Path(r"C:\Program Files\Amazon\SessionManagerPlugin\bin")


def _aws_env() -> dict[str, str]:
    env = os.environ.copy()
    env["AWS_PAGER"] = ""
    env["AWS_CLI_AUTO_PROMPT"] = "off"
    if SESSION_MANAGER_PLUGIN_WIN.is_dir():
        env["PATH"] = f"{SESSION_MANAGER_PLUGIN_WIN}{os.pathsep}{env.get('PATH', '')}"
    return env


def _resolve_profile(explicit: str | None) -> str:
    profile = explicit or os.getenv("AWS_PROFILE") or os.getenv("PROFILE_NAME")
    if not profile:
        raise RuntimeError("Set --profile or AWS_PROFILE.")
    return profile


def _resolve_password(explicit: str | None, *, required: bool = True) -> str:
    password = (explicit or os.getenv("RDS_DB_PASSWORD") or "").strip()
    if not password and required:
        raise RuntimeError("Set RDS_DB_PASSWORD or pass --password.")
    return password


def _run_step(
    label: str,
    cmd: list[str],
    *,
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
    dry_run: bool = False,
) -> None:
    print(f"\n==> {label}")
    print(f"    {' '.join(cmd)}")
    if dry_run:
        print("    [dry-run] skipped")
        return
    merged = _aws_env()
    if env:
        merged.update(env)
    result = subprocess.run(cmd, cwd=str(cwd) if cwd else None, env=merged, check=False)
    if result.returncode != 0:
        raise RuntimeError(f"{label} failed (exit {result.returncode})")


def _run_python_script(
    script: str,
    args: list[str],
    *,
    label: str | None = None,
    dry_run: bool = False,
) -> None:
    cmd = [sys.executable, str(SCRIPT_DIR / script), *args]
    _run_step(label or script, cmd, cwd=REPO_ROOT, dry_run=dry_run)


def _check_prerequisites(*, require_env_files: bool) -> None:
    for tool in ("terraform", "aws", "docker", "uv"):
        if shutil.which(tool) is None:
            raise RuntimeError(f"Required tool not found on PATH: {tool}")

    if require_env_files:
        missing = [
            path
            for path in (
                REPO_ROOT / "api" / ".env",
                REPO_ROOT / "ui" / ".env",
                REPO_ROOT / "voice-agent" / ".env",
            )
            if not path.is_file()
        ]
        if missing:
            raise RuntimeError(
                "Missing local .env files (copy from .env.example and fill secrets):\n"
                + "\n".join(f"  - {path}" for path in missing)
            )


def _terraform_output(terraform_dir: Path, key: str) -> str:
    result = subprocess.run(
        ["terraform", "output", "-raw", key],
        cwd=str(terraform_dir),
        capture_output=True,
        text=True,
        check=True,
        env=_aws_env(),
    )
    value = (result.stdout or "").strip()
    if not value or value == "null":
        raise RuntimeError(f"Terraform output {key!r} is empty")
    return value


def _wait_rds_available(
    *,
    profile: str,
    region: str,
    instance_id: str,
    timeout_s: int = 900,
    dry_run: bool = False,
) -> None:
    print(f"\n==> Wait for RDS ({instance_id})")
    if dry_run:
        print("    [dry-run] skipped")
        return

    sys.path.insert(0, str(SCRIPT_DIR))
    from cost_control import wait_rds_available  # noqa: WPS433

    wait_rds_available(profile, region, instance_id, timeout_s=timeout_s)


def _wait_api_ec2_instance(
    *,
    profile: str,
    region: str,
    timeout_s: int = 900,
    dry_run: bool = False,
) -> str:
    print("\n==> Wait for API EC2 instance (SSM tunnel bastion)")
    if dry_run:
        print("    [dry-run] skipped")
        return "i-dryrun"

    deadline = time.time() + timeout_s
    while time.time() < deadline:
        result = subprocess.run(
            [
                "aws",
                "ec2",
                "describe-instances",
                "--profile",
                profile,
                "--region",
                region,
                "--filters",
                "Name=tag:Name,Values=relaydesk-prod-ecs-api",
                "Name=instance-state-name,Values=running",
                "--query",
                "Reservations[0].Instances[0].InstanceId",
                "--output",
                "text",
                "--no-cli-pager",
            ],
            capture_output=True,
            text=True,
            env=_aws_env(),
            check=False,
        )
        instance_id = (result.stdout or "").strip()
        if result.returncode == 0 and instance_id and instance_id != "None":
            print(f"    api instance: {instance_id}")
            return instance_id
        print("    waiting for relaydesk-prod-ecs-api instance...")
        time.sleep(20)
    raise RuntimeError("Timed out waiting for API EC2 instance")


def _wait_for_port(host: str, port: int, *, timeout_s: int = 120) -> None:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        try:
            with socket.create_connection((host, port), timeout=2):
                return
        except OSError:
            time.sleep(2)
    raise RuntimeError(f"Timed out waiting for {host}:{port}")


@contextlib.contextmanager
def _rds_tunnel(
    *,
    profile: str,
    region: str,
    terraform_dir: Path,
    local_port: int = TUNNEL_PORT,
    dry_run: bool = False,
):
    if dry_run:
        print("\n==> RDS tunnel [dry-run]")
        yield
        return

    rds_host = _terraform_output(terraform_dir, "rds_endpoint")
    instance_id = _wait_api_ec2_instance(profile=profile, region=region)

    print("\n==> Start RDS SSM tunnel (background)")
    proc = subprocess.Popen(
        [
            "aws",
            "ssm",
            "start-session",
            "--profile",
            profile,
            "--region",
            region,
            "--target",
            instance_id,
            "--document-name",
            "AWS-StartPortForwardingSessionToRemoteHost",
            "--parameters",
            f"host={rds_host},portNumber=5432,localPortNumber={local_port}",
        ],
        env=_aws_env(),
    )
    try:
        _wait_for_port(TUNNEL_HOST, local_port, timeout_s=120)
        print(f"    tunnel ready on {TUNNEL_HOST}:{local_port}")
        yield
    finally:
        print("    stopping tunnel")
        proc.terminate()
        try:
            proc.wait(timeout=15)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=5)


def _wait_ecs_services_running(
    *,
    profile: str,
    region: str,
    cluster: str,
    services: list[str],
    timeout_s: int = 1200,
    dry_run: bool = False,
) -> None:
    print(f"\n==> Wait for ECS services: {', '.join(services)}")
    if dry_run:
        print("    [dry-run] skipped")
        return

    deadline = time.time() + timeout_s
    while time.time() < deadline:
        pending: list[str] = []
        for service in services:
            result = subprocess.run(
                [
                    "aws",
                    "ecs",
                    "describe-services",
                    "--cluster",
                    cluster,
                    "--services",
                    service,
                    "--profile",
                    profile,
                    "--region",
                    region,
                    "--query",
                    "services[0].{desired:desiredCount,running:runningCount,rollout:deployments[0].rolloutState}",
                    "--output",
                    "json",
                    "--no-cli-pager",
                ],
                capture_output=True,
                text=True,
                env=_aws_env(),
                check=True,
            )
            info = json.loads(result.stdout or "{}")
            desired = int(info.get("desired") or 0)
            running = int(info.get("running") or 0)
            rollout = str(info.get("rollout") or "")
            if desired > 0 and (running < desired or rollout not in {"", "COMPLETED"}):
                pending.append(f"{service}({running}/{desired},{rollout})")
        if not pending:
            print("    all services healthy")
            return
        print(f"    waiting: {', '.join(pending)}")
        time.sleep(20)
    raise RuntimeError("Timed out waiting for ECS services to become healthy")


def _terraform_destroy(terraform_dir: Path, *, dry_run: bool) -> None:
    _run_step(
        "terraform destroy",
        ["terraform", "destroy", "-auto-approve"],
        cwd=terraform_dir,
        dry_run=dry_run,
    )


def _ui_domain_configured(terraform_dir: Path) -> bool:
    """True when terraform.tfvars sets a non-empty ui_domain_name."""
    tfvars = terraform_dir / "terraform.tfvars"
    if not tfvars.is_file():
        return False
    for raw in tfvars.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line.startswith("#") or "ui_domain_name" not in line or "=" not in line:
            continue
        key, _, value = line.partition("=")
        if key.strip() != "ui_domain_name":
            continue
        return bool(value.strip().strip('"').strip("'"))
    return False


def _print_acm_dns_records(terraform_dir: Path) -> None:
    result = subprocess.run(
        ["terraform", "output", "-json", "acm_dns_validation_records"],
        cwd=str(terraform_dir),
        capture_output=True,
        text=True,
        env=_aws_env(),
        check=False,
    )
    print("\n==> Cloudflare: add ACM validation CNAME(s) now (DNS only / gray cloud)")
    if result.returncode != 0:
        print("    (could not read acm_dns_validation_records — check Terraform state)")
        print((result.stderr or result.stdout or "").strip())
        return
    try:
        records = json.loads(result.stdout or "[]")
    except json.JSONDecodeError:
        print(result.stdout)
        return
    if not records:
        print("    (no validation records — ui_domain_name may be unset)")
        return
    for record in records:
        print(f"    Type:  {record.get('type')}")
        print(f"    Name:  {record.get('name')}")
        print(f"    Value: {record.get('value')}")
        print("    Proxy: DNS only (gray cloud) — required")
        print()
    print("    Docs: infra/README.md § Custom domain (Cloudflare + ACM)")
    print("    Waiting for ACM certificate to become ISSUED...")


def _acm_certificate_arn(terraform_dir: Path) -> str | None:
    result = subprocess.run(
        ["terraform", "state", "show", "-no-color", "aws_acm_certificate.ui[0]"],
        cwd=str(terraform_dir),
        capture_output=True,
        text=True,
        env=_aws_env(),
        check=False,
    )
    if result.returncode != 0:
        return None
    for line in (result.stdout or "").splitlines():
        if "arn" in line and "acm" in line and "=" in line:
            return line.split("=", 1)[1].strip().strip('"')
    return None


def _wait_acm_issued(
    *,
    profile: str,
    region: str,
    terraform_dir: Path,
    timeout_s: int = 1800,
    dry_run: bool = False,
) -> None:
    if dry_run:
        print("\n==> Wait for ACM ISSUED [dry-run]")
        return

    arn = _acm_certificate_arn(terraform_dir)
    if not arn:
        raise RuntimeError(
            "Could not find aws_acm_certificate.ui[0] in Terraform state. "
            "Add ui_domain_name to terraform.tfvars or run apply manually."
        )

    deadline = time.time() + timeout_s
    while time.time() < deadline:
        result = subprocess.run(
            [
                "aws",
                "acm",
                "describe-certificate",
                "--certificate-arn",
                arn,
                "--profile",
                profile,
                "--region",
                region,
                "--query",
                "Certificate.Status",
                "--output",
                "text",
                "--no-cli-pager",
            ],
            capture_output=True,
            text=True,
            env=_aws_env(),
            check=False,
        )
        status = (result.stdout or "").strip()
        print(f"    ACM status: {status or 'unknown'}")
        if status == "ISSUED":
            return
        if status in {"FAILED", "VALIDATION_TIMED_OUT", "REVOKED"}:
            raise RuntimeError(f"ACM certificate entered status {status}")
        time.sleep(30)
    raise RuntimeError(
        "Timed out waiting for ACM ISSUED. Confirm the Cloudflare ACM CNAME "
        "is DNS-only (gray cloud) and matches terraform output acm_dns_validation_records."
    )


def _terraform_apply(
    terraform_dir: Path,
    *,
    password: str,
    profile: str,
    region: str,
    dry_run: bool,
) -> None:
    env = {"TF_VAR_rds_master_password": password}
    _run_step("terraform init", ["terraform", "init"], cwd=terraform_dir, dry_run=dry_run)

    # Custom domain: create cert first, print Cloudflare ACM CNAMEs, wait for ISSUED,
    # then full apply (avoids apply hanging forever on certificate validation).
    if _ui_domain_configured(terraform_dir):
        _run_step(
            "terraform apply (ACM certificate only)",
            [
                "terraform",
                "apply",
                "-auto-approve",
                "-target=aws_acm_certificate.ui[0]",
            ],
            cwd=terraform_dir,
            env=env,
            dry_run=dry_run,
        )
        if not dry_run:
            _print_acm_dns_records(terraform_dir)
        _wait_acm_issued(
            profile=profile,
            region=region,
            terraform_dir=terraform_dir,
            dry_run=dry_run,
        )

    _run_step(
        "terraform apply",
        ["terraform", "apply", "-auto-approve"],
        cwd=terraform_dir,
        env=env,
        dry_run=dry_run,
    )

    if _ui_domain_configured(terraform_dir) and not dry_run:
        try:
            alb = _terraform_output(terraform_dir, "alb_dns_name")
            print("\n==> Cloudflare: point app CNAME (@ or www) at ALB (DNS only first)")
            print(f"    Type:  CNAME")
            print(f"    Name:  @  (or www)")
            print(f"    Value: {alb}")
            print("    Proxy: DNS only until HTTPS works; SSL mode Full (strict)")
        except RuntimeError:
            pass


def _sync_secrets(
    *,
    profile: str,
    region: str,
    password: str,
    terraform_dir: Path,
    dry_run: bool,
) -> None:
    base_args = ["--profile", profile, "--region", region]
    _run_python_script(
        "sync_ssm_parameters.py",
        base_args,
        label="Sync SSM from local .env files",
        dry_run=dry_run,
    )
    _run_python_script(
        "sync_ssm_parameters.py",
        [
            *base_args,
            "--only",
            "DATABASE_URL",
            "--from-rds",
            "--password",
            password,
            "--terraform-dir",
            str(terraform_dir),
        ],
        label="Sync production DATABASE_URL to SSM",
        dry_run=dry_run,
    )
    _run_python_script(
        "sync_ssm_parameters.py",
        [
            *base_args,
            "--only",
            "COGNITO_CLIENT_SECRET",
            "--from-terraform",
            "--terraform-dir",
            str(terraform_dir),
            "--terraform-resource",
            VOICE_COGNITO_TF_RESOURCE,
        ],
        label="Sync voice-agent Cognito M2M secret from Terraform",
        dry_run=dry_run,
    )


def _bootstrap_database(*, password: str, dry_run: bool) -> None:
    with _rds_tunnel(
        profile=_active_profile,
        region=_active_region,
        terraform_dir=_active_terraform_dir,
        dry_run=dry_run,
    ):
        _run_python_script(
            "bootstrap_db.py",
            ["--use-tunnel", "--password", password, "--yes"],
            label="Bootstrap RDS (drop + schema + Deepak seed)",
            dry_run=dry_run,
        )


def _deploy_all_services(*, profile: str, region: str, terraform_dir: Path, dry_run: bool) -> None:
    _run_python_script(
        "deploy_all.py",
        [
            "--profile",
            profile,
            "--region",
            region,
            "--terraform-dir",
            str(terraform_dir),
        ],
        label="Build and deploy API, UI, and voice-agent",
        dry_run=dry_run,
    )


def _collect_ecs_services(terraform_dir: Path) -> list[str]:
    services: list[str] = []
    for key in (
        "ecs_service_api_name",
        "ecs_service_ui_name",
        "ecs_service_voice_agent_name",
    ):
        try:
            value = _terraform_output(terraform_dir, key)
        except RuntimeError:
            continue
        if value:
            services.append(value)
    return services


# Set during provision() for tunnel helper
_active_profile = ""
_active_region = ""
_active_terraform_dir = DEFAULT_TERRAFORM_DIR


def provision(args: argparse.Namespace) -> int:
    global _active_profile, _active_region, _active_terraform_dir

    profile = _resolve_profile(args.profile)
    password = _resolve_password(args.password, required=not args.dry_run)
    region = args.region
    terraform_dir = Path(args.terraform_dir).resolve()
    _active_profile = profile
    _active_region = region
    _active_terraform_dir = terraform_dir

    _check_prerequisites(require_env_files=True)

    if not args.skip_terraform:
        _terraform_apply(
            terraform_dir,
            password=password,
            profile=profile,
            region=region,
            dry_run=args.dry_run,
        )

    if args.dry_run:
        rds_id = "relaydesk-prod-postgres"
        cluster = "relaydesk-prod"
        services = ["relaydesk-prod-api", "relaydesk-prod-ui", "relaydesk-prod-voice-agent"]
    else:
        rds_id = _terraform_output(terraform_dir, "rds_instance_identifier")
        cluster = _terraform_output(terraform_dir, "ecs_cluster_name")
        services = _collect_ecs_services(terraform_dir)

    _wait_rds_available(
        profile=profile,
        region=region,
        instance_id=rds_id,
        dry_run=args.dry_run,
    )

    if not args.skip_bootstrap:
        _bootstrap_database(password=password, dry_run=args.dry_run)

    _sync_secrets(
        profile=profile,
        region=region,
        password=password,
        terraform_dir=terraform_dir,
        dry_run=args.dry_run,
    )

    if not args.skip_deploy:
        _deploy_all_services(
            profile=profile,
            region=region,
            terraform_dir=terraform_dir,
            dry_run=args.dry_run,
        )
        _wait_ecs_services_running(
            profile=profile,
            region=region,
            cluster=cluster,
            services=services,
            dry_run=args.dry_run,
        )

    print("\nRebuild complete.")
    if not args.dry_run:
        try:
            alb = _terraform_output(terraform_dir, "alb_dns_name")
            print(f"  ALB: http://{alb}")
        except RuntimeError:
            pass
        try:
            domain = _terraform_output(terraform_dir, "ui_public_base_url")
            if domain:
                print(f"  UI:  {domain}")
        except RuntimeError:
            pass
        print(
            "\nNext (manual):\n"
            "  1. Cloudflare app CNAME → ALB (see infra/README.md §6) if not done\n"
            "  2. Cognito: sign in once, then approve_cognito_user.py if needed"
        )
    return 0


def destroy(args: argparse.Namespace) -> int:
    terraform_dir = Path(args.terraform_dir).resolve()
    _check_prerequisites(require_env_files=False)
    _terraform_destroy(terraform_dir, dry_run=args.dry_run)
    print("\nDestroy complete. Run `rebuild_infra.py provision` to recreate.")
    return 0


def rebuild(args: argparse.Namespace) -> int:
    if not args.yes:
        print("Refusing to rebuild without --yes (destroys all AWS resources).", file=sys.stderr)
        return 1
    destroy(args)
    return provision(args)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command",
        choices=["destroy", "provision", "rebuild"],
        help="destroy: terraform destroy; provision: apply+seed+deploy; rebuild: both",
    )
    parser.add_argument("--profile", default=None)
    parser.add_argument("--region", default=os.getenv("AWS_REGION", "ap-south-1"))
    parser.add_argument("--password", default=None, help="RDS password (or RDS_DB_PASSWORD)")
    parser.add_argument("--terraform-dir", type=Path, default=DEFAULT_TERRAFORM_DIR)
    parser.add_argument(
        "--skip-terraform",
        action="store_true",
        help="Skip terraform apply (use after manual apply)",
    )
    parser.add_argument(
        "--skip-bootstrap",
        action="store_true",
        help="Skip RDS drop/seed (keep existing DB)",
    )
    parser.add_argument(
        "--skip-deploy",
        action="store_true",
        help="Skip Docker build and ECS deploy",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Required for destroy/rebuild (confirms data loss)",
    )
    parser.add_argument("--dry-run", action="store_true")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "destroy" and not args.yes:
        print("Refusing to destroy without --yes.", file=sys.stderr)
        return 1

    try:
        if args.command == "destroy":
            return destroy(args)
        if args.command == "provision":
            return provision(args)
        return rebuild(args)
    except RuntimeError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

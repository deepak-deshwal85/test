#!/usr/bin/env python3
"""Stop or start billable RelayDesk AWS resources to reduce idle cost.

Stops (saves state, then scales down):
  - ECS services (API, UI, voice-agent) → desired count 0
  - EC2 Auto Scaling groups (API + voice hosts) → 0 instances
  - RDS PostgreSQL (optional, --include-rds)

Start restores counts from the saved state file.

Still billed while stopped: NAT Gateway, ALB, public IPv4, EBS on RDS, SSM, etc.
Destroy those with Terraform only if you accept full teardown.

Examples:
  python infra/scripts/cost_control.py status --profile relaydesk-admin
  python infra/scripts/cost_control.py stop --profile relaydesk-admin --include-rds
  python infra/scripts/cost_control.py start --profile relaydesk-admin
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_STATE_FILE = Path(__file__).resolve().parent / "cost-control-state.json"
DEFAULT_TERRAFORM_DIR = REPO_ROOT / "infra" / "terraform"


@dataclass(frozen=True)
class InfraTargets:
    cluster: str
    ecs_services: dict[str, str]  # logical name → service name
    asgs: dict[str, str]  # logical name → ASG name
    rds_instance_id: str | None


def _aws_base(profile: str | None, region: str) -> list[str]:
    cmd = ["aws"]
    if profile:
        cmd.extend(["--profile", profile])
    cmd.extend(["--region", region])
    return cmd


def aws_call(
    profile: str | None,
    region: str,
    service: str,
    operation: str,
    *,
    args: list[str] | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    cmd = _aws_base(profile, region) + [service, operation]
    if args:
        cmd.extend(args)
    if dry_run:
        print(f"[dry-run] {' '.join(cmd)}")
        return {}
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise RuntimeError(
            f"AWS command failed ({service} {operation}): {result.stderr.strip() or result.stdout}"
        )
    if not result.stdout.strip():
        return {}
    return json.loads(result.stdout)


def terraform_outputs(terraform_dir: Path) -> dict[str, Any]:
    result = subprocess.run(
        ["terraform", "output", "-json"],
        cwd=str(terraform_dir),
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(result.stdout)


def output_value(outputs: dict[str, Any], key: str) -> Any:
    obj = outputs.get(key)
    if not isinstance(obj, dict):
        return None
    return obj.get("value")


def load_infra_targets(terraform_dir: Path) -> InfraTargets:
    outputs = terraform_outputs(terraform_dir)
    cluster = output_value(outputs, "ecs_cluster_name")
    if not cluster:
        raise RuntimeError("Missing terraform output: ecs_cluster_name")

    services: dict[str, str] = {}
    api = output_value(outputs, "ecs_service_api_name")
    voice = output_value(outputs, "ecs_service_voice_agent_name")
    ui = output_value(outputs, "ecs_service_ui_name")
    if api:
        services["api"] = str(api)
    if voice:
        services["voice-agent"] = str(voice)
    if ui:
        services["ui"] = str(ui)

    asgs: dict[str, str] = {}
    api_asg = output_value(outputs, "ecs_api_asg_name")
    voice_asg = output_value(outputs, "ecs_voice_asg_name")
    if api_asg:
        asgs["api"] = str(api_asg)
    if voice_asg:
        asgs["voice"] = str(voice_asg)

    rds_id = output_value(outputs, "rds_instance_identifier")
    return InfraTargets(
        cluster=str(cluster),
        ecs_services=services,
        asgs=asgs,
        rds_instance_id=str(rds_id) if rds_id else None,
    )


def describe_ecs_service(
    profile: str | None, region: str, cluster: str, service: str
) -> dict[str, Any]:
    data = aws_call(
        profile,
        region,
        "ecs",
        "describe-services",
        args=["--cluster", cluster, "--services", service],
    )
    services = data.get("services", [])
    return services[0] if services else {}


def describe_asg(profile: str | None, region: str, asg_name: str) -> dict[str, Any]:
    data = aws_call(
        profile,
        region,
        "autoscaling",
        "describe-auto-scaling-groups",
        args=["--auto-scaling-group-names", asg_name],
    )
    groups = data.get("AutoScalingGroups", [])
    return groups[0] if groups else {}


def describe_rds(profile: str | None, region: str, instance_id: str) -> dict[str, Any]:
    data = aws_call(
        profile,
        region,
        "rds",
        "describe-db-instances",
        args=["--db-instance-identifier", instance_id],
    )
    instances = data.get("DBInstances", [])
    return instances[0] if instances else {}


def capture_state(targets: InfraTargets, profile: str | None, region: str) -> dict[str, Any]:
    ecs_state: dict[str, int] = {}
    for name, service in targets.ecs_services.items():
        info = describe_ecs_service(profile, region, targets.cluster, service)
        ecs_state[service] = int(info.get("desiredCount", 0))

    asg_state: dict[str, dict[str, int]] = {}
    for name, asg_name in targets.asgs.items():
        info = describe_asg(profile, region, asg_name)
        asg_state[asg_name] = {
            "min": int(info.get("MinSize", 0)),
            "max": int(info.get("MaxSize", 0)),
            "desired": int(info.get("DesiredCapacity", 0)),
        }

    rds_state: dict[str, Any] | None = None
    if targets.rds_instance_id:
        info = describe_rds(profile, region, targets.rds_instance_id)
        rds_state = {
            "instance_id": targets.rds_instance_id,
            "status": info.get("DBInstanceStatus", "unknown"),
        }

    return {
        "cluster": targets.cluster,
        "ecs_services": ecs_state,
        "asgs": asg_state,
        "rds": rds_state,
    }


def save_state_file(path: Path, state: dict[str, Any], region: str) -> None:
    payload = {
        "region": region,
        "saved_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        **state,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"wrote state {path}")


def load_state_file(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise RuntimeError(
            f"State file not found: {path}. Run `cost_control.py stop` first, "
            "or pass --state-file with a saved snapshot."
        )
    return json.loads(path.read_text(encoding="utf-8"))


def set_ecs_desired(
    profile: str | None,
    region: str,
    cluster: str,
    service: str,
    desired: int,
    *,
    dry_run: bool = False,
) -> None:
    print(f"ecs {service}: desiredCount={desired}")
    aws_call(
        profile,
        region,
        "ecs",
        "update-service",
        args=[
            "--cluster",
            cluster,
            "--service",
            service,
            "--desired-count",
            str(desired),
        ],
        dry_run=dry_run,
    )


def clear_asg_scale_in_protection(
    profile: str | None, region: str, asg_name: str, *, dry_run: bool = False
) -> None:
    info = describe_asg(profile, region, asg_name)
    instance_ids = [
        inst["InstanceId"]
        for inst in info.get("Instances", [])
        if inst.get("ProtectedFromScaleIn")
    ]
    if not instance_ids:
        return
    print(f"asg {asg_name}: clearing scale-in protection on {len(instance_ids)} instance(s)")
    aws_call(
        profile,
        region,
        "autoscaling",
        "set-instance-protection",
        args=[
            "--auto-scaling-group-name",
            asg_name,
            "--instance-ids",
            *instance_ids,
            "--no-protected-from-scale-in",
        ],
        dry_run=dry_run,
    )


def set_asg_capacity(
    profile: str | None,
    region: str,
    asg_name: str,
    *,
    min_size: int,
    max_size: int,
    desired: int,
    dry_run: bool = False,
) -> None:
    print(f"asg {asg_name}: min={min_size} max={max_size} desired={desired}")
    aws_call(
        profile,
        region,
        "autoscaling",
        "update-auto-scaling-group",
        args=[
            "--auto-scaling-group-name",
            asg_name,
            "--min-size",
            str(min_size),
            "--max-size",
            str(max_size),
            "--desired-capacity",
            str(desired),
        ],
        dry_run=dry_run,
    )


def wait_ecs_services_stopped(
    profile: str | None,
    region: str,
    cluster: str,
    services: list[str],
    timeout_s: int = 600,
) -> None:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        running = 0
        for service in services:
            info = describe_ecs_service(profile, region, cluster, service)
            running += int(info.get("runningCount", 0))
        if running == 0:
            print("ecs: all services stopped")
            return
        print(f"ecs: waiting for tasks to stop ({running} running)...")
        time.sleep(15)
    raise RuntimeError("Timed out waiting for ECS tasks to stop")


def wait_rds_available(
    profile: str | None, region: str, instance_id: str, timeout_s: int = 900
) -> None:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        info = describe_rds(profile, region, instance_id)
        status = info.get("DBInstanceStatus", "unknown")
        print(f"rds {instance_id}: status={status}")
        if status == "available":
            return
        if status in {"failed", "incompatible-parameters"}:
            raise RuntimeError(f"RDS {instance_id} entered status {status}")
        time.sleep(20)
    raise RuntimeError(f"Timed out waiting for RDS {instance_id} to become available")


def cmd_stop(args: argparse.Namespace, targets: InfraTargets) -> int:
    state = capture_state(targets, args.profile, args.region)
    if not args.dry_run:
        save_state_file(args.state_file, state, args.region)

    for service in targets.ecs_services.values():
        set_ecs_desired(
            args.profile,
            args.region,
            targets.cluster,
            service,
            0,
            dry_run=args.dry_run,
        )

    if not args.dry_run:
        wait_ecs_services_stopped(
            args.profile,
            args.region,
            targets.cluster,
            list(targets.ecs_services.values()),
        )

    for asg_name in targets.asgs.values():
        clear_asg_scale_in_protection(args.profile, args.region, asg_name, dry_run=args.dry_run)
        set_asg_capacity(
            args.profile,
            args.region,
            asg_name,
            min_size=0,
            max_size=0,
            desired=0,
            dry_run=args.dry_run,
        )

    if args.include_rds and targets.rds_instance_id:
        info = describe_rds(args.profile, args.region, targets.rds_instance_id)
        status = info.get("DBInstanceStatus", "unknown")
        if status == "stopped":
            print(f"rds {targets.rds_instance_id}: already stopped")
        elif status == "available":
            print(f"rds {targets.rds_instance_id}: stopping")
            aws_call(
                args.profile,
                args.region,
                "rds",
                "stop-db-instance",
                args=["--db-instance-identifier", targets.rds_instance_id],
                dry_run=args.dry_run,
            )
        else:
            print(f"rds {targets.rds_instance_id}: skip stop (status={status})")

    print("stop complete")
    print("still billed: NAT Gateway, ALB, Elastic IPs, stopped RDS storage, etc.")
    return 0


def cmd_start(args: argparse.Namespace, targets: InfraTargets) -> int:
    state = load_state_file(args.state_file)
    if state.get("region") and state["region"] != args.region:
        print(
            f"warning: state region {state['region']} != CLI region {args.region}",
            file=sys.stderr,
        )

    rds_info = state.get("rds") or {}
    rds_id = (rds_info or {}).get("instance_id") or targets.rds_instance_id
    if args.include_rds and rds_id:
        info = describe_rds(args.profile, args.region, rds_id)
        status = info.get("DBInstanceStatus", "unknown")
        if status == "stopped":
            print(f"rds {rds_id}: starting")
            aws_call(
                args.profile,
                args.region,
                "rds",
                "start-db-instance",
                args=["--db-instance-identifier", rds_id],
                dry_run=args.dry_run,
            )
            if not args.dry_run:
                wait_rds_available(args.profile, args.region, rds_id)
        else:
            print(f"rds {rds_id}: skip start (status={status})")

    for asg_name, caps in (state.get("asgs") or {}).items():
        set_asg_capacity(
            args.profile,
            args.region,
            asg_name,
            min_size=int(caps.get("min", 0)),
            max_size=int(caps.get("max", 0)),
            desired=int(caps.get("desired", 0)),
            dry_run=args.dry_run,
        )

    if not args.dry_run and (state.get("asgs") or {}):
        print("waiting 90s for EC2 instances to register with ECS...")
        time.sleep(90)

    for service, desired in (state.get("ecs_services") or {}).items():
        set_ecs_desired(
            args.profile,
            args.region,
            targets.cluster,
            service,
            int(desired),
            dry_run=args.dry_run,
        )

    print("start complete — verify https://relaydesk.uk and place a test call")
    return 0


def cmd_status(args: argparse.Namespace, targets: InfraTargets) -> int:
    print(f"cluster: {targets.cluster}")
    for name, service in targets.ecs_services.items():
        info = describe_ecs_service(args.profile, args.region, targets.cluster, service)
        print(
            f"ecs {name} ({service}): "
            f"desired={info.get('desiredCount', 0)} running={info.get('runningCount', 0)}"
        )
    for name, asg_name in targets.asgs.items():
        info = describe_asg(args.profile, args.region, asg_name)
        print(
            f"asg {name} ({asg_name}): "
            f"min={info.get('MinSize', 0)} max={info.get('MaxSize', 0)} "
            f"desired={info.get('DesiredCapacity', 0)} "
            f"instances={len(info.get('Instances', []))}"
        )
    if targets.rds_instance_id:
        info = describe_rds(args.profile, args.region, targets.rds_instance_id)
        print(
            f"rds ({targets.rds_instance_id}): status={info.get('DBInstanceStatus', 'unknown')}"
        )
    if args.state_file.exists():
        state = load_state_file(args.state_file)
        print(f"saved state: {args.state_file} (saved_at={state.get('saved_at')})")
    else:
        print(f"saved state: {args.state_file} (not found)")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command",
        choices=["status", "stop", "start"],
        help="status: show current counts; stop: scale down; start: restore from state file",
    )
    parser.add_argument("--terraform-dir", type=Path, default=DEFAULT_TERRAFORM_DIR)
    parser.add_argument("--region", default=os.getenv("AWS_REGION", "ap-south-1"))
    parser.add_argument(
        "--profile",
        default=os.getenv("AWS_PROFILE"),
        help="AWS CLI profile (or set AWS_PROFILE).",
    )
    parser.add_argument(
        "--state-file",
        type=Path,
        default=DEFAULT_STATE_FILE,
        help="JSON file used to restore counts on start (default: infra/scripts/cost-control-state.json)",
    )
    parser.add_argument(
        "--include-rds",
        action="store_true",
        help="Also stop/start RDS PostgreSQL (saves storage; auto-starts after 7 days).",
    )
    parser.add_argument("--dry-run", action="store_true")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    if not args.profile:
        print("Set --profile or AWS_PROFILE.", file=sys.stderr)
        return 1

    targets = load_infra_targets(args.terraform_dir.resolve())

    if args.command == "status":
        return cmd_status(args, targets)
    if args.command == "stop":
        return cmd_stop(args, targets)
    if args.command == "start":
        return cmd_start(args, targets)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

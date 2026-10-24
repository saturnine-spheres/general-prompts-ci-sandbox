#!/usr/bin/env python3
"""Run one verifier tier from .assurance/verifiers.json and write a verification-result record.

Commands are argument vectors executed without a shell, optionally inside the tier's pinned
container image. The record follows schemas/verification-result.schema.json; the exit code is 0
only when the record's status is pass.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import pathlib
import platform
import secrets
import shutil
import subprocess
import sys
from typing import Any

sys.dont_write_bytecode = True  # keep installed .assurance/tools free of __pycache__

from validate_artifacts import content_sha256, read_json, schema_accepts, verification_semantic

TIERS = ("verify-fast", "verify", "verify-live", "verify-release")


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")


def git(root: pathlib.Path, *arguments: str) -> str | None:
    try:
        completed = subprocess.run(["git", *arguments], cwd=root, capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return completed.stdout if completed.returncode == 0 else None


def revision_identity(root: pathlib.Path) -> tuple[str, bool, list[str]]:
    """Return a sha256 revision identity, the dirty flag, and limitations."""
    commit = (git(root, "rev-parse", "HEAD") or "").strip()
    status = git(root, "status", "--porcelain")
    if not commit or status is None:
        return "sha256:" + hashlib.sha256(b"unversioned:" + str(root).encode("utf-8")).hexdigest(), True, [
            "No Git revision was available; the revision digest identifies the working directory path only."
        ]
    dirty = bool(status.strip())
    material = f"git-commit:{commit}"
    if dirty:
        material += "\n" + (git(root, "diff", "HEAD") or "") + status
    limitation = f"Revision digest is sha256 over Git commit {commit}" + (" plus the uncommitted diff." if dirty else ".")
    return "sha256:" + hashlib.sha256(material.encode("utf-8")).hexdigest(), dirty, [limitation]


def versioned_digest(path: pathlib.Path, version_key: str) -> dict[str, str]:
    version = "unknown"
    try:
        version = str(read_json(path).get(version_key, "unknown"))
    except (OSError, ValueError, AttributeError):
        pass
    digest = content_sha256(path) if path.is_file() else hashlib.sha256(b"missing").hexdigest()
    return {"version": version, "digest": f"sha256:{digest}"}


def wrap(argv: list[str], root: pathlib.Path, tier: dict[str, Any]) -> list[str]:
    container = tier["container"]
    if container is None:
        resolved = shutil.which(argv[0])
        return [resolved or argv[0], *argv[1:]]
    network = ["--network", "none"] if tier["network"] == "denied" else []
    return ["docker", "run", "--rm", *network, "-v", f"{root}:/work", "-w", "/work", container["image"], *argv]


def run(argv: list[str], root: pathlib.Path, timeout: int) -> tuple[str, int | None, str]:
    try:
        completed = subprocess.run(argv, cwd=root, capture_output=True, text=True, timeout=timeout)
    except FileNotFoundError:
        return "missing", None, f"executable not found: {argv[0]}"
    except subprocess.TimeoutExpired:
        return "timeout", None, f"timed out after {timeout} seconds"
    return "ran", completed.returncode, (completed.stdout or "") + (completed.stderr or "")


def main() -> int:
    script_root = pathlib.Path(__file__).resolve().parent.parent.parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tier", required=True, choices=TIERS)
    parser.add_argument("--root", type=pathlib.Path, default=script_root, help="repository root")
    args = parser.parse_args()

    root = args.root.resolve()
    assurance = root / ".assurance"
    config_path = assurance / "verifiers.json"
    schema_dir = assurance / "schemas"
    accepted, errors = schema_accepts(config_path, schema_dir / "verifier-config.schema.json")
    if not accepted:
        print("ERROR: .assurance/verifiers.json is invalid: " + "; ".join(errors[:5]), file=sys.stderr)
        return 2
    config = read_json(config_path)
    tier = config["tiers"].get(args.tier)
    if tier is None:
        print(f"ERROR: tier {args.tier} is not configured in .assurance/verifiers.json", file=sys.stderr)
        return 2

    revision, dirty, limitations = revision_identity(root)
    started = utc_now()
    checks: list[dict[str, Any]] = []
    for check in tier["checks"]:
        check_started = utc_now()
        version_state, _code, version_output = run(wrap(check["version_command"], root, tier), root, 60)
        version = version_output.strip().splitlines()[0][:200] if version_state == "ran" and version_output.strip() else "unknown"
        state, code, output = run(wrap(check["command"], root, tier), root, check["timeout_seconds"])
        check_limitations: list[str] = []
        if state != "ran":
            status = "error"
            check_limitations.append(output)
        elif code != 0:
            status = "fail"
            check_limitations.append(f"exit code {code}: " + output.strip()[-400:])
        elif check["fail_on_output"] and output.strip():
            status = "fail"
            check_limitations.append("command printed findings: " + output.strip()[-400:])
        else:
            status = "pass"
        checks.append({
            "id": check["id"],
            "control_ids": check["control_ids"],
            "command": " ".join(check["command"]),
            "tool": {"id": check["command"][0], "version": version, "digest": "not-applicable:unpinned-local-tool"},
            "started_at": check_started,
            "completed_at": utc_now(),
            "status": status,
            "blocking": check["blocking"],
            "attempts": 1,
            "evidence": [],
            "limitations": check_limitations,
        })
        print(f"{status.upper():5} {check['id']}")

    blocking = [item for item in checks if item["blocking"]]
    if any(item["status"] == "error" for item in blocking):
        overall = "error"
    elif any(item["status"] != "pass" for item in blocking):
        overall = "fail"
    else:
        overall = "pass"
    container = tier["container"]
    record = {
        "schema_version": "1.0.0",
        "result_id": "VER-" + dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + secrets.token_hex(4).upper(),
        "project": config["project"],
        "revision": revision,
        "dirty": dirty,
        "tier": args.tier,
        "command": f".assurance/tools/{args.tier} (run_verifier.py --tier {args.tier})",
        "started_at": started,
        "completed_at": utc_now(),
        "runner": {
            "identity": "local:" + (platform.node() or "unknown-host"),
            "environment": f"container:{container['image']}" if container else "host",
            "os": f"{platform.system()}-{platform.release()}".lower(),
            "architecture": platform.machine() or "unknown",
            "network_policy": tier["network"] if container else f"{tier['network']} (declared; not enforced on the host)",
        },
        "profile": versioned_digest(assurance / "project-assurance-profile.json", "profile_version"),
        "catalog": versioned_digest(assurance / "control-catalog.yaml", "catalog_version"),
        "status": overall,
        "checks": checks,
        "unrun_checks": [],
        "limitations": limitations + ["Generated by the general-prompts verifier starter; tools are unpinned until the project records versions and digests."],
        "attachments": [],
    }
    output_path = root / pathlib.PurePosixPath(tier["output"])
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    valid, problems = schema_accepts(output_path, schema_dir / "verification-result.schema.json")
    if not valid or not verification_semantic(record):
        print("ERROR: generated verification result failed validation: " + "; ".join(problems[:5]), file=sys.stderr)
        return 2
    print(f"{overall.upper()}: {args.tier}; record: {tier['output']}")
    return 0 if overall == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())

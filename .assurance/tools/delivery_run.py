#!/usr/bin/env python3
"""Record one delivery run under .assurance/runs/<run-id>/ following the process contract.

Harness- and forge-neutral: a harness adapter (for example the Claude Code /deliver skill) or a
person calls these subcommands as the run moves through its stages.

  start        create the run and its manifest (status running) and record the intake stage
  plan-tier    compute the tier for planned paths before build; significant runs wait for approval
  stage        record one stage outcome; refuses a stage beyond the contract's rework limit
  approve      record a human approval (run it yourself; agent hooks refuse it)
  sentinels    measure the run sentinels a local run can measure and write them for the verifier
  status       set awaiting_approval, running, blocked, failed, or cancelled
  finish       recompute the tier from the actual diff, collect artifact digests, and validate
  show         print the manifest

The manifest conforms to schemas/run-manifest.schema.json and is committed with the change.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import pathlib
import re
import secrets
import subprocess
import sys
from typing import Any

sys.dont_write_bytecode = True  # keep installed .assurance/tools free of __pycache__

from assurance_gate import EVIDENCE_PREFIXES, RANK, TIERS, changed_files, classify, classify_changes, files_at, matches  # noqa: E402
from validate_artifacts import content_sha256, read_json, run_manifest_semantic, validate_instance  # noqa: E402

RUNS = ".assurance/runs"
SECRET_PATTERNS = [
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{36,}\b"),
    re.compile(r"\bglpat-[A-Za-z0-9_-]{20,}\b"),
    re.compile(r"\bxox[abpr]-[A-Za-z0-9-]{10,}\b"),
    re.compile(r"\bsk-(?:ant-)?[A-Za-z0-9_-]{32,}\b"),
]


def now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def git(root: pathlib.Path, *arguments: str) -> str:
    completed = subprocess.run(["git", "-C", str(root), *arguments], capture_output=True, text=True, encoding="utf-8", errors="replace")
    if completed.returncode != 0:
        raise SystemExit(f"ERROR: git {' '.join(arguments)} failed: {completed.stderr.strip()}")
    return completed.stdout.strip()


def uncommitted(root: pathlib.Path) -> list[str]:
    """Paths with uncommitted changes, untracked files listed individually (porcelain lines keep their leading space)."""
    completed = subprocess.run(["git", "-C", str(root), "status", "--porcelain", "--untracked-files=all"], capture_output=True, text=True, encoding="utf-8", errors="replace")
    return [line[3:] for line in completed.stdout.splitlines() if line.strip()]


def default_base(root: pathlib.Path) -> str:
    for candidate in ("origin/HEAD", "origin/main", "origin/master", "main", "master"):
        probe = subprocess.run(["git", "-C", str(root), "rev-parse", "--verify", f"{candidate}^{{commit}}"], capture_output=True, text=True)
        if probe.returncode == 0:
            return git(root, "merge-base", "HEAD", candidate)
    return git(root, "rev-parse", "HEAD")


def manifest_path(root: pathlib.Path, run_id: str) -> pathlib.Path:
    if not re.fullmatch(r"RUN-[A-Z0-9-]{8,}", run_id):
        raise SystemExit(f"ERROR: invalid run ID {run_id!r}")
    return root / RUNS / run_id / "run-manifest.json"


def load(root: pathlib.Path, run_id: str) -> dict[str, Any]:
    path = manifest_path(root, run_id)
    if not path.is_file():
        raise SystemExit(f"ERROR: run {run_id} not found at {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def save(root: pathlib.Path, manifest: dict[str, Any]) -> pathlib.Path:
    schema = read_json(root / ".assurance/schemas/run-manifest.schema.json")
    errors = validate_instance(manifest, schema, schema)
    if errors:
        raise SystemExit("ERROR: run manifest would be invalid: " + "; ".join(errors[:5]))
    path = manifest_path(root, manifest["run_id"])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def profile_of(root: pathlib.Path) -> dict[str, Any] | None:
    path = root / ".assurance/project-assurance-profile.json"
    return read_json(path) if path.is_file() else None


def process_of(root: pathlib.Path) -> dict[str, Any]:
    path = root / ".assurance/process.json"
    if not path.is_file():
        raise SystemExit("ERROR: .assurance/process.json is missing")
    return read_json(path)


def declared_scope(text: str) -> list[str]:
    """Path patterns from the work item's 'Filesystem scope' line (backticked globs)."""
    line = re.search(r"^- Filesystem scope:\s*(.+)$", text, re.M)
    if not line:
        return []
    paths = []
    for item in re.findall(r"`([^`]+)`", line.group(1)):
        if re.search(r"REPLACE|\[[A-Z]", item):
            continue
        # Tolerate several paths in one backtick pair and wrappers such as "[read/write a.go, b.go]".
        for token in re.split(r"[,\s]+", item.strip().strip("[]()")):
            token = token.strip("[]()'\"")
            if token and token.lower() not in {"read", "write", "read/write", "rw", "only", "if", "and", "or"} and re.search(r"[/.*]", token):
                paths.append(token.removeprefix("./"))
    return paths


def cmd_start(root: pathlib.Path, args: argparse.Namespace) -> int:
    work_item = root / args.work_item
    if not work_item.is_file():
        raise SystemExit(f"ERROR: work item {args.work_item} does not exist")
    process = process_of(root)
    run_id = "RUN-" + dt.datetime.now(dt.timezone.utc).strftime("%Y%m%d-%H%M%S") + "-" + secrets.token_hex(2).upper()
    base = args.base or default_base(root)
    manifest = {
        "schema_version": "1.0.0", "run_id": run_id,
        "specification": {"work_item": args.work_item, "source": args.source, "digest": f"sha256:{content_sha256(work_item)}"},
        "process_contract": {"version": process["contract_version"], "digest": f"sha256:{content_sha256(root / '.assurance/process.json')}"},
        "computed_tier": "routine", "approved_tier": "routine", "status": "running",
        "started_at": now(), "completed_at": None,
        "base_revision": git(root, "rev-parse", base),
        "stages": [{"stage": "intake", "runner": {"identity": args.runner, "kind": args.kind, "context_id": args.context}, "model": args.model,
                    "started_at": now(), "completed_at": now(), "duration_seconds": 0.0, "cost": {"currency": "EUR", "amount": 0.0},
                    "attempts": 1, "outcome": "pass"}],
        "artifacts": [], "approvals": [],
    }
    path = save(root, manifest)
    print(run_id)
    print(f"run started: {path.relative_to(root).as_posix()} (base {manifest['base_revision'][:12]})", file=sys.stderr)
    return 0


def cmd_plan_tier(root: pathlib.Path, args: argparse.Namespace) -> int:
    manifest = load(root, args.run)
    changes = [(path, args.lines // max(len(args.path), 1)) for path in args.path]
    result = classify_changes(changes, profile_of(root), lambda: files_at(root, "HEAD"))
    manifest["computed_tier"] = result["tier"]
    manifest["approved_tier"] = TIERS[max(RANK[result["tier"]], RANK[manifest["approved_tier"]])]
    rule = process_of(root)["approvals"][result["tier"]]
    if rule["run_approval_required"] and not approvals_satisfied(manifest, result["tier"], rule["minimum_approvals"]):
        manifest["status"] = "awaiting_approval"
    save(root, manifest)
    print(json.dumps({"tier": result["tier"], "reasons": result["reasons"], "status": manifest["status"],
                      "approval_required": rule["run_approval_required"], "before_stage": rule["before_stage"]}, indent=2))
    return 0


def approvals_satisfied(manifest: dict[str, Any], tier: str, minimum: int) -> bool:
    granted = {item["identity"] for item in manifest["approvals"] if item["decision"] == "approve" and RANK[item["tier"]] >= RANK[tier]}
    return len(granted) >= minimum


def cmd_stage(root: pathlib.Path, args: argparse.Namespace) -> int:
    manifest = load(root, args.run)
    process = process_of(root)
    known = {stage["id"] for stage in process["stages"]}
    if args.stage not in known:
        raise SystemExit(f"ERROR: stage {args.stage!r} is not in the process contract ({', '.join(sorted(known))})")
    if manifest["status"] == "awaiting_approval" and args.stage not in {"intake", "specify", "tier-check", "approval"}:
        raise SystemExit("ERROR: the run is waiting for the human approval its tier requires; build cannot start")
    previous = [stage for stage in manifest["stages"] if stage["stage"] == args.stage]
    attempts = (previous[-1]["attempts"] + 1) if previous else 1
    if attempts > process["rework_limit"] + 1:
        raise SystemExit(f"ERROR: stage {args.stage} would exceed the rework limit ({process['rework_limit']}); stop and ask the owner "
                         "whether the approach is wrong (two-strike rule), then mark the run blocked")
    finished = now()
    manifest["stages"] = [stage for stage in manifest["stages"] if stage["stage"] != args.stage]
    manifest["stages"].append({
        "stage": args.stage,
        "runner": {"identity": args.runner, "kind": args.kind, "context_id": args.context},
        "model": args.model, "started_at": args.started or finished, "completed_at": finished,
        "duration_seconds": args.duration, "cost": {"currency": args.currency, "amount": args.cost},
        "attempts": attempts, "outcome": args.outcome,
    })
    save(root, manifest)
    print(f"stage {args.stage}: {args.outcome} (attempt {attempts})")
    return 0


def cmd_approve(root: pathlib.Path, args: argparse.Namespace) -> int:
    manifest = load(root, args.run)
    if args.identity.lower().startswith("agent:"):
        raise SystemExit("ERROR: approvals are human decisions; an agent identity cannot approve")
    manifest["approvals"].append({"identity": args.identity, "kind": "human", "role": args.role, "tier": args.tier,
                                  "decision": args.decision, "decided_at": now(), "reference": args.reference})
    rule = process_of(root)["approvals"][manifest["approved_tier"]]
    if manifest["status"] == "awaiting_approval" and args.decision == "approve" and approvals_satisfied(manifest, manifest["approved_tier"], rule["minimum_approvals"]):
        manifest["status"] = "running"
    if args.decision == "reject":
        manifest["status"] = "cancelled"
        manifest["completed_at"] = now()
    save(root, manifest)
    print(f"{args.decision} recorded for {args.identity}; run status {manifest['status']}")
    return 0


def cmd_sentinels(root: pathlib.Path, args: argparse.Namespace) -> int:
    manifest = load(root, args.run)
    base = manifest.get("base_revision") or default_base(root)
    changes = [path for path, _lines in changed_files(root, base, "HEAD") if not path.startswith(EVIDENCE_PREFIXES)]
    touched = sorted(set(changes) | {path for path in uncommitted(root) if not path.startswith(EVIDENCE_PREFIXES)})
    sentinels: list[dict[str, Any]] = []

    hits = 0
    for path in touched:
        file = root / path
        if file.is_file() and file.stat().st_size < 2_000_000:
            text = file.read_text(encoding="utf-8", errors="ignore")
            hits += sum(len(pattern.findall(text)) for pattern in SECRET_PATTERNS)
    sentinels.append({"name": "secret patterns in changed files", "kind": "secret_findings", "comparison": "equals", "expected": 0, "observed": hits,
                      "outcome": "pass" if hits == 0 else "fail"})

    scope = declared_scope((root / manifest["specification"]["work_item"]).read_text(encoding="utf-8"))
    if scope:
        allowed = scope + [manifest["specification"]["work_item"]]
        outside = [path for path in touched if not matches(path, allowed)]
        sentinels.append({"name": "writes outside the work item's filesystem scope", "kind": "writes_outside_declared_paths", "comparison": "equals",
                          "expected": 0, "observed": len(outside), "outcome": "pass" if not outside else "fail"})
        if outside:
            print("outside declared scope: " + ", ".join(outside[:20]), file=sys.stderr)
    else:
        sentinels.append({"name": "writes outside the work item's filesystem scope", "kind": "writes_outside_declared_paths", "comparison": "equals",
                          "expected": 0, "observed": None, "outcome": "not_measured"})
        print("work item has no 'Filesystem scope' line with backticked paths; writes are not measured", file=sys.stderr)

    costs = [stage["cost"]["amount"] for stage in manifest["stages"]]
    profile = profile_of(root) or {}
    budget = ((profile.get("human_involvement") or {}).get("tier_rules") or {}).get("run_budget")
    if budget and args.costs_recorded:
        spent = round(sum(costs), 4)
        sentinels.append({"name": "run spend", "kind": "spend", "comparison": "at_most", "expected": budget["amount"], "observed": spent,
                          "outcome": "pass" if spent <= budget["amount"] else "fail"})
    output = root / pathlib.PurePosixPath(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(sentinels, indent=2) + "\n", encoding="utf-8")
    for sentinel in sentinels:
        print(f"{sentinel['outcome'].upper():12} {sentinel['kind']}: observed {sentinel['observed']} expected {sentinel['expected']}")
    return 0 if all(sentinel["outcome"] == "pass" for sentinel in sentinels) else 1


def cmd_status(root: pathlib.Path, args: argparse.Namespace) -> int:
    manifest = load(root, args.run)
    manifest["status"] = args.status
    if args.status in {"blocked", "failed", "cancelled"}:
        manifest["completed_at"] = now()
    save(root, manifest)
    print(f"run {args.run}: {args.status}")
    return 0


def cmd_finish(root: pathlib.Path, args: argparse.Namespace) -> int:
    manifest = load(root, args.run)
    base = manifest.get("base_revision") or default_base(root)
    actual = classify(root, base, "HEAD", profile_of(root))
    manifest["computed_tier"] = actual["tier"]
    artifacts = [{"type": "work_item", "uri": manifest["specification"]["work_item"],
                  "digest": f"sha256:{content_sha256(root / manifest['specification']['work_item'])}"}]
    kinds = {".assurance/evidence/": "verification_result", ".assurance/reviews/": "review_record", ".assurance/waivers/": "waiver"}
    for path in sorted({path for path, _lines in changed_files(root, base, "HEAD")} | set(uncommitted(root))):
        kind = next((value for prefix, value in kinds.items() if path.startswith(prefix)), None)
        if kind and path.endswith(".json") and (root / path).is_file():
            artifacts.append({"type": kind, "uri": path, "digest": f"sha256:{content_sha256(root / path)}"})
    manifest["artifacts"] = artifacts
    manifest["status"] = args.status
    manifest["completed_at"] = now()
    started = dt.datetime.fromisoformat(manifest["started_at"].replace("Z", "+00:00"))
    manifest["totals"] = {"duration_seconds": round((dt.datetime.now(dt.timezone.utc) - started).total_seconds(), 1),
                          "cost": {"currency": manifest["stages"][0]["cost"]["currency"] if manifest["stages"] else "EUR",
                                   "amount": round(sum(stage["cost"]["amount"] for stage in manifest["stages"]), 4)}}
    if args.status == "succeeded" and not run_manifest_semantic(manifest):
        problems = []
        if RANK[manifest["approved_tier"]] < RANK[manifest["computed_tier"]]:
            problems.append(f"actual tier {manifest['computed_tier']} is higher than the approved tier {manifest['approved_tier']}; get approval for the higher tier")
        problems += [f"stage {stage['stage']} is {stage['outcome']}" for stage in manifest["stages"] if stage["outcome"] not in {"pass", "not_required"}]
        if manifest["approved_tier"] == "significant" and not approvals_satisfied(manifest, "significant", 1):
            problems.append("significant run lacks a recorded human approval")
        raise SystemExit("ERROR: the run cannot be marked succeeded: " + "; ".join(problems or ["run manifest semantics failed"]))
    save(root, manifest)
    print(f"run {args.run}: {args.status}; actual tier {actual['tier']} ({'; '.join(actual['reasons'])})")
    return 0


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--root", type=pathlib.Path, default=pathlib.Path(__file__).resolve().parent.parent.parent)
    sub = parser.add_subparsers(dest="command", required=True)
    start = sub.add_parser("start")
    start.add_argument("--work-item", required=True)
    start.add_argument("--source", required=True, help="issue, ticket, or request reference")
    start.add_argument("--base", help="target branch commit; default: merge base with the remote default branch")
    start.add_argument("--runner", default="agent:unrecorded", help="who ran intake; recorded as the intake stage")
    start.add_argument("--kind", default="agent", choices=("agent", "human", "automated_service"))
    start.add_argument("--context", default="unrecorded-context")
    start.add_argument("--model", default="none")
    plan = sub.add_parser("plan-tier")
    plan.add_argument("--run", required=True)
    plan.add_argument("--path", action="append", required=True, help="planned path; repeatable")
    plan.add_argument("--lines", type=int, required=True, help="estimated changed lines in total")
    stage = sub.add_parser("stage")
    stage.add_argument("--run", required=True)
    stage.add_argument("--stage", required=True)
    stage.add_argument("--outcome", required=True, choices=("pass", "fail", "blocked", "not_run", "not_required"))
    stage.add_argument("--runner", required=True)
    stage.add_argument("--kind", default="agent", choices=("agent", "human", "automated_service"))
    stage.add_argument("--context", default="unrecorded-context")
    stage.add_argument("--model", default="none")
    stage.add_argument("--started")
    stage.add_argument("--duration", type=float, default=0.0)
    stage.add_argument("--cost", type=float, default=0.0)
    stage.add_argument("--currency", default="EUR")
    approve = sub.add_parser("approve")
    approve.add_argument("--run", required=True)
    approve.add_argument("--identity", required=True)
    approve.add_argument("--role", required=True)
    approve.add_argument("--tier", required=True, choices=TIERS)
    approve.add_argument("--decision", default="approve", choices=("approve", "reject"))
    approve.add_argument("--reference", default="recorded in the delivery session")
    sentinels = sub.add_parser("sentinels")
    sentinels.add_argument("--run", required=True)
    sentinels.add_argument("--output", required=True, help="path under the repository for the sentinel list")
    sentinels.add_argument("--costs-recorded", action="store_true", help="stage costs are real, so measure spend against the run budget")
    status = sub.add_parser("status")
    status.add_argument("--run", required=True)
    status.add_argument("--status", required=True, choices=("awaiting_approval", "running", "blocked", "failed", "cancelled"))
    finish = sub.add_parser("finish")
    finish.add_argument("--run", required=True)
    finish.add_argument("--status", default="succeeded", choices=("succeeded", "failed", "blocked"))
    show = sub.add_parser("show")
    show.add_argument("--run", required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    if args.command == "show":
        print(json.dumps(load(root, args.run), indent=2))
        return 0
    return {"start": cmd_start, "plan-tier": cmd_plan_tier, "stage": cmd_stage, "approve": cmd_approve, "sentinels": cmd_sentinels,
            "status": cmd_status, "finish": cmd_finish}[args.command](root, args)


if __name__ == "__main__":
    raise SystemExit(main())

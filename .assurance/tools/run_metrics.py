#!/usr/bin/env python3
"""Aggregate delivery run manifests into team metrics (design section 8.4). Forge-neutral.

Reads every .assurance/runs/*/run-manifest.json at the given Git revisions (default: all local and remote
branches), deduplicated by run ID with the most advanced status, and reports acceptance rate, human minutes,
cost, cycle time, and escalation rate as JSON (and a short text summary).
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import pathlib
import statistics
import subprocess
import sys
from typing import Any

ORDER = {"running": 0, "awaiting_approval": 1, "blocked": 2, "failed": 2, "cancelled": 2, "succeeded": 3}


def git(root: pathlib.Path, *argv: str) -> str:
    completed = subprocess.run(["git", "-C", str(root), *argv], capture_output=True, text=True, encoding="utf-8", errors="replace")
    return completed.stdout if completed.returncode == 0 else ""


def manifests(root: pathlib.Path, refs: list[str]) -> dict[str, dict[str, Any]]:
    found: dict[str, dict[str, Any]] = {}
    for ref in refs:
        for path in git(root, "ls-tree", "-r", "--name-only", ref, "--", ".assurance/runs").splitlines():
            if not path.endswith("/run-manifest.json"):
                continue
            try:
                value = json.loads(git(root, "show", f"{ref}:{path}"))
            except ValueError:
                continue
            current = found.get(value["run_id"])
            if current is None or ORDER.get(value["status"], 0) > ORDER.get(current["status"], 0):
                found[value["run_id"]] = value
    return found


def seconds(start: str, end: str | None) -> float | None:
    if not end:
        return None
    parse = lambda value: dt.datetime.fromisoformat(value.replace("Z", "+00:00"))  # noqa: E731
    return (parse(end) - parse(start)).total_seconds()


def summarize(runs: dict[str, dict[str, Any]]) -> dict[str, Any]:
    values = list(runs.values())
    finished = [run for run in values if run["status"] in {"succeeded", "failed", "blocked", "cancelled"}]
    succeeded = [run for run in finished if run["status"] == "succeeded"]
    escalated = [run for run in values if run["approved_tier"] == "significant" or run["status"] in {"blocked", "failed"}
                 or any(stage["runner"]["kind"] == "human" for stage in run["stages"])]
    cycle = [value for value in (seconds(run["started_at"], run["completed_at"]) for run in succeeded) if value is not None]
    human_minutes = sum(stage["duration_seconds"] for run in values for stage in run["stages"] if stage["runner"]["kind"] == "human") / 60
    cost = sum(stage["cost"]["amount"] for run in values for stage in run["stages"])
    return {
        "runs": len(values),
        "by_status": {status: sum(1 for run in values if run["status"] == status) for status in sorted({run["status"] for run in values})},
        "by_tier": {tier: sum(1 for run in values if run["computed_tier"] == tier) for tier in ("routine", "notable", "significant")},
        "acceptance_rate": round(len(succeeded) / len(finished), 3) if finished else None,
        "escalation_rate": round(len(escalated) / len(values), 3) if values else None,
        "human_minutes": round(human_minutes, 1),
        "cost": round(cost, 4),
        "cycle_time_median_minutes": round(statistics.median(cycle) / 60, 1) if cycle else None,
        "note": "Acceptance counts runs that reached a pull or merge request; whether a person merged it is tracked on the forge.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--root", type=pathlib.Path, default=pathlib.Path.cwd())
    parser.add_argument("--ref", action="append", help="revision to read; repeatable (default: every branch)")
    parser.add_argument("--json", action="store_true", help="print JSON only")
    args = parser.parse_args()
    root = args.root.resolve()
    refs = args.ref or [line.strip() for line in git(root, "for-each-ref", "--format=%(refname)", "refs/heads", "refs/remotes").splitlines() if line.strip()] or ["HEAD"]
    result = summarize(manifests(root, refs))
    if args.json:
        print(json.dumps(result, indent=2))
        return 0
    print(json.dumps(result, indent=2))
    rate = "n/a" if result["acceptance_rate"] is None else f"{result['acceptance_rate']:.0%}"
    print(f"{result['runs']} run(s); acceptance {rate}; escalations {result['escalation_rate']}; human minutes {result['human_minutes']}; cost {result['cost']}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

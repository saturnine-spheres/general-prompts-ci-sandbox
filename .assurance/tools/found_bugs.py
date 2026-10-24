#!/usr/bin/env python3
"""Handle bugs a delivery run found outside its work (design section 8.6). Forge-neutral.

  process --run ID [--candidates FILE] [--forge github|gitlab|none]

The builder and reviewer write candidates to .assurance/runs/<run>/found-bugs.json, a JSON list of
  {"summary", "path", "start_line", "end_line", "evidence", "severity": low|medium|high|critical,
   "security": bool, "blocking": bool, "fixed": bool, "reproduces_on_base": bool, "certain": bool,
   "found_by": builder|reviewer}
This tool classifies each one by evidence, not by the agent's say-so: a finding is pre-existing when it
reproduces on the run's base commit or its lines are not in the run's diff. It applies the rule table:

  introduced by this run                      fixed in the run (else the run is blocked)
  pre-existing, fixed, inside the work scope  fixed in scope, recorded, no ticket
  pre-existing, blocking, out of scope        ticket; the run is blocked unless the candidate notes a safe workaround
  pre-existing, unrelated, not blocking       ticket, not fixed
  uncertain                                   observation in the run report, no ticket

Tickets go through the forge adapter (<forge>_forge.py report-bug), which comments on a matching open
issue instead of filing a duplicate, and labels new ones agent-found and needs-triage with no assignee or
priority. At most ticket_automation.found_bugs.max_tickets_per_run tickets (default 3); the rest become
observations. Security findings never go to a public ticket: the adapter may open a private advisory;
otherwise the finding is withheld from committed records and its details stay in .git/ on the runner.
Every finding is recorded in the run manifest's findings array. Prints a JSON summary.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import re
import subprocess
import sys
import tempfile
from typing import Any

sys.dont_write_bytecode = True  # keep installed .assurance/tools free of __pycache__

from delivery_run import declared_scope, git, load, save  # noqa: E402
from assurance_gate import matches  # noqa: E402
from validate_artifacts import findings_semantic, read_json  # noqa: E402

TOOLS = pathlib.Path(__file__).resolve().parent
SEVERITIES = {"low", "medium", "high", "critical"}


def added_ranges(root: pathlib.Path, base: str, path: str) -> list[tuple[int, int]]:
    """Line ranges the run added or changed in path, from git diff -U0 against the run base."""
    diff = subprocess.run(["git", "-C", str(root), "diff", "-U0", base, "HEAD", "--", path], capture_output=True, text=True,
                          encoding="utf-8", errors="replace").stdout
    ranges = []
    for start, count in re.findall(r"^@@ -\S+ \+(\d+)(?:,(\d+))? @@", diff, re.M):
        length = int(count) if count != "" else 1
        if length:
            ranges.append((int(start), int(start) + length - 1))
    return ranges


def fingerprint(path: str, summary: str) -> str:
    words = " ".join(re.findall(r"[a-z0-9]+", summary.lower()))
    return hashlib.sha256(f"{path}\n{words}".encode()).hexdigest()[:16]


def classify(candidate: dict[str, Any], in_diff: bool, in_scope: bool) -> str:
    if not candidate.get("certain", True):
        return "uncertain"
    if in_diff and not candidate.get("reproduces_on_base"):
        return "introduced"
    if candidate.get("fixed") and in_scope:
        return "in_scope_preexisting"
    return "blocking_out_of_scope" if candidate.get("blocking") else "unrelated"


def forge_call(root: pathlib.Path, forge: str, *argv: str) -> dict[str, Any] | None:
    helper = root / f".assurance/tools/{forge}_forge.py"
    if forge == "none" or not helper.is_file():
        return None
    completed = subprocess.run([sys.executable, str(helper), *argv], cwd=root, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120)
    if completed.returncode != 0:
        print(f"{forge} adapter {argv[0]} failed: {(completed.stderr or completed.stdout).strip()[-300:]}", file=sys.stderr)
        return None
    try:
        return json.loads(completed.stdout.strip().splitlines()[-1])
    except (ValueError, IndexError):
        return None


def ticket_body(candidate: dict[str, Any], commit: str, run_id: str, mark: str) -> str:
    return (f"{candidate['summary']}\n\n"
            f"- **Location:** `{candidate['path']}` lines {candidate['start_line']}-{candidate['end_line']} at commit `{commit}`\n"
            f"- **Reproduction or failing test:** {candidate['evidence']}\n"
            f"- **Severity guess:** {candidate['severity']}\n"
            f"- **Found by:** delivery run `{run_id}` ({candidate.get('found_by', 'builder')}); the run did not change this code.\n\n"
            "Filed automatically from a delivery run; a person triages it.\n\n"
            f"<!-- assurance-finding: {mark} -->\n")


def cmd_process(root: pathlib.Path, args: argparse.Namespace) -> int:
    manifest = load(root, args.run)
    path = pathlib.Path(args.candidates) if args.candidates else root / f".assurance/runs/{args.run}/found-bugs.json"
    candidates = read_json(path) if path.is_file() else []
    if not isinstance(candidates, list):
        raise SystemExit(f"ERROR: {path} must hold a JSON list")
    profile_path = root / ".assurance/project-assurance-profile.json"
    automation = (read_json(profile_path) if profile_path.is_file() else {}).get("ticket_automation") or {}
    policy = automation.get("found_bugs") or {"enabled": True, "max_tickets_per_run": 3}
    cap = policy["max_tickets_per_run"] if policy.get("enabled", True) else 0
    base = manifest["base_revision"]
    head = git(root, "rev-parse", "HEAD")
    work_item = root / manifest["specification"]["work_item"]
    scope = declared_scope(work_item.read_text(encoding="utf-8")) if work_item.is_file() else []
    findings = list(manifest.get("findings", []))
    summary: dict[str, Any] = {"tickets": [], "observations": 0, "withheld": 0, "blocked": []}
    filed = 0
    seen: dict[str, str] = {}
    private: list[dict[str, Any]] = []
    for candidate in candidates:
        try:
            start, end = int(candidate["start_line"]), int(candidate["end_line"])
            candidate_path = str(candidate["path"]).replace("\\", "/").removeprefix("./")
            text_summary, evidence = str(candidate["summary"]).strip(), str(candidate["evidence"]).strip()
        except (KeyError, TypeError, ValueError):
            print(f"skipped malformed candidate: {str(candidate)[:200]}", file=sys.stderr)
            continue
        if not text_summary or not evidence or start < 1 or end < start:
            print(f"skipped incomplete candidate: {text_summary[:120]}", file=sys.stderr)
            continue
        candidate.update({"path": candidate_path, "summary": text_summary, "evidence": evidence})
        severity = candidate.get("severity") if candidate.get("severity") in SEVERITIES else "medium"
        candidate["severity"] = severity
        in_diff = any(start <= high and low <= end for low, high in added_ranges(root, base, candidate_path))
        classification = classify(candidate, in_diff, matches(candidate_path, scope))
        commit = head if classification == "introduced" else base
        security = bool(candidate.get("security"))
        ticket = None
        record_summary, record_evidence = text_summary, evidence
        if classification == "uncertain":
            action = "observation"
        elif classification == "introduced":
            action = "fixed" if candidate.get("fixed") else "blocked"
            if action == "blocked":
                summary["blocked"].append(f"a bug this run introduced is not fixed: {text_summary[:120]}")
        elif classification == "in_scope_preexisting":
            action = "fixed_in_scope"
        elif security:
            mark = fingerprint(candidate_path, text_summary)
            with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False, encoding="utf-8") as handle:
                handle.write(ticket_body(candidate, commit, args.run, mark))
            result = forge_call(root, args.forge, "advisory", "--summary", text_summary[:200], "--body-file", handle.name, "--severity", severity)
            pathlib.Path(handle.name).unlink()
            if result and result.get("url"):
                action, ticket = "private_advisory", result["url"]
            else:
                action = "withheld"
                summary["withheld"] += 1
                private.append({**candidate, "commit": commit, "run": args.run})
            record_summary, record_evidence = "Security finding withheld from public records.", "Details are kept out of committed records and public tickets."
        elif fingerprint(candidate_path, text_summary) in seen:
            action, ticket = "commented_existing", seen[fingerprint(candidate_path, text_summary)]  # the same finding twice in one run
        elif filed < cap:
            mark = fingerprint(candidate_path, text_summary)
            with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False, encoding="utf-8") as handle:
                handle.write(ticket_body(candidate, commit, args.run, mark))
            result = forge_call(root, args.forge, "report-bug", "--title", text_summary[:120], "--body-file", handle.name,
                                "--fingerprint", mark, "--path", candidate_path)
            pathlib.Path(handle.name).unlink()
            if result and result.get("url"):
                action, ticket = result.get("action", "ticket_filed"), result["url"]
                filed += 1
                seen[mark] = ticket
                summary["tickets"].append(ticket)
            else:
                action = "observation" if classification == "unrelated" else "blocked"
        else:
            action = "observation" if classification == "unrelated" else "blocked"
        if classification == "blocking_out_of_scope" and not candidate.get("workaround") and action != "blocked":
            summary["blocked"].append(f"blocked by a pre-existing bug outside the work item's scope: {ticket or text_summary[:120]}")
        elif action == "blocked" and classification == "blocking_out_of_scope":
            summary["blocked"].append(f"blocked by a pre-existing bug outside the work item's scope, and no ticket could be filed: {text_summary[:120]}")
        if action == "observation":
            summary["observations"] += 1
        findings.append({"id": f"F-{len(findings) + 1}", "classification": classification, "summary": record_summary,
                         "location": {"path": candidate_path, "start_line": start, "end_line": end, "commit": commit},
                         "evidence": record_evidence, "severity": severity, "security": security,
                         "found_by": candidate.get("found_by") if candidate.get("found_by") in {"builder", "reviewer", "gate"} else "builder",
                         "action": action, "ticket": ticket})
    if not findings_semantic(findings):
        raise SystemExit("ERROR: findings would break the design 8.6 rule table")
    if findings:
        manifest["findings"] = findings
        save(root, manifest)
    if private:
        (root / ".git/assurance-security-findings.json").write_text(json.dumps(private, indent=2), encoding="utf-8")
    if path.is_file() and not args.candidates:
        path.unlink()  # the manifest is the record; candidates may hold withheld security details
    print(json.dumps(summary))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--root", type=pathlib.Path, default=pathlib.Path.cwd())
    sub = parser.add_subparsers(dest="command", required=True)
    process = sub.add_parser("process")
    process.add_argument("--run", required=True)
    process.add_argument("--candidates")
    process.add_argument("--forge", default="none")
    args = parser.parse_args()
    return cmd_process(args.root.resolve(), args)


if __name__ == "__main__":
    raise SystemExit(main())

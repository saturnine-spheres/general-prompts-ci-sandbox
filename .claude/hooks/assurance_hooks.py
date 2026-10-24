#!/usr/bin/env python3
"""Claude Code hooks that enforce the repository's assurance rules (general-prompts Claude Code adapter).

Events (first argument), each reading the hook JSON from stdin:

  post-edit       PostToolUse on Edit/Write/MultiEdit/NotebookEdit: run verify-fast and report failures to Claude
  pre-bash        PreToolUse on Bash: refuse force-push, agent pushes the profile forbids, unsigned commits when
                  signing is required, attribution the profile forbids, commits while verify-fast fails, and
                  agents recording human approvals
  stop            Stop: refuse to finish while an active delivery run fails the evidence gate
  reviewer-write  PreToolUse in the reviewer subagent: allow writes only under .assurance/reviews/

The CI evidence gate stays authoritative; these hooks give early feedback and can be skipped locally.
Set ASSURANCE_HOOK_VERIFY_FAST=0 to skip the verify-fast runs (not the policy checks).
"""

from __future__ import annotations

import json
import os
import pathlib
import re
import subprocess
import sys
import tempfile
from typing import Any

sys.dont_write_bytecode = True

DOC_ONLY = re.compile(r"(^\.assurance/(evidence|runs|reviews|waivers|baseline|approvals|discovery)/|^docs/|\.md$)")
ATTRIBUTION = re.compile(r"co-authored-by|generated with|🤖|noreply@anthropic\.com|claude code", re.I)


def root_of(data: dict[str, Any]) -> pathlib.Path:
    return pathlib.Path(os.environ.get("CLAUDE_PROJECT_DIR") or data.get("cwd") or ".").resolve()


def load(path: pathlib.Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return None


def deny(reason: str) -> int:
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny", "permissionDecisionReason": reason}}))
    return 0


def git(root: pathlib.Path, *arguments: str) -> str:
    completed = subprocess.run(["git", "-C", str(root), *arguments], capture_output=True, text=True, encoding="utf-8", errors="replace")
    return completed.stdout if completed.returncode == 0 else ""


def verify_fast(root: pathlib.Path) -> tuple[bool, str]:
    """Run verify-fast into a temporary record; return (passed, summary of failing checks)."""
    if os.environ.get("ASSURANCE_HOOK_VERIFY_FAST") == "0" or not (root / ".assurance/verifiers.json").is_file():
        return True, ""
    with tempfile.TemporaryDirectory() as scratch:
        record_path = pathlib.Path(scratch, "verify-fast.json")
        completed = subprocess.run([sys.executable, str(root / ".assurance/tools/run_verifier.py"), "--tier", "verify-fast", "--root", str(root),
                                    "--output", str(record_path)], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=850)
        record = load(record_path)
    if completed.returncode == 0:
        return True, ""
    if not record:
        return False, (completed.stderr or completed.stdout).strip()[-1500:]
    failing = [f"{check['id']} ({check['status']}): {' '.join(check['limitations'])[-600:]}" for check in record["checks"] if check["status"] != "pass"]
    return False, "\n".join(failing)


def segments(command: str) -> list[str]:
    return [part.strip() for part in re.split(r"&&|\|\||;|\n", command) if part.strip()]


def pre_bash(data: dict[str, Any]) -> int:
    root = root_of(data)
    command = (data.get("tool_input") or {}).get("command", "")
    if re.search(r"delivery_run\.py\b[^\n]*\bapprove\b", command):
        return deny("Approvals are human decisions. Ask the person to review the work item and run the approve command themselves "
                    "(in Claude Code, prefix it with ! so it runs as their own command).")
    profile = load(root / ".assurance/project-assurance-profile.json") or {}
    delivery = profile.get("delivery") or {}
    for part in segments(command):
        if not re.search(r"\bgit\b", part):
            continue
        if re.search(r"\bgit\b(\s+-\S+)*\s+push\b", part):
            if re.search(r"(^|\s)(--force(-with-lease)?(=\S*)?|-f|--mirror)(\s|$)|\s\+[^\s]+", part):
                return deny("Force-push is never allowed (delivery.push_policy.force_push is false).")
            if delivery and not delivery["push_policy"]["agent_may_push"]:
                return deny("The profile does not allow agents to push (delivery.push_policy.agent_may_push is false). "
                            "Stop and give the person the push and pull request commands.")
        if re.search(r"\bgit\b(\s+-\S+)*\s+commit\b", part):
            if delivery.get("attribution") == "forbidden" and ATTRIBUTION.search(part):
                return deny("The profile forbids AI or agent attribution in commits (delivery.attribution is forbidden). Remove the trailer.")
            message_file = re.search(r"(?:-F|--file)[ =](\S+)", part)
            if message_file and delivery.get("attribution") == "forbidden":
                candidate = root / message_file.group(1).strip("'\"")
                if candidate.is_file() and ATTRIBUTION.search(candidate.read_text(encoding="utf-8", errors="ignore")):
                    return deny("The commit message file contains attribution the profile forbids.")
            if (profile.get("signing") or {}).get("commits_required"):
                signed_flag = re.search(r"(^|\s)(-S\S*|--gpg-sign(=\S+)?)(\s|$)", part)
                configured = git(root, "config", "--get", "commit.gpgsign").strip().lower() == "true"
                if not signed_flag and not configured:
                    return deny("The profile requires signed commits (signing.commits_required). Use git commit -S.")
            staged = set(git(root, "diff", "--cached", "--name-only").split())
            if re.search(r"(^|\s)(-a|--all|-\w*a\w*)(\s|$)", part) or "git add" in command:
                staged |= set(git(root, "diff", "--name-only").split()) | set(git(root, "ls-files", "--others", "--exclude-standard").split())
            if staged and not all(DOC_ONLY.search(path) for path in staged):
                passed, summary = verify_fast(root)
                if not passed:
                    return deny("verify-fast fails, so the commit is refused. Fix these first:\n" + summary)
    return 0


def post_edit(data: dict[str, Any]) -> int:
    root = root_of(data)
    tool_input = data.get("tool_input") or {}
    target = tool_input.get("file_path") or tool_input.get("notebook_path") or ""
    try:
        relative = pathlib.Path(target).resolve().relative_to(root).as_posix()
    except ValueError:
        return 0
    if DOC_ONLY.search(relative) or relative.startswith((".claude/", ".assurance/")):
        return 0
    passed, summary = verify_fast(root)
    if passed:
        return 0
    print(f"verify-fast fails after editing {relative}:\n{summary}", file=sys.stderr)
    return 2


def stop(data: dict[str, Any]) -> int:
    if data.get("stop_hook_active"):
        return 0
    root = root_of(data)
    runs = root / ".assurance/runs"
    if not runs.is_dir():
        return 0
    problems: list[str] = []
    for manifest_path in sorted(runs.glob("*/run-manifest.json")):
        manifest = load(manifest_path)
        if not manifest or manifest.get("status") != "running":
            continue
        run_id = manifest["run_id"]
        with tempfile.TemporaryDirectory() as scratch:
            result_path = pathlib.Path(scratch, "gate.json")
            subprocess.run([sys.executable, str(root / ".assurance/tools/assurance_gate.py"), "check", "--root", str(root),
                            "--base", manifest.get("base_revision") or "HEAD", "--head", "HEAD",
                            "--work-item", manifest["specification"]["work_item"], "--output", str(result_path)],
                           capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=280)
            result = load(result_path) or {}
        findings = [item["fingerprint"] for item in result.get("findings", []) if item.get("status") == "new"]
        dirty = [line[3:] for line in git(root, "status", "--porcelain", "--untracked-files=all").splitlines() if line.strip()]
        if dirty:
            findings.append("uncommitted changes: " + ", ".join(dirty[:8]))
        if findings:
            problems.append(f"run {run_id} is still running and fails the evidence gate: " + "; ".join(findings))
    if not problems:
        return 0
    print(json.dumps({"decision": "block", "reason": "\n".join(problems) + "\nFinish the remaining stages, or record why the run stops with "
                      "`python .assurance/tools/delivery_run.py status --run <id> --status blocked` and tell the person."}))
    return 0


def reviewer_write(data: dict[str, Any]) -> int:
    root = root_of(data)
    tool_input = data.get("tool_input") or {}
    target = tool_input.get("file_path") or tool_input.get("notebook_path") or ""
    try:
        relative = pathlib.Path(target).resolve().relative_to(root).as_posix()
    except ValueError:
        relative = target
    if relative.startswith(".assurance/reviews/") and relative.endswith(".json"):
        return 0
    return deny("The reviewer only writes its review record under .assurance/reviews/; it never changes the implementation.")


def main() -> int:
    event = sys.argv[1] if len(sys.argv) > 1 else ""
    try:
        data = json.load(sys.stdin)
    except ValueError:
        data = {}
    handlers = {"pre-bash": pre_bash, "post-edit": post_edit, "stop": stop, "reviewer-write": reviewer_write}
    if event not in handlers:
        print(f"assurance hook: unknown event {event!r}", file=sys.stderr)
        return 1
    return handlers[event](data)


if __name__ == "__main__":
    raise SystemExit(main())

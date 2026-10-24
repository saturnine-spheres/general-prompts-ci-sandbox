#!/usr/bin/env python3
"""Forge-neutral CI evidence gate and tier classifier for pull or merge requests.

Subcommands (all read the repository at --root with Git history for --base..--head):

- classify: compute the delivery tier (routine, notable, significant) from the diff and the
  profile's human_involvement rules. Unknown or failed classification is significant.
- check: run the evidence gate. Modes: enforce (any finding fails), report (never fails), and
  ratchet (only findings that are new against the recorded baseline fail; process findings
  always count; the baseline may not grow without explicit approval).
- baseline: record the current check findings as the ratchet baseline.

The tool is dependency-free and runs the same way in GitHub Actions, GitLab CI, or any other CI.
It writes a gate-result record and prints one line per finding. Exit code 0 means pass.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import pathlib
import re
import subprocess
import sys
from typing import Any

sys.dont_write_bytecode = True  # keep installed .assurance/tools free of __pycache__

from validate_artifacts import (  # noqa: E402
    read_json, review_semantic, run_manifest_semantic, schema_accepts, validate_instance, verification_semantic, waiver_semantic,
)

TIERS = ("routine", "notable", "significant")
RANK = {name: index for index, name in enumerate(TIERS)}
EVIDENCE_PREFIXES = (".assurance/evidence/", ".assurance/runs/", ".assurance/reviews/", ".assurance/waivers/", ".assurance/baseline/", ".assurance/approvals/")
DEPENDENCY_MANIFESTS = re.compile(r"(^|/)(go\.mod|go\.sum|package\.json|package-lock\.json|npm-shrinkwrap\.json|yarn\.lock|pnpm-lock\.yaml|"
                                  r"requirements[^/]*\.txt|pyproject\.toml|poetry\.lock|Pipfile(\.lock)?|uv\.lock|Cargo\.toml|Cargo\.lock|"
                                  r"Gemfile(\.lock)?|pom\.xml|build\.gradle(\.kts)?|composer\.(json|lock))$")
SOURCE_SUFFIXES = (".go", ".py", ".ts", ".tsx", ".js", ".jsx", ".rs", ".java", ".kt", ".cs", ".rb", ".php", ".c", ".cpp", ".swift")
BASELINE_PATH = ".assurance/baseline/gate-baseline.json"
# Work items are process records: they are part of the change but do not count toward the tier's size limits.
TIER_EXCLUDED = EVIDENCE_PREFIXES + ("docs/work-items/",)
# Governance files decide how the gate itself judges a change; editing them is always significant so a
# change cannot lower its own thresholds. Evidence under EVIDENCE_PREFIXES is excluded before this check.
GOVERNANCE = re.compile(r"^(\.assurance/|AGENTS\.md$|\.github/workflows/assurance-gate\.ya?ml$|\.gitlab/assurance-gate\.gitlab-ci\.yml$|\.gitlab-ci\.yml$)")
PLACEHOLDER = re.compile(r"REPLACE|\[[A-Z][A-Za-z _/-]*\]|\[Observable behaviour")


class GateError(RuntimeError):
    pass


# ---------------------------------------------------------------- Git helpers

def git(root: pathlib.Path, *arguments: str, check: bool = True) -> str:
    completed = subprocess.run(["git", "-C", str(root), *arguments], capture_output=True, text=True, encoding="utf-8", errors="replace")
    if check and completed.returncode != 0:
        raise GateError(f"git {' '.join(arguments)} failed: {completed.stderr.strip()}")
    return completed.stdout


def resolve(root: pathlib.Path, revision: str) -> str:
    return git(root, "rev-parse", "--verify", f"{revision}^{{commit}}").strip()


def changed_files(root: pathlib.Path, base: str, head: str) -> list[tuple[str, int]]:
    """(path, added + deleted lines) for each file changed between the merge base and head."""
    rows = []
    for line in git(root, "diff", "--numstat", "--no-renames", f"{base}...{head}").splitlines():
        added, deleted, path = line.split("\t", 2)
        lines = 0 if added == "-" else int(added) + int(deleted)
        rows.append((path, lines))
    return rows


def show(root: pathlib.Path, revision: str, path: str) -> str | None:
    completed = subprocess.run(["git", "-C", str(root), "show", f"{revision}:{path}"], capture_output=True, text=True, encoding="utf-8", errors="replace")
    return completed.stdout if completed.returncode == 0 else None


def files_at(root: pathlib.Path, revision: str) -> list[str]:
    return git(root, "ls-tree", "-r", "--name-only", revision).splitlines()


# ---------------------------------------------------------------- tier classification

def glob_regex(pattern: str) -> re.Pattern[str]:
    out, index = "", 0
    while index < len(pattern):
        char = pattern[index]
        if pattern.startswith("**/", index):
            out, index = out + "(?:.*/)?", index + 3
        elif pattern.startswith("**", index):
            out, index = out + ".*", index + 2
        elif char == "*":
            out, index = out + "[^/]*", index + 1
        elif char == "?":
            out, index = out + "[^/]", index + 1
        else:
            out, index = out + re.escape(char), index + 1
    return re.compile(f"^{out}$")


def matches(path: str, patterns: list[str]) -> bool:
    return any(glob_regex(pattern).match(path) for pattern in patterns)


def is_test(path: str) -> bool:
    name = path.rsplit("/", 1)[-1]
    parts = path.split("/")
    return (name.endswith("_test.go") or (name.startswith("test_") and name.endswith(".py")) or name.endswith("_test.py")
            or re.search(r"\.(test|spec)\.[jt]sx?$", name) is not None or "tests" in parts or "__tests__" in parts)


def classify(root: pathlib.Path, base: str, head: str, profile: dict[str, Any] | None) -> dict[str, Any]:
    try:
        changes = [(path, lines) for path, lines in changed_files(root, base, head) if not path.startswith(TIER_EXCLUDED)]
    except GateError as exc:
        return {"tier": "significant", "reasons": [f"classification failed: {exc}"], "changed_files": 0, "changed_lines": 0}
    return classify_changes(changes, profile, lambda: files_at(root, head))


def classify_changes(changes: list[tuple[str, int]], profile: dict[str, Any] | None, repository_files) -> dict[str, Any]:
    """Tier for (path, changed lines) pairs; repository_files() lists files at head, for the touch-it-test-it rule.
    Used for the actual diff in CI and for a planned change before a run builds anything."""
    reasons: list[str] = []
    paths = [path for path, _lines in changes]
    total = sum(lines for _path, lines in changes)
    involvement = (profile or {}).get("human_involvement")
    if not involvement:
        return {"tier": "significant", "reasons": ["profile has no human_involvement tier rules; unknown classification is significant"],
                "changed_files": len(paths), "changed_lines": total}
    rules = involvement["tier_rules"]
    protected = [path for path in paths if matches(path, rules["protected_paths"])]
    governance = [path for path in paths if GOVERNANCE.match(path)]
    if governance:
        tier = "significant"
        reasons.append("governance files changed (always significant): " + ", ".join(governance[:10]))
    elif protected:
        tier = "significant"
        reasons.append("protected paths changed: " + ", ".join(protected[:10]))
    elif all(matches(path, rules["routine_path_allowlist"]) for path in paths) and total <= rules["routine_max_changed_lines"] and len(paths) <= rules["routine_max_changed_files"]:
        tier = "routine"
        reasons.append(f"{len(paths)} files and {total} lines inside the routine allowlist and limits")
    elif total <= rules["notable_max_changed_lines"]:
        tier = "notable"
        outside = [path for path in paths if not matches(path, rules["routine_path_allowlist"])]
        reasons.append(f"{len(paths)} files, {total} lines" + (f"; outside the routine allowlist: {', '.join(outside[:5])}" if outside else "; above routine limits"))
    else:
        tier = "significant"
        reasons.append(f"{total} changed lines exceed notable_max_changed_lines {rules['notable_max_changed_lines']}")
    dependencies = [path for path in paths if DEPENDENCY_MANIFESTS.search(path)]
    if dependencies and RANK[rules["dependency_change_tier"]] > RANK[tier]:
        tier = rules["dependency_change_tier"]
        reasons.append("dependency manifests changed: " + ", ".join(dependencies))
    if rules.get("untested_touch_raises_tier") and tier != "significant":
        tests = [path for path in [*repository_files(), *paths] if is_test(path)]
        tested_dirs = {path.rsplit("/", 1)[0] if "/" in path else "." for path in tests}
        test_names = {path.rsplit("/", 1)[-1].lower() for path in tests}

        def tested(path: str) -> bool:
            """A test sits in the same directory, or a test anywhere is named after the file (test_x.py, x_test.go, x.test.ts)."""
            stem = path.rsplit("/", 1)[-1].rsplit(".", 1)[0].lower()
            return (path.rsplit("/", 1)[0] if "/" in path else ".") in tested_dirs or any(
                name.rsplit(".", 1)[0] in {f"test_{stem}", f"{stem}_test", f"{stem}.test", f"{stem}.spec", f"{stem}test", f"test{stem}"} for name in test_names)

        untested = sorted({path for path in paths if path.endswith(SOURCE_SUFFIXES) and not is_test(path) and not tested(path)})
        if untested:
            tier = TIERS[RANK[tier] + 1]
            reasons.append("touched code without tests raises the tier (touch it, test it): " + ", ".join(untested[:5]))
    return {"tier": tier, "reasons": reasons, "changed_files": len(paths), "changed_lines": total}


# ---------------------------------------------------------------- evidence discovery

def load_json_text(text: str | None) -> Any:
    if text is None:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def changed_documents(root: pathlib.Path, base: str, head: str) -> dict[str, Any]:
    """JSON documents added or changed in the request, read at head."""
    documents: dict[str, Any] = {}
    for path, _lines in changed_files(root, base, head):
        if path.endswith(".json") and path.startswith(".assurance/"):
            value = load_json_text(show(root, head, path))
            if isinstance(value, dict):
                documents[path] = value
    return documents


def revision_identity(commit: str) -> str:
    return "sha256:" + hashlib.sha256(f"git-commit:{commit}".encode("utf-8")).hexdigest()


def fresh(root: pathlib.Path, base: str, head: str, revision: str) -> bool:
    """True when the record names a commit in the request (or head) and only evidence changed after it."""
    commits = git(root, "rev-list", f"{base}..{head}").split() + [head]
    for commit in commits:
        if revision_identity(commit) == revision:
            later = [path for path in git(root, "diff", "--name-only", commit, head).splitlines() if path and not path.startswith(EVIDENCE_PREFIXES)]
            return not later
    return False


def parse_work_item(text: str) -> tuple[list[str], bool]:
    """Return acceptance-criterion IDs with real text, and whether change classes are declared."""
    criteria: list[str] = []
    section = re.search(r"^## Acceptance criteria\s*$(.*?)(?=^## )", text, re.M | re.S)
    if section:
        for match in re.finditer(r"`(AC-\d+)`:\s*(.+)", section.group(1)):
            if not PLACEHOLDER.search(match.group(2)):
                criteria.append(match.group(1))
    classes = re.search(r"^- Change classes:\s*(.+)$", text, re.M)
    declared = bool(classes) and not PLACEHOLDER.search(classes.group(1)) and bool(classes.group(1).strip(" `"))
    return criteria, declared


# ---------------------------------------------------------------- the gate

class Findings:
    def __init__(self) -> None:
        self.items: list[dict[str, Any]] = []

    def add(self, fingerprint: str, message: str, ratchetable: bool = False) -> None:
        if not any(item["fingerprint"] == fingerprint for item in self.items):
            self.items.append({"fingerprint": fingerprint, "message": message, "ratchetable": ratchetable, "status": "new"})


def effective_approved_tier(run_manifest: dict[str, Any] | None, approved: str | None, computed: str) -> str:
    """An agent run is held to the tier in its run manifest. A change written by a person has no run
    approval of its own: notable review is the forge's code-owner rule, and significant changes still
    need a recorded human approval (rule 6)."""
    if run_manifest is not None:
        return run_manifest["approved_tier"]
    return approved or computed


def evaluate(root: pathlib.Path, base: str, head: str, work_item_arg: str | None, approved_arg: str | None,
             approval_record: pathlib.Path | None, today: dt.date) -> tuple[dict[str, Any], Findings, dict[str, Any]]:
    findings = Findings()
    assurance = root / ".assurance"
    schemas = assurance / "schemas"
    profile = load_json_text(show(root, head, ".assurance/project-assurance-profile.json"))
    process = load_json_text(show(root, head, ".assurance/process.json"))
    catalog = load_json_text(show(root, head, ".assurance/control-catalog.yaml")) or {"controls": []}
    controls = {control["id"]: control for control in catalog.get("controls", [])}
    tier_info = classify(root, base, head, profile)
    documents = changed_documents(root, base, head)

    def valid(document: Any, schema_name: str) -> bool:
        schema_path = schemas / schema_name
        if not schema_path.is_file():
            return False
        schema = read_json(schema_path)
        return not validate_instance(document, schema, schema)

    run_manifests = {path: value for path, value in documents.items() if str(value.get("run_id", "")).startswith("RUN-")}
    run_manifest = None
    for path, value in run_manifests.items():
        if not valid(value, "run-manifest.schema.json") or not run_manifest_semantic(value):
            findings.add(f"run-manifest-invalid:{path}", f"{path} is not a schema- and semantics-valid run manifest")
        else:
            run_manifest = value
    approved = effective_approved_tier(run_manifest, approved_arg, tier_info["tier"])
    effective = TIERS[max(RANK[approved], RANK[tier_info["tier"]])]

    # Rule 1: a work item with acceptance criteria and change classes is referenced.
    work_item_path = work_item_arg or (run_manifest["specification"]["work_item"] if run_manifest else None)
    if work_item_path is None:
        candidates = [path for path, _lines in changed_files(root, base, head) if re.match(r"^docs/work-items/.+\.md$", path)]
        work_item_path = candidates[0] if len(candidates) == 1 else None
    criteria: list[str] = []
    if work_item_path is None:
        findings.add("work-item-missing", "no work item is referenced (Work-Item: line, run manifest, or one changed docs/work-items/*.md)")
    else:
        text = show(root, head, work_item_path)
        if text is None:
            findings.add("work-item-missing", f"referenced work item {work_item_path} does not exist at head")
        else:
            criteria, declared = parse_work_item(text)
            if not criteria:
                findings.add("work-item-acceptance-criteria", f"{work_item_path} has no filled-in acceptance criteria (`AC-n`: ...)")
            if not declared:
                findings.add("work-item-change-classes", f"{work_item_path} does not declare change classes")

    # Rule 2: every declared gate has a fresh, valid verification result; blocking checks pass or are waived.
    waivers = []
    for path in files_at(root, head):
        if path.startswith(".assurance/waivers/") and path.endswith(".json"):
            value = load_json_text(show(root, head, path))
            if isinstance(value, dict) and valid(value, "waiver.schema.json") and waiver_semantic(value, controls) and value["status"] == "active":
                issued = dt.datetime.fromisoformat(value["issued_at"].replace("Z", "+00:00")).date()
                expires = dt.datetime.fromisoformat(value["expires_at"].replace("Z", "+00:00")).date()
                if issued <= today <= expires:
                    waivers.append(value)
    waived_controls = {control for waiver in waivers for control in waiver["control_ids"]}
    stages = (process or {}).get("stages", [])
    declared_gates = sorted({gate for stage in stages if effective in stage["applies_to_tiers"] for gate in stage["gates"]})
    if process is None:
        findings.add("process-contract-missing", ".assurance/process.json is missing or unreadable at head")
    results = {path: value for path, value in documents.items() if str(value.get("result_id", "")).startswith("VER-")}
    for gate in declared_gates:
        candidates = [(path, value) for path, value in results.items() if value.get("tier") == gate]
        if not candidates:
            findings.add(f"gate-missing:{gate}", f"no verification result for declared gate {gate} is part of this change")
            continue
        for path, value in candidates:
            if not valid(value, "verification-result.schema.json"):
                findings.add(f"gate-invalid:{gate}", f"{path} does not conform to the verification-result schema")
                continue
            if not fresh(root, base, head, value["revision"]):
                findings.add(f"gate-stale:{gate}", f"{path} does not verify a commit of this change with only evidence changed after it")
            for check in value["checks"]:
                if check["blocking"] and check["status"] != "pass":
                    if set(check["control_ids"]) <= waived_controls:
                        continue
                    if check.get("findings"):
                        for item in check["findings"]:
                            findings.add(f"check:{gate}:{check['id']}:{item}", f"blocking check {check['id']} reports {item} in {path}", ratchetable=True)
                    else:
                        findings.add(f"check:{gate}:{check['id']}", f"blocking check {check['id']} is {check['status']} in {path}", ratchetable=True)
            if any(item["required"] for item in value["unrun_checks"]):
                findings.add(f"gate-unrun:{gate}", f"{path} lists required checks that did not run")
            # Rule 5: a sentinel that differs from its expected value fails, wherever it appears.
            if not verification_semantic(value):
                findings.add(f"gate-semantics:{gate}", f"{path} fails verification semantics (status, sentinels, or vulnerability data)")
            for sentinel in value.get("sentinels", []):
                if sentinel["outcome"] != "pass":
                    findings.add(f"sentinel:{sentinel['kind']}", f"sentinel {sentinel['name']} is {sentinel['outcome']} (expected {sentinel['expected']}, observed {sentinel['observed']})")
    if run_manifest is not None:
        present = {sentinel["kind"] for value in results.values() for sentinel in value.get("sentinels", []) if sentinel["outcome"] == "pass"}
        for kind in (process or {}).get("required_sentinels", []):
            if kind not in present:
                findings.add(f"sentinel-missing:{kind}", f"agent run lacks a passing {kind} sentinel required by the process contract")

    # Rule 3: the review record covers every acceptance criterion.
    review_required = any(effective in stage["applies_to_tiers"] and "review_record" in stage["produces"] for stage in stages)
    reviews = [(path, value) for path, value in documents.items() if str(value.get("record_id", "")).startswith("REV-")]
    if review_required:
        if not reviews:
            findings.add("review-missing", "no review record is part of this change")
        covered: set[str] = set()
        for path, value in reviews:
            if not valid(value, "review-record.schema.json") or not review_semantic(value):
                findings.add("review-invalid", f"{path} is not a schema- and semantics-valid review record")
                continue
            if value["decision"] != "approve":
                findings.add("review-not-approved", f"{path} decision is {value['decision']}")
            covered |= {item["id"] for item in value.get("acceptance_criteria", [])}
        for criterion in criteria:
            if reviews and criterion not in covered:
                findings.add(f"review-uncovered:{criterion}", f"no review verdict covers {criterion}")

    # Rule 4: the computed tier is not higher than the tier the run was approved for.
    if RANK[tier_info["tier"]] > RANK[approved]:
        findings.add("tier-exceeds-approval", f"computed tier {tier_info['tier']} is higher than approved tier {approved}")

    # Rule 6: the approval required for the tier is recorded.
    rule = ((process or {}).get("approvals") or {}).get(effective)
    if rule and rule["run_approval_required"]:
        approvals = list(run_manifest["approvals"]) if run_manifest else []
        if approval_record is not None:
            record = load_json_text(approval_record.read_text(encoding="utf-8")) if approval_record.is_file() else None
            approvals += (record or {}).get("approvals", [])
        granted = [item for item in approvals if item.get("decision") == "approve" and item.get("kind") == "human"
                   and RANK.get(item.get("tier", "routine"), 0) >= RANK[effective]]
        if len({item.get("identity") for item in granted}) < rule["minimum_approvals"]:
            findings.add("approval-missing", f"tier {effective} needs {rule['minimum_approvals']} recorded human approval(s)")

    context = {"computed_tier": tier_info["tier"], "approved_tier": approved, "effective_tier": effective,
               "tier_reasons": tier_info["reasons"], "work_item": work_item_path, "declared_gates": declared_gates}
    return tier_info, findings, context


def load_baseline(root: pathlib.Path, revision: str) -> dict[str, Any] | None:
    return load_json_text(show(root, revision, BASELINE_PATH))


def apply_ratchet(root: pathlib.Path, base: str, head: str, findings: Findings, growth_approved: bool, today: dt.date) -> dict[str, Any]:
    base_baseline = load_baseline(root, base)
    head_baseline = load_baseline(root, head)
    schema_path = root / ".assurance/schemas/gate-baseline.schema.json"
    info: dict[str, Any] = {"path": BASELINE_PATH, "present": head_baseline is not None, "report_only_until": None, "known": 0}
    if head_baseline is None:
        findings.add("baseline-missing", f"ratchet mode needs {BASELINE_PATH}")
        return info
    schema = read_json(schema_path) if schema_path.is_file() else None
    if schema is None or validate_instance(head_baseline, schema, schema):
        findings.add("baseline-invalid", f"{BASELINE_PATH} does not conform to the gate-baseline schema")
        return info
    known = {item["fingerprint"] for item in (base_baseline or {"findings": []}).get("findings", [])}
    grown = sorted({item["fingerprint"] for item in head_baseline["findings"]} - known) if base_baseline is not None else []
    if grown and not growth_approved:
        findings.add("baseline-grew", "baseline gained entries without explicit approval: " + ", ".join(grown))
    accepted = known | (set(grown) if growth_approved else set())
    if base_baseline is None:
        accepted = {item["fingerprint"] for item in head_baseline["findings"]}
        info["introduced"] = True
    for item in findings.items:
        if item["ratchetable"] and item["fingerprint"] in accepted:
            item["status"] = "known"
            info["known"] += 1
    until = head_baseline.get("report_only_until")
    info["report_only_until"] = until
    info["report_only"] = bool(until) and today <= dt.date.fromisoformat(until)
    return info


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("command", choices=("classify", "check", "baseline"))
    parser.add_argument("--root", type=pathlib.Path, default=pathlib.Path.cwd())
    parser.add_argument("--base", required=True, help="target branch commit (merge-base side)")
    parser.add_argument("--head", default="HEAD", help="request head commit")
    parser.add_argument("--mode", choices=("enforce", "report", "ratchet"), default="enforce")
    parser.add_argument("--work-item", help="work item path, for example from a Work-Item: line in the request description")
    parser.add_argument("--approved-tier", choices=TIERS, help="tier the change was approved for when no run manifest records it")
    parser.add_argument("--approval-record", type=pathlib.Path, help="JSON file with an approvals array exported from the forge")
    parser.add_argument("--baseline-growth-approved", action="store_true", help="a maintainer explicitly approved new baseline entries")
    parser.add_argument("--report-only-until", help="baseline: last day (YYYY-MM-DD) of the report-only period")
    parser.add_argument("--approved-by", help="baseline: person who approved the baseline")
    parser.add_argument("--today", help="override today's date (YYYY-MM-DD) for tests")
    parser.add_argument("--output", type=pathlib.Path, help="write the gate-result JSON here")
    args = parser.parse_args()

    root = args.root.resolve()
    today = dt.date.fromisoformat(args.today) if args.today else dt.datetime.now(dt.timezone.utc).date()
    try:
        base, head = resolve(root, args.base), resolve(root, args.head)
    except GateError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        if args.command == "classify":
            print(json.dumps({"tier": "significant", "label": "tier:significant", "reasons": [str(exc)]}))
        return 2

    if args.command == "classify":
        profile = load_json_text(show(root, head, ".assurance/project-assurance-profile.json"))
        result = classify(root, base, head, profile)
        result["label"] = f"tier:{result['tier']}"
        print(json.dumps(result, indent=2))
        if args.output:
            args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        return 0

    try:
        _tier, findings, context = evaluate(root, base, head, args.work_item, args.approved_tier, args.approval_record, today)
    except GateError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    if args.command == "baseline":
        if not args.approved_by:
            parser.error("baseline needs --approved-by")
        baseline = {"schema_version": "1.0.0", "created_at": dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z"),
                    "approved_by": args.approved_by, "report_only_until": args.report_only_until,
                    "findings": [{"fingerprint": item["fingerprint"], "note": item["message"]} for item in findings.items if item["ratchetable"]]}
        path = root / BASELINE_PATH
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(baseline, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"BASELINE: {len(baseline['findings'])} check finding(s) recorded in {BASELINE_PATH}; commit it for review and approval.")
        return 0

    baseline_info = None
    report_only = args.mode == "report"
    if args.mode == "ratchet":
        baseline_info = apply_ratchet(root, base, head, findings, args.baseline_growth_approved, today)
        report_only = bool(baseline_info.get("report_only"))
    failing = [item for item in findings.items if item["status"] == "new"]
    status = "pass" if not failing else ("report_only" if report_only else "fail")
    result = {"schema_version": "1.0.0", "generated_at": dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z"),
              "base": base, "head": head, "mode": args.mode, **context,
              "findings": [{key: value for key, value in item.items() if key != "ratchetable"} | {"ratchetable": item["ratchetable"]} for item in findings.items],
              "baseline": baseline_info, "status": status}
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"tier: computed={context['computed_tier']} approved={context['approved_tier']} effective={context['effective_tier']} label=tier:{context['computed_tier']}")
    for reason in context["tier_reasons"]:
        print(f"  reason: {reason}")
    for item in findings.items:
        print(f"{item['status'].upper():6} {item['fingerprint']}: {item['message']}")
    print(f"GATE {status.upper()}: {len(failing)} blocking finding(s)" + (" (report-only)" if status == "report_only" else ""))
    return 1 if status == "fail" else 0


if __name__ == "__main__":
    raise SystemExit(main())

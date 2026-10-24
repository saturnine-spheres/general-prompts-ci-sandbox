#!/usr/bin/env python3
"""Ticket triage and guarded pickup (design section 8.5). Forge-neutral: reads normalized ticket intake files.

  report   --intake-dir DIR | --intake FILE...  --output FILE [--markdown FILE] [--level N]
           rank open tickets: acceptance criteria present and testable, estimated size and tier under the
           profile's human_involvement rules, and agent suitability, each with reasons
  pickup   --report FILE --context FILE [--output FILE] [--markdown FILE]
           level 3 only: decide which tickets to start; prints the ticket IDs to start, one per line

Judgments are deterministic text rules, not model calls, so ticket text (untrusted data) cannot steer them,
and every judgment carries its reasons. They are advisory: a person chooses what to run, and a started
run's tier is recomputed from its actual diff.

The pickup context is a JSON object the forge adapter builds:
  {"attempts": {"<ticket id>": n}, "active_runs": n, "spent_today": amount,
   "eligible_by": {"<ticket id>": "<login with write access who applied an eligibility label>" or null}}
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import pathlib
import re
import secrets
import sys
from typing import Any

sys.dont_write_bytecode = True  # keep installed .assurance/tools free of __pycache__

from assurance_gate import GateError, classify_changes, files_at  # noqa: E402
from validate_artifacts import read_json, schema_accepts, triage_report_semantic  # noqa: E402

AC_LINE = re.compile(r"`?\bAC-(\d+)\b`?\s*[:.)-]\s*(.+)")
CHECKBOX = re.compile(r"^\s*[-*]\s*\[[ xX]\]\s*(.+)$", re.M)
OBSERVABLE = re.compile(r"`[^`]+`|\d|\b(returns?|shows?|displays?|responds?|reports?|rejects?|fails?|errors?|logs?|equals?|contains?|"
                        r"prints?|exits?|raises?|redirects?|creates?|deletes?|stores?|sends?|receives?|lists?|counts?|status)\b", re.I)
VAGUE = re.compile(r"\b(fast(er)?|quick(ly)?|nice(r)?|better|clean(er)?|intuitive|user[- ]friendly|robust|modern|simple|easy|properly|"
                   r"appropriate(ly)?|seamless(ly)?|as needed|etc)\b", re.I)
CROSS_CUTTING = re.compile(r"\b(across (the|all|every)|whole (codebase|code base|system|app)|entire (codebase|code base|system|app)|"
                           r"every (module|service|file|package)|all (services|modules|repositories|repos)|rewrite|re-architect|"
                           r"migrate (everything|all)|overhaul|multiple repositor(y|ies)|several repositor(y|ies))\b", re.I)
PATH_TOKEN = re.compile(r"`([A-Za-z0-9_.\-/]+\.[A-Za-z0-9]{1,6}|[A-Za-z0-9_.\-]+/[A-Za-z0-9_.\-/]*)`")
OTHER_REPO = re.compile(r"\b([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)#\d+")
SIZE_LINES = {"small": 40, "medium": 150, "large": 400}
OPEN_RUN_LABELS = {"run:running", "run:awaiting-approval", "run:pr-open"}


def now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def criteria_of(body: str) -> list[str]:
    """Acceptance criteria as written: `AC-n:` lines, else checkbox or list items under an 'Acceptance criteria' heading."""
    found = [match.group(2).strip() for match in AC_LINE.finditer(body)]
    if found:
        return found
    section = re.search(r"^#{1,6}\s*acceptance criteria\s*$(.*?)(?=^#{1,6}\s|\Z)", body, re.I | re.M | re.S)
    if section:
        items = re.findall(r"^\s*(?:[-*]|\d+[.)])\s*(?:\[[ xX]\]\s*)?(.+)$", section.group(1), re.M)
        return [item.strip() for item in items if item.strip() and not item.strip().startswith("_")]
    return [item.strip() for item in CHECKBOX.findall(body)]


def assess(intake: dict[str, Any], profile: dict[str, Any] | None, repository_files: list[str]) -> dict[str, Any]:
    body = intake.get("body") or ""
    text = f"{intake.get('title', '')}\n{body}"
    criteria = criteria_of(body)
    vague = [item for item in criteria if VAGUE.search(item) and not re.search(r"\d", item)]
    unobservable = [item for item in criteria if not OBSERVABLE.search(item)]
    testable = bool(criteria) and not vague and not unobservable
    paths = sorted(set(PATH_TOKEN.findall(body)))
    paths = [path for path in paths if not path.startswith(("http", "www."))]
    reasons: list[str] = []
    questions: list[str] = []

    size = "small" if len(criteria) <= 3 and len(paths) <= 3 else "medium" if len(criteria) <= 6 and len(paths) <= 8 else "large"
    if paths:
        lines = SIZE_LINES[size]
        result = classify_changes([(path, max(lines // len(paths), 1)) for path in paths], profile, lambda: repository_files)
        tier = result["tier"]
        reasons += [f"estimated tier {tier}: {reason}" for reason in result["reasons"]]
    else:
        tier = "notable"
        reasons.append("estimated tier notable: the ticket names no files, so the routine allowlist cannot be checked")
        questions.append("Which files or components does this concern? Name them in backticks, for example `src/orders/count.go`.")

    if criteria:
        reasons.append(f"{len(criteria)} acceptance criteria" + ("" if testable else " (not all testable)"))
    else:
        reasons.append("no acceptance criteria")
        questions.insert(0, "Which observable behaviour shows this is done? Add acceptance criteria as `AC-1: <behaviour a user or caller can observe>` lines.")
    for item in vague[:3]:
        questions.append(f"The criterion \"{item[:80]}\" is not measurable: what threshold or test shows it is met?")
    for item in [item for item in unobservable if item not in vague][:3]:
        questions.append(f"The criterion \"{item[:80]}\" names no observable result: what does a user or caller see when it is met?")

    poor: list[str] = []
    if CROSS_CUTTING.search(text):
        poor.append("cross-cutting or rewrite-sized wording: " + CROSS_CUTTING.search(text).group(0))
    other_repos = sorted({repo for repo in OTHER_REPO.findall(text) if repo.lower() != str(intake["source"]["project"]).lower()})
    if other_repos:
        poor.append("involves other repositories: " + ", ".join(other_repos[:3]))
    if size == "large":
        poor.append("large: many criteria or files")
    untested = [reason for reason in reasons if "touch it, test it" in reason]
    if untested:
        poor.append("touches code without tests (untested legacy area)")

    if poor:
        suitability = "not-suitable"
        reasons += [f"poor agent fit: {item}" for item in poor]
        questions = []
    elif not testable:
        suitability = "needs-info"
    else:
        suitability = "ready"
        questions = [question for question in questions if not question.startswith("Which files")]
        reasons.append("good agent fit: bounded, testable acceptance criteria")
    score = {"ready": 70, "needs-info": 30, "not-suitable": 5}[suitability]
    score += {"routine": 20, "notable": 10, "significant": 0}[tier] + {"small": 10, "medium": 5, "large": 0}[size]
    return {"source": intake["source"], "title": intake.get("title", ""), "labels": sorted(intake.get("labels", [])),
            "acceptance_criteria": {"present": bool(criteria), "testable": testable, "count": len(criteria)},
            "estimated_size": size, "estimated_tier": tier, "suitability": suitability, "score": float(min(score, 100)),
            "rank": 0, "reasons": reasons, "questions": questions if suitability == "needs-info" else []}


def automation_of(profile: dict[str, Any] | None) -> dict[str, Any]:
    return (profile or {}).get("ticket_automation") or {"level": 1, "pickup": {"enabled": False}, "found_bugs": {"enabled": False, "max_tickets_per_run": 3}}


def cmd_report(root: pathlib.Path, args: argparse.Namespace) -> int:
    profile_path = root / ".assurance/project-assurance-profile.json"
    profile = read_json(profile_path) if profile_path.is_file() else None
    automation = automation_of(profile)
    level = args.level or automation["level"]
    files = [pathlib.Path(item) for item in args.intake or []]
    if args.intake_dir:
        files += sorted(pathlib.Path(args.intake_dir).glob("*.json"))
    excluded = set((automation.get("triage") or {}).get("exclude_labels", []))
    limit = (automation.get("triage") or {}).get("max_tickets_per_pass", 500)
    tickets = []
    try:
        repository_files = files_at(root, "HEAD")
    except (GateError, OSError):
        repository_files = []
    schema = root / ".assurance/schemas/ticket-intake.schema.json"
    for path in files:
        if schema.is_file():
            accepted, errors = schema_accepts(path, schema)
            if not accepted:
                print(f"skipped {path.name}: invalid intake: {'; '.join(errors[:2])}", file=sys.stderr)
                continue
        intake = read_json(path)
        if intake.get("state", "open") != "open" or excluded & set(intake.get("labels", [])):
            continue
        tickets.append(assess(intake, profile, repository_files))
    tickets.sort(key=lambda item: (-item["score"], int(item["source"]["id"]) if item["source"]["id"].isdigit() else 0, item["source"]["id"]))
    tickets = tickets[:limit]
    for index, item in enumerate(tickets, start=1):
        item["rank"] = index
    report = {"schema_version": "1.0.0", "report_id": "TRI-" + dt.datetime.now(dt.timezone.utc).strftime("%Y%m%d-%H%M%S") + "-" + secrets.token_hex(2).upper(),
              "generated_at": now(), "level": level, "tickets": tickets}
    write_report(pathlib.Path(args.output), report)
    if args.markdown:
        with open(args.markdown, "a", encoding="utf-8") as handle:
            handle.write(markdown(report))
    print(f"triage: {len(tickets)} ticket(s); ready {sum(item['suitability'] == 'ready' for item in tickets)}, "
          f"needs-info {sum(item['suitability'] == 'needs-info' for item in tickets)}, not-suitable {sum(item['suitability'] == 'not-suitable' for item in tickets)}")
    return 0


def write_report(path: pathlib.Path, report: dict[str, Any]) -> None:
    if not triage_report_semantic(report):
        raise SystemExit("ERROR: triage report would break its semantic rules")
    path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def markdown(report: dict[str, Any]) -> str:
    lines = [f"## Ticket triage `{report['report_id']}` (level {report['level']})", "",
             "Advisory: a person chooses which tickets to run.", "",
             "| Rank | Ticket | Suitability | Tier | Size | Criteria | Pickup |", "|---|---|---|---|---|---|---|"]
    for item in report["tickets"]:
        criteria = item["acceptance_criteria"]
        pickup = item.get("pickup", {}).get("decision", "")
        title = item["title"].replace("|", "\\|")[:70]
        lines.append(f"| {item['rank']} | [#{item['source']['id']}]({item['source']['url']}) {title} | {item['suitability']} | {item['estimated_tier']} | "
                     f"{item['estimated_size']} | {criteria['count']}{'' if criteria['testable'] else ' (not testable)'} | {pickup} |")
    lines.append("")
    for item in report["tickets"]:
        lines.append(f"- **#{item['source']['id']}**: " + "; ".join(item["reasons"]) + (f" ({item['pickup']['reason']})" if item.get("pickup") else ""))
    return "\n".join(lines) + "\n\n"


def cmd_pickup(root: pathlib.Path, args: argparse.Namespace) -> int:
    profile_path = root / ".assurance/project-assurance-profile.json"
    profile = read_json(profile_path) if profile_path.is_file() else None
    automation = automation_of(profile)
    report = read_json(pathlib.Path(args.report))
    context = read_json(pathlib.Path(args.context))
    pickup = automation["pickup"]
    started: list[str] = []
    active = int(context.get("active_runs", 0))
    budget = (pickup.get("daily_budget") or {}).get("amount", 0)
    for item in sorted(report["tickets"], key=lambda entry: entry["rank"]):
        ticket = item["source"]["id"]
        attempts = int(context.get("attempts", {}).get(ticket, 0))
        labels = set(item.get("labels", []))
        eligible = set(pickup.get("eligibility_labels", [])) & labels
        if report["level"] != 3 or automation["level"] != 3 or not pickup.get("enabled"):
            decision = ("skip", "autonomous pickup is off (level 3 is not enabled in the profile)")
        elif labels & OPEN_RUN_LABELS:
            decision = ("skip", "a run for this ticket is already open")
        elif "agent:needs-human" in labels:
            decision = ("skip", "labelled agent:needs-human")
        elif not eligible:
            decision = ("skip", "no eligibility label (" + ", ".join(pickup.get("eligibility_labels", [])) + ")")
        elif not context.get("eligible_by", {}).get(ticket):
            decision = ("skip", "the eligibility label was not applied by a person with write access")
        elif item["estimated_tier"] != "routine":
            decision = ("skip", f"{item['estimated_tier']} tickets are triaged but never started automatically")
        elif item["suitability"] != "ready":
            decision = ("skip", f"triage judged it {item['suitability']}")
        elif attempts >= pickup["max_attempts"]:
            decision = ("needs-human", f"{attempts} attempts used of {pickup['max_attempts']}; a person must take over")
        elif active >= pickup["concurrency_limit"]:
            decision = ("skip", f"concurrency limit {pickup['concurrency_limit']} reached")
        elif float(context.get("spent_today", 0)) >= budget > 0:
            decision = ("skip", f"daily budget {budget} {pickup['daily_budget']['currency']} spent")
        else:
            decision = ("start", f"labelled {', '.join(sorted(eligible))} by {context['eligible_by'][ticket]}; routine; attempt {attempts + 1} of {pickup['max_attempts']}")
            active += 1
            started.append(ticket)
        item["pickup"] = {"decision": decision[0], "reason": decision[1]}
    write_report(pathlib.Path(args.output or args.report), report)
    if args.markdown:
        with open(args.markdown, "a", encoding="utf-8") as handle:
            handle.write("### Pickup\n\n" + "\n".join(f"- #{item['source']['id']} {item['pickup']['decision']}: {item['pickup']['reason']}"
                                                       for item in sorted(report["tickets"], key=lambda entry: entry["rank"])) + "\n\n")
    for ticket in started:
        print(ticket)
    print(f"pickup: {len(started)} run(s) to start", file=sys.stderr)
    return 0


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--root", type=pathlib.Path, default=pathlib.Path.cwd())
    sub = parser.add_subparsers(dest="command", required=True)
    report = sub.add_parser("report")
    report.add_argument("--intake", nargs="*")
    report.add_argument("--intake-dir")
    report.add_argument("--output", required=True)
    report.add_argument("--markdown")
    report.add_argument("--level", type=int, choices=(1, 2, 3))
    pickup = sub.add_parser("pickup")
    pickup.add_argument("--report", required=True)
    pickup.add_argument("--context", required=True)
    pickup.add_argument("--output")
    pickup.add_argument("--markdown", help="append the pickup decisions to this Markdown file")
    args = parser.parse_args()
    root = args.root.resolve()
    return {"report": cmd_report, "pickup": cmd_pickup}[args.command](root, args)


if __name__ == "__main__":
    raise SystemExit(main())

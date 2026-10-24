#!/usr/bin/env python3
"""GitHub forge helper for asynchronous delivery runs and ticket triage (general-prompts GitHub adapter).

Standard library only; uses GITHUB_REPOSITORY, GITHUB_API_URL, and GITHUB_TOKEN (or GH_TOKEN).

  intake        --issue N --output FILE        normalized ticket intake (issue, comments, linked issues one level deep)
  open-issues   --output-dir DIR [--limit N]   intake files for open issues (pull requests excluded)
  can-act       --user LOGIN                   exit 0 when the user has write, maintain, or admin permission
  status        --issue N --run ID --state S --message TEXT [--url URL]
                                               create or update the single status comment and set one run:* label
  approvals     --issue N --stakeholders a,b --after ISO --output FILE
                                               /approve comments from listed stakeholders with write access, after a time
  pr            --head B --base B --title T --body-file F   open (or find) the pull request; prints its URL
  triage-apply  --report FILE                  level 2+: one agent:* label per ticket, one question comment when they change,
                                               agent:needs-human with its reason
  pickup-context --report FILE --labels a,b --output FILE [--per-run-cost X]
                                               attempts, running runs, today's estimated spend, and who applied an eligibility label
  dispatch      --issue N --on-behalf-of LOGIN start assurance-deliver.yml for a picked-up ticket (Routine only)
  report-bug    --title T --body-file F --fingerprint FP --path P
                                               comment on a matching open issue or file one labelled agent-found, needs-triage
  advisory      --summary S --body-file F --severity LEVEL
                                               open a private repository security advisory (needs a token allowed to)

Write-back is limited to the status comment, run:* and agent:* labels, one triage question comment, found-bug
issues and comments, and the pull request (design sections 8.3, 8.5, 8.6).
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

MARKER = "<!-- assurance-run-status -->"
TRIAGE_MARKER = "<!-- assurance-triage -->"
STATES = ("running", "awaiting-approval", "pr-open", "blocked", "failed")
AGENT_LABELS = ("agent:ready", "agent:needs-info", "agent:not-suitable")
WRITE = {"admin", "maintain", "write"}


class Forge:
    def __init__(self) -> None:
        self.repo = os.environ["GITHUB_REPOSITORY"]
        self.api = os.environ.get("GITHUB_API_URL", "https://api.github.com").rstrip("/")
        self.token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN") or ""

    def call(self, method: str, path: str, body: Any = None) -> Any:
        url = path if path.startswith("http") else f"{self.api}{path}"
        data = json.dumps(body).encode() if body is not None else None
        request = urllib.request.Request(url, data=data, method=method, headers={
            "Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28",
            **({"Authorization": f"Bearer {self.token}"} if self.token else {}), **({"Content-Type": "application/json"} if data else {})})
        with urllib.request.urlopen(request, timeout=30) as response:
            text = response.read().decode("utf-8")
            return json.loads(text) if text else None

    def pages(self, path: str, limit: int = 10000) -> list[Any]:
        items, page = [], 1
        while True:
            separator = "&" if "?" in path else "?"
            batch = self.call("GET", f"{path}{separator}per_page=100&page={page}")
            items += batch
            if len(batch) < 100 or len(items) >= limit:
                return items[:limit]
            page += 1


def iso(value: str) -> str:
    return value if value.endswith("Z") or "+" in value else value + "Z"


def own_comment(body: str) -> bool:
    return MARKER in body or TRIAGE_MARKER in body


def build_intake(forge: Forge, number: str, issue: dict[str, Any] | None = None) -> dict[str, Any]:
    issue = issue or forge.call("GET", f"/repos/{forge.repo}/issues/{number}")
    comments = forge.pages(f"/repos/{forge.repo}/issues/{number}/comments")
    linked: dict[str, dict[str, Any]] = {}

    def add(other_number: str, relation: str) -> None:
        if other_number == str(number) or other_number in linked or len(linked) >= 20:
            return
        try:
            other = forge.call("GET", f"/repos/{forge.repo}/issues/{other_number}")
        except urllib.error.HTTPError:
            return
        linked[other_number] = {"id": other_number, "relation": relation, "title": other.get("title") or "", "body": other.get("body") or "",
                                "state": other.get("state", "open"), "url": other.get("html_url", "")}

    for text in [issue.get("body") or ""] + [comment.get("body") or "" for comment in comments]:
        for other_number in re.findall(r"(?<![\w/])#(\d+)\b", text):
            add(other_number, "mentioned")
    try:
        for event in forge.pages(f"/repos/{forge.repo}/issues/{number}/timeline"):
            source = (event.get("source") or {}).get("issue") or {}
            if event.get("event") == "cross-referenced" and source.get("number") and source.get("repository_url", "").endswith(forge.repo):
                add(str(source["number"]), "cross-referenced")
    except urllib.error.HTTPError:
        pass
    return {
        "schema_version": "1.0.0", "trust": "untrusted",
        "fetched_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "source": {"system": "github", "project": forge.repo, "id": str(number), "url": issue["html_url"]},
        "title": issue["title"], "body": issue.get("body") or "", "state": issue["state"], "author": issue["user"]["login"],
        "labels": sorted({label["name"] for label in issue.get("labels", [])}),
        "comments": [{"id": str(comment["id"]), "author": comment["user"]["login"], "created_at": iso(comment["created_at"]),
                      "body": comment.get("body") or "", "url": comment["html_url"]} for comment in comments if not own_comment(comment.get("body") or "")],
        "linked": list(linked.values()),
    }


def cmd_intake(forge: Forge, args: argparse.Namespace) -> int:
    intake = build_intake(forge, str(args.issue))
    with open(args.output, "w", encoding="utf-8") as handle:
        json.dump(intake, handle, indent=2, ensure_ascii=False)
    print(f"intake: issue #{args.issue}, {len(intake['comments'])} comment(s), {len(intake['linked'])} linked issue(s)")
    return 0


def cmd_open_issues(forge: Forge, args: argparse.Namespace) -> int:
    os.makedirs(args.output_dir, exist_ok=True)
    issues = [issue for issue in forge.pages(f"/repos/{forge.repo}/issues?state=open", limit=args.limit) if "pull_request" not in issue]
    for issue in issues:
        intake = build_intake(forge, str(issue["number"]), issue)
        with open(os.path.join(args.output_dir, f"issue-{issue['number']}.json"), "w", encoding="utf-8") as handle:
            json.dump(intake, handle, indent=2, ensure_ascii=False)
    print(f"open-issues: {len(issues)} intake file(s) in {args.output_dir}")
    return 0


def permission(forge: Forge, user: str) -> str:
    try:
        return forge.call("GET", f"/repos/{forge.repo}/collaborators/{urllib.parse.quote(user)}/permission").get("permission", "none")
    except urllib.error.HTTPError:
        return "none"


def cmd_can_act(forge: Forge, args: argparse.Namespace) -> int:
    level = permission(forge, args.user)
    print(f"{args.user}: {level}")
    return 0 if level in WRITE else 1


def remove_label(forge: Forge, issue: str, label: str) -> None:
    try:
        forge.call("DELETE", f"/repos/{forge.repo}/issues/{issue}/labels/{urllib.parse.quote(label)}")
    except urllib.error.HTTPError:
        pass


def cmd_status(forge: Forge, args: argparse.Namespace) -> int:
    body = f"{MARKER}\n**Delivery run `{args.run}`: {args.state}**\n\n{args.message}" + (f"\n\n{args.url}" if args.url else "")
    comments = forge.pages(f"/repos/{forge.repo}/issues/{args.issue}/comments")
    existing = next((comment for comment in comments if MARKER in (comment.get("body") or "")), None)
    if existing:
        forge.call("PATCH", f"/repos/{forge.repo}/issues/comments/{existing['id']}", {"body": body})
    else:
        forge.call("POST", f"/repos/{forge.repo}/issues/{args.issue}/comments", {"body": body})
    for state in STATES:
        if state != args.state:
            remove_label(forge, args.issue, "run:" + state)
    forge.call("POST", f"/repos/{forge.repo}/issues/{args.issue}/labels", {"labels": [f"run:{args.state}"]})
    print(f"status: #{args.issue} run:{args.state}")
    return 0


def cmd_approvals(forge: Forge, args: argparse.Namespace) -> int:
    stakeholders = {name.strip().lower().removeprefix("github:") for name in args.stakeholders.split(",") if name.strip()}
    after = dt.datetime.fromisoformat(args.after.replace("Z", "+00:00"))
    approvals = []
    for comment in forge.pages(f"/repos/{forge.repo}/issues/{args.issue}/comments"):
        login = comment["user"]["login"]
        created = dt.datetime.fromisoformat(iso(comment["created_at"]).replace("Z", "+00:00"))
        if (comment.get("body") or "").strip().lower().startswith("/approve") and login.lower() in stakeholders and created > after \
                and permission(forge, login) in WRITE:
            approvals.append({"identity": f"github:{login}", "reference": comment["html_url"], "decided_at": iso(comment["created_at"])})
    with open(args.output, "w", encoding="utf-8") as handle:
        json.dump(approvals, handle, indent=2)
    print(f"{len(approvals)} stakeholder approval comment(s)")
    return 0


def cmd_pr(forge: Forge, args: argparse.Namespace) -> int:
    owner = forge.repo.split("/")[0]
    open_prs = forge.call("GET", f"/repos/{forge.repo}/pulls?state=open&head={urllib.parse.quote(owner + ':' + args.head)}")
    if open_prs:
        print(open_prs[0]["html_url"])
        return 0
    with open(args.body_file, encoding="utf-8") as handle:
        body = handle.read()
    created = forge.call("POST", f"/repos/{forge.repo}/pulls", {"head": args.head, "base": args.base, "title": args.title, "body": body})
    print(created["html_url"])
    return 0


def last_triage_comment(forge: Forge, issue: str, kind: str) -> str | None:
    """Body of the newest triage comment of one kind (questions or needs-human), to post again only when it changes."""
    found = None
    for comment in forge.pages(f"/repos/{forge.repo}/issues/{issue}/comments"):
        body = comment.get("body") or ""
        if TRIAGE_MARKER in body and f"<!-- kind: {kind} " in body:
            found = body
    return found


def post_triage_comment(forge: Forge, issue: str, kind: str, text: str) -> bool:
    digest = hashlib.sha256(text.encode()).hexdigest()[:12]
    previous = last_triage_comment(forge, issue, kind)
    if previous and f"<!-- kind: {kind} {digest} -->" in previous:
        return False
    forge.call("POST", f"/repos/{forge.repo}/issues/{issue}/comments", {"body": f"{TRIAGE_MARKER}\n<!-- kind: {kind} {digest} -->\n{text}"})
    return True


def cmd_triage_apply(forge: Forge, args: argparse.Namespace) -> int:
    with open(args.report, encoding="utf-8") as handle:
        report = json.load(handle)
    if report["level"] < 2:
        print("triage-apply: level 1 writes nothing to tickets")
        return 0
    labelled = commented = 0
    for item in report["tickets"]:
        issue = item["source"]["id"]
        wanted = f"agent:{item['suitability']}"
        current = set(item.get("labels", []))
        for label in AGENT_LABELS:
            if label != wanted and label in current:
                remove_label(forge, issue, label)
        if wanted not in current:
            forge.call("POST", f"/repos/{forge.repo}/issues/{issue}/labels", {"labels": [wanted]})
            labelled += 1
        if item["suitability"] == "needs-info" and item["questions"]:
            text = ("Triage needs more information before an agent can take this ticket:\n\n" + "\n".join(f"- {question}" for question in item["questions"])
                    + "\n\nEdit the issue description; the next triage pass checks it again. This is an automated, advisory triage note.")
            commented += post_triage_comment(forge, issue, "questions", text)
        if (item.get("pickup") or {}).get("decision") == "needs-human" and "agent:needs-human" not in current:
            forge.call("POST", f"/repos/{forge.repo}/issues/{issue}/labels", {"labels": ["agent:needs-human"]})
            commented += post_triage_comment(forge, issue, "needs-human", f"Automatic pickup stopped: {item['pickup']['reason']}.")
    print(f"triage-apply: {labelled} label change(s), {commented} comment(s)")
    return 0


def attempts_for(forge: Forge, issue: str) -> int:
    try:
        refs = forge.call("GET", f"/repos/{forge.repo}/git/matching-refs/heads/deliver/issue-{issue}") or []
    except urllib.error.HTTPError:
        return 0
    return sum(1 for ref in refs if re.fullmatch(rf"refs/heads/deliver/issue-{issue}(-\d+)?", ref["ref"]))


def cmd_pickup_context(forge: Forge, args: argparse.Namespace) -> int:
    with open(args.report, encoding="utf-8") as handle:
        report = json.load(handle)
    eligible_labels = {label.strip() for label in args.labels.split(",") if label.strip()}
    running = [issue for issue in forge.pages(f"/repos/{forge.repo}/issues?state=open&labels={urllib.parse.quote('run:running')}") if "pull_request" not in issue]
    today = dt.datetime.now(dt.timezone.utc).date().isoformat()
    try:
        # Every label or comment event creates a workflow run; only runs that did work count toward spend.
        runs = forge.call("GET", f"/repos/{forge.repo}/actions/workflows/assurance-deliver.yml/runs?created=%3E%3D{today}&per_page=100").get("workflow_runs", [])
        runs_today = sum(1 for run in runs if run.get("conclusion") not in {"skipped", "cancelled"})
    except urllib.error.HTTPError:
        runs_today = 0
    context: dict[str, Any] = {"attempts": {}, "active_runs": len(running), "spent_today": runs_today * args.per_run_cost, "eligible_by": {}}
    for item in report["tickets"]:
        issue = item["source"]["id"]
        context["attempts"][issue] = attempts_for(forge, issue)
        if not eligible_labels & set(item.get("labels", [])):
            continue
        actor = None
        for event in forge.pages(f"/repos/{forge.repo}/issues/{issue}/events"):
            if event.get("event") == "labeled" and (event.get("label") or {}).get("name") in eligible_labels:
                actor = (event.get("actor") or {}).get("login")
        context["eligible_by"][issue] = actor if actor and permission(forge, actor) in WRITE else None
    with open(args.output, "w", encoding="utf-8") as handle:
        json.dump(context, handle, indent=2)
    print(f"pickup-context: {len(running)} running, {runs_today} run(s) today")
    return 0


def cmd_dispatch(forge: Forge, args: argparse.Namespace) -> int:
    if permission(forge, args.on_behalf_of) not in WRITE:
        print(f"ERROR: {args.on_behalf_of} lacks write access", file=sys.stderr)
        return 1
    branch = forge.call("GET", f"/repos/{forge.repo}")["default_branch"]
    forge.call("POST", f"/repos/{forge.repo}/actions/workflows/assurance-deliver.yml/dispatches",
               {"ref": branch, "inputs": {"issue": str(args.issue), "on_behalf_of": args.on_behalf_of, "routine_only": "true"}})
    print(f"dispatch: issue #{args.issue} on behalf of {args.on_behalf_of}")
    return 0


def words(text: str) -> set[str]:
    return {word for word in re.findall(r"[a-z0-9]+", text.lower()) if len(word) > 2}


def cmd_report_bug(forge: Forge, args: argparse.Namespace) -> int:
    with open(args.body_file, encoding="utf-8") as handle:
        body = handle.read()
    mark = f"<!-- assurance-finding: {args.fingerprint} -->"
    title_words = words(args.title)

    def find() -> dict[str, Any] | None:
        for issue in forge.pages(f"/repos/{forge.repo}/issues?state=open&sort=created&direction=desc", limit=1000):
            if "pull_request" in issue:
                continue
            text = issue.get("body") or ""
            other = words(issue.get("title") or "")
            similar = bool(title_words and other) and len(title_words & other) / len(title_words | other) >= 0.5
            if mark in text or (args.path in text and similar):
                return issue
        return None

    match = find()
    if match is None:
        time.sleep(5)  # the issue list can lag a moment behind an issue filed just before; look once more before filing
        match = find()
    if match:
        forge.call("POST", f"/repos/{forge.repo}/issues/{match['number']}/comments",
                   {"body": "Another delivery run met this problem:\n\n" + body.replace(mark, "")})
        print(json.dumps({"action": "commented_existing", "url": match["html_url"]}))
        return 0
    created = forge.call("POST", f"/repos/{forge.repo}/issues", {"title": args.title, "body": body, "labels": ["agent-found", "needs-triage"]})
    print(json.dumps({"action": "ticket_filed", "url": created["html_url"]}))
    return 0


def cmd_advisory(forge: Forge, args: argparse.Namespace) -> int:
    with open(args.body_file, encoding="utf-8") as handle:
        body = handle.read()
    created = forge.call("POST", f"/repos/{forge.repo}/security-advisories", {
        "summary": args.summary, "description": body, "severity": args.severity,
        "vulnerabilities": [{"package": {"ecosystem": "other", "name": forge.repo}}]})
    print(json.dumps({"url": created["html_url"]}))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    intake = sub.add_parser("intake")
    intake.add_argument("--issue", required=True)
    intake.add_argument("--output", required=True)
    open_issues = sub.add_parser("open-issues")
    open_issues.add_argument("--output-dir", required=True)
    open_issues.add_argument("--limit", type=int, default=200)
    can = sub.add_parser("can-act")
    can.add_argument("--user", required=True)
    status = sub.add_parser("status")
    status.add_argument("--issue", required=True)
    status.add_argument("--run", required=True)
    status.add_argument("--state", required=True, choices=STATES)
    status.add_argument("--message", required=True)
    status.add_argument("--url")
    approvals = sub.add_parser("approvals")
    approvals.add_argument("--issue", required=True)
    approvals.add_argument("--stakeholders", required=True)
    approvals.add_argument("--after", required=True)
    approvals.add_argument("--output", required=True)
    pr = sub.add_parser("pr")
    pr.add_argument("--head", required=True)
    pr.add_argument("--base", required=True)
    pr.add_argument("--title", required=True)
    pr.add_argument("--body-file", required=True)
    triage_apply = sub.add_parser("triage-apply")
    triage_apply.add_argument("--report", required=True)
    pickup_context = sub.add_parser("pickup-context")
    pickup_context.add_argument("--report", required=True)
    pickup_context.add_argument("--labels", required=True)
    pickup_context.add_argument("--output", required=True)
    pickup_context.add_argument("--per-run-cost", type=float, default=0.0)
    dispatch = sub.add_parser("dispatch")
    dispatch.add_argument("--issue", required=True)
    dispatch.add_argument("--on-behalf-of", required=True)
    report_bug = sub.add_parser("report-bug")
    report_bug.add_argument("--title", required=True)
    report_bug.add_argument("--body-file", required=True)
    report_bug.add_argument("--fingerprint", required=True)
    report_bug.add_argument("--path", required=True)
    advisory = sub.add_parser("advisory")
    advisory.add_argument("--summary", required=True)
    advisory.add_argument("--body-file", required=True)
    advisory.add_argument("--severity", required=True, choices=("low", "medium", "high", "critical"))
    args = parser.parse_args()
    forge = Forge()
    handlers = {"intake": cmd_intake, "open-issues": cmd_open_issues, "can-act": cmd_can_act, "status": cmd_status, "approvals": cmd_approvals,
                "pr": cmd_pr, "triage-apply": cmd_triage_apply, "pickup-context": cmd_pickup_context, "dispatch": cmd_dispatch,
                "report-bug": cmd_report_bug, "advisory": cmd_advisory}
    try:
        return handlers[args.command](forge, args)
    except urllib.error.HTTPError as exc:
        print(f"ERROR: GitHub API {exc.code} {exc.reason}: {exc.read().decode('utf-8', 'replace')[:300]}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

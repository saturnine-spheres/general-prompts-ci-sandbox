# Installation and update guide

Installation is a local repository change. It does not approve application coding, tool installation, remote CI/repository settings, release, deployment, or other external effects.

## Canonical greenfield structure

```text
repository/
├── README.md
├── AGENTS.md
├── .assurance/
│   ├── README.md
│   ├── assurance-system-manifest.json
│   ├── project-assurance-profile.json
│   ├── process.json
│   ├── verifiers.json (when a verifier starter is generated)
│   ├── control-catalog.yaml
│   ├── change-class-evidence-matrix.json
│   ├── generalized-development-assurance-guidelines.md
│   ├── tiered-verifier-contract.md
│   ├── glossary.md
│   ├── schemas/
│   ├── tools/
│   │   ├── validate-artifacts.ps1
│   │   ├── validate-artifacts.sh
│   │   ├── validate_artifacts.py
│   │   └── project-native verify entrypoints
│   ├── templates/
│   ├── evidence/
│   ├── reviews/
│   ├── waivers/
│   ├── migrations/ (install, update, and rollback records)
│   └── backups/ (update snapshots for rollback)
├── docs/
│   ├── START-HERE.md
│   ├── product/
│   │   ├── project-discovery.md
│   │   ├── product-brief.md
│   │   └── requirements.md
│   ├── architecture/
│   │   ├── architecture.md
│   │   └── decisions/0001-initial-architecture.md
│   ├── roadmap/roadmap.md
│   ├── quality/test-strategy.md
│   ├── status/current-status.md
│   └── work-items/WI-0001-bootstrap.md
├── src/ or stack-native source roots
└── tests/ or stack-native test roots
```

`AGENTS.md` is compact execution guidance. `.assurance/` contains machine/governance contracts, validators, evidence, and upstream template copies. `docs/` contains project-owned human decisions and plans. Architecture is human-governed documentation even when diagrams and traceability are machine-validated.

Empty evidence/review/waiver directories may begin with a README describing retention and schema rules; fabricated placeholder evidence is forbidden.

## Greenfield install

1. Resolve an absolute target path and confirm local write scope.
2. Run discovery and select a preset. Do not infer owner identities or sensitive/production authority.
3. Run the optional scaffolder without `--apply`; review every destination and conflict.
4. Apply only to an empty or purpose-created repository. The scaffolder preflights every destination and writes nothing if any target exists.
5. Adapt `AGENTS.md`, the project profile, catalog ownership, verifier commands, and human documents. Replace placeholders with facts, explicit `UNKNOWN(...)`, or explicit disabled/not-used decisions supported by the preset rules.
6. Record each installed file in `.assurance/assurance-system-manifest.json` with upstream and installed digests and ownership policy.
7. After adapting files and updating manifest digests/local-change flags, run `.assurance/tools/validate-installed-assurance.ps1` or `.assurance/tools/validate-installed-assurance.sh`. Review the full diff and unresolved unknowns.
8. Obtain owner acceptance of the pre-code baseline before implementing application code.

## Existing repository adoption

Existing adoption is a merge and authority-analysis task. The scaffolder applies only a plan that has been reviewed, adds only missing paths, and never overwrites an existing file:

1. Freeze the baseline revision and capture dirty state without changing it.
2. Read every applicable `AGENTS.md`, contribution/policy file, product/architecture/ADR/roadmap/status document, CI workflow, build/test entrypoint, and repository rule description.
3. Produce the plan with `--mode existing --plan-out <file>` and review it with the full diff it prints. Existing project-owned files are `KEEP`; existing merge-managed files such as `AGENTS.md` are `SUGGEST` (kept, upstream text shown for a reviewed merge); missing paths are `ADD`; a differing upstream-managed file is a `CONFLICT` that blocks the plan. Existing project decisions default to project-owned.
4. Resolve authority conflicts with the named owner. A newer package file cannot silently outrank an approved repository contract.
5. Apply the reviewed plan with `--apply --plan <file>`. The tool refuses the plan if the target or package changed since review, if the plan file was edited, or if an uncommitted change overlaps a planned write. It writes `.assurance/` artifacts without relabelling current failures as passing and records an install migration record.
6. Merge root `AGENTS.md` compactly and link detailed policies. Map existing docs into the canonical topics; do not duplicate them merely to match names. Record aliases in `docs/START-HERE.md` and the manifest.
7. Use the generated verifier starter (below) or implement verifier wrappers around existing native commands. CI may orchestrate but must call the same underlying entrypoints.
8. Run gates in observation mode, record baseline debt with owners/dates, pilot one routine change, and enable blocking enforcement in approved stages.

### Minimal install

`--footprint minimal` installs only root `AGENTS.md` and `.assurance/` (profile, catalog, matrix, policy, process contract, schemas, validators, work-item template, and verifier starters). Product and architecture documents are added later; the installed validator then requires only the minimal set.

### Legacy repositories

`--legacy` adds three things for repositories without assurance history:

- smaller Routine runs in the profile (`routine_max_changed_lines` 80, `routine_max_changed_files` 4, `notable_max_changed_lines` 400) until tests cover touched areas;
- `untested_touch_raises_tier`: touched code without tests raises the tier by one level, and the builder adds characterization tests before changing that behaviour (touch it, test it);
- `.assurance/discovery/legacy-discovery.md`: a recovered architecture view, change hotspots and likely owners from Git history, proposed protected paths, and source directories without tests. Everything in it is `proposed`; maintainers confirm it before any item reaches the tier rules.

`--discover-out <directory>` writes the same discovery report outside the target without installing anything, for a read-only first look.

### Verifier starters

For a Go, Node/TypeScript, or Python repository without `verify-fast`/`verify` entrypoints, existing mode generates `.assurance/verifiers.json` (project-owned; review and adapt the commands) and `.assurance/tools/verify-fast` and `verify` as `.sh` and `.ps1`. The entrypoints call `.assurance/tools/run_verifier.py`, which runs each check as an argument vector without a shell, optionally inside a pinned container image for old toolchains, and writes a schema-valid `verification-result` record. Choose the stack with `--verifier-starter go|node|python`, or skip it with `none`.

Each tier's `output` may use `{branch}` (the current branch, as a path segment), `{tier}`, and `{revision}` (12 hex digits of the commit). The starter writes `.assurance/evidence/{branch}/{tier}.json`, so each change keeps its records in its own folder: a rerun on the branch overwrites them, and two open pull requests never edit the same file, so merging one does not make the other conflict. The evidence gate reads the records that are part of the change wherever they are, and merged changes keep their folders as history.

## Ownership and safe update

Each manifest entry uses one policy:

- `upstream-managed`: schemas, unadapted templates, and distribution validators. Replace only when the current digest equals the recorded installed digest; otherwise create a conflict for review.
- `merge-managed`: root `AGENTS.md`, detailed policy, catalog, matrix, verifier contract, and local verifier adapters. Always review a three-way diff.
- `project-owned`: product brief, requirements, architecture decisions, roadmap, test strategy, active work items, assurance-profile decisions, process contract, verifier configuration, evidence, reviews, waivers, and status. Never overwrite from upstream.

Digests are computed over file content with CRLF line endings read as LF, so a Windows checkout with Git line-ending conversion keeps matching its recorded lineage. For LF files this equals the raw SHA-256.

Update procedure:

1. Validate the candidate package and identify its version/source digest. The installed version is `system.version` in the manifest; a candidate older than it is refused.
2. From the candidate package, run `--mode update --target <repository> --base-package <previously installed package> --plan-out <file>`. The tool compares candidate upstream digest, prior upstream digest, recorded installed digest, and current repository digest for every path, and prints the plan and full diff.
3. The plan blocks on a missing record, digest mismatch, path traversal, symlink/reparse target, schema migration (an installed profile, catalog, matrix, process contract, or verifier configuration that no longer validates against a changed schema), or an uncommitted change that overlaps a planned write.
4. Clean `upstream-managed` files are `REPLACE`d. `merge-managed` files without local changes are replaced; with local changes they are three-way merged against the base package (`MERGE`), and a merge conflict blocks the plan for a reviewed merge. `project-owned` files are never written; a changed template is shown as `SUGGEST` with the upstream change.
5. Migrate historical evidence by creating traceable copies. Never rewrite an original evidence record to fit a new schema.
6. Apply with `--apply --plan <file> --owner <name>`. The tool snapshots every file it changes and the manifest under `.assurance/backups/<migration-id>/`, writes `.assurance/migrations/<migration-id>.json`, updates digests and the version stamp, and appends the migration to `migration_history`. Revalidate, review the entire diff, and obtain the required owner approval.

When you adapt a `project-owned` or `merge-managed` file after installation (for example the profile or `verifiers.json`), record it with `--mode record --target <repository> --path <file>` (repeatable): it prints the digest change, and with `--apply` stores the new installed digest and the local-change flag in the manifest, so the installed validator's lineage check passes and a later update sees the adaptation. It changes only the manifest, and it refuses `upstream-managed` files, whose local edits must surface as update conflicts, and derived files, which are regenerated.

Rollback (`--mode rollback --migration <migration-id>`, then `--apply`) restores the snapshot and the manifest revision and records a rollback migration. It refuses when any file changed after the migration. It does not delete new evidence or owner decisions; those receive explicit disposition. Rerun validation afterwards.

## Optional safe scaffolder

From the package root (or, for updates, the candidate package root):

```text
python tools/scaffold_project.py --target <absolute-repository-path> --mode greenfield --profile lightweight
python tools/scaffold_project.py --target <absolute-repository-path> --mode greenfield --profile lightweight --apply
python tools/scaffold_project.py --target <absolute-repository-path> --mode existing --profile general --footprint minimal --legacy --plan-out plan.json
python tools/scaffold_project.py --target <absolute-repository-path> --mode existing --profile general --footprint minimal --legacy --apply --plan plan.json --owner <name>
python tools/scaffold_project.py --target <absolute-repository-path> --mode update --base-package <old-package> --plan-out update.json
python tools/scaffold_project.py --target <absolute-repository-path> --mode update --base-package <old-package> --apply --plan update.json --owner <name>
python tools/scaffold_project.py --target <absolute-repository-path> --mode rollback --migration <migration-id> --apply
```

Properties:

- plan-only by default, with the full diff printed for every planned write;
- accepts only an existing absolute target directory;
- rejects symlinks, reparse points, and destinations outside the target; greenfield `--apply` refuses the whole operation if any destination exists;
- preflights all paths before writing, then copies package files and generated starters only;
- never installs tools/dependencies, initializes Git, edits remotes, commits, pushes, or deploys;
- refuses `existing --apply` and `update --apply` without a reviewed plan file, and refuses a stale or edited plan;
- never writes a `project-owned` file that already exists;
- installs and records `--adapter claude-code|github|gitlab` files, and adds adapters to an installation with `--mode update --adapter <name>`;
- leaves templates in draft state for agent/human adaptation and validation.

The initial scaffold intentionally fails the installed validator's active-placeholder check until the adopting agent or user replaces every `REPLACE` in active documents with an established fact or an explicit owned `UNKNOWN(...)`. Template copies under `.assurance/templates/` retain placeholders.

The command is a scaffold aid, not evidence that the resulting profile or documents are approved. `tools/test_scaffold_project.py` exercises install, update, conflict, and rollback paths in temporary repositories.

## CI evidence gate

`.assurance/tools/assurance_gate.py` is a dependency-free command that runs on every pull or merge request in any CI system. It needs the repository with Git history (`fetch-depth: 0` or `GIT_DEPTH: 0`) and Python 3.9 or newer:

```text
python .assurance/tools/assurance_gate.py classify --base <target-commit> --head <request-head>
python .assurance/tools/assurance_gate.py check --base <target-commit> --head <request-head> [--mode enforce|report|ratchet] [--work-item <path>] [--approval-record <file>]
python .assurance/tools/assurance_gate.py baseline --base <target-commit> --head <request-head> --approved-by <name> [--report-only-until YYYY-MM-DD]
```

`classify` computes the tier from the diff and `human_involvement.tier_rules`: governance files (`.assurance/` outside evidence, `AGENTS.md`, and the gate's CI files) and protected paths make a change significant; changes inside the routine allowlist and limits are routine; dependency manifests raise the tier to `dependency_change_tier`; `untested_touch_raises_tier` raises it one level for touched code without tests. Evidence and work items under `docs/work-items/` do not count toward the size limits. A missing profile block or a failed classification is significant.

`check` fails when:

- no work item is referenced (a `Work-Item: <path>` line in the request description, the run manifest, or exactly one changed `docs/work-items/*.md`), or it lacks filled-in acceptance criteria or change classes;
- a gate the process contract declares for the tier has no schema-valid verification result in the change, the result does not verify a commit of the change with only evidence changed after it, or a blocking check is not `pass` and no active, valid waiver covers all its controls;
- the review record is missing, invalid, not approving, or does not cover every acceptance criterion;
- the computed tier is higher than the tier an agent run was approved for (a change written by a person is held to its computed tier);
- a sentinel is not `pass`, or an agent run lacks a sentinel the process contract requires;
- the approval the tier requires is not recorded (run manifest approvals or an `--approval-record` exported from the forge).

It writes a `gate-result` record and exits 0 only when it passes.

### Ratchet mode for legacy repositories

`--mode ratchet` reads `.assurance/baseline/gate-baseline.json` at the target and the request head. A blocking-check finding (`check:<tier>:<check-id>`, or `check:<tier>:<check-id>:<finding>` when the check lists individual findings, such as one line per unformatted file or untested package) that the target's baseline already lists is reported as `known` and does not fail; a new one fails. Process findings, such as a missing work item or review, are never baselined. The baseline may not gain entries unless a maintainer explicitly approves (`--baseline-growth-approved`, set by the wrappers from the `baseline-approved` label). While `report_only_until` is today or later, the gate reports findings without failing; after that date it enforces. Create the first baseline with the `baseline` command, review it, and record its approver.

### GitHub and GitLab wrappers

- `--adapter github` installs `.github/workflows/assurance-gate.yml`. It classifies the pull request and sets one `tier:*` label, exports approving reviews on the head commit from logins in the `ASSURANCE_STAKEHOLDERS` variable as approvals, and runs the gate in `ASSURANCE_GATE_MODE` (default `enforce`). Make `assurance-gate` a required status check on the default branch so a failing gate blocks merge. Branch protection for private repositories needs a paid GitHub plan; without it the check still runs and reports.
- `--adapter gitlab` installs `.gitlab/assurance-gate.gitlab-ci.yml` and `.assurance/tools/gitlab_mr.py`. Include the job from the project's `.gitlab-ci.yml` (the scaffolder never edits that file) and enable "Pipelines must succeed". Tier labels and stakeholder approvals need an `ASSURANCE_GITLAB_TOKEN` project access token; without it the tier appears in the job log only. Enable "Remove all approvals when commits are added" so approvals refer to the head commit.
- Other CI systems (Jenkins, Azure DevOps) call the same two commands with the target and head commits.

## Claude Code adapter

`--adapter claude-code` (at installation, or later with `--mode update --adapter claude-code`) installs the harness adapter, generated from the neutral core:

- `CLAUDE.md` imports `@AGENTS.md` and `@.assurance/agent-pack.md`. Claude Code reads `CLAUDE.md` instead of `AGENTS.md` when both exist, so an existing `CLAUDE.md` must import `@AGENTS.md`; the installed validator checks this.
- `.claude/skills/deliver/SKILL.md` adds `/deliver <specification, file, or issue reference>`. It walks the stages of `.assurance/process.json`: intake, specify, a tier check with an approval pause when the tier requires it, build, gates, review, evidence, and publish. It records each stage with `.assurance/tools/delivery_run.py` in `.assurance/runs/<run-id>/run-manifest.json`. Only a person invokes it.
- `.claude/agents/assurance-specifier.md`, `assurance-builder.md`, and `assurance-reviewer.md` are the stage subagents. The reviewer starts in a fresh context with only the work item, revisions, and evidence, never the builder's instructions; it has no edit tool, and a scoped hook lets it write only its review record.
- `.claude/settings.json` registers the hooks in `.claude/hooks/`: `verify-fast` runs after each code edit and failures go back to Claude; commits are refused while `verify-fast` fails or when they break the profile's signing or attribution rules; force-push, pushes the profile does not allow, and agents recording approvals are refused; Claude cannot finish while an active run fails the evidence gate. The hooks need bash and Python 3.9+ (Git Bash on Windows). They give early feedback; the CI evidence gate stays authoritative. On Windows clones with Git line-ending conversion, add `*.sh text eol=lf` to the repository's `.gitattributes` so the installed shell scripts keep LF line endings; bash cannot run them with carriage returns.
- `.assurance/agent-pack.md` is the compact agent pack: commands, tier rules, process stages, delivery rules, stop conditions, and blocking controls, generated from the profile, process contract, verifier configuration, and catalog (at most 6 KiB). It is derived, not tracked in the manifest; regenerate it with `.assurance/tools/agent_pack.py` after changing those files. The installed validator reports a stale pack.

A significant run stops before build. The person reviews the work item and records the approval themselves, for example `! python .assurance/tools/delivery_run.py approve --run <id> --identity <name> --role <role> --tier significant` in Claude Code; the hook refuses the same command from the agent.

The run records two sentinels a local session can measure: secret patterns in changed files and writes outside the work item's `Filesystem scope`. Spend is measured when stage costs are recorded. Egress, leftover resources, and forge actions need an isolated runner (the asynchronous forge runs of a later version), so the default process contract does not require them.

## Asynchronous runs from GitHub issues

The `github` adapter also installs `.github/workflows/assurance-deliver.yml`, the specification issue form `.github/ISSUE_TEMPLATE/specification.yml`, and `.assurance/tools/github_forge.py`. A maintainer adds the `deliver` label to an issue; the workflow refuses anyone without write access, reads the issue, its comments, and linked issues one level deep into a normalized ticket intake (`ticket-intake.schema.json`, always marked untrusted), and runs `.assurance/tools/async_deliver.py`:

- Deterministic steps run in the orchestrator: the run branch `deliver/issue-<n>`, the run record, the planned tier, gates and sentinels, commits, the local evidence gate, the pull request, and one status comment on the issue with a `run:*` label (`running`, `awaiting-approval`, `pr-open`, `blocked`, `failed`).
- The model is used only for specify, build, and review, each as one narrow Claude Code call in `--bare` mode with an explicit tool list. Build and gates retry up to the process contract's rework limit; a missing or invalid review record blocks the run instead of being worked around.
- A significant run stops before build with `run:awaiting-approval`. A stakeholder listed in `human_involvement.roles.significant.stakeholders` (as `github:<login>`) with write access comments `/approve`; the workflow records the approval in the run manifest and resumes. This works on every GitHub plan; protected environments with required reviewers can replace it where the plan allows them.
- Write-back is limited to the status comment, `run:*` labels, the run branch, and the pull request. Ticket text is data, never instructions, and the tier is recomputed from the actual diff.

Model and runner are configuration, not code:

| Setting | Local model (testing) | Cloud model |
|---|---|---|
| `ASSURANCE_AGENT_RUNS_ON` | `["self-hosted","assurance-local-model"]` | `"ubuntu-latest"` (default) |
| `ASSURANCE_MODEL_PROVIDER` | `local` | `anthropic` (default) |
| `ASSURANCE_MODEL` | a model served by the local Anthropic-compatible server | an Anthropic model ID |
| `ASSURANCE_MODEL_BASE_URL` | for example `http://127.0.0.1:11435` (Ollama) | not set |
| Secret | none | `ANTHROPIC_API_KEY` |
| Spend | recorded as zero | capped per run by `ASSURANCE_RUN_BUDGET_USD` or the profile's run budget |

The workflow opens pull requests with the job's `GITHUB_TOKEN`, so enable Settings → Actions → General → "Allow GitHub Actions to create and approve pull requests"; that setting also lets workflows approve pull requests, so a repository that must not allow it can give the workflow a GitHub App token with pull-request write access instead. A rerun for the same issue uses the next free branch name (`deliver/issue-<n>-2`, …), so no run branch is ever force-pushed. GitHub holds workflows on a pull request opened by `GITHUB_TOKEN` until a maintainer approves them, so the evidence gate on an agent pull request shows "approval required" until someone with write access selects "Approve and run" on its checks; a GitHub App token avoids that hold. An agent call that exceeds `ASSURANCE_AGENT_TIMEOUT` seconds (default 3600) counts as one failed attempt against the stage's retry or rework limit; raise it for slow local models.

Use self-hosted runners only with private repositories: on a public repository anyone's pull request could run code on the runner machine. `.assurance/tools/run_metrics.py` aggregates run manifests from every branch into acceptance rate, escalation rate, human minutes, cost, and cycle time.

## Ticket triage and pickup

The optional `ticket_automation` profile block sets one of three levels (design section 8.5):

| Level | What happens | Where |
|---|---|---|
| 1, on request | `triage.py report` ranks open tickets: acceptance criteria present and testable, estimated size and tier under `human_involvement`, and agent suitability, each with reasons. A person chooses what to run. | locally or in the scheduled job's summary |
| 2, scheduled | The scheduled job also sets one `agent:ready`, `agent:needs-info`, or `agent:not-suitable` label per ticket and posts one comment with clarifying questions when they change. It never starts runs. | `.github/workflows/assurance-triage.yml` |
| 3, guarded pickup | The job also starts delivery runs for tickets that a person with write access labelled with an eligibility label (default `agent-ok`), that triage judged ready and Routine, within the concurrency limit, the daily budget, and two attempts per ticket. After two attempts the ticket gets `agent:needs-human`. Notable and significant tickets are never started automatically, and a started run stops before build if its own planned tier is higher than Routine. | the same workflow dispatches `assurance-deliver.yml` |

Level 3 is off by default and only valid with `pickup.enabled` set (the validator enforces both directions); enable it after a period of level 2 triage you trust (GP-9). Triage uses deterministic text rules, not a model, so it needs no API key, ticket text cannot steer it, and the same tickets always get the same judgment. Its judgments are advisory, and a run's tier is recomputed from the actual diff.

To run level 1 locally against GitHub:

```bash
GITHUB_REPOSITORY=<owner/repo> GH_TOKEN=$(gh auth token) python3 .assurance/tools/github_forge.py open-issues --output-dir /tmp/tickets
python3 .assurance/tools/triage.py report --intake-dir /tmp/tickets --output /tmp/triage.json --markdown /tmp/triage.md
```

The triage workflow needs `issues: write` and `actions: write` (to dispatch runs) and runs on `ASSURANCE_TRIAGE_RUNS_ON` (default `ubuntu-latest`).

### Bugs found during a run

Builders and reviewers record bugs outside their work in `.assurance/runs/<run>/found-bugs.json`. `found_bugs.py process` applies the design section 8.6 rule table by evidence, not by the agent's claim: a finding is pre-existing when it reproduces on the run's base commit or its lines are not in the run's diff. Bugs the run introduced must be fixed in the run; pre-existing bugs fixed inside the work item's scope are recorded without a ticket; unrelated and blocking out-of-scope bugs get a ticket; uncertain ones are observations. A blocking out-of-scope bug blocks the run unless a safe workaround is noted. The forge adapter comments on a matching open issue instead of filing a duplicate, labels new issues `agent-found` and `needs-triage` with no assignee or priority, and files at most `found_bugs.max_tickets_per_run` (default 3) per run. Security findings never go to a public ticket: the adapter tries a private security advisory, which needs a token allowed to create one (the default `GITHUB_TOKEN` usually is not); otherwise the finding is recorded as withheld and its details stay only in `.git/` on the runner. Every finding is recorded in the run manifest's `findings` array.

## Example repository

`python tools/build_example.py --target <new directory>` builds a small, fully adopted example repository with the package's own tools: a minimal installation with the GitHub and Claude Code adapters and an adapted profile, a routine change with verifier results and a review record, a significant run that waits for a stakeholder approval before build, an active waiver, and the evidence gate passing for each change before its merge. Its `docs/TOUR.md` explains each record. The example is generated rather than stored, so it always matches the current tools; rebuild it instead of copying an old one, because its waiver dates are relative to the build time.

## Self-evaluation

`python tools/self_eval.py run --suite evaluation/textkit-suite --out <directory>` runs the suite's twelve specifications through asynchronous delivery runs in four variants (lightweight or general preset, with or without the compact agent pack), using the model configured in `ASSURANCE_MODEL_*`. Each run starts from a fresh copy of the fixture, and afterwards the specification's hidden acceptance tests, which the agent never saw, run on the result. The results record whether each run reached a reviewed, gated pull-request branch, its rework, duration, and cost, and whether it is an escaped defect (ready, but failing the hidden tests). Human minutes and final acceptance stay `null` until the owner fills them in; `self_eval.py summarize --results <file>` prints the comparison. `--specs` and `--variants` select a subset, and a rerun skips runs already recorded. The installed presets share one profile template, so the preset variants differ in the agent pack's posture section until the profile is adapted.

## Migration notes

### 1.3.0

All 1.3.0 changes are additive. An existing installation keeps validating without changes, and nothing in a repository needs to be migrated.

- Profile schema: accepts `schema_version` `1.1.0` or `1.2.0` and adds optional `human_involvement`, `delivery`, and `process_light_mode` blocks. The profile is project-owned, so an update presents the new blocks as suggestions; adopting them is an owner decision.
- Verification-result and review-record schemas: accept `schema_version` `1.0.0` or `1.1.0` and add optional `sentinels` and `acceptance_criteria` arrays. Existing evidence is never rewritten to add them.
- New `run-manifest.schema.json` and `process-contract.schema.json` are `upstream-managed` schemas. `process-contract.template.json` is shipped with the package; installing it as `.assurance/process.json` and run evidence under `.assurance/runs/` is part of the scaffolder and update work in a later version.
- The work-item template adds acceptance criteria, value check, kill or rethink criteria, and rigor budget sections. Active work items are project-owned and keep their current form until their owner updates them.
- `AGENTS.template.md` and the guidelines add the two-strike rule, the rigor-budget stop, and light-mode re-entry triggers. Both are `merge-managed`, so the update is a reviewed three-way merge.

### 1.4.0

All 1.4.0 changes are additive for existing installations; an installation made by an earlier version keeps validating.

- The scaffolder adds existing-repository apply from a reviewed plan, update mode with snapshots and migration records, rollback, the minimal footprint, legacy adoption, verifier starters, and adapter selection. Existing behaviour is unchanged: greenfield commands work as before, and `--mode existing --apply` without a reviewed plan is still refused.
- The manifest schema accepts `schema_version` `1.0.0` or `1.1.0` and adds optional `installation.footprint`, `installation.legacy`, `installation.adapters`, and `migration_history[].migration_id`. A manifest without them is read as a full, non-legacy installation without adapters.
- New `upstream-managed` schemas `verifier-config.schema.json` and `migration-record.schema.json`, and the new tool `run_verifier.py`. An update adds them, and adds `.assurance/process.json` (project-owned) where it is missing.
- The profile schema adds the optional `human_involvement.tier_rules.untested_touch_raises_tier` flag.
- The installed validator checks the process contract, verifier configuration, and migration records when present, and computes digests and the `AGENTS.md` size with CRLF line endings read as LF.
- The package version is in the root `VERSION` file; the validator checks that it matches the README and the manifest template.

### 1.5.0

All 1.5.0 changes are additive for existing installations.

- New `upstream-managed` tool `assurance_gate.py` (tier classifier and CI evidence gate with ratchet mode) and schemas `gate-result.schema.json` and `gate-baseline.schema.json`. An update adds them.
- The `github` and `gitlab` adapters now install the CI wrappers; an update adds them to installations that recorded those adapters. The `claude-code` adapter still has no files.
- Changing governance files (`.assurance/` outside evidence, `AGENTS.md`, and the gate's CI files) is classified significant, so it always needs a recorded human approval.
- Verification-result checks accept an optional `findings` list; the verifier runner fills it from `fail_on_output` checks, one finding per output line, so ratchet mode can tell a known finding from a new one inside the same check. Evidence and verifier commands no longer make the next tier's revision dirty.

### 1.6.0

All 1.6.0 changes are additive for existing installations.

- The `claude-code` adapter now installs `CLAUDE.md`, the `/deliver` skill, three stage subagents, and hooks (see "Claude Code adapter"). `--mode update --adapter claude-code` adds it to an existing installation.
- New `upstream-managed` tools `delivery_run.py` (run records under `.assurance/runs/`) and `agent_pack.py` (the derived `.assurance/agent-pack.md`).
- The run-manifest schema adds an optional `base_revision`; the migration-record schema accepts `derived` ownership for generated files such as the agent pack.
- The default process contract requires the `secret_findings` and `writes_outside_declared_paths` sentinels only. Existing `process.json` files are project-owned and keep their list; the update shows the change as a suggestion.
- `run_verifier.py` accepts `--sentinels` and `--output`; the installed validator checks that an agent pack is current and that an existing `CLAUDE.md` imports `@AGENTS.md`.

### 1.7.0

All 1.7.0 changes are additive for existing installations.

- The `github` adapter adds the asynchronous delivery workflow, the specification issue form, and `github_forge.py`; an update adds them to installations that recorded the adapter.
- New `upstream-managed` tools `async_deliver.py` (asynchronous run orchestrator) and `run_metrics.py`, and the schema `ticket-intake.schema.json`.
- Asynchronous runs need a model: a local Anthropic-compatible server on a self-hosted runner in a private repository, or `ANTHROPIC_API_KEY` as a repository secret with a per-run budget.

### 1.8.0

All 1.8.0 changes are additive for existing installations.

- New optional profile block `ticket_automation` (level, ticket sources, triage limits, guarded pickup, found-bug ticket limit) and an optional `findings` array in run manifests; existing profiles and manifests keep validating.
- New `upstream-managed` tools `triage.py` and `found_bugs.py` and the schema `triage-report.schema.json`.
- The `github` adapter adds the scheduled `assurance-triage.yml` workflow and new `github_forge.py` commands; `assurance-deliver.yml` accepts the `on_behalf_of` and `routine_only` dispatch inputs that pickup uses.
- Asynchronous runs and `/deliver` now record bugs found outside the work and file deduplicated tickets for them.
- The dependency-free Python validator now enforces the JSON Schema `maximum` keyword, which the PowerShell validator already enforced.

### 1.9.0

All 1.9.0 changes are additive, with one classifier correction.

- The agent pack has a Posture section with the preset rule and the profile's risk class, separation of duties, signing, external-effect policy, corporate-agent controls, and data rules, so each preset's pack states its own posture. An update regenerates the pack.
- The scaffolder's new `--mode record` stores an owner's adaptation of a `project-owned` or `merge-managed` file in the manifest.
- `tools/build_example.py` builds the example repository, and `tools/self_eval.py` with `evaluation/textkit-suite/` runs the self-evaluation.
- A work item's `Filesystem scope` may list several paths inside one pair of backticks, and asynchronous runs tell the builder which files fell outside the scope when that sentinel fails.
- Touch it, test it: a source file now also counts as tested when a test file anywhere is named after it (`test_x.py`, `x_test.go`, `x.test.ts`), not only when a test sits in the same directory. Changes in projects with a separate `tests/` tree are no longer raised a tier when their tests exist.

### 2.0.0

2.0.0 marks the delivery workflow as complete for GitHub. It has no breaking changes: every 1.x installation keeps validating, and the `human_involvement`, `delivery`, `process_light_mode`, and `ticket_automation` profile blocks stay optional. Update with `--mode update` as for any 1.x release.

Known gaps, by owner decision for this release:

- GitLab: the CI evidence gate wrapper and `gitlab_mr.py` ship but have not run on a GitLab instance; asynchronous runs, triage, and found-bug handling for GitLab are not built yet (design section 8.2).
- Jira intake (E2) is not built.
- Self-evaluation: the harness and suite ship; results depend on the model you run them with.

### 2.0.1

- Verifier records can be written per branch: `run_verifier.py` replaces `{branch}`, `{tier}`, and `{revision}` in a tier's `output`, and new installations default to `.assurance/evidence/{branch}/{tier}.json`. With the earlier fixed paths (`.assurance/evidence/verify.json`), every open pull request conflicts with the others as soon as one merges. `verifiers.json` is project-owned, so an update does not change it: switch each tier's `output` to `.assurance/evidence/{branch}/{tier}.json`, record the change with `scaffold_project.py --mode record --path .assurance/verifiers.json --apply`, and regenerate the agent pack. Records already on the main branch can stay where they are.

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
- records `--adapter claude-code|github|gitlab` selections in the manifest; adapter files arrive in later package versions;
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

`classify` computes the tier from the diff and `human_involvement.tier_rules`: governance files (`.assurance/` outside evidence, `AGENTS.md`, and the gate's CI files) and protected paths make a change significant; changes inside the routine allowlist and limits are routine; dependency manifests raise the tier to `dependency_change_tier`; `untested_touch_raises_tier` raises it one level for touched code without tests. A missing profile block or a failed classification is significant.

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

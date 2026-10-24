# Work item: WI-0003 Update general-prompts to 2.0.1

Status: `ready for review`

## Outcome

The repository runs the general-prompts 2.0.1 tools, and verifier records go to one folder per branch, so open pull requests no longer conflict on shared evidence files.

## Acceptance criteria

1. `AC-1`: `.assurance/assurance-system-manifest.json` records version `2.0.1`, and the installed-assurance validator reports no lineage or schema errors.
2. `AC-2`: both tiers in `.assurance/verifiers.json` write to `.assurance/evidence/{branch}/{tier}.json`, and running `verify` on this branch writes `.assurance/evidence/package-2.0.1/verify.json`.
3. `AC-3`: `verify-fast` and `verify` pass on this branch.

## Value check

Merging one pull request no longer forces every other open pull request to resolve evidence conflicts.

## Change declaration

- Change classes: `ci_enforcement`
- Risk class: `moderate`
- Escalation triggers present: governance files under `.assurance/` change, so the change is significant and needs a stakeholder approval.

## Execution and effect plan

- Filesystem scope: `.assurance/**`, `.github/**`, `docs/work-items/WI-0003-package-2-0-1.md`
- Estimated changed lines: 5000 (package files replaced by the scaffolder's reviewed update plan)
- External effects: `none`
- Rollback: `scaffold_project.py --mode rollback --migration MIG-20261024T161528Z-91a22225`

## Known limitations

- The installed-assurance validator still reports the profile's unresolved `REPLACE` placeholders, which predate this change.

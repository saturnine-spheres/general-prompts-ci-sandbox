# Work item: WI-0004 — Runnable verifier tiers and a usable run budget

## Outcome

Praxis runs against this repository can run its `verify-fast` and `verify` tiers, and a run is no longer Significant just because of the budget. Before this change, the profile's tier entrypoints were the template's `REPLACE command`. Its run budget was `0 EUR`, which Praxis cannot use, because it budgets in USD and needs a positive amount.

## Acceptance criteria

1. `AC-1`: `verification_tiers.verify-fast.entrypoint` is `bash .assurance/tools/verify-fast.sh` and `verification_tiers.verify.entrypoint` is `bash .assurance/tools/verify.sh`. The scripts are committed without the executable bit, so they are run through `bash`.
2. `AC-2`: both tiers pass on this change's commit, and their records are part of the change.
3. `AC-3`: `human_involvement.tier_rules.run_budget` is USD 5 with `max_duration_minutes` unchanged at 60. USD 5 is the Praxis team default (Praxis decision V0-8), and the lower of the two applies.
4. `AC-4`: the system manifest records the profile's new digest, so `validate_installed_assurance.py` reports nothing beyond the placeholder finding already on `main`.

## Change declaration

- Change classes: `dependencies_tooling`
- Risk class: `low`
- Changed files: `.assurance/project-assurance-profile.json` (entrypoints and run budget only), `.assurance/assurance-system-manifest.json` (the profile's `installed_digest` only), this work item, and the tiers' evidence.
- Not changed: `verify-live` and `verify-release` (Praxis does not run them), and the evidence paths, which the open general-prompts 2.0.1 update moves per branch.

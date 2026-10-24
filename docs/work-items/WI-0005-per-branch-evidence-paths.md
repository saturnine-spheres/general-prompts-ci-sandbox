# Work item: WI-0005 — Profile evidence paths follow the per-branch records

## Outcome

Tools that read the profile find each tier's record where the verifier writes it. Since general-prompts 2.0.1 (#5), `verifiers.json` files records under `.assurance/evidence/{branch}/{tier}.json`. The profile's `evidence_path` still named the earlier fixed paths, so Praxis looked in the wrong place.

## Acceptance criteria

1. `AC-1`: `verification_tiers.verify-fast.evidence_path` is `.assurance/evidence/{branch}/verify-fast.json` and `verification_tiers.verify.evidence_path` is `.assurance/evidence/{branch}/verify.json`, the same paths `verifiers.json` writes.
2. `AC-2`: both tiers pass on this change's commit and write their records under this branch's folder, and those records are part of the change.
3. `AC-3`: the system manifest records the profile's new digest, so `validate_installed_assurance.py` reports nothing beyond the placeholder finding already on `main`.

## Change declaration

- Change classes: `dependencies_tooling`
- Risk class: `low`
- Changed files: `.assurance/project-assurance-profile.json` (two `evidence_path` values), `.assurance/assurance-system-manifest.json` (the profile's `installed_digest`), this work item, and the tiers' evidence.

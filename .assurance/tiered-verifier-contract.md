# Tiered verifier contract

This contract defines behavior, not a universal script. Each repository implements native, version-controlled entrypoints and declares them in its project profile.

## Common interface

Each entrypoint MUST:

1. Resolve the repository root and refuse an ambiguous target.
2. Read the approved project profile and control catalog versions.
3. Record exact revision, dirty-state status, platform, architecture, runtime, UTC start time, and invoked command.
4. Resolve pinned tool identities and fail on missing or disallowed substitutions.
5. Select checks from the tier plus declared change classes and control triggers.
6. Resolve architecture/diagram triggers, SLO/error-budget state, control-evidence age, adversarial methods, privileged-access requirements, approved domain-contract checks, and progressive-delivery requirements before executing checks.
7. Enforce per-check timeout, cancellation propagation, process/resource limits, and safe cleanup.
8. Preserve each check outcome as `pass`, `fail`, `error`, `skipped`, `not_run`, `inconclusive`, or `blocked`.
9. Emit one schema-valid verification-result JSON record even after failure, unless the runtime cannot write; that condition is itself a blocking error.
10. Exit nonzero if any blocking check is not `pass` and lacks a validated active waiver.
11. Never convert retry success into an unqualified pass; retain attempt history and flake status.

Every evidence attachment MUST include media type, size, SHA-256 digest, producer, and local path or durable URI. Secrets and prohibited data MUST NOT appear in evidence.

## `verify-fast`

Purpose: rapid developer feedback, not delivery assurance.

Baseline checks:

- formatting or format-drift check;
- compile/type check for affected components;
- focused static analysis/lint;
- affected deterministic unit tests;
- changed schema/config syntax validation;
- changed architecture/flow/state diagram parse and render checks;
- secret scan of changed content;
- work-item/profile/catalog schema validation.

`verify-fast` MAY use dependency caches but MUST record cache identity when it can affect results. It MUST NOT be reported as the normal repository gate.

## `verify`

Purpose: complete ordinary repository gate for the declared revision.

Baseline checks:

- everything in `verify-fast` from a clean process context;
- full unit and contract tests required by the matrix;
- repository-wide static analysis and configured security analysis;
- dependency, vulnerability, license, and secret scans;
- schema, fixture, migration, documentation-link, generated-drift, and policy validation;
- architecture/threat completeness, node/flow identity, contract/config traceability, and documented-to-deployed drift validation when triggered;
- API compatibility and versioning checks when triggered;
- accessibility automation and real-browser/UI checks when triggered;
- observability, SLO/error-budget, timeout, cancellation, resource-bound, and regression checks when triggered;
- adversarial-method selection/results, privileged-access evidence age, control-effectiveness evidence age, and approved domain-contract checks when triggered.

Pinned scanner versions and advisory data are separate identities. Vulnerability evidence MUST record scanner digest/version, advisory source, database snapshot/revision, fetched-at time, scan time, and maximum permitted age.

## `verify-live`

Purpose: establish properties that mocks or static checks cannot prove.

Baseline behavior:

- provision isolated disposable production-equivalent dependencies;
- use unique namespaces and minimally privileged short-lived identities;
- pin engines, images, extensions, schemas, drivers, and service contracts;
- exercise real concurrency, permissions, clocks, migration behavior, network failures, retries, cleanup, and external confirmation selected by the profile;
- exercise triggered system-of-record/reconciliation/recovery, adversarial/fault scenarios, third-party continuity/exit, SLO telemetry, and rollback/safe-disable properties against declared limits;
- prevent access to production unless a separate production-test authority explicitly grants it;
- retain provisioning and cleanup evidence;
- fail if cleanup is incomplete or target identity is ambiguous.

Live tests MUST state the exact property for which the environment is production-equivalent. They MUST NOT generalize beyond that evidence ceiling.

## `verify-release`

Purpose: qualify an immutable release candidate.

Baseline checks:

- all required `verify` and `verify-live` results against the same revision or traceably identical source;
- clean checkout in a disposable environment;
- reproducible build or declared equivalence comparison;
- complete configured security, dependency, license/IP, secret, and policy scans;
- SBOM, artifact inventory, build provenance, checksums, and signature verification;
- upgrade, migration, rollback, backup/restore, disaster-recovery, safe-disable, and platform-support checks selected by profile;
- current architecture/threat review, control-effectiveness assessment, SLO/error-budget state, approved domain-contract evidence, penetration/adversarial evidence, privileged-access review, and third-party resilience evidence selected by triggers;
- a progressive-delivery plan bound to the candidate with stages, signals, promotion/abort thresholds, blast-radius ceilings, automatic halt, rollback, safe-disable, and owner; execution occurs only under separate deployment authority;
- performance/resource budgets and capacity evidence;
- release notes, compatibility/deprecation notices, observability/runbook/on-call readiness;
- independent review and required human approval;
- confirmation that protected-branch, tag, environment, and release rules are enforced.

Release publication is a separate external effect. Passing `verify-release` does not authorize publishing or deployment.

## Portable pseudocode

```text
run_tier(tier, work_item):
  context = resolve_immutable_context_or_stop()
  profile = validate_and_load_profile()
  catalog = validate_and_load_catalog()
  checks = select(tier, work_item.change_classes, profile, catalog)
  assert_authority(checks, context)
  result = begin_result(context, tier, checks)
  for check in dependency_order(checks):
    if cancelled: record(check, "blocked", "cancelled"); break
    if prerequisite_not_passed(check): record(check, "blocked"); continue
    identity = resolve_pinned_tool(check.tool)
    if identity mismatch: record(check, "blocked"); continue
    outcome = run_bounded(check, identity, timeout, resources)
    record_exact_attempts_and_evidence(result, outcome)
  cleanup = run_idempotent_scoped_cleanup()
  finalize_and_validate(result, cleanup)
  exit_nonzero_unless_all_blocking_controls_satisfied(result)
```

## CI relationship

CI MUST invoke the same version-controlled tier entrypoints used locally. CI MAY provide platform/runtime matrices, isolated secrets, ephemeral infrastructure, artifact retention, concurrency control, and approval environments. CI MUST NOT reimplement hidden pass/fail logic that makes local and CI meanings diverge.

## Safe scaffold

A repository wrapper should contain only orchestration and mappings, for example:

```text
verify --tier <fast|normal|live|release> --work-item <path> --output <result.json>
```

The wrapper maps named checks to native tools declared in the profile. It refuses unknown tiers, unknown tools, missing pins, undeclared network access, ambiguous repositories, and output paths outside its evidence directory.

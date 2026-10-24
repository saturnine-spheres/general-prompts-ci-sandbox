# Assurance glossary

These definitions constrain claims made by agents, developers, reviewers, and automation.

## Acceptance criterion

A numbered, observable behaviour of a work item that a user or caller would notice, stated so review can judge it `met`, `not_met`, or `not_verifiable`. Tests passing, lint, and coverage are gates, not acceptance criteria. A review that approves cannot carry a `not_met` verdict.

## Agent pack

A generated summary of at most 6 KiB that a coding agent loads next to `AGENTS.md`: the repository's verifier commands, tier rules, process stages, delivery rules, stop conditions, and blocking control IDs, rendered from the installed profile, process contract, verifier configuration, and catalog. It carries no authority of its own and is regenerated whenever those files change.

## Architecture diagram

A version-controlled, renderable model of one declared structural view—system context, component/dependency, deployment/environment, or data-flow/trust-boundary—with stable node/flow IDs and traceability to contracts, implementation/configuration, tests, ownership, and deployment evidence. A diagram is current only when its review age and diagram-to-reality drift checks satisfy the profile.

## Blast radius

The maximum population, traffic, region, tenant, data, permissions, external effects, spend, resources, and duration exposed before a change is halted, rolled back, or safely disabled. A staged rollout must declare measurable ceilings rather than describe exposure as “small.”

## Complete verification

Every gate required by the approved profile, applicable control triggers, change-class matrix, work item, and active authoritative obligations ran against the exact claimed revision and target environments; each blocking result passed; evidence is schema-valid and retained; and no required result is skipped, unavailable, inconclusive, stale beyond its declared limit, or hidden by a waiver. A waiver means verification is qualified, not complete.

## Critical path or branch

Code or configuration whose failure can violate authorization, confidentiality, integrity, availability, safety, financial, legal, privacy, tenancy, data-loss, release, or recovery invariants. The project profile must identify critical paths by path, component, tag, or ownership rule; an agent may add an item but may not remove one without approval.

## Control effectiveness

Design effectiveness means a control, as specified, can prevent, detect, or recover from its target failure. Operating effectiveness means retained evidence from the declared population, period, and risk-stratified sample shows that it actually did so. Configuration presence, one convenient example, or an implementer assertion proves neither.

## Delivery tier

The approval route of one change: `routine`, `notable`, or `significant`, computed from the actual diff and the profile `human_involvement` rules. Unknown or failed classification is `significant`. The tier decides who must approve; the risk class decides which controls and gates apply. The two are declared separately and neither lowers the other.

## Domain authority

The qualified human role, approved contract, or organizational policy authorized to define a specialized financial, legal, medical, safety, employment, tax, accounting, regulatory, or other domain requirement. Software-assurance actors may trace and verify implementation against that requirement but cannot create, reinterpret, approve, or accept risk for it.

## External effect

Any state change outside the isolated local workspace: network transmission; message, ticket, email, payment, order, or account action; remote Git change; deployment; database or cloud mutation; credential issuance; publication; production query with side effects; or action affecting another person or system. Reading externally can also be an effect when it discloses identity, query content, regulated data, or incurs cost.

## Flowchart or state diagram

A version-controlled behavioral model required by a declared trigger: authorization/approval branching, multi-stage transaction, state machine, retry/timeout/recovery, rollback/safe-disable, external effect, system-of-record/reconciliation, or incident/continuity. Every branch, transition, negative path, partial failure, compensation, cleanup, and terminal outcome maps to a contract, executable test/control, or explicit residual-risk decision. It is not required for a trivial linear edit.

## High risk

A profile risk class or work-item escalation caused by at least one declared trigger: authentication/authorization or tenant boundary change; sensitive/regulated data; destructive or irreversible operation; production effect; cryptography/key handling; safety or high-impact decision; material model/tool/provider change; public API breaking change; migration with data-loss potential; release/signing/provenance change; critical availability/recovery path; or impact above the profile's human, financial, legal, privacy, or operational threshold.

## Independent review

Review by an authorized identity that did not implement or direct the change and is not operating in the same model conversation, agent state, writable workspace, mutable evidence store, or correlated execution context. The reviewer receives immutable revision and evidence identities, can reproduce or challenge results, and has no incentive or technical mechanism to rewrite the implementation's evidence. A second pass by the same person/agent/context, a renamed self-review, or a subagent inheriting the same authority and mutable context is not independent.

## Material change

A change that alters an external contract, security/privacy boundary, production dependency, toolchain, CI enforcement, external service, model/provider, plugin/MCP server, dataset, data classification/residency/retention, supported platform, migration, release/signing path, cost model, high-impact decision, or risk-control behavior. The profile may define additional deterministic triggers but may not silently exclude these baseline triggers.

## Operational

Deployed in the declared target environment, enabled for the declared population, observed through approved telemetry, within service and risk thresholds, supported by on-call/ownership and rollback/recovery procedures, and confirmed by current operational evidence. Implemented or deployed alone does not mean operational.

## Process contract

The engine-neutral description of the delivery workflow in `process-contract.schema.json`: stages, artifacts per stage, gates, tier-based approvals, the rework limit, and required sentinels. Adapters read it; it names no harness or forge.

## Progressive delivery

Release of one immutable candidate through ordered, bounded exposure stages. Each stage compares declared candidate and control signals for a minimum observation period, promotes only on passing evidence, halts automatically at abort thresholds, and verifies rollback or safe-disable within the declared blast-radius and time limits.

## Production-equivalent

An isolated environment whose relevant versions, configuration, identity/permission model, data shape and scale, concurrency, network behavior, failure modes, and external contracts match production closely enough to establish the specific claimed property. Equivalence is per property and must be declared; a generic staging label is insufficient.

## Representative evidence

Evidence selected by a declared sampling rule that covers the relevant populations, boundaries, failure modes, platforms, and risk strata. Convenient or synthetic examples alone are not representative. The record states population, selection method, sample size, exclusions, and the claim ceiling.

## Ratchet mode

A CI evidence gate mode for legacy repositories in which a blocking-check finding already listed in the target branch's approved baseline does not fail, while every new finding and every process finding does. The baseline may not grow without explicit maintainer approval, and an optional report-only period ends on a recorded date.

## Reproducible

An independent authorized runner can use identified source, inputs, dependencies, toolchains, configuration, environment, and commands to produce the same artifact digest or a declared equivalence result within stated tolerances. Network data, advisory databases, clocks, randomness, and platform variation are pinned or recorded. “Builds twice on one machine” is evidence but not sufficient by itself.

## Rigor budget

The expected evidence effort of a work item, `light`, `standard`, or `full`, and the condition that would justify more. Materially exceeding it is a stop condition, not a reason to keep going.

## Run manifest

The per-run audit record in `run-manifest.schema.json`: specification reference, computed and approved tier, each stage with runner, model, duration, cost, and outcome, artifact digests, and human approvals.

## Safe cleanup

Removal or revocation of temporary resources, credentials, locks, test data, network access, reservations, containers, files, and remote state without deleting pre-existing or unrelated state. Cleanup is bounded to resolved targets, idempotent, logged, confirmed, and backed by recovery or escalation when it fails.

## Sentinel

A measured run property with an expected value recorded in a verification result: spend, egress outside the allowlist, secret findings, writes outside declared paths, leftover resources, or unexpected forge actions. Each sentinel compares its observed value with the expected value by `equals` or `at_most`. A verification result cannot pass while any sentinel is unmeasured or fails that comparison.

## Service-level indicator, objective, and error budget

An SLI is a versioned query or formula over identified telemetry that measures a user-visible service outcome. An SLO is its target over a declared population and window. The error budget is the permitted shortfall; its policy sets burn thresholds, release restrictions, recovery work, exception authority, and restoration criteria.

## Threat model

A maintained record of assets, actors, boundaries, data flows, dependencies, plausible threats and abuse cases, preconditions, preventive/detective/recovery controls, verification, residual risk, and human ownership. It must change with the architecture and is not equivalent to a scanner report.

## Verification evidence ceiling

The strongest conclusion supported by the method and sample. Static analysis cannot prove runtime operation; mocks cannot prove a real integration; synthetic data cannot prove production representativeness; a local test cannot prove deployment; and self-review cannot prove independent approval.

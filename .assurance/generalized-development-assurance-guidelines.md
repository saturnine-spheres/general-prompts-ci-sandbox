# Generalized development and corporate-agent assurance guidelines

Version: 1.1.0\
Status: reusable policy reference; adoption requires an approved project profile and control catalog\
Normative language: uppercase terms follow BCP 14 (RFC 2119/RFC 8174)

## 1. Purpose and system boundary

This document defines a cross-project assurance model for ordinary software engineering and governed corporate agents. It preserves the original development-assurance intent—static and mutation verification, reproducible database qualification, transaction/evidence integrity, adversarial testing, repository-wide gates, manual review, and source-control assurance—while moving applicability and enforcement into machine-readable layers.

This document is not a universal prompt. A repository uses:

1. a compact root `AGENTS.md` for immediate operating rules;
2. an approved project assurance profile for project-specific facts and thresholds;
3. a stable control catalog for normative requirements and triggers;
4. a declared work item and change-class matrix for each change;
5. version-controlled verifier entrypoints;
6. schema-valid evidence, review, waiver, and effect records.
7. project-owned product, requirements, architecture/ADR, roadmap, test-strategy, status, and work-item documents;
8. an installed-system provenance manifest recording package identity, per-file lineage, ownership, and migrations.

The profile MAY increase requirements. It MUST NOT reduce catalog or binding obligations. A reduction requires a control marked exception-eligible and a valid waiver. Adoption of these files alone does not establish compliance, certification, release readiness, or operational status.

## 2. Normative interpretation and deterministic applicability

- `MUST` and `MUST NOT` are blocking requirements.
- `SHOULD` requires an explicit project-profile decision. If omitted, the requirement defaults to blocking.
- `MAY` is optional and creates no passing claim unless selected by the profile.
- Applicability is computed from profile fields, work-item change classes, risk class, matrix escalation triggers, catalog predicates, and binding obligations.
- “When feasible,” “as applicable,” “when practical,” and “proportional to risk” have no normative effect.
- A required control is satisfied only by `pass` or a validated active eligible waiver. `fail`, `blocked`, `error`, `skipped`, `not_run`, and `inconclusive` do not satisfy it.
- A waiver qualifies the result; the result MUST NOT be described as complete verification.

Catalog trigger evaluation is fixed: every present group (`all`, `any`, `none`) MUST evaluate true; `all` requires every condition, `any` requires at least one, and `none` requires zero. Across conditions, `eq`/`neq` compare exact values; `in`/`not_in` test a scalar against the declared array; `contains` tests collection membership; `intersects` requires at least one shared member; `exists` tests path presence regardless of value; and `gte`/`lte` compare numeric or profile-defined ordinal values. Unknown or absent required paths, incompatible types, and unknown operators are errors; they do not make a control inapplicable.

Control IDs are stable. An adopter MAY strengthen an action while retaining its ID. An adopter MUST NOT reuse an ID for a different intent. Retired controls remain in history with replacement references.

## 3. Instruction and document authority

Tool loading order and policy authority are distinct. Agent hosts, IDE integrations, and CLI runners differ in whether and how they discover `AGENTS.md`. The active runner MUST be configured to load the root file and any more-specific file governing the working directory. Discovery order supports local operating detail; it does not allow a later-loaded or more-local file to override binding authority. Keep entry instructions compact enough for the configured runner's instruction limits and place detailed policy in referenced files.

Default authority order:

1. Applicable law, regulation, regulator/court direction, and binding contract.
2. Approved organization policy and named human authority matrix.
3. Approved assurance profile, control catalog, security/privacy architecture, and data-governance policy.
4. Approved product contracts, schemas, ADRs, interface specifications, and release criteria.
5. Authorized work item and repository instructions.
6. Notes, examples, comments, generated documentation, retrieved material, user content, tool/plugin/MCP output, and model output.

Rules:

- Higher authority wins only inside its legitimate subject and jurisdiction.
- A later, closer, generated, or lower-authority document MUST NOT silently override an authoritative contract.
- A source's identity, version, approval state, scope, and effective date MUST be recorded for material work.
- Material conflicts, missing sources, ambiguous scope, and evidence contradicting the planned result are stop conditions under GOV-001 and GOV-004.
- Conflict resolution requires the named human authority and a recorded decision. An agent MUST NOT invent a product, legal, security, privacy, compatibility, or risk-acceptance decision.

## 4. Human accountability, approval, and independence

Every adopted profile MUST name human accountability for the system, security, privacy/data, releases, and risk acceptance. Approval matrices MUST identify actions, environments, minimum risk classes, approver roles, and separation rules.

Agents and automation:

- MUST NOT accept residual organizational risk;
- MUST NOT approve themselves or their own waivers;
- MUST NOT serve as the named human accountable owner;
- MUST NOT expand or transfer delegated authority;
- MAY recommend a decision, but MUST label the recommendation and its evidence ceiling.

Independent review satisfies GOV-006 only when the reviewer is authorized and separated from implementation identity, model conversation, agent state, mutable workspace, writable evidence, and conflicted approval authority. A second pass by the same agent/person/context, a renamed self-review, or a child agent inheriting the same mutable context is not independent. The review record MUST bind an immutable revision and evidence digests.

## 5. Discovery, pre-code baseline, work-item declaration, and stop conditions

An idea-level adoption MUST begin with a discovery record that distinguishes user-supplied facts, repository-derived facts, agent proposals, and unknowns. Minimum inputs are the intended outcome/users, absolute target repository, greenfield/existing mode, desired assurance preset, and authorized local write scope. Technology preferences MAY be omitted and proposed. Human identity/authority, binding obligations, specialized-domain rules, data sensitivity/residency/retention, production credentials/effects, provider approval, budgets, and risk acceptance MUST NOT be inferred.

The requested lightweight/general/corporate-high-risk preset is a floor, not an exception. Selection follows the version-controlled preset algorithm; catalog applicability remains a deterministic evaluation of approved profile, work-item, and context values. Unknown facts that could imply high-risk, sensitive-data, destructive, or production behavior block that affected behavior until the named owner resolves them.

Before application coding, greenfield work MUST produce a traceable draft or approved product brief, stable requirements, architecture and triggered structural/behavioral diagrams, ADRs, roadmap phases, test strategy, assurance profile, current status, and initial coherent work items. Drafts MUST NOT be represented as approved. Existing repositories MUST map and preserve equivalent authoritative documents instead of duplicating or silently replacing them.

Installation and updates MUST record package version/source/digest, baseline revision, per-file upstream and installed digests, ownership, local adaptations, and migration history. Project-owned decisions and historical evidence MUST NOT be automatically overwritten. Clean upstream-managed files may be replaced only after digest comparison; merge-managed files require reviewed reconciliation.

Before material implementation, the work item MUST declare outcome, non-goals, authoritative sources, affected contracts/data, change classes, diagram triggers, risk, tools, external effects, bounds, test plan, definition of done, and stop conditions. Large work MUST be divided into coherent reviewable units with independent acceptance evidence.

The actor MUST stop before further mutation for:

- missing/expired authority, approval, credential, contract, profile, control, or owner decision;
- conflicting authoritative sources or contradictory evidence;
- destructive, irreversible, production, privacy, legal, financial, or safety effects outside explicit authority;
- secrets or unexpected sensitive/regulated data in prompts, source, logs, fixtures, output, or evidence;
- overlapping unexpected dirty state that cannot be safely preserved;
- a required blocking gate that is unavailable, failing, skipped, inconclusive, or unable to emit evidence;
- an unapproved new tool, production dependency, CI change, external service, model/provider, plugin/MCP server, dataset, or egress destination;
- impending cost, runtime, token, request, rate, resource, or egress overrun;
- delegation beyond the parent grant;
- cleanup/rollback whose exact targets or safety cannot be demonstrated.

Retries MUST retain attempt history and MUST NOT erase the stop condition. A formal waiver applies only to eligible controls; agents cannot approve it.

Process guardrails keep effort proportionate to risk:

- **Acceptance criteria.** Every work item declares numbered, observable acceptance criteria. Review records a `met`, `not_met`, or `not_verifiable` verdict for each one; a review that approves cannot carry a `not_met` verdict. Mechanical checks are gates, not acceptance criteria.
- **Two-strike rule.** After two failed qualification or remediation rounds on the same question, the actor MUST stop and ask the owner whether the approach (model, design, or scope) is wrong before planning a third round.
- **Rigor budget.** Every work item declares its expected evidence effort (`light`, `standard`, or `full`) and the condition that would justify more. Materially exceeding the declared budget is a stop condition.
- **Touch it, test it.** When the profile sets `untested_touch_raises_tier`, a change to code without tests raises the delivery tier by one level, and the builder adds characterization tests for the touched behaviour before changing it.
- **Light mode and re-entry triggers.** A profile MAY declare a light process in `process_light_mode` for named kinds of work. It MUST list re-entry triggers; when any re-entry trigger fires, the full process applies again for that work item. Light mode never lowers the catalog baseline or a matrix minimum.

## 6. Material changes and tool adoption

The following are material by default: external contract; architecture, trust, identity, security, privacy, network, deployment, or system-of-record boundary; production dependency; toolchain; CI enforcement; external service; model/provider; plugin/MCP server; dataset; data classification/residency/retention; supported platform; migration; privileged access; SLI/SLO/error-budget definition; progressive-delivery policy; release/signing/provenance; cost model; high-impact decision; and risk-control behavior.

Each material-change record MUST include:

- problem and intended benefit;
- evaluated alternatives, including no change;
- exact version/digest and provenance;
- capabilities, permissions, network/data access, and supply-chain risk;
- license/IP and provider terms;
- maintenance owner, update/deprecation plan, and noise/suppression budget;
- compatibility, rollout, rollback, and safe-disable plan;
- verification/evaluation evidence;
- required human authorization.

Broad linter bundles and scanners SHOULD NOT be adopted by default. Select a small non-overlapping set, pin it, and investigate findings. Possible secrets and security alerts MUST NOT be automatically suppressed. False positives require narrow fingerprinted rules, reason, owner, and review date.

## 7. Repository working agreement

### Before changing files

The actor MUST read governing instructions, contribution guidance, current status, authoritative designs, ADRs, and the work item; inspect current implementation/tests; and define completion evidence. Planned behavior MUST NOT be assumed implemented.

### During implementation

- Preserve unrelated user/contributor changes.
- Follow approved architecture and dependency direction.
- Update code, tests, schemas, fixtures, migrations, architecture/threat/flow/state diagrams, documentation, observability, and generated artifacts together when they express one contract.
- Keep compatibility, versioning, migration, rollout, rollback, safe-disable, cancellation, timeout, idempotency, and resource bounds explicit.
- Correct defects caused by or invalidating the work. Add regression coverage under ENG-003.
- Record unrelated defects separately unless the authorized scope explicitly includes them.
- Introduce no secret, personal/private conversation, prohibited data, or fabricated evidence.

### Delivery

Review the complete diff and intended file list. Commit, sign, push, publish, merge, deploy, or mutate remote state only under explicit authority. Report exact changes, passes, failures, skipped/unrun checks, effect status, limitations, unknowns, compatibility/security/privacy impact, and follow-up owners.

## 8. Architecture, threat models, diagrams, and behavioral flows

`DES-001` triggers for the `architecture_design` change class and the catalog's declared material boundaries. The actor MUST update `architecture-assurance.template.md` before approval with scope, authoritative requirements, assets, users, components, dependencies, environments, identities, trust boundaries, data classifications/flows, external effects, failure modes, threats/abuse cases, mitigations, tests, residual-risk owners, and review identity. Threat modeling is a maintained engineering record, not a one-time workshop or a generated picture.

`DES-002` requires the profile-selected views as version-controlled diagram source: system context; container/component/dependency; deployment/environment; and data-flow/trust-boundary. Nodes and flows use stable IDs and map to contracts, ADRs, implementation/configuration, tests, and deployment evidence. Verification MUST parse and render the source, resolve references, and compare documented inventories/flows with authoritative generated configuration or runtime inventories selected by the profile. Unexplained drift blocks the affected claim. A rendered diagram does not prove runtime correspondence without that traceability evidence.

Flowcharts are conditional, not decorative. The work item MUST declare diagram triggers. `DES-003` requires a behavioral flow or state diagram for authorization/approval branching, multi-stage transactions, state machines, retry/timeout/recovery, rollback/safe-disable, external effects, system-of-record/reconciliation, or incident/continuity paths. Every decision branch, transition, timeout, negative path, partial failure, compensation, reconciliation, cleanup, and terminal result maps to a contract, executable test/control, or human-owned residual-risk decision. Work with none of those triggers records `none` and does not create a flowchart.

## 9. Static, schema, mutation, and repository verification

The project profile declares languages and exact pinned tools. Verification SHOULD combine the language formatter, compiler/type checker, native correctness analyzer, focused deeper analysis, unit/contract tests, semantic security analysis, dependency/license scans, and documentation/schema gates.

For schemas, canonical fixtures, generators, parsers, and validators:

- validate every authoritative schema and canonical fixture in scope;
- maintain deliberately corrupted mutations proving invalid inputs are rejected;
- validate exact keysets when unknown or missing members are prohibited;
- test malformed serialization, type/shape errors, extra/missing members, ordering where semantic, substituted projections, inconsistent mirrors, and incorrect digests;
- regenerate committed artifacts and require an empty diff;
- derive expected inventories from authoritative manifests while detecting unexpected additions/deletions;
- validate embedded documentation examples and cross-contract consistency.

Property-based testing SHOULD cover parsers, serializers, canonicalization, state machines, arithmetic/sequence invariants, and protocols. Mutation testing SHOULD target declared critical paths. Survivors require analysis; superficial execution-only assertions do not count as correction.

## 10. Database and datastore qualification

For datastore changes, the profile declares engines, versions/digests, compatibility modes, drivers, extensions, migration rules, isolation assumptions, and live-test properties.

Qualification MUST:

- use an isolated disposable instance or namespace;
- prevent silent engine/image/dependency substitution;
- use unique run identifiers and scoped cleanup;
- install exact migrations, routines, constraints, permissions, representative data, and generated definitions;
- verify object ownership, signatures, execution rights, safety/volatility/concurrency classifications, and role/user access supported by the engine;
- test forward migration, invariants, data-loss/downtime budgets, concurrency, backup/restore, abort thresholds, and rollback or recovery;
- state the property for which the environment is production-equivalent.

If a datastore lacks a feature such as multi-record transaction, deferred constraint, skip-locked claim, advisory lock, row-level policy, or database routine, the design MUST identify the invariant and implement a native alternative. Conditional batches, optimistic concurrency, idempotent state machines, transactional messaging, sagas, and compensation are acceptable only after failure semantics are tested. The alternative MUST NOT silently weaken consistency, isolation, tenancy, auditability, or rollback guarantees.

## 11. Claiming, leasing, sequencing, and time

Work-claim systems MUST test deterministic ordering with a unique tie-breaker, one/many/partial batches, genuinely competing sessions, duplicate-prevention behavior, tenant/partition boundaries, sequence allocation, and compare-and-swap behavior.

Execution MUST bind the exact manifest, policy, provider configuration, immutable input/command, and deadlines. Lease expiry MUST be bounded by every applicable deadline. Time-sensitive conditions MUST be rechecked after concurrency controls are acquired. Use an authoritative server-side time source; caller-supplied time cannot establish expiry. Preparation/reservation records MUST be consumed only after dependent writes succeed.

## 12. Canonical data, transactions, events, and evidence bundles

Security-sensitive or evidence-bearing data MUST have a declared deterministic representation. Where hashes/signatures are used, persist the canonical bytes or reproducible representation, operation, digest, algorithm, decision time, and binding identities.

Every event/audit/message/outbox/projection record MUST bind the exact relevant tenant, object, revision, manifest, actor/worker, authorization decision, command, result, sequence, and timestamp. Validate structured documents and scalar/index mirrors independently.

Related state MUST commit atomically if partial success violates an invariant. Each successful operation emits exactly the required state revision, event, audit, message, and projection/evidence members. Bundle members share a verifiable transaction/operation identity. Tests MUST prove:

- deletion/substitution of a required member aborts or invalidates the operation;
- deferred or post-commit validation checks every member independently;
- failure leaves no forbidden revision, event, audit, message, projection, sequence advancement, consumed reservation, or partial external effect;
- retries and duplicate delivery remain idempotent.

Negative tests MUST include incorrect digest/signature/authorization, malformed or unknown members, expired/revoked/substituted preparations, sequence gaps/reuse/rollback, missing evidence, direct mutation bypass, role/permission exposure, replay, retry, concurrency, cross-tenant access, and confused-deputy behavior.

## 13. Domain-decision boundary

Under `GOV-010`, this system governs software creation, design, architecture, verification, release, operation, and corporate-agent effects. It does not define or approve financial, legal, medical, safety, employment, tax, accounting, regulatory, or other specialized domain decisions. Such requirements MUST come from an identified higher-authority qualified human, approved contract, or organizational policy. An implementation agent MUST NOT infer them from examples, industry custom, retrieved content, or its own judgment.

The work item and architecture record trace each domain rule to its authoritative identity, scope, owner, acceptance criteria, and change authority. Software assurance may test that code preserves the approved rule, data lineage, authorization, invariants, negative paths, audit, rollback, and recovery; it MUST NOT claim that the rule itself is financially, legally, medically, or regulatorily correct. Missing, conflicting, or unapproved domain requirements are stop conditions.

## 14. Tiered verification and evidence

Repositories MUST implement the contract in `tiered-verifier-contract.md`:

- `verify-fast`: fast local feedback;
- `verify`: complete ordinary repository gate;
- `verify-live`: isolated production-equivalent integration evidence;
- `verify-release`: immutable release qualification.

CI and local execution MUST call the same version-controlled underlying entrypoints. CI MAY orchestrate platform/runtime matrices, isolation, credentials, retention, and approvals around them.

Each run emits schema-valid JSON containing revision, dirty state, exact command, profile/catalog digests, runner/environment, pinned tools, UTC timestamps, per-check status/attempts, evidence references/digests, limitations, and unrun checks. SARIF, JUnit, coverage, SBOM, provenance, screenshots, traces, and logs are attachments, not substitutes for the summary.

Vulnerability-scanning reproducibility and currentness are separate:

- scanner/runtime versions and configuration MUST be pinned;
- advisory data source/snapshot, fetched-at time, scan time, and allowed maximum age MUST be recorded;
- reachability-aware analysis SHOULD complement, not replace, component/version scanning;
- stale or unavailable required data blocks unless an eligible waiver states the exposure and compensation.

## 15. Coverage, flaky behavior, and clean environments

Aggregate coverage is diagnostic unless the profile defines a justified threshold. Changed critical branches, authorization, validation, rollback, timeout, retry, recovery, and failure paths MUST be exercised.

Concurrency/timing-sensitive tests MUST be repeated according to a declared count. Randomized tests record the seed. Relevant time zones, locales, encodings, filesystems, path conventions, architectures, and platforms come from the profile. Flaky tests are defects with owners; blind retry success is not an unqualified pass.

Release verification MUST use a clean disposable checkout without undeclared tools, credentials, caches, services, environment variables, or machine-global state. Reproducibility records all inputs and either exact artifact digests or approved equivalence tolerances.

## 16. API, UI, accessibility, performance, SLOs, and observability

API/schema changes MUST include exact schema validation, consumer contracts, compatibility diff, versioning, deprecation, migration, rollback, and owner approval selected by the evidence matrix.

UI changes MUST be tested in real supported browsers/devices. Automated accessibility scans are necessary evidence but insufficient alone. Required evidence includes keyboard/focus behavior, zoom/reflow, assistive technology, visual/error/loading/empty states, accessible authentication/consent where present, and manual review. The profile declares the applicable accessibility target; the informative reference map points to WCAG 2.2.

Performance changes MUST define workload, baseline, latency/throughput/resource/cost budgets, sample count, variance, warm/cold state, saturation behavior, and pass thresholds before execution. Test cancellation/timeouts and budget enforcement.

Operational changes MUST provide redacted logs, metrics, traces, alerts, correlation identities, retention, owners, and runbooks. Telemetry MUST NOT contain secrets or data prohibited by the profile. An implementation is not operational until deployed, observed within thresholds, supported by ownership, and recoverable.

Production services MUST declare user-visible service-level indicators, objective thresholds, measurement windows, telemetry/query identity, and human owner. The error-budget policy defines burn thresholds, release restriction or halt, required recovery work, exception authority, and restoration criteria. A performance budget does not substitute for an SLO: performance measures a workload; an SLO constrains the service outcome experienced by its declared population.

## 17. Security, adversarial assurance, privileged access, and software supply chain

Run secret detection on changed content, in CI, and periodically over history. A real secret requires revocation/rotation and incident assessment; deleting it from the current tree is insufficient.

Dependency assurance MUST inventory direct/transitive libraries, build tools, containers, operating-system components, generated artifacts, models, datasets, and plugins selected by the profile. Pin identities; verify provenance; scan vulnerabilities; review licenses/IP and terms; maintain allowlists; produce an SBOM for release.

Build/release systems MUST protect source and artifact integrity, use approved signing custody, verify signatures independently, generate provenance, restrict protected-ref bypass, and test hosting rules. SLSA/SPDX mappings are informative until the adopter declares and verifies exact target requirements.

`SEC-006` selects adversarial methods from explicit risk/change triggers: fuzzing, dynamic analysis, penetration testing, red teaming, fault injection, and domain abuse suites. The profile declares scope, cadence, independence, environment, success thresholds, evidence ceiling, remediation/disclosure deadlines, intake channel, and PSIRT owner. Findings retain reproduction, triage, root cause, correction, regression, and retest evidence. A clean automated scan does not replace a triggered independent penetration or adversarial exercise.

`SEC-007` governs privileged access through separated development/test/build/production environments and identities, least privilege, just-in-time time-bounded grants, authorization, session audit, periodic recertification, revocation, and logged break-glass with an immediate after-action review. Shared, embedded, inherited, or unbounded production credentials are prohibited. Access evidence records effective permission and expiry, not merely a requested role.

## 18. Privacy, data governance, and test data

The profile MUST define data classifications, default classification, purposes, owners, residency, retention/deletion, legal holds, DLP, provider/subprocessor disclosure, prompt/log/telemetry handling, training use, and test-data rules.

Unknown data receives the default classification. Collection and disclosure MUST be minimized. Secrets use approved custody references and MUST NOT enter prompts, source, logs, fixtures, model memory, evaluation data, or evidence.

Synthetic/de-identified test data is the default. Use of personal, production-derived, confidential, restricted, or regulated data requires recorded authority, minimization, isolation, access, retention, deletion, and re-identification review. Evidence MUST state the dataset identity/classification without embedding prohibited records.

## 19. Progressive release, backup/recovery, third-party resilience, and platform lifecycle

Release candidates are immutable. `verify-release` MUST bind source, inputs, tools, artifacts, SBOM, provenance, signatures, review, and approval. Passing release verification does not authorize publication or deployment; those are separately authorized effects.

Production deployment triggers `REL-003`. The profile declares ordered exposure stages, candidate/control signals, minimum observation, promotion authority, automatic halt thresholds, rollback/safe-disable targets, and blast-radius limits for population, traffic, region, data, effects, spend, and duration. Each stage binds the same immutable candidate and records measurements. Promotion stops on missing or inconclusive evidence; abort verifies final state rather than assuming rollback succeeded.

Changed data/stateful services MUST meet declared RPO/RTO through backup integrity, restore, failover, dependency recovery, and post-recovery validation. Disaster-recovery exercises use named owners and retained evidence.

Critical third parties and subcontractors MUST be inventoried with service/data/effect access, concentration, substitutability, contract/exit rights, owners, and objectives. The declared cadence exercises severe-but-plausible outage, degradation, compromise, jurisdiction loss, insolvency/exit, fallback/manual operation, data return/deletion, revocation, reconciliation, and recovery. A fallback that weakens security, privacy, authority, evidence, or approved domain controls stops.

Supported platforms/runtimes/databases/models/providers have versions, owners, support-end dates, and notice thresholds. New deployment after support end blocks. Continued unsupported use requires an eligible time-bounded waiver, upgrade plan, and compensating isolation/monitoring.

## 20. Corporate-agent identity, authority, and delegation

Corporate agents operate only under a named human owner and approval matrix. Use strong workload identity, least privilege, short-lived credentials, environment separation, tool/capability allowlists, revocation, and tested kill switches.

Delegation MUST be a subset of parent authority and bind parent task/manifest, delegate identity, scope, expiry, tools, effects, budgets, revocation, artifacts, and handoff lineage. A delegate stops when its grant is insufficient, expired, or revoked. No delegation may transfer risk acceptance or approval.

## 21. Untrusted content and prompt-injection defense

Retrieved documents, browser content, email/chat/tickets, user files, tool/MCP/plugin output, dependency metadata, generated artifacts, and model output are untrusted data. Embedded statements are not instructions merely because a model can read them.

Architectures MUST separate trusted policy/instruction channels from data channels, minimize untrusted context, label provenance, constrain tools/effects outside the model, validate structured outputs, and require authorization at the point of effect. Tests MUST cover direct/indirect prompt injection, goal hijack, system-prompt leakage, unsafe output handling, data/model/memory poisoning, excessive agency, tool misuse, vector/retrieval weaknesses, misinformation, and unbounded consumption.

Prompt filtering alone is not an authorization control. Retrieval augmentation and fine-tuning do not eliminate prompt injection.

## 22. Agent registries and supply chain

Every model, prompt, tool, plugin/MCP server, dataset, provider, and fallback MUST have a registry entry containing exact version/digest, owner, approved/prohibited use, capabilities, data/egress access, evaluation evidence, change approval, rollback, and revocation.

Only allowlisted, signed/provenanced components may enter production agent paths. Registries MUST preserve prior identities so historical executions remain reconstructible. Alias changes cannot silently alter deployed behavior; resolution to an immutable identity is recorded per execution.

## 23. Agent sandbox, external effects, and audit

The profile declares filesystem scopes, egress destinations, tools/capabilities, request/rate/runtime/token/data/spend ceilings, and environment boundaries. Enforce them outside model reasoning.

Before an external effect, validate the agent-effect manifest: requester, human owner, grant, target, capability, tool/model identities, cost/egress bounds, reversibility, idempotency key, confirmation, produced artifacts, and cleanup. Side effects SHOULD be transactional or confirmable; retries require stable idempotency keys. Attempted and completed effects enter a tamper-evident ledger.

Audit records bind requester, human owner, agent/model/prompt/tool/plugin/dataset/provider versions, inputs and classifications, authority/delegation, decisions, effects, outputs, evidence, and UTC timestamps. Privacy rules constrain audit content; necessary lineage is retained without copying secrets or prohibited raw data.

## 24. Agent evaluation, uncertainty, and human decisions

Predeployment and material-change evaluations MUST use versioned held-out sets, adversarial and prompt-injection suites, unsafe-output/tool-effect tests, repeated runs, and declared thresholds. Bias/fairness evaluation is required when outputs affect people or protected groups. Monitor drift/currentness after deployment with halt thresholds and owners.

Evaluation records state datasets, exclusions, contamination controls, model/prompt/tool/provider identities, sampling, repetitions, variance, metrics, thresholds, failures, and evidence ceiling. Synthetic or narrow evaluations cannot prove general correctness.

Agent outputs distinguish sourced facts, inferences, proposals, and unknowns. Required missing evidence fails closed. Configured high-impact decisions require authorized human review of inputs, explanation, uncertainty, alternatives, conflicts, and override/appeal path before final action.

## 25. Agent incidents, continuity, and fallback

Incident response MUST support detection, agent halt, containment, credential/tool/model/plugin/egress revocation, evidence preservation, forensic reconstruction, required notification, verified recovery, and regression coverage.

Incident closure triggers `OPS-005`. The profile sets the review deadline and independence. The record includes impact, timeline, root and contributing causes, failed or missing controls, detection/recovery gaps, corrective owners/dates, regression evidence, and a later operating-effectiveness retest. Blameless learning does not remove named accountability or permit historical evidence rewriting.

Business-continuity and provider/model fallbacks MUST be registered and evaluated. A fallback may run only if it preserves authority, identity, privacy/residency, security, audit, evidence, effect limits, and human-review guarantees. Silent capability or control degradation is prohibited; stop when equivalence is not established.

## 26. Waivers and baseline debt

Waivers require specific scope, control IDs, distinct human owner/approver, reason, risk, compensating control and its verifier, evidence, linked issue/work item, issue/expiry times, status, and verified signature. The catalog determines eligibility; profile-prohibited controls cannot be waived.

Baseline debt is a recorded failure state. New or worsened violations block; unchanged debt follows an approved remediation plan with owner and deadline. Blanket, permanent, “legacy,” all-repository, or agent-approved waivers are invalid. Expired/revoked waivers cannot satisfy a gate.

## 27. Source control and remote state

- Stage only intended files and review staged names/statistics/diff.
- Exclude secrets, local configuration, temporary files, unrelated generated output, and pre-existing changes.
- Run required gates for the exact committed revision or record the traceable source-to-commit identity.
- Follow configured authorship, message, signing, and provenance policy.
- Verify signatures independently.
- Push, merge, tag, publish, release, or deploy only with authority and effect records.
- Confirm the remote target contains the exact intended revision/artifact and that final local/remote state is reported accurately.
- Never rewrite shared history or delete remote state without explicit destructive-operation authority.

## 28. Manual review, control effectiveness, and defect handling

Green automation is necessary evidence, not complete review. Manual review MUST inspect trust boundaries, missing failure paths, rollback/cleanup, concurrency, field availability in hooks/triggers/callbacks, exact keyset validation, signature/API completeness, scalar/document consistency, compatibility, and claims not exercised by tests.

Each correction reruns affected generators, validators, security analyses, integration/live checks, and regression suites. Corrected defects receive regression coverage or an eligible approved waiver naming why it is technically impossible and the compensating check.

Configured control does not mean effective control. Under `GOV-009`, the profile sets evidence age, population, risk-stratified sampling, assessor independence, failure action, and owner. Assessment distinguishes design effectiveness—the control could address the risk—from operating effectiveness—it actually did so over the sampled period. Stale, convenient-only, or implementer-selected evidence cannot support a complete assurance claim. Failures block affected claims, receive owners/dates, and remain open through independent retest.

## 29. Compliance mapping and claim limits

`compliance-reference-map.md` links current primary sources consulted for this distribution. Mappings are informative until a qualified owner declares exact legal/contractual authority and edition. Do not copy licensed normative text. Do not claim certification or conformity from thematic mappings, tool passes, or adoption of this system.

The evidence ceiling always applies:

- static checks do not prove runtime operation;
- mocks do not prove real integration;
- synthetic fixtures prove mechanics, not production representativeness;
- local verification does not prove deployment;
- deployment does not prove operational health;
- self-review does not prove independent approval;
- a valid schema does not prove truthful content;
- a control mapping does not prove compliance.

## 30. System validation and maintenance

The artifact distribution MUST validate all machine-readable templates and positive fixtures, reject negative fixtures, check stable unique control IDs, validate control/waiver references, check relative links, enforce the root template byte budget, and record file digests in `validation-report.json`.

The system owner reviews profiles, control catalog, tool/model/provider registries, platform support, standards references, and waiver inventory on declared cadences and after incidents or material changes. Historical evidence remains immutable; schema migrations create traceable copies rather than rewriting originals.

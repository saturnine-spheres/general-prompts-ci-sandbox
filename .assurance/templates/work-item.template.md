# Work item: [IDENTIFIER] — [TITLE]

Status: `draft | authorized | in_progress | blocked | verification | complete | cancelled`\
Human owner: `[NAME_OR_ROLE]`\
Approver(s): `[NAME_OR_ROLE]`\
Target revision/baseline: `[IMMUTABLE_REVISION]`\
Profile version: `[PROFILE_VERSION]`\
Control-catalog version: `[CATALOG_VERSION]`

## Outcome

[One observable result. State who receives value and what state will exist at completion.]

## Non-goals

- [Explicitly excluded result]
- [Adjacent decision not authorized]

## Acceptance criteria

Numbered, observable behaviours a user or caller would notice. Review judges each one as `met`, `not_met`, or `not_verifiable` and records the verdict by its identifier. Mechanical checks such as tests passing, lint, or coverage are gates, not acceptance criteria.

1. `AC-1`: [Observable behaviour, who observes it, and under which condition]
2. `AC-2`: [Observable behaviour, who observes it, and under which condition]

## Value check

For a multi-item effort: the human-defined representative or user-facing check, its threshold, and who runs it. For a single item: `not applicable: single item`.

- Check: `[REPRESENTATIVE OR USER-FACING CHECK]`
- Threshold: `[MEASURABLE THRESHOLD]`
- Defined by: `[HUMAN NAME OR ROLE]`

## Kill or rethink criteria

For a multi-item effort: the evidence that would stop the effort or send it back to design. For a single item: `not applicable: single item`.

- `[CONDITION]` → `stop | rethink scope | rethink design`

## Rigor budget

- Expected evidence effort: `light | standard | full`
- Condition that would justify more: `[CONDITION]`

Materially exceeding the budget is a stop condition. After two failed qualification or remediation rounds on the same question, stop and ask the owner whether the approach is wrong before planning a third.

## Authority

- Request/issue: `[URI_OR_ID]`
- Authorized actor(s): `[IDENTITIES]`
- Allowed repositories/environments: `[SCOPES]`
- Allowed remote or production effects: `[NONE_OR_EXPLICIT_LIST]`
- Approval matrix entries: `[REFERENCES]`
- Authority expires: `[RFC3339_TIMESTAMP_OR_NULL]`

## Authoritative inputs and conflict check

| Authority rank | Source and version | Scope | Conflicts found |
|---|---|---|---|
| 1–5 | `[URI/PATH@VERSION]` | `[SCOPE]` | `none | [DETAIL]` |

Conflict disposition: `[NONE_OR_HUMAN_DECISION_REFERENCE]`

## Change declaration

- Change classes: `[docs, architecture_design, domain_code, api_schema, migrations_data, auth_security, dependencies_tooling, ui_accessibility, performance, ai_model_behavior, infrastructure, release]`
- Risk class: `low | moderate | high | critical`
- Escalation triggers present: `[EXACT_MATRIX_TRIGGER_IDS_OR_NONE]`
- Diagram triggers: `[authorization_or_approval, multi_stage_transaction, state_machine, retry_timeout_recovery, rollback_or_safe_disable, external_effect, system_of_record_or_reconciliation, incident_or_continuity, or none]`
- Material change: `true | false`
- Material-change justification/approval: `[REFERENCE_OR_NOT_REQUIRED]`

## Affected contracts and assets

| Contract/asset | Current identity | Intended change | Compatibility/versioning | Owner |
|---|---|---|---|---|
| `[NAME]` | `[VERSION/DIGEST]` | `[CHANGE]` | `[IMPACT]` | `[OWNER]` |

Data classification, residency, retention, and test-data impact: `[DECLARATION]`

Specialized domain rules and qualified owners: `[AUTHORITATIVE RULE/POLICY/CONTRACT@VERSION, OWNER, SCOPE, ACCEPTANCE CRITERIA, OR NONE]`

Architecture-assurance record and affected node/flow IDs: `[PATH@VERSION / IDS / NOT_TRIGGERED_WITH_REASON]`

## Risks and controls

| Risk | Likelihood | Impact | Control IDs | Residual risk owner |
|---|---|---|---|---|
| `[RISK]` | `low/moderate/high` | `low/moderate/high/critical` | `[IDS]` | `[HUMAN]` |

The implementation agent cannot accept residual risk.

## Execution and effect plan

- Requested tools/capabilities: `[ALLOWLIST]`
- Filesystem scope: `[READ/WRITE PATHS]`
- Network/egress destinations: `[ALLOWLIST_OR_NONE]`
- External effects: `[EFFECT TYPES/TARGETS_OR_NONE]`
- Cost/spend ceiling: `[CURRENCY AND AMOUNT]`
- Runtime/token/request/data-egress limits: `[LIMITS]`
- Credentials and workload identity: `[CUSTODY/IDENTITY, NEVER SECRET VALUES]`
- Idempotency/confirmation strategy: `[DETAIL]`
- Cleanup/revocation/rollback: `[DETAIL]`
- Agent-effect manifest path: `[PATH_OR_NOT_REQUIRED]`

## Implementation plan

1. [Coherent reviewable step]
2. [Coherent reviewable step]

## Test and evidence plan

| Required tier/check | Reason/trigger | Entrypoint | Required evidence | Blocking |
|---|---|---|---|---|
| `[verify tier or check]` | `[MATRIX/CONTROL ID]` | `[COMMAND]` | `[SCHEMA/ARTIFACT]` | `true` |

Required independent reviewer and independence basis: `[IDENTITY/SEPARATION_OR_NOT_REQUIRED]`

## Exact definition of done

- [ ] Outcome is observable against `[TARGET]`.
- [ ] Every acceptance criterion has a review verdict; none is `not_met`, and each `not_verifiable` verdict has a recorded reason and owner.
- [ ] Every affected contract and artifact is updated and versioned.
- [ ] Triggered architecture/threat/flow/state diagrams render and trace to contracts, implementation, configuration, tests, and deployment evidence.
- [ ] Every applicable blocking control is `pass` or has an active eligible waiver.
- [ ] Required verifier tiers completed for the exact revision and environment.
- [ ] Verification-result, review, waiver, and effect records validate against their schemas.
- [ ] Corrected defects have regression coverage or an approved waiver with compensating control.
- [ ] Compatibility, migration, progressive delivery, rollback, safe-disable, SLO/error-budget, observability, resource, adversarial, privileged-access, privacy, accessibility, license, resilience, domain-contract, and deprecation obligations selected by the matrix are satisfied.
- [ ] External effects are confirmed; cleanup and credential revocation are complete.
- [ ] Diff and intended file list are reviewed; unrelated changes remain untouched.
- [ ] Remaining limitations and unknowns are recorded without completion overclaim.

## Stop conditions

Stop immediately for missing or expired authority; authoritative conflict; unexpected dirty state overlapping this work; secret or sensitive-data exposure; destructive or production effect outside the manifest; unavailable/failing required gate; cost/egress/resource overrun; unexpected dependency/tool/service requirement; evidence contradicting the intended outcome; independence failure; unsafe rollback/cleanup; or any attempt to enlarge delegated authority.

Resolution requires: `[NAMED OWNER/APPROVER AND RECORD TYPE]`.

## Completion record

- Final revision/artifact digest: `[IDENTITY]`
- Verification-result record(s): `[PATHS/URIS]`
- Review record: `[PATH/URI]`
- Waivers: `[PATHS/URIS_OR_NONE]`
- Effect manifest/ledger: `[PATHS/URIS_OR_NONE]`
- Known limitations and unrun checks: `[LIST_OR_NONE]`
- Follow-up issues and owners: `[LIST_OR_NONE]`

# Work item: WI-0001 — Add orders.Count

Status: `draft`\
Human owner: `github:saturnine-spheres`\
Approver(s): `github:saturnine-spheres` (profile approval-matrix roles are still `REPLACE` placeholders; see open questions)\
Target revision/baseline: `b22e4118f8d66121d146c3feebbc5b339ffdaac2` (branch `assurance/claude-adapter`)\
Profile version: `0.2.0`\
Control-catalog version: `1.1.0`

## Outcome

A caller of package `orders` (`src/orders`) can call `Count()` and get the number of orders the package knows about. `Find` and `Count` read the same order set, so the two always agree. The change goes out as a pull request from `deliver/orders-count` into `assurance/claude-adapter`.

## Non-goals

- Changing `Find`'s signature or behaviour, or the set of known orders.
- Adding new orders, persistence, or mutation APIs.
- Opening a pull request against `main`, or merging any pull request.

## Acceptance criteria

1. `AC-1`: A caller can call `orders.Count()`, which takes no arguments and returns an `int`, and it compiles from another package that imports `orders`.
2. `AC-2`: With the current order set (one order, ID `1`, `"first"`), a caller of `orders.Count()` gets `1`.
3. `AC-3`: `Count()` equals the number of distinct IDs for which `Find` reports `ok == true`. Both functions read one shared order set, so adding an order to that set changes both.
4. `AC-4`: Callers see no change in `Find`: `Find(1)` returns `("first", true)` and `Find(2)` returns `("", false)`.
5. `AC-5`: A reviewer can open a pull request whose head is `deliver/orders-count` and whose base is `assurance/claude-adapter`, not `main`.

## Value check

`not applicable: single item`

## Kill or rethink criteria

`not applicable: single item`

## Rigor budget

- Expected evidence effort: `light`
- Condition that would justify more: the change spreads beyond `src/orders/` or the work item, touches a protected path (`src/payments/**`), adds a dependency, changes an exported signature other than adding `Count`, or the tier check classifies it as `significant`.

Materially exceeding the budget is a stop condition. After two failed qualification or remediation rounds on the same question, stop and ask the owner whether the approach is wrong before planning a third.

## Authority

- Request/issue: in-session specification from the person: "Add a Count function to src/orders that returns the number of known orders, with a unit test. Open the pull request against the branch assurance/claude-adapter, not main." No ticket or comment was used.
- Authorized actor(s): `github:saturnine-spheres` (requester and owner); delivery agent run under that account.
- Allowed repositories/environments: `github.com/saturnine-spheres/general-prompts-ci-sandbox`, local worktree, branch `deliver/orders-count`.
- Allowed remote or production effects: pushing branch `deliver/orders-count` (no force-push), and opening one pull request with head `deliver/orders-count` and base `assurance/claude-adapter`. No merge, no production effect.
- Approval matrix entries: `merge ordinary change` (merging is not in scope for this run).
- Authority expires: `null` (ends when the pull request is opened)

## Authoritative inputs and conflict check

| Authority rank | Source and version | Scope | Conflicts found |
|---|---|---|---|
| 3 | `.assurance/project-assurance-profile.json@0.2.0` | profile, tiers, approval matrix | none (approver roles are placeholders) |
| 3 | `.assurance/control-catalog.yaml@1.1.0` | blocking controls | none |
| 5 | `AGENTS.md`, `.assurance/agent-pack.md` @ `b22e411` | repository instructions, delivery rules | none |
| 5 | In-session specification (person) | outcome, PR target branch | none; it names `assurance/claude-adapter` as the PR base, which overrides the default `main` |

Conflict disposition: `none`

## Change declaration

- Change classes: `domain_code`
- Risk class: `low`
- Escalation triggers present: `none`
- Diagram triggers: `none`
- Material change: `false`
- Material-change justification/approval: `not required` (no new dependency, tool, service, or contract)

## Affected contracts and assets

| Contract/asset | Current identity | Intended change | Compatibility/versioning | Owner |
|---|---|---|---|---|
| Go package `orders` exported API | `src/orders/orders.go@b22e411` | add `func Count() int` | additive; `Find` unchanged | `github:saturnine-spheres` |

Data classification, residency, retention, and test-data impact: none. The fixture data is a single hard-coded non-personal order (`1: "first"`).

Specialized domain rules and qualified owners: `none`

Architecture-assurance record and affected node/flow IDs: `not triggered`: additive function in a fixture package, with no diagram trigger.

## Risks and controls

| Risk | Likelihood | Impact | Control IDs | Residual risk owner |
|---|---|---|---|---|
| `Count` and `Find` drift apart because each has its own copy of the data | low | low | ENG (shared order set, AC-3 test) | `github:saturnine-spheres` |
| PR opened against `main` instead of `assurance/claude-adapter` | low | low | AGT (effect confirmation of PR base) | `github:saturnine-spheres` |

The implementation agent cannot accept residual risk.

## Execution and effect plan

- Requested tools/capabilities: file read/edit, `go` toolchain (`gofmt`, `go vet`, `go test`) through the declared verifier entrypoints, `git` (commit, push without force), and the GitHub pull-request create capability.
- Filesystem scope: `docs/work-items/WI-0001-orders-count.md`, `src/orders/orders.go`, `src/orders/orders_test.go`, `.assurance/evidence/**` (verifier and run records produced by the entrypoints)
- Network/egress destinations: `github.com` (push and PR creation only).
- External effects: push of branch `deliver/orders-count`; creation of one PR `deliver/orders-count` → `assurance/claude-adapter`.
- Cost/spend ceiling: `0 EUR`
- Runtime/token/request/data-egress limits: 60 minutes per run (agent-pack run budget); egress limited to the git push and one PR-create request.
- Credentials and workload identity: the existing local git and GitHub credentials for `saturnine-spheres` from their current custody. No secret values go into files or output.
- Idempotency/confirmation strategy: before creating the PR, check that no open PR already exists for head `deliver/orders-count`. After creating it, read the PR back and confirm head `deliver/orders-count`, base `assurance/claude-adapter`, and the pushed commit SHA.
- Cleanup/revocation/rollback: revert the commit on the branch or close the PR. No temporary credentials are issued.
- Agent-effect manifest path: required by AGENTS.md for remote Git effects; to be created by the delivery run under `.assurance/evidence/` before the push (exact path set by `delivery_run.py`).

## Implementation plan

1. In `src/orders/orders.go`, move the order map into one package-level unexported variable. Have `Find` read it, and add `Count() int` returning `len` of that map, with a doc comment.
2. In `src/orders/orders_test.go`, add `TestCount`: it asserts `Count() == 1` and checks that `Count()` equals the number of IDs `Find` resolves in the shared set. Keep `TestFind` unchanged.
3. Run `verify-fast` during the build and `verify` before delivery, then commit with a short imperative subject and no attribution.
4. Push `deliver/orders-count`, open the PR against `assurance/claude-adapter`, and confirm its head and base.

## Test and evidence plan

| Required tier/check | Reason/trigger | Entrypoint | Required evidence | Blocking |
|---|---|---|---|---|
| `verify-fast` (go-vet, go-test-short) | build stage gate | `bash .assurance/tools/verify-fast.sh` | `.assurance/evidence/verify-fast.json` | `true` |
| `verify` (gofmt, go-vet, go-test) | gates stage, `domain_code` | `bash .assurance/tools/verify.sh` | `.assurance/evidence/verify.json` | `true` |
| assurance gate | CI evidence gate | `python .assurance/tools/assurance_gate.py check --base b22e4118f8d66121d146c3feebbc5b339ffdaac2 --head HEAD` | gate output | `true` |
| tier classification | tier-check stage | `python .assurance/tools/assurance_gate.py classify --base b22e4118f8d66121d146c3feebbc5b339ffdaac2 --head HEAD` | expected `notable` (this work item alone is over the 60-line routine limit); `significant` is a stop | `true` |

Required independent reviewer and independence basis: review stage in a fresh context without the builder's instructions (process `review`). Merge approval is out of scope for this run.

## Exact definition of done

- [ ] Outcome is observable against `src/orders` at the pushed head of `deliver/orders-count`.
- [ ] Every acceptance criterion has a review verdict; none is `not_met`, and each `not_verifiable` verdict has a recorded reason and owner.
- [ ] Every affected contract and artifact is updated and versioned.
- [ ] Triggered architecture/threat/flow/state diagrams render and trace to contracts, implementation, configuration, tests, and deployment evidence. (None triggered.)
- [ ] Every applicable blocking control is `pass` or has an active eligible waiver.
- [ ] Required verifier tiers completed for the exact revision and environment.
- [ ] Verification-result, review, waiver, and effect records validate against their schemas.
- [ ] Corrected defects have regression coverage or an approved waiver with compensating control. (No defect correction planned.)
- [ ] Compatibility, migration, progressive delivery, rollback, safe-disable, SLO/error-budget, observability, resource, adversarial, privileged-access, privacy, accessibility, license, resilience, domain-contract, and deprecation obligations selected by the matrix are satisfied.
- [ ] External effects are confirmed (PR base is `assurance/claude-adapter`); cleanup and credential revocation are complete.
- [ ] Diff and intended file list are reviewed; unrelated changes remain untouched.
- [ ] Remaining limitations and unknowns are recorded without completion overclaim.

## Stop conditions

Stop immediately for missing or expired authority; authoritative conflict; unexpected dirty state overlapping this work; secret or sensitive-data exposure; destructive or production effect outside the manifest; unavailable/failing required gate; cost/egress/resource overrun; unexpected dependency/tool/service requirement; evidence contradicting the intended outcome; independence failure; unsafe rollback/cleanup; or any attempt to enlarge delegated authority. Also stop if the tier check returns `significant`, or if the only available PR target is `main`.

Resolution requires: `github:saturnine-spheres`, decision recorded in the session or on the work item.

## Completion record

- Final revision/artifact digest: `pending`
- Verification-result record(s): `pending`
- Review record: `pending`
- Waivers: `none`
- Effect manifest/ledger: `pending`
- Known limitations and unrun checks: `pending`
- Follow-up issues and owners: `none`

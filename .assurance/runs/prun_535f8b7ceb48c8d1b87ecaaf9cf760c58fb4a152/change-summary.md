# Change summary

## What changed and why
Added `orders.Names() []string` returning order names sorted by ascending ID. The order map moved from a local in `Find` to package-level `knownOrders` so both share one source (the spec's preferred reading; `Find`/`Exists` API and behaviour unchanged).

## Files touched
- `src/orders/orders.go`
- `src/orders/orders_test.go` (existing file, `TestNames` appended; existing tests untouched)
- `docs/work-items/WI-0002-order-names.md` (new)

## Tests added
`TestNames`: shipped data (`["first"]`), a fixture `{3:alpha,1:zulu,2:mike}` expecting `[zulu mike alpha]`, and an empty map (non-nil empty slice); each checked 5 times.

## Checks run
None. No Go toolchain is installed in this environment (`which go` found nothing), so `go vet ./...`, `go test ./...` and `-count=10` were NOT run. I reviewed the code by hand only.

## Deviations from plan
None, other than the checks that could not run.

## Concerns
- Acceptance criterion 5 (`go vet`/`go test` pass) is unverified; the Verify gate must run it.
- The work item is minimal and does not fill every template field (owner, approver, etc.), as I have no authority to set them. It follows the style of WI-0001.
- `AGENTS.md` still has `[PLACEHOLDER]` entries.
- Tests mutate a package-level variable, so they must not use `t.Parallel`.

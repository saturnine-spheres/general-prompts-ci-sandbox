# Change summary

## What changed and why
Added `Count() int` to package `orders` returning the number of known orders (1), plus `TestCount`. `Find` and `Exists` are untouched. `Count` holds its own list of known IDs because `Find`'s map is a local variable.

## Files touched
- `src/orders/orders.go` (added `Count`)
- `src/orders/orders_test.go` (added `TestCount`)
- `docs/work-items/WI-0006-order-count.md` (new; required by AGENTS.md)

## Tests
`TestCount` asserts `Count() == 1` and that it equals the number of IDs in -5..100 for which `Exists` is true, to detect drift between the two data copies.

## Checks run
- `go test ./src/orders/...`: NOT RUN. `go` is not installed in this environment (`go: command not found`). No check, including gofmt, was run; the change is unverified.

## Deviations
Added the work item file, which the spec's AC-5 permits as a process-required record.

## Concerns
- Tests have not been executed; the Verify gate must run them.
- Duplicated data between `Find` and `Count` can drift; the cross-check test only covers IDs -5..100.
- AGENTS.md still has unreplaced placeholders; I did not read the `.assurance/` profile files beyond listing them.

# Spec: List the known order names

## Outcome

Callers of package `src/orders` can call `Names() []string` and get the names of all known orders, sorted by ascending order ID.

## Non-goals

- No change to the signature or behaviour of `Find` or `Exists`.
- No new orders, new dependencies, or changes to CI, docs or other packages.

## Affected contracts and assets

- `src/orders/orders.go`: new exported function `Names`. The known-order data is currently a map local to `Find`, so `Names` needs access to the same data (see Unknowns).
- `src/orders/orders_test.go` (new, or extended if it exists): unit test for `Names`.
- Per `AGENTS.md`, a work item in `docs/work-items/` is also expected.

## Change classes

- `domain_code`: adds an exported function to the orders package.

## Proposed tier

`routine`: small, additive, backward-compatible change to a fixture package. No security, data or schema impact.

## Implementation plan

1. Move the order data to a package-level variable (`map[int]string{1: "first"}`) so `Find` and `Names` share one source. `Find` keeps its signature and observable behaviour.
2. Add `Names()`. Collect the IDs, sort them with `sort.Ints`, and return the names in that order. Return an empty non-nil slice if there are no orders.
3. Add a table-style unit test. Cover the current data (`[]string{"first"}`). Check that the order is by ID, not by name or map iteration order. This needs a test that swaps the package variable to several entries, restoring it afterwards.
4. Confirm the existing `Find` and `Exists` tests, if any, still pass unchanged.

## Acceptance criteria

1. `orders.Names()` returns `[]string{"first"}` with the shipped data.
2. With a multi-entry fixture whose names are not alphabetical in ID order, the result follows ascending ID.
3. The result is deterministic across repeated calls (`go test -count=10`).
4. `Find` and `Exists` signatures and results are unchanged.
5. `go vet ./...` and `go test ./...` pass.

## Unknowns and risks

- `Find` holds the data in a function-local map. Sharing it requires editing the body of `Find`, which is in tension with "keep the existing functions unchanged". Narrowest reading: unchanged means API and behaviour. The alternative is to duplicate the map in `Names`, which risks the two drifting apart. Confirm which is preferred.
- `AGENTS.md` still contains unreplaced `[PLACEHOLDER]` verify commands, so the repository's verify entrypoints are unknown. `go test` is assumed.
- I could not list the directory and found no `orders_test.go` by guessing. I read only `orders.go` and `go.mod`, so existing test files are unconfirmed.
- Nothing suspicious was found in the repository content I read.

## Stop conditions

- Stop if making the data shareable would require changing the signature or results of `Find` or `Exists`.
- Stop if the repository's required verify gates are unavailable or fail.
- Stop if a new dependency, or any file outside `src/orders` and the work item, is needed.

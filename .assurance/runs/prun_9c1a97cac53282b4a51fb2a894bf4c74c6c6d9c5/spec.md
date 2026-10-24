# Spec: Count the known orders

## Outcome

Callers of package `orders` get `Count() int`, which returns how many orders are known (currently 1), covered by a unit test.

## Non-goals

- No change to the source of `Find` or `Exists`, or to their behaviour.
- No new orders, no new dependencies, no exported data.
- No work item, docs or CI changes beyond what the repository process requires of the Builder.

## Affected contracts and assets

- `src/orders/orders.go`: add exported `Count() int`.
- `src/orders/orders_test.go`: add `TestCount`.
- Public API of package `orders` gains one function. Nothing is removed or altered.

## Change classes

- Change classes: `domain_code`
- `domain_code`: adds a function and a test to the Go package `orders`.

## Proposed tier

`routine`: a small, additive, backward-compatible change to one package, with no security, data or schema impact.

## Implementation plan

1. In `orders.go`, add `Count()`. Leave `Find` and `Exists` untouched. The known-order data is a local variable inside `Find`, so `Count` needs its own source for it (see Unknowns).
2. In `orders_test.go`, add `TestCount`, in the style of the existing tests.
3. Run `go test ./src/orders/...`, or the profile's declared verify command if one is set.

## Acceptance criteria

- `AC-1`: `Count()` exists in `src/orders/orders.go` with signature `func Count() int`.
- `AC-2`: `Count()` returns `1`, which is the number of orders `Find` currently recognises.
- `AC-3`: `TestCount` in `src/orders/orders_test.go` asserts the value from `AC-2` and passes.
- `AC-4`: The `Find` and `Exists` code and their tests (`TestFind`, `TestExists`) are unchanged and still pass.
- `AC-5`: The diff touches only `src/orders/orders.go` and `src/orders/orders_test.go`, plus any work-item record the repository process requires.

## Unknowns and risks

- Ambiguity: `Find` keeps its order map as a local variable, so `Count` cannot read it without either duplicating the data or moving it to package level, which would edit `Find`. The narrowest reading of "keep the existing functions unchanged" is to leave `Find` and `Exists` byte-for-byte unchanged. That means `Count` carries a second copy of the data, so the two can drift apart. A test that checks `Count()` against `Find` over a range of IDs would reduce that risk. If the requester prefers a shared package-level variable, they should confirm that `Find` may be edited.
- `AGENTS.md` still contains unreplaced `[PLACEHOLDER]` and `[VERIFY_*_COMMAND]` entries. I could not identify the exact verify entrypoints, and I did not read the `.assurance/` profile files.
- `AGENTS.md` asks for a work item in `docs/work-items/` before implementation. The Builder should follow that if it is in scope for this run.
- I found no instructions in the repository content that try to redirect this stage.

## Stop conditions

- Making `Count` correct would require changing `Find` or `Exists`, and the requester has not approved that.
- The package contains other order data or files that contradict the assumption that exactly one order is known.
- The required verify command is unavailable or fails.
- A new dependency or tool would be needed.
- Any change outside `src/orders/` or the work-item record seems necessary.

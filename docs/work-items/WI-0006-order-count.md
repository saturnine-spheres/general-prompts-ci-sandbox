# Work item: WI-0006 — Count the known orders

## Outcome

Callers can ask how many orders are known.

## Acceptance criteria

1. `AC-1`: `Count()` exists in `src/orders/orders.go` with signature `func Count() int`.
2. `AC-2`: `Count()` returns `1`, the number of orders `Find` recognises.
3. `AC-3`: `TestCount` asserts the value from `AC-2` and passes.
4. `AC-4`: `Find`, `Exists` and their tests are unchanged.

## Change declaration

- Change classes: `domain_code`
- Risk class: `low`

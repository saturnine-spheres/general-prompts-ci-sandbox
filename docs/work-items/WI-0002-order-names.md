# Work item: WI-0002 — List the known order names

## Outcome

Callers can list the names of all known orders, sorted by order ID.

## Acceptance criteria

1. `AC-1`: `Names()` returns `[]string{"first"}` with the shipped data.
2. `AC-2`: `Names()` returns names in ascending order-ID order, not name order.
3. `AC-3`: `Names()` returns the same result on repeated calls.
4. `AC-4`: `Find` and `Exists` keep their signatures and results.

## Change declaration

- Change classes: `domain_code`
- Risk class: `low`

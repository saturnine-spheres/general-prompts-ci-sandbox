# Work item: WI-0001 — Report whether an order exists

## Outcome

Callers can check for an order without reading its name.

## Acceptance criteria

1. `AC-1`: `Exists(1)` returns true for the known fixture order.
2. `AC-2`: `Exists(2)` returns false for an unknown order.

## Change declaration

- Change classes: `domain_code`
- Risk class: `low`

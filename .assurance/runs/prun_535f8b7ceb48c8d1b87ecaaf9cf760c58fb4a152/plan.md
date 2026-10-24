# Plan

1. Move the order map in `src/orders/orders.go` to package-level `knownOrders`; `Find` reads it (same signature and behaviour).
2. Add `Names()`: collect IDs, `sort.Ints`, return names in that order (empty non-nil slice if none).
3. Add `TestNames` to `src/orders/orders_test.go` (shipped data, non-alphabetical multi-entry fixture, empty; repeated calls; variable restored via defer).
4. Add `docs/work-items/WI-0002-order-names.md` as AGENTS.md expects.
5. Run `gofmt`/`go vet`/`go test` if a Go toolchain is available.

Files: `src/orders/orders.go`, `src/orders/orders_test.go`, `docs/work-items/WI-0002-order-names.md`.

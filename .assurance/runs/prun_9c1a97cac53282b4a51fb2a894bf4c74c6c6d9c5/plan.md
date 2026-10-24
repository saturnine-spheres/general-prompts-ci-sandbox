# Plan

1. Append `Count() int` to `src/orders/orders.go`, with its own copy of the known-order IDs (`Find` stays byte-for-byte unchanged).
2. Append `TestCount` to `src/orders/orders_test.go`: asserts 1, and cross-checks against `Exists` over IDs -5..100 to catch drift.
3. Add work item `docs/work-items/WI-0006-order-count.md` as AGENTS.md requires.
4. Run `go test ./src/orders/...` (Go may be unavailable here).

Files: `src/orders/orders.go`, `src/orders/orders_test.go`, `docs/work-items/WI-0006-order-count.md`, run files.

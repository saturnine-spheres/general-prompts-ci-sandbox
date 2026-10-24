package orders

import "testing"

func TestFind(t *testing.T) {
	if name, ok := Find(1); !ok || name != "first" {
		t.Fatalf("Find(1) = %q, %v", name, ok)
	}
	if _, ok := Find(2); ok {
		t.Fatal("Find(2) should be unknown")
	}
}

// AC-1: Count takes no arguments and returns an int.
var _ func() int = Count

// findable counts the distinct IDs in the shared set that Find resolves.
func findable(t *testing.T) int {
	t.Helper()
	n := 0
	for id := range known {
		if _, ok := Find(id); ok {
			n++
		}
	}
	return n
}

func TestCount(t *testing.T) {
	// AC-2: the current order set holds exactly one order.
	if got := Count(); got != 1 {
		t.Fatalf("Count() = %d, want 1", got)
	}
	// AC-3: Count agrees with the IDs Find resolves.
	if got, want := Count(), findable(t); got != want {
		t.Fatalf("Count() = %d, Find resolves %d IDs", got, want)
	}
}

func TestCountAndFindShareOrderSet(t *testing.T) {
	// AC-3: adding an order to the shared set changes both Find and Count.
	known[2] = "second"
	t.Cleanup(func() { delete(known, 2) })

	if name, ok := Find(2); !ok || name != "second" {
		t.Fatalf("Find(2) = %q, %v after adding order 2", name, ok)
	}
	if got := Count(); got != 2 {
		t.Fatalf("Count() = %d, want 2 after adding order 2", got)
	}
	if got, want := Count(), findable(t); got != want {
		t.Fatalf("Count() = %d, Find resolves %d IDs", got, want)
	}
}

func TestExists(t *testing.T) {
	if !Exists(1) || Exists(2) {
		t.Fatal("Exists must be true for 1 and false for 2")
	}
}

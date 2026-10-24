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

func TestExists(t *testing.T) {
	if !Exists(1) || Exists(2) {
		t.Fatal("Exists must be true for 1 and false for 2")
	}
}

func TestCount(t *testing.T) {
	if got := Count(); got != 1 {
		t.Fatalf("Count() = %d, want 1", got)
	}
	known := 0
	for id := -5; id <= 100; id++ {
		if Exists(id) {
			known++
		}
	}
	if got := Count(); got != known {
		t.Fatalf("Count() = %d, but Find recognises %d IDs", got, known)
	}
}

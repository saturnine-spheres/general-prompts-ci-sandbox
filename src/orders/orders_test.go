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

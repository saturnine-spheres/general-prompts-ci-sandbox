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

func TestNames(t *testing.T) {
	original := knownOrders
	defer func() { knownOrders = original }()

	tests := []struct {
		name   string
		orders map[int]string
		want   []string
	}{
		{"shipped data", original, []string{"first"}},
		{"sorted by id not name", map[int]string{3: "alpha", 1: "zulu", 2: "mike"}, []string{"zulu", "mike", "alpha"}},
		{"empty", map[int]string{}, []string{}},
	}
	for _, tc := range tests {
		t.Run(tc.name, func(t *testing.T) {
			knownOrders = tc.orders
			for i := 0; i < 5; i++ {
				got := Names()
				if got == nil || len(got) != len(tc.want) {
					t.Fatalf("Names() = %#v, want %#v", got, tc.want)
				}
				for j := range got {
					if got[j] != tc.want[j] {
						t.Fatalf("Names() = %#v, want %#v", got, tc.want)
					}
				}
			}
		})
	}
}

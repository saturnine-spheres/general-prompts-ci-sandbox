package payments

import "testing"

func TestFee(t *testing.T) {
	if Fee(1000) != 10 {
		t.Fatal("Fee(1000) must be 10")
	}
}

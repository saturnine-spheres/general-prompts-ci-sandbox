// Package payments is a protected-path fixture for the general-prompts CI evidence gate.
package payments

// Fee returns the processing fee in cents.
func Fee(amount int) int { return amount / 100 }

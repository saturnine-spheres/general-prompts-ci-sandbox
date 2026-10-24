// Package orders is a tiny fixture for the general-prompts CI evidence gate.
package orders

// known is the single order set that Find and Count both read.
var known = map[int]string{1: "first"}

// Find returns the order name for an ID, or false when the order is unknown.
func Find(id int) (string, bool) {
	name, ok := known[id]
	return name, ok
}

// Count returns the number of known orders.
func Count() int {
	return len(known)
}

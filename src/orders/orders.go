// Package orders is a small fixture for the general-prompts CI evidence gate.
package orders

// Find returns the order name for an ID, or false when the order is unknown.
func Find(id int) (string, bool) {
	orders := map[int]string{1: "first"}
	name, ok := orders[id]
	return name, ok
}

// Package orders is a tiny fixture for the general-prompts CI evidence gate.
package orders

// Find returns the order name for an ID, or false when the order is unknown.
func Find(id int) (string, bool) {
	orders := map[int]string{1: "first"}
	name, ok := orders[id]
	return name, ok
}

// Exists reports whether an order ID is known.
func Exists(id int) bool {
	_, ok := Find(id)
	return ok
}

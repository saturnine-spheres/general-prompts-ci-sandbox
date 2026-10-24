// Package orders is a tiny fixture for the general-prompts CI evidence gate.
package orders

import "sort"

// knownOrders maps each known order ID to its name.
var knownOrders = map[int]string{1: "first"}

// Find returns the order name for an ID, or false when the order is unknown.
func Find(id int) (string, bool) {
	name, ok := knownOrders[id]
	return name, ok
}

// Exists reports whether an order ID is known.
func Exists(id int) bool {
	_, ok := Find(id)
	return ok
}

// Names returns the names of all known orders, sorted by ascending order ID.
func Names() []string {
	ids := make([]int, 0, len(knownOrders))
	for id := range knownOrders {
		ids = append(ids, id)
	}
	sort.Ints(ids)
	names := make([]string, 0, len(ids))
	for _, id := range ids {
		names = append(names, knownOrders[id])
	}
	return names
}

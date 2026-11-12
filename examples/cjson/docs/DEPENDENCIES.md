# Dependencies

Arrows point from a user to its dependency. Containment is structural, not a dependency. Graph-confirmed pairs appear in both the tree and resolved call/import edges. Model-inferred pairs appear only in the tree. Graph-only pairs appear only in the graph.
Graph-confirmed and model-inferred pairs count edges between two subtrees. Graph-only pairs count edges between direct node owners. Containment rows show resolved edges between ancestor direct units and a descendant subtree in both directions. Within containment rows count direct owner pairs separately. Neither kind of containment row appears in Mermaid or the three dependency totals.

```mermaid
flowchart LR
  n0["JSON Pointer Patch Utilities"]
  n1["Public Utility API and Mutators"]
  n2["Core JSON Parse and Print"]
  n3["Item Creation and Lifecycle"]
  n2 --> n3
  n2 --> n0
  n2 --> n1
  n0 --> n3
  n0 --> n1
  n1 --> n3
  n1 --> n0
```

Selected 4 nodes by connection count. Legend: `-->` graph-confirmed; `-.->` model-inferred; `==>` graph-only.

## Dependency list

- [Core JSON Parse and Print](nodes/core-json-parse-and-print.md) → [Item Creation and Lifecycle](nodes/item-creation-and-lifecycle.md) · graph-confirmed · 7 edge(s) · Core parsing and printing uses item creation and lifecycle helpers to build and manage cJSON nodes.
- [Core JSON Parse and Print](nodes/core-json-parse-and-print.md) → [JSON Pointer Patch Utilities](nodes/json-pointer-patch-utilities.md) · graph-confirmed · 3 edge(s)
- [Core JSON Parse and Print](nodes/core-json-parse-and-print.md) → [Public Utility API and Mutators](nodes/public-utility-api-and-mutators.md) · graph-confirmed · 2 edge(s)
- [JSON Pointer Patch Utilities](nodes/json-pointer-patch-utilities.md) → [Item Creation and Lifecycle](nodes/item-creation-and-lifecycle.md) · graph-confirmed · 28 edge(s) · JSON Pointer and patch utilities use item creation and lifecycle helpers when constructing or changing nodes.
- [JSON Pointer Patch Utilities](nodes/json-pointer-patch-utilities.md) → [Public Utility API and Mutators](nodes/public-utility-api-and-mutators.md) · graph-confirmed · 5 edge(s) · JSON Pointer and patch utilities use public utility mutators and lookup helpers for object and array operations.
- [Public Utility API and Mutators](nodes/public-utility-api-and-mutators.md) → [Item Creation and Lifecycle](nodes/item-creation-and-lifecycle.md) · graph-confirmed · 11 edge(s)
- [Public Utility API and Mutators](nodes/public-utility-api-and-mutators.md) → [JSON Pointer Patch Utilities](nodes/json-pointer-patch-utilities.md) · graph-confirmed · 5 edge(s) · Public utility API and mutators use JSON Pointer and patch utilities for merge-patch wrappers.

Graph-only pairs are ranked by edge count; 0 omitted.

### Within containment


Within containment: 0 pairs, ranked by edge count; 0 omitted. Each graph list keeps at most 40 pairs independently.

# Collection Tree Core (nodes.py)

**Capability.** Owns the abstract collection-tree model shared by all collectors and items: Node construction and parent wiring, marker storage and lookup, finalization, warning attribution, failure representation, and path resolution. It is infrastructure consumed by python.py and plugins.

Read this subtree to understand how any collected node is built, linked to its parent, decorated with markers, and how failures and warnings are rendered against its source location. It contains no Python-specific discovery logic; that lives in the python-collection subtree.

**Children.**

- [Node Base and Lifecycle](r7-node-base-lifecycle.md) `r7-node-base-lifecycle` · 15 unit(s)
- [Collector and Item Types](r7-item-collector-types.md) `r7-item-collector-types` · 4 unit(s)

**Depended on by.**

- [Discovery Rules and Collect Hooks](r7-py-collector-discovery.md) · graph-confirmed · 5 edge(s)
- [Function Item and Execution](r7-py-function-item.md) · graph-confirmed · 1 edge(s)
- [Module, Class, and Package Collectors](r7-py-module-class-package.md) · model-inferred · 0 edge(s)

Parent: [pytest Codebase](r7-pytest-codebase.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

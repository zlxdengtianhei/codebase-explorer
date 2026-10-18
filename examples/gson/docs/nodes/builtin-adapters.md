# Built-in Type Adapters

**Capability.** Concrete adapters for common Java kinds: arrays, enums, Number/Object with pluggable ToNumberStrategy, plus the strategy hook itself; each adapter is created by a factory that claims matching types.

Use this subtree to see how specific Java types map to JSON; number shaping in Object/Number deserialization is controlled by ToNumberStrategy implementations.

**Depends on.**

- [Internal Utilities and Data Structures](internal-infrastructure.md) · model-inferred · 0 edge(s)

Parent: [Type Adapter Pipeline and Object Construction](adapter-pipeline.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

# Built-in Type Adapter Factories

**Capability.** The stock TypeAdapterFactories Gson assembles by default: JDK primitive/wrapper/utility types, collections/maps and the JsonElement tree itself, and date/time families; each factory claims a type family and defers by returning null otherwise.

Use this subtree to find where a given Java type's default JSON mapping is implemented, split by primitive/utility, container/tree, and date/time families.

**Depends on.**

- [Internal Utilities and Data Structures](internal-infrastructure.md) · model-inferred · 0 edge(s)

Parent: [Type Adapter Pipeline and Object Construction](adapter-pipeline.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

# Type Adapter Pipeline and Object Construction

**Capability.** Owns how adapters are created and composed and how objects are instantiated: the TypeAdapter contract and factory plumbing, built-in adapters for common Java kinds, the stock default factories claiming type families, and the priority-ordered construction strategy all factories use to obtain ObjectConstructors.

Use this subtree to see how adapters compose and delegate, where a given Java type's default JSON mapping lives, and which constructor wins for a type. Changes here affect every binding path.

**Children.**

- [TypeAdapter Framework](adapter-framework.md) `adapter-framework` · 0 unit(s)
- [Built-in Type Adapters](builtin-adapters.md) `builtin-adapters` · 0 unit(s)
- [Built-in Type Adapter Factories](default-adapters.md) `default-adapters` · 0 unit(s)
- [Object Construction Strategy](object-construction.md) `object-construction` · 0 unit(s)

**Depends on.**

- [Internal Utilities and Data Structures](internal-infrastructure.md) · model-inferred · 0 edge(s) · Adapters rely on JavaVersion, date utilities, and Streams bridging trees and streams.

**Depended on by.**

- [Reflection-Based Object Binding](reflective-type-adapter-factory.md) · model-inferred · 0 edge(s)

Parent: [Gson JSON Library](gson-json-library.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

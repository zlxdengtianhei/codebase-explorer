# Field Binding and Introspection

**Capability.** Builds reflective TypeAdapters over class fields with naming and exclusion rules, backed by reflection utilities and record introspection.

Readers tracing how fields map to JSON members should come here. One child constructs the adapter factory; the other supplies accessible-object handling and record support.

**Children.**

- [Reflective type adapter factory](reflective-type-adapter-factory.md) `reflective-type-adapter-factory` · 14 unit(s)
- [Reflection and record support](reflection-and-record-support.md) `reflection-and-record-support` · 12 unit(s)

**Depends on.**

- [Instance Creation and Access Control](instance-creation-and-access-control.md) · graph-confirmed · 4 edge(s)

**Depended on by.**

- [Instance Creation and Access Control](instance-creation-and-access-control.md) · graph-confirmed · 4 edge(s)

Parent: [Reflective Object Binding](reflective-object-binding.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

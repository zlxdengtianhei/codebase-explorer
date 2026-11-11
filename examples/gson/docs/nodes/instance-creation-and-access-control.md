# Instance Creation and Access Control

**Capability.** Produces object constructors for deserialization—from InstanceCreators to Unsafe allocation—and filters which classes reflection may touch.

Come here for how deserialized objects are instantiated and which classes are permitted. The children divide constructor production from reflection access filtering.

**Children.**

- [Instance construction utilities](instance-construction-utilities.md) `instance-construction-utilities` · 18 unit(s)
- [Reflection access filtering](reflection-access-filtering.md) `reflection-access-filtering` · 5 unit(s)

**Depends on.**

- [Field Binding and Introspection](field-binding-and-introspection.md) · graph-confirmed · 4 edge(s)

**Depended on by.**

- [Field Binding and Introspection](field-binding-and-introspection.md) · graph-confirmed · 4 edge(s)

Parent: [Reflective Object Binding](reflective-object-binding.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

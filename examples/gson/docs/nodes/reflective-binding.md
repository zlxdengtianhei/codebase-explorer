# Reflection Policy and Object Binding

**Capability.** Turns arbitrary classes and records into adapters and decides what reflection may touch: exclusion strategies (version, modifier, Expose, inner-class rules), field naming, access filters, low-level reflection helpers, per-field BoundField collection, and @JsonAdapter handling.

Use this subtree to trace how objects have their fields bound: which members are omitted, how names derive, and how regular classes differ from records.

**Children.**

- [Exclusion and Reflection Policy](reflection-policy.md) `reflection-policy` · 0 unit(s)
- [Reflection-Based Object Binding](reflective-type-adapter-factory.md) `reflective-type-adapter-factory` · 0 unit(s)

**Depends on.**

- [Runtime Generic Type Model](type-model.md) · model-inferred · 0 edge(s)

Parent: [Gson JSON Library](gson-json-library.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

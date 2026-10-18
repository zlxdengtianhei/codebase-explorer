# Reflection-Based Object Binding

**Capability.** Turns arbitrary classes and records into adapters by walking their fields, resolving names, exclusion, accessibility, and per-field adapters, and by honoring @JsonAdapter at type and field level.

Use the ReflectiveTypeAdapterFactory subtree to trace how BoundFields are collected across the class hierarchy and how regular classes differ from records; the @JsonAdapter annotation factory child instantiates and caches annotated adapter classes.

**Depends on.**

- [Type Adapter Pipeline and Object Construction](adapter-pipeline.md) · model-inferred · 0 edge(s)
- [Exclusion and Reflection Policy](reflection-policy.md) · model-inferred · 0 edge(s)

Parent: [Reflection Policy and Object Binding](reflective-binding.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

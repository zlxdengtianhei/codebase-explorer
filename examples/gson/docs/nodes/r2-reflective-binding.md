# Reflection-Based Object Binding

**Capability.** Turns arbitrary classes and records into adapters by walking their fields, resolving names, exclusion, accessibility, and per-field adapters, and by honoring @JsonAdapter at type and field level.

Use the ReflectiveTypeAdapterFactory subtree to trace how BoundFields are collected across the class hierarchy and how regular classes differ from records. The JsonAdapterAnnotationTypeAdapterFactory child implements the @JsonAdapter contract, instantiating annotated adapter classes and caching factories per class.

**Children.**

- [ReflectiveTypeAdapterFactory](r2-reflective-type-adapter-factory.md) `r2-reflective-type-adapter-factory` · 14 unit(s)
- [@JsonAdapter Annotation Handling](r2-jsonadapter-annotation-factory.md) `r2-jsonadapter-annotation-factory` · 8 unit(s)

Parent: [Gson JSON Library](r2-gson.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

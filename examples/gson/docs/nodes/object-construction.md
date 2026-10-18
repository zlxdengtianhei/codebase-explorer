# Object Construction Strategy

**Capability.** Selects, in strict priority order, how to instantiate a requested type: registered InstanceCreator, special collections, no-args constructor, JDK default implementations for Collection/Map interfaces, or last-resort Unsafe allocation, with instantiability diagnostics.

Consult ConstructorConstructor.get to understand which constructor wins for a type. All adapter factories obtain their ObjectConstructors here, so this priority order affects every binding path.

**Depends on.**

- [Runtime Generic Type Model](type-model.md) · model-inferred · 0 edge(s)

Parent: [Type Adapter Pipeline and Object Construction](adapter-pipeline.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

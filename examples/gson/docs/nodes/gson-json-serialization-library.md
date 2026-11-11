# Gson JSON Serialization Library

**Capability.** Converts Java objects to JSON and back, combining streaming readers/writers, an element tree model, reflective binding, and a pluggable adapter framework.

This is the whole gson repository. Readers should start at the Gson facade and adapter groups, then descend into streaming, tree, and reflection subgroups depending on the feature of interest.

**Children.**

- [Type Adapter Framework](type-adapter-framework.md) `type-adapter-framework` · 120 unit(s)
- [Public API and Type Resolution](public-api-and-type-resolution.md) `public-api-and-type-resolution` · 96 unit(s)
- [JSON Element Tree Model](json-element-tree-model.md) `json-element-tree-model` · 79 unit(s)
- [JSON Reading Infrastructure](json-reading-infrastructure.md) `json-reading-infrastructure` · 76 unit(s)
- [Reflective Object Binding](reflective-object-binding.md) `reflective-object-binding` · 49 unit(s)
- [JSON Writing Infrastructure](json-writing-infrastructure.md) `json-writing-infrastructure` · 40 unit(s)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

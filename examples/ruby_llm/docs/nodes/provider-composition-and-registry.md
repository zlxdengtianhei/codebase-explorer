# Provider Composition And Registry

**Capability.** Combines provider-specific integration modules with model registry and media formatting so backends expose chat, models, media, and capabilities.

Come here for provider composition and model registry/media concerns. Provider Integration Compositions assembles backend modules; Model Registry And Media maintains metadata and formats media/capability data for resolution.

**Children.**

- [Provider Integration Compositions](provider-integration-compositions.md) `provider-integration-compositions` · 22 unit(s)
- [Model Registry And Media](model-registry-and-media.md) `model-registry-and-media` · 16 unit(s)

Parent: [Provider Model Abstractions](provider-model-abstractions.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

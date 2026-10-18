# Model Registry

**Capability.** A provider-agnostic catalog of model metadata: registry loading and querying, resolution of model id + provider into Model::Info, rich metadata objects, and generic alias mapping.

Query RubyLLM.models to find and resolve models; Models.resolve returns a Model::Info plus a provider instance. Model::Info and PricingTier normalize sparse metadata; Aliases maps generic names to provider ids.

**Children.**

- [Registry Catalog](r1-registry-catalog.md) `r1-registry-catalog` · 3 unit(s)
- [Model Metadata Objects](r1-model-metadata.md) `r1-model-metadata` · 2 unit(s)
- [Model Aliases](r1-aliases.md) `r1-aliases` · 1 unit(s)

Parent: [RubyLLM Gem](r1-ruby-llm-gem.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

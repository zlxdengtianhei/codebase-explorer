# Model Registry

**Capability.** A provider-agnostic catalog of model metadata: registry loading and querying, resolution of model id + provider into Model::Info, rich metadata objects, and generic alias mapping.

Query RubyLLM.models to find and resolve models; Models.resolve returns a Model::Info plus a provider instance. Model::Info and PricingTier normalize sparse metadata; Aliases maps generic names to provider ids.

**Depends on.**

- [Shared Utilities](shared-utilities.md) · model-inferred · 0 edge(s)

**Depended on by.**

- [ActiveRecord & Rails Integration](active-record-integration.md) · model-inferred · 0 edge(s)
- [Developer Tooling](developer-tooling.md) · model-inferred · 0 edge(s)
- [Public API, Bootstrap & Core Runtime](public-api-bootstrap.md) · model-inferred · 0 edge(s)

Parent: [RubyLLM](ruby-llm.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

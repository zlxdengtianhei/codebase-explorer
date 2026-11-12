# Capability And Model Metadata

**Capability.** Defines model capability, pricing, modality, and display metadata plus value objects used to resolve and describe provider models.

Use this group for model capability and metadata representation. Provider Capability Metadata derives provider-specific facts; Model Metadata Value Objects store metadata, modalities, pricing, tiers, and predicates.

**Children.**

- [Provider Capability Metadata](provider-capability-metadata.md) `provider-capability-metadata` · 23 unit(s)
- [Model Metadata Value Objects](model-metadata-value-objects.md) `model-metadata-value-objects` · 7 unit(s)

Parent: [Provider Model Abstractions](provider-model-abstractions.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

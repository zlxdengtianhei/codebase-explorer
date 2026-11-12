# Provider Model Abstractions

**Capability.** Organizes provider integrations, model metadata, and embedding hooks so LLM backends share consistent model and capability abstractions.

Use this group to understand how provider-specific modules, model metadata, and embedding hooks fit together. G3 composes provider integrations and registry/media support; G4 supplies capability and model metadata value objects; embedding/provider hooks cover embedding flow and provider-specific hooks.

**Children.**

- [Provider Composition And Registry](provider-composition-and-registry.md) `provider-composition-and-registry` · 38 unit(s)
- [Capability And Model Metadata](capability-and-model-metadata.md) `capability-and-model-metadata` · 30 unit(s)
- [Embedding And Provider Hooks](embedding-and-provider-hooks.md) `embedding-and-provider-hooks` · 17 unit(s)

**Depends on.**

- [Provider Transport And Streaming](provider-transport-and-streaming.md) · graph-confirmed · 6 edge(s) · Provider model abstractions use provider transport and streaming to connect model operations to provider requests.

**Depended on by.**

- [Provider Transport And Streaming](provider-transport-and-streaming.md) · graph-confirmed · 2 edge(s)

Parent: [RubyLLM Multi-Provider Library](rubyllm-multi-provider-library.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

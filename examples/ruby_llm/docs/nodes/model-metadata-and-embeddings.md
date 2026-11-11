# Model Metadata and Embeddings

**Capability.** Resolves model identity, capabilities, limits, and pricing across providers, and implements embedding endpoints and the Mistral adapter.

Come here to look up or extend what a model can do and what it costs, or to work with embeddings. G5 holds per-provider capability lookups; the remaining children add embeddings endpoints, Mistral support, and model info value objects.

**Children.**

- [Per-Provider Capability Lookups](per-provider-capability-lookups.md) `per-provider-capability-lookups` · 46 unit(s)
- [Embeddings and Mistral support](embeddings-and-mistral-support.md) `embeddings-and-mistral-support` · 18 unit(s)
- [Model info value objects](model-info-value-objects.md) `model-info-value-objects` · 6 unit(s)

**Depends on.**

- [Provider Adapters and Tools](provider-adapters-and-tools.md) · graph-confirmed · 2 edge(s) · Model metadata and embedding support feed capability lookups into the provider adapters.
- [Streaming and Provider Core](streaming-and-provider-core.md) · graph-confirmed · 2 edge(s)

**Depended on by.**

- [Provider Adapters and Tools](provider-adapters-and-tools.md) · graph-confirmed · 1 edge(s)
- [Streaming and Provider Core](streaming-and-provider-core.md) · model-inferred · 1 inferred relation(s)

Parent: [RubyLLM LLM Integration Gem](rubyllm-llm-integration-gem.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

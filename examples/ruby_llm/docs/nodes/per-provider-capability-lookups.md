# Per-Provider Capability Lookups

**Capability.** Provides provider-specific resolution of model families, context limits, capabilities, pricing, and display names.

Come here to adjust how a specific provider's models are classified or priced. Each child handles one provider (OpenAI, Perplexity, DeepSeek, Anthropic, Gemini, Bedrock) with its own lookup conventions.

**Children.**

- [OpenAI model capabilities](openai-model-capabilities.md) `openai-model-capabilities` · 10 unit(s)
- [Perplexity provider adapter](perplexity-provider-adapter.md) `perplexity-provider-adapter` · 9 unit(s)
- [DeepSeek provider adapter](deepseek-provider-adapter.md) `deepseek-provider-adapter` · 8 unit(s)
- [Anthropic model metadata](anthropic-model-metadata.md) `anthropic-model-metadata` · 7 unit(s)
- [Gemini model capabilities](gemini-model-capabilities.md) `gemini-model-capabilities` · 6 unit(s)
- [Bedrock model capabilities](bedrock-model-capabilities.md) `bedrock-model-capabilities` · 6 unit(s)

Parent: [Model Metadata and Embeddings](model-metadata-and-embeddings.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

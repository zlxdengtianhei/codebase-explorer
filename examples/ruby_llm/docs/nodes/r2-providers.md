# Provider Adapters

**Capability.** Per-vendor adapters translating RubyLLM's model of chat, embeddings, images, moderation, transcription, models, and streaming into each vendor's wire format.

Each provider subtree owns payload rendering, response parsing, streaming, and model catalogs for its vendor. OpenAI-derived vendors reuse OpenAI modules via inheritance.

**Children.**

- [OpenAI Adapter](r2-provider-openai.md) `r2-provider-openai` · 14 unit(s)
- [Anthropic Adapter](r2-provider-anthropic.md) `r2-provider-anthropic` · 13 unit(s)
- [Bedrock Adapter](r2-provider-bedrock.md) `r2-provider-bedrock` · 15 unit(s)
- [Gemini Adapter](r2-provider-gemini.md) `r2-provider-gemini` · 22 unit(s)
- [Mistral Capabilities](r2-provider-mistral-capabilities.md) `r2-provider-mistral-capabilities` · 6 unit(s)

Parent: [RubyLLM](r2-ruby-llm.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

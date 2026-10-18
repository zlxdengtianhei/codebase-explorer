# Provider Adapters

**Capability.** Concrete per-vendor adapters translating RubyLLM's provider-independent model of chat, embeddings, images, moderation, transcription, models, and streaming into each vendor's wire format: an OpenAI-descended family plus Gemini, Anthropic, Bedrock, and Ollama.

Each provider subtree owns payload rendering, response parsing, streaming, capability metadata, and model catalogs for its vendor; OpenAI-derived vendors reuse OpenAI modules via inheritance. Providers depend on conversation-core value objects (Message, ToolCall, Image), shared utilities, and the transport base.

**Depends on.**

- [Conversation Core](conversation-core.md) · model-inferred · 0 edge(s)
- [Shared Utilities](shared-utilities.md) · model-inferred · 0 edge(s)
- [HTTP Transport & Provider Base](transport.md) · model-inferred · 0 edge(s)

Parent: [RubyLLM](ruby-llm.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

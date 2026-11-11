# Provider Adapters and Tools

**Capability.** Defines provider classes and their composition, plus the Tool DSL for declaring and executing function calls.

Come here to add or modify a provider or to define tools. Provider class composition assembles each provider from chat, media, and models modules, while Tool definition and execution supplies the parameter schema and invocation machinery.

**Children.**

- [Chat Wire and Media Formats](chat-wire-and-media-formats.md) `chat-wire-and-media-formats` · 36 unit(s)
- [Provider class composition](provider-class-composition.md) `provider-class-composition` · 18 unit(s)
- [Tool definition and execution](tool-definition-and-execution.md) `tool-definition-and-execution` · 17 unit(s)

**Depends on.**

- [Attachment Normalization and MIME](attachment-normalization-and-mime.md) · graph-confirmed · 2 edge(s)
- [Model Metadata and Embeddings](model-metadata-and-embeddings.md) · graph-confirmed · 1 edge(s)
- [Persistence and Conversation Layer](persistence-and-conversation-layer.md) · model-inferred · 1 inferred relation(s)
- [Streaming and Provider Core](streaming-and-provider-core.md) · graph-confirmed · 9 edge(s) · Provider adapters rely on the shared provider base, connections, and streaming machinery to execute requests.

**Depended on by.**

- [Model Metadata and Embeddings](model-metadata-and-embeddings.md) · graph-confirmed · 2 edge(s) · Model metadata and embedding support feed capability lookups into the provider adapters.
- [Persistence and Conversation Layer](persistence-and-conversation-layer.md) · graph-confirmed · 4 edge(s) · 2 inferred relation(s) · The persistence layer uses provider adapters and tool machinery when converting stored records into live chats.
- [Streaming and Provider Core](streaming-and-provider-core.md) · graph-confirmed · 1 edge(s)

Parent: [RubyLLM LLM Integration Gem](rubyllm-llm-integration-gem.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

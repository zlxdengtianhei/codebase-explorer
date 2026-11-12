# Provider Transport And Streaming

**Capability.** Handles provider connections, request/error behavior, and streaming chunk accumulation so responses are transported and assembled consistently.

Come here for connection, error, and streaming mechanics. G6 formats chat/tool payloads and auxiliary operations; Provider Connection And Errors wraps HTTP/config/errors; Streaming Chunk Accumulation adapts and accumulates streamed chunks.

**Children.**

- [Chat Payload And Auxiliary APIs](chat-payload-and-auxiliary-apis.md) `chat-payload-and-auxiliary-apis` · 41 unit(s)
- [Provider Connection And Errors](provider-connection-and-errors.md) `provider-connection-and-errors` · 22 unit(s)
- [Streaming Chunk Accumulation](streaming-chunk-accumulation.md) `streaming-chunk-accumulation` · 17 unit(s)

**Depends on.**

- [Attachment And Content Handling](attachment-and-content-handling.md) · graph-confirmed · 2 edge(s) · 1 inferred relation(s)
- [Provider Model Abstractions](provider-model-abstractions.md) · graph-confirmed · 2 edge(s)

**Depended on by.**

- [Attachment And Content Handling](attachment-and-content-handling.md) · graph-confirmed · 2 edge(s) · Attachment and content handling uses provider transport and streaming for provider-facing content handling.
- [Chat Persistence And Orchestration](chat-persistence-and-orchestration.md) · graph-confirmed · 3 edge(s) · Chat persistence and orchestration uses provider transport and streaming to send chat requests and consume streamed responses.
- [Provider Model Abstractions](provider-model-abstractions.md) · graph-confirmed · 6 edge(s) · Provider model abstractions use provider transport and streaming to connect model operations to provider requests.

Parent: [RubyLLM Multi-Provider Library](rubyllm-multi-provider-library.md)

Look up code: the commands are under "Read further" in [INDEX.md](../INDEX.md); `cbe query` and `cbe source` take a unit title or anchor from this page.

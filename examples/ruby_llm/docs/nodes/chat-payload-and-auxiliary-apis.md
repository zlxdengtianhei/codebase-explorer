# Chat Payload And Auxiliary APIs

**Capability.** Formats chat messages, tools, schemas, and provider payloads while covering auxiliary operations such as aliases, images, moderation, transcription, and Rails entrypoints.

Use this group for message/tool formatting and auxiliary provider operations. Chat Message And Tool Formatting builds payloads and parses completions; Media And Auxiliary Operations handles aliases, images, moderation, transcription, model listing, and Rails integration.

**Children.**

- [Chat Message And Tool Formatting](chat-message-and-tool-formatting.md) `chat-message-and-tool-formatting` · 29 unit(s)
- [Media And Auxiliary Operations](media-and-auxiliary-operations.md) `media-and-auxiliary-operations` · 12 unit(s)

**Depends on.**

- [Provider Connection And Errors](provider-connection-and-errors.md) · graph-confirmed · 3 edge(s) · Chat payload and auxiliary APIs use provider connection and errors for request dispatch and error handling.
- [Streaming Chunk Accumulation](streaming-chunk-accumulation.md) · graph-confirmed · 1 edge(s)

**Depended on by.**

- [Streaming Chunk Accumulation](streaming-chunk-accumulation.md) · graph-confirmed · 3 edge(s) · 1 inferred relation(s) · Streaming chunk accumulation uses chat payload and auxiliary APIs to turn accumulated chunks into chat messages.

Parent: [Provider Transport And Streaming](provider-transport-and-streaming.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

# Conversation Core

**Capability.** Provider-independent conversation machinery: chat sessions and the completion/tool-call loop, message and tool-call value objects, the tool definition DSL, stream accumulation, and attachment/image content types.

Use this subtree for everything a caller manipulates directly regardless of provider. Chat composes messages and tools and drives completion; StreamAccumulator turns provider chunks back into Messages. Attachment, Image, and MimeType model user-supplied and generated media.

**Children.**

- [Chat Session & Completion Loop](r1-chat-session.md) `r1-chat-session` · 4 unit(s)
- [Message & ToolCall Value Objects](r1-messaging-primitives.md) `r1-messaging-primitives` · 2 unit(s)
- [Tool Definition DSL](r1-tool-dsl.md) `r1-tool-dsl` · 1 unit(s)
- [Stream Accumulation](r1-streaming-accumulation.md) `r1-streaming-accumulation` · 3 unit(s)
- [Attachments & Images](r1-content-media.md) `r1-content-media` · 3 unit(s)

Parent: [RubyLLM Gem](r1-ruby-llm-gem.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

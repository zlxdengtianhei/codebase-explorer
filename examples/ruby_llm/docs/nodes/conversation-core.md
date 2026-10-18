# Conversation Core

**Capability.** Provider-independent conversation machinery: chat sessions and the completion/tool-call loop, message and tool-call value objects, the tool definition DSL, stream accumulation, and attachment/image content types.

Use this for everything a caller manipulates directly regardless of provider. Chat composes messages and tools and drives completion; StreamAccumulator turns provider chunks back into Messages. Attachment, Image, and MimeType model user-supplied and generated media.

**Depends on.**

- [Public API, Bootstrap & Core Runtime](public-api-bootstrap.md) · model-inferred · 0 edge(s)
- [Shared Utilities](shared-utilities.md) · model-inferred · 0 edge(s)

**Depended on by.**

- [ActiveRecord & Rails Integration](active-record-integration.md) · model-inferred · 0 edge(s)
- [Provider Adapters](provider-framework.md) · model-inferred · 0 edge(s)
- [Public API, Bootstrap & Core Runtime](public-api-bootstrap.md) · model-inferred · 0 edge(s)

Parent: [RubyLLM](ruby-llm.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

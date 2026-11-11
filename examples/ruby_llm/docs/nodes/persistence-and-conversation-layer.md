# Persistence and Conversation Layer

**Capability.** Bridges chat conversations to ActiveRecord persistence and orchestrates message history, configuration, and completion dispatch.

Come here when chats must be stored in a database or driven through the high-level API. The ActiveRecord persistence bridge maps records to RubyLLM objects; G8 provides conversation orchestration and the gem's entry facade.

**Children.**

- [ActiveRecord persistence bridge](activerecord-persistence-bridge.md) `activerecord-persistence-bridge` · 27 unit(s)
- [Chat Orchestration and Gem Facade](chat-orchestration-and-gem-facade.md) `chat-orchestration-and-gem-facade` · 24 unit(s)

**Depends on.**

- [Attachment Normalization and MIME](attachment-normalization-and-mime.md) · graph-confirmed · 1 edge(s)
- [Provider Adapters and Tools](provider-adapters-and-tools.md) · graph-confirmed · 4 edge(s) · 2 inferred relation(s) · The persistence layer uses provider adapters and tool machinery when converting stored records into live chats.

**Depended on by.**

- [Provider Adapters and Tools](provider-adapters-and-tools.md) · model-inferred · 1 inferred relation(s)

Parent: [RubyLLM LLM Integration Gem](rubyllm-llm-integration-gem.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

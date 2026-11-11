# Chat Orchestration and Gem Facade

**Capability.** Manages conversations with fluent tool and parameter configuration, and exposes the RubyLLM module entry point and global configuration.

Come here to drive conversations programmatically or to configure the gem. Chat conversation orchestration handles history, dispatch, and tool-call callbacks; Gem entry and configuration provides the module facade, Configuration, Contexts, and provider registration.

**Children.**

- [Chat conversation orchestration](chat-conversation-orchestration.md) `chat-conversation-orchestration` · 13 unit(s)
- [Gem entry and configuration](gem-entry-and-configuration.md) `gem-entry-and-configuration` · 11 unit(s)

**Depended on by.**

- [ActiveRecord persistence bridge](activerecord-persistence-bridge.md) · graph-confirmed · 2 edge(s) · The ActiveRecord bridge builds and drives Chat objects from persisted records.

Parent: [Persistence and Conversation Layer](persistence-and-conversation-layer.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

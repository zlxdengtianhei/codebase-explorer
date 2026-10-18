# ActiveRecord & Rails Integration

**Capability.** Persistence-facing mixins that bridge database rows and in-memory RubyLLM objects: legacy and modern acts_as support for chats, messages, tool calls, and model records, row-to-value-object conversion, registry-record syncing, and the Rails railtie hook.

Use this when ActiveRecord-backed models must talk to LLMs or expose registry data. Legacy support rebuilds chats from persisted rows; MessageMethods and ModelMethods convert rows to value objects and sync assistant responses back. The railtie activates only when Rails::Railtie is loaded; generators emit these declarations.

**Depends on.**

- [Conversation Core](conversation-core.md) · model-inferred · 0 edge(s)
- [Model Registry](model-registry.md) · model-inferred · 0 edge(s)
- [Shared Utilities](shared-utilities.md) · model-inferred · 0 edge(s)

**Depended on by.**

- [Developer Tooling](developer-tooling.md) · model-inferred · 0 edge(s)

Parent: [RubyLLM](ruby-llm.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

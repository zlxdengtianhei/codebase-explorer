# ActiveRecord Integration

**Capability.** Maps chats, messages, tool calls, and model records onto ActiveRecord models via acts_as_* declarations, and syncs LLM completions into persisted rows.

Use to understand how a persisted chat model bridges to the in-memory Chat, how model strings resolve to model rows, and how assistant responses are written back. Generators emit these declarations.

**Children.**

- [acts\_as Declarations](r2-acts-as-declarations.md) `r2-acts-as-declarations` · 5 unit(s)
- [ChatMethods Persistence](r2-chat-persistence.md) `r2-chat-persistence` · 9 unit(s)

Parent: [RubyLLM](r2-ruby-llm.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

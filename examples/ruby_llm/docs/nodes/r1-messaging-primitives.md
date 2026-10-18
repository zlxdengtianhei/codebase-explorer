# Message & ToolCall Value Objects

**Capability.** The core value objects of a conversation: a role-restricted Message and an immutable ToolCall.

These are produced by providers and stream accumulation and consumed by Chat. Message roles are limited to the frozen ROLES list.

**Depended on by.**

- [Bedrock Event-Stream Streaming](r1-bedrock-streaming.md) · model-inferred · 0 edge(s)
- [Chat Session & Completion Loop](r1-chat-session.md) · graph-confirmed · 1 edge(s) · Chat constructs Message objects when composing and completing conversations.
- [Gemini Chat & Schema](r1-gemini-chat.md) · graph-confirmed · 1 edge(s)
- [Stream Accumulation](r1-streaming-accumulation.md) · graph-confirmed · 3 edge(s) · StreamAccumulator finalizes accumulated chunks into Message and ToolCall objects.
- [Anthropic Adapter](r2-provider-anthropic.md) · graph-only · 3 edge(s)
- [Gemini Tools](r1-gemini-tools.md) · graph-only · 1 edge(s)
- [OpenAI Tools](r1-openai-tools.md) · graph-only · 1 edge(s)
- [OpenAI Adapter](r2-provider-openai.md) · graph-only · 1 edge(s)

Parent: [Conversation Core](r1-conversation-core.md)

## Units (2)

<a id="u-cb349e033cb3"></a>
### `Message`

`class Message` · [lib/ruby_llm/message.rb:L5-L12][f1]

One chat-conversation message with a role restricted to the frozen ROLES list (system, user, assistant, tool).

`initialize(options)` requires :role and :content keys (KeyError if missing), converts role to a symbol, normalizes content via `normalize_content` (String becomes `Content.new(string)`, Hash becomes `Content.new(hash[:text], hash)`, anything else is stored as-is), stores optional model_id, tool_calls, tool_call_id, token counts, and raw payload, then `ensure_valid_role` raises `InvalidRoleError` if the role is not in ROLES. `content` unwraps a Content holder back to its plain text only when text is present and no attachments exist; otherwise the Content object is returned. `tool_call?` is true when tool_calls is non-nil and non-empty; `tool_result?` is true when tool_call_id is non-nil and non-empty; `tool_results` returns the content only for tool-result messages. `to_h` builds a hash of the message fields and `.compact`s it, dropping nil entries (including a nil model_id). `instance_variables` subtracts :@raw from super, excluding the raw payload from reflection; `content=` is the only writer.

uses: [Content](r2-content-value-objects.md#u-fb6f20b3ce1b)

<a id="u-f564974b1732"></a>
### `ToolCall`

`class ToolCall` · [lib/ruby_llm/tool_call.rb:L5-L8][f2]

Immutable value object for a model-issued function call.

`initialize(id:, name:, arguments: {})` stores the three keywords (arguments defaults to an empty hash, no validation or copying). `to_h` returns `{id:, name:, arguments:}` with the same references, so mutation of the caller's arguments hash is visible through both. Graph evidence shows provider tool-parsing and stream-accumulation code constructs it.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/message.rb
[f2]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/tool_call.rb
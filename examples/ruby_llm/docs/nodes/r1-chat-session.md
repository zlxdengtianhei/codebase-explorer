# Chat Session & Completion Loop

**Capability.** Configures a Chat conversation (model, tools, params, Enumerable plumbing) and drives completion, including executing requested tool calls and re-entering complete.

Read Chat#complete as the main entry point; it delegates to provider payloads and loops through handle_tool_calls. Initialization validates provider/model assumptions early.

**Depends on.**

- [Message & ToolCall Value Objects](r1-messaging-primitives.md) · graph-confirmed · 1 edge(s) · Chat constructs Message objects when composing and completing conversations.
- [Registry Catalog](r1-registry-catalog.md) · model-inferred · 0 edge(s) · Chat uses Models.resolve to pick a model and provider from the registry catalog.
- [Tool Definition DSL](r1-tool-dsl.md) · model-inferred · 0 edge(s) · Chat executes tool calls whose schemas are declared via the tool DSL.

**Depended on by.**

- [Legacy acts\_as Support](r1-legacy-acts-as.md) · graph-confirmed · 1 edge(s) · Legacy ChatLegacyMethods.to_llm builds an in-memory Chat from persisted rows and delegates complete to it.
- [Public API & Bootstrap](r1-public-api-bootstrap.md) · graph-confirmed · 1 edge(s) · The RubyLLM facade delegates to Chat, constructing a chat session for callers.
- [ChatMethods Persistence](r2-chat-persistence.md) · graph-only · 1 edge(s)
- [Configuration and Context](r2-config-context.md) · graph-only · 1 edge(s)

Parent: [Conversation Core](r1-conversation-core.md)

## Units (4)

<a id="u-eaa27ccbda2c"></a>
### `chat.rb-configuration`

`def ask(message = nil, with: nil, &)` · [lib/ruby_llm/chat.rb:L33-L36][f1]

Configures a Chat conversation and supplies its Enumerable and message plumbing.

with_instructions adds a system message, or removes all prior system messages first when replace: true. with_tool accepts a class (instantiated) or instance and registers it under its name.to_sym; with_tools compacts arguments and clears the registry first on replace. with_model delegates to Models.resolve and caches the provider's connection; with_context swaps config and re-resolves the current model with assume_exists: true. with_params/with_headers replace their hashes wholesale; with_schema accepts an object responding to to_json_schema (storing its [:schema]) or a raw schema value. The four on_* methods store per-event callbacks and return self. ask (aliased say) adds a user message and completes. each iterates messages, making Chat Enumerable. add_message wraps non-Message input in Message.new. reset_messages! empties history. instance_variables hides @connection/@config so serialization does not capture them. Private helpers: wrap_streaming_block fires :new_message on the first streamed chunk only; execute_tool looks up the tool by name.to_sym and calls it with the call's arguments; build_content passes Content-like values through and otherwise wraps message plus attachments in Content.new; content_like? accepts Content or Content::Raw.

calls: [RubyLLM.Chat.complete](r1-chat-session.md#u-115f6c6ea65d); uses: [RubyLLM.Models.resolve](r1-registry-catalog.md#u-3dcbba4582dc)

**Uncertainties.**

- Content.new in build_content has three candidate constructors in the graph; its exact constructor contract is outside this batch

<a id="u-115f6c6ea65d"></a>
### `RubyLLM.Chat.complete`

`def complete(&) # rubocop:disable Metrics/PerceivedComplexity` · [lib/ruby_llm/chat.rb:L124-L154][f1]

Sends the conversation to the provider and finalizes the assistant reply.

Calls provider.complete with messages, tools, temperature, params, headers, schema, and the streaming block wrapped so the :new_message callback fires on the first streamed chunk; the raw :new_message callback fires only when no block was given. When a schema is set and the content is a String, content is JSON.parse'd, keeping the string on JSON::ParserError. The response is appended to messages, :end_message fires with it, and if the response has tool calls, handling is delegated to handle_tool_calls (which may recurse into complete); otherwise the response is returned.

calls: [RubyLLM.Chat.handle_tool_calls](r1-chat-session.md#u-1b19f1a82466), [chat.rb-configuration](r1-chat-session.md#u-eaa27ccbda2c)

**Uncertainties.**

- Whether provider.complete streams or blocks depends on the provider implementation, not visible here

<a id="u-1b19f1a82466"></a>
### `RubyLLM.Chat.handle_tool_calls`

`def handle_tool_calls(response, &) # rubocop:disable Metrics/PerceivedComplexity` · [lib/ruby_llm/chat.rb:L188-L205][f1]

Executes every requested tool call, appending one tool-role message per result.

For each tool call it fires :new_message and :tool_call callbacks, runs execute_tool, fires :tool_result, converts a Tool::Halt result to its content, stringifies non-content-like payloads, adds the tool message with the originating tool_call_id, and fires :end_message with it. When a Halt result is seen its value is captured; after the loop a Halt short-circuits and is returned instead of continuing the conversation, otherwise complete is called again so the model can react to the tool outputs.

calls: [chat.rb-configuration](r1-chat-session.md#u-eaa27ccbda2c), [RubyLLM.Chat.complete](r1-chat-session.md#u-115f6c6ea65d)

<a id="u-986c171f6698"></a>
### `RubyLLM.Chat.initialize`

`def initialize(model: nil, provider: nil, assume_model_exists: false, context: nil)` · [lib/ruby_llm/chat.rb:L10-L31][f1]

Builds a chat session, raising ArgumentError immediately when assume_model_exists is true without a provider.

Picks the config from the given context or the global RubyLLM.config, resolves the model (falling back to config.default_model) via with_model, and initializes empty messages, tools, params, headers, a nil schema and temperature, and a nil-valued @on callback hash for new_message/end_message/tool_call/tool_result events.

calls: [chat.rb-configuration](r1-chat-session.md#u-eaa27ccbda2c); uses: [chat.rb-configuration](r1-chat-session.md#u-eaa27ccbda2c)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/chat.rb
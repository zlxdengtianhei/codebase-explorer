# Chat conversation orchestration

**Capability.** Manages a conversation: message history, fluent configuration of tools and parameters, completion dispatch, and tool-call execution with callbacks.

The central Chat object: chainable setup (instructions, tools, params, schema), ask/complete flows that delegate to the provider, and the loop that executes tool calls, honors Halt, and fires lifecycle callbacks. Also Enumerable over its messages.

**Depends on.**

- [Provider chat wire formatting](provider-chat-wire-formatting.md) · graph-only · 1 edge(s) · Chat orchestration renders conversation state into provider-specific chat payloads.

**Depended on by.**

- [Gem entry and configuration](gem-entry-and-configuration.md) · graph-confirmed · 2 edge(s)
- [ActiveRecord persistence bridge](activerecord-persistence-bridge.md) · graph-only · 2 edge(s)

Parent: [Chat Orchestration and Gem Facade](chat-orchestration-and-gem-facade.md)

## Units (13)

<a id="u-645865ce3852"></a>
### `chat.rb-chat`

`class Chat` · [lib/ruby_llm/chat.rb:L5-L10][f1]

Represents a conversation with an AI model, holding messages, tools, params, headers, schema, and event callbacks.

initialize raises ArgumentError when assume_model_exists is true without a provider, resolves config from the context or global config, resolves the model via with_model (defaulting to config.default_model), and initializes empty messages/tools/params/headers, nil temperature/schema, and four nil callbacks. Includes Enumerable over messages.

<a id="u-7ad41d62d255"></a>
### `chat.rb-chat-configuration-builders`

`def with_instructions(instructions, replace: false)` · [lib/ruby_llm/chat.rb:L40-L45][f1]

Fluent chainable configuration: with_instructions adds a system message (optionally removing existing system messages with replace:); with_tool registers a Tool instance (instantiating classes) keyed by its name symbol; with_tools registers many (optionally clearing first, nils skipped); with_model re-resolves model+provider via Models.resolve and refreshes the connection; with_temperature, with_params, with_headers replace their respective state; with_context swaps config and re-resolves the current model; with_schema accepts a Schema instance/class (via to_json_schema, taking the :schema entry) or a plain JSON schema hash.

All return self.

<a id="u-58e740285657"></a>
### `chat.rb-content-construction`

`def build_content(message, attachments)` · [lib/ruby_llm/chat.rb:L213-L217][f1]

build_content passes through Content/Content::Raw objects unchanged and otherwise wraps message plus attachments in a new Content; content_like?

is the predicate used for that check.

<a id="u-3d5e60698265"></a>
### `chat.rb-event-callbacks`

`def on_new_message(&block)` · [lib/ruby_llm/chat.rb:L100-L103][f1]

Register optional blocks fired during completion: on_new_message (at message start), on_end_message (with the finished message), on_tool_call, on_tool_result.

Each stores the block and returns self.

<a id="u-a8901225eea1"></a>
### `RubyLLM.Chat.add_message`

`def add_message(message_or_attributes)` · [lib/ruby_llm/chat.rb:L156-L160][f1]

Appends a Message (passing through existing Message instances, otherwise constructing one from attributes) to messages and returns it.

<a id="u-6c1bea735c37"></a>
### `RubyLLM.Chat.ask`

`def ask(message = nil, with: nil, &)` · [lib/ruby_llm/chat.rb:L33-L36][f1]

Appends a user message (wrapping non-Content input with attachments via build_content) and runs complete, returning its result; a block is forwarded for streaming.

<a id="u-115f6c6ea65d"></a>
### `RubyLLM.Chat.complete`

`def complete(&) # rubocop:disable Metrics/PerceivedComplexity` · [lib/ruby_llm/chat.rb:L124-L154][f1]

Sends the whole message history to the provider with tools, temperature, model, params, headers, schema, and an optional streaming block wrapped by wrap_streaming_block.

Without a streaming block it fires the new_message callback. When a schema is set and the response content is a String, it attempts JSON.parse and keeps the string on JSON::ParserError. It appends the response as a message, fires end_message, then either dispatches tool calls via handle_tool_calls (when the response has a tool call) or returns the response. Provider/network errors propagate uncaught.

<a id="u-0b21bbf177f2"></a>
### `RubyLLM.Chat.each`

`def each(&)` · [lib/ruby_llm/chat.rb:L120-L122][f1]

Delegates each to messages, enabling Enumerable iteration over the conversation.

<a id="u-843e2d9646be"></a>
### `RubyLLM.Chat.execute_tool`

`def execute_tool(tool_call)` · [lib/ruby_llm/chat.rb:L207-L211][f1]

Looks up the tool by the call's name symbol in the registered tools and invokes it with the call's arguments; a missing tool raises NoMethodError on nil.

<a id="u-1b19f1a82466"></a>
### `RubyLLM.Chat.handle_tool_calls`

`def handle_tool_calls(response, &) # rubocop:disable Metrics/PerceivedComplexity` · [lib/ruby_llm/chat.rb:L188-L205][f1]

Executes every tool call in the response in order without breaking on halts: for each it fires new_message and tool_call callbacks, executes the tool, fires tool_result, converts the result (Halt results use their content) to a Content-like value or to_s, appends a tool-role message with the tool_call_id, and fires end_message.

A Tool::Halt result is recorded into halt_result (overwriting any earlier one, so the last Halt wins) but remaining tool calls still execute and append their messages. After the loop, if any Halt occurred, that last Halt result is returned and no further completion request is made; otherwise it recurses into complete with the streaming block, continuing the tool loop until the model stops requesting tools.

<a id="u-96f04ac48aa5"></a>
### `RubyLLM.Chat.instance_variables`

`def instance_variables` · [lib/ruby_llm/chat.rb:L166-L168][f1]

Hides @connection and @config from the default instance_variables list (used by duplication/serialization helpers).

<a id="u-d755bd627e1d"></a>
### `RubyLLM.Chat.reset_messages!`

`def reset_messages!` · [lib/ruby_llm/chat.rb:L162-L164][f1]

Clears the messages array.

<a id="u-5429c02071a1"></a>
### `RubyLLM.Chat.wrap_streaming_block`

`def wrap_streaming_block(&block)` · [lib/ruby_llm/chat.rb:L172-L186][f1]

Returns nil without a block; otherwise wraps the streaming block so the new_message callback fires exactly once on the first received chunk, then forwards each chunk to the original block.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/chat.rb

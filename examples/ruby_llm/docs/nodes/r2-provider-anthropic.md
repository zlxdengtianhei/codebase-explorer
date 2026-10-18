# Anthropic Adapter

**Capability.** Renders Anthropic request payloads (system content, tool declarations, content blocks) and parses completions, tool calls, and streaming tool events back into Messages.

Read to see Anthropic's system-prompt separation and block-based content/tool formats. Bedrock reuses the Tools mixins.

**Depends on.**

- [Content and Result Value Objects](r2-content-value-objects.md) · model-inferred · 0 edge(s)
- [Shared Streaming](r2-streaming-shared.md) · model-inferred · 0 edge(s)
- [Message & ToolCall Value Objects](r1-messaging-primitives.md) · graph-only · 3 edge(s)
- [Shared Utilities](r1-shared-utilities.md) · graph-only · 1 edge(s)

**Depended on by.**

- [Bedrock Adapter](r2-provider-bedrock.md) · model-inferred · 0 edge(s) · Bedrock reuses Anthropic tool formatting mixins for messages and tool calls.

Parent: [Provider Adapters](r2-providers.md)

## Units (13)

<a id="u-93453b561b20"></a>
### `RubyLLM.Providers.Anthropic.Chat.render_payload`

`def render_payload(messages, tools:, temperature:, model:, stream: false, schema: nil…` · [lib/ruby_llm/providers/anthropic/chat.rb:L14-L21][f1]

Assembles the Anthropic request payload: partitions messages via separate_messages, converts the system messages through build_system_content, builds the base payload from the chat messages, then in a tap mutates it via add_optional_fields to attach system content, tool declarations, and temperature.

The schema parameter is accepted but unused (marked by the rubocop disable).

calls: [chat-rb-payload-helpers](r2-provider-anthropic.md#u-a0340b8d5f16), [RubyLLM.Providers.Anthropic.Chat.build_system_content](r2-provider-anthropic.md#u-4fd1f565e1b2)

<a id="u-4fd1f565e1b2"></a>
### `RubyLLM.Providers.Anthropic.Chat.build_system_content`

`def build_system_content(system_messages)` · [lib/ruby_llm/providers/anthropic/chat.rb:L27-L46][f1]

Converts system messages into Anthropic system content.

Returns [] immediately when there are no system messages. When more than one system message is given it logs a warning that they will be combined, then flat_maps each message: RubyLLM::Content::Raw values pass through unchanged, everything else goes through Media.format_content, producing a list of content blocks.

calls: [RubyLLM.Providers.Anthropic.Media.format_content](r2-provider-anthropic.md#u-ec5dcd587029)

<a id="u-3afe5a370160"></a>
### `RubyLLM.Providers.Anthropic.Chat.format_message`

`def format_message(msg)` · [lib/ruby_llm/providers/anthropic/chat.rb:L99-L107][f1]

Dispatches one message to its wire format by predicate: tool_call?

messages go to Tools.format_tool_call, tool_result? messages to Tools.format_tool_result, all other messages to format_basic_message.

calls: [RubyLLM.Providers.Anthropic.Tools.format_tool_call](r2-provider-anthropic.md#u-36674469387b), [RubyLLM.Providers.Anthropic.Tools.format_tool_result](r2-provider-anthropic.md#u-9c55482e5da8)

<a id="u-a0340b8d5f16"></a>
### `chat-rb-payload-helpers`

`def completion_url` · [lib/ruby_llm/providers/anthropic/chat.rb:L10-L12][f1]

Small payload-assembly helpers.

completion_url returns '/v1/messages'. separate_messages partitions messages on role == :system into [system_messages, chat_messages]. build_base_payload emits {model: model.id, messages: chat_messages.map { format_message }, stream:, max_tokens: model.max_tokens || 4096}. add_optional_fields mutates the payload: :tools (Tools.function_for per value) only when tools are present, :system only when system_content is non-empty, :temperature only when not nil. format_basic_message renders {role: convert_role(role), content: Media.format_content(content)}; convert_role maps :tool and :user to 'user' and everything else to 'assistant'.

calls: [RubyLLM.Providers.Anthropic.Chat.format_message](r2-provider-anthropic.md#u-3afe5a370160), [RubyLLM.Providers.Anthropic.Tools.function_for](r2-provider-anthropic.md#u-f6541c8c164e)

<a id="u-a4b46617a2b2"></a>
### `chat-rb-response-parsing`

`def parse_completion_response(response)` · [lib/ruby_llm/providers/anthropic/chat.rb:L63-L71][f1]

Turns an Anthropic completion response into a Message.

parse_completion_response reads the JSON body, defaults 'content' to [], extracts text via extract_text_content (concatenating all blocks of type 'text') and tool uses via Tools.find_tool_uses, then builds the message. build_message reads usage tokens: input_tokens, output_tokens, cache_read_input_tokens as cached_tokens; cache_creation_tokens comes from 'cache_creation_input_tokens', or, when nil and 'cache_creation' is a Hash, from the sum of that hash's non-nil values. It constructs Message.new with role :assistant, the joined content, Tools.parse_tool_calls(tool_use_blocks), the token fields, model_id from data['model'], and the raw response.

calls: [tools-rb-block-helpers](r2-provider-anthropic.md#u-b406c04d99ca), [RubyLLM.Providers.Anthropic.Tools.parse_tool_calls](r2-provider-anthropic.md#u-d6fce8bde72e), [Message](r1-messaging-primitives.md#u-cb349e033cb3)

<a id="u-ec5dcd587029"></a>
### `RubyLLM.Providers.Anthropic.Media.format_content`

`def format_content(content) # rubocop:disable Metrics/PerceivedComplexity` · [lib/ruby_llm/providers/anthropic/media.rb:L10-L32][f2]

Normalizes message content into Anthropic content blocks, with early returns: RubyLLM::Content::Raw passes through as its raw value; a Hash or Array is wrapped as a single text block of its JSON serialization; any non-Content value is wrapped as one text block.

For a RubyLLM::Content it starts with an optional text block when content.text is truthy, then maps each attachment by type — :image to format_image, :pdf to format_pdf, :text to format_text_file — and raises UnsupportedAttachmentError with the attachment's mime_type for any other type.

calls: [media-rb-format-helpers](r2-provider-anthropic.md#u-a8935c082e3f); raises: [RubyLLM.Providers.Anthropic.Media.format_content](r2-provider-anthropic.md#u-ec5dcd587029)

<a id="u-a8935c082e3f"></a>
### `media-rb-format-helpers`

`def format_text(text)` · [lib/ruby_llm/providers/anthropic/media.rb:L34-L39][f2]

Block builders for individual media pieces.

format_text wraps a string as {type: 'text', text:}. format_image and format_pdf share a shape: when the attachment reports url? the source is {type: 'url', url: attachment.source}; otherwise it is {type: 'base64', media_type: attachment.mime_type, data: attachment.encoded}, with block type 'image' or 'document' respectively. format_text_file emits a text block containing the file's for_llm representation.

**Uncertainties.**

- The url?/encoded/for_llm accessors are defined outside this file; their failure behavior is not visible here.

<a id="u-f6541c8c164e"></a>
### `RubyLLM.Providers.Anthropic.Tools.function_for`

`def function_for(tool)` · [lib/ruby_llm/providers/anthropic/tools.rb:L55-L68][f3]

Builds an Anthropic tool declaration from a tool object.

The input_schema comes from tool.params_schema when set, otherwise from SchemaDefinition.from_parameters(tool.parameters)&.json_schema; if neither yields a schema, default_input_schema is used. The declaration {name, description, input_schema} is returned as-is when tool.provider_params is empty, otherwise deep-merged with the provider params, letting provider_params override the base keys.

calls: [utils-utils-helpers](r1-shared-utilities.md#u-add7cf7f30e5)

<a id="u-36674469387b"></a>
### `RubyLLM.Providers.Anthropic.Tools.format_tool_call`

`def format_tool_call(msg)` · [lib/ruby_llm/providers/anthropic/tools.rb:L14-L29][f3]

Renders an assistant message that issued tool calls.

If the content is RubyLLM::Content::Raw it short-circuits to {role: 'assistant', content: raw value} with no tool blocks. Otherwise it builds a content list, prepending a text block via Media.format_text only when content is non-nil and non-empty, then appends one format_tool_use_block per tool call, and returns {role: 'assistant', content: list}.

calls: [tools-rb-block-helpers](r2-provider-anthropic.md#u-b406c04d99ca), [media-rb-format-helpers](r2-provider-anthropic.md#u-a8935c082e3f)

<a id="u-9c55482e5da8"></a>
### `RubyLLM.Providers.Anthropic.Tools.format_tool_result`

`def format_tool_result(msg)` · [lib/ruby_llm/providers/anthropic/tools.rb:L31-L36][f3]

Renders a user message carrying a tool result.

Raw content passes through as its value; any other content is wrapped as a single format_tool_result_block, producing {role: 'user', content: [block]}.

<a id="u-d6fce8bde72e"></a>
### `RubyLLM.Providers.Anthropic.Tools.parse_tool_calls`

`def parse_tool_calls(content_blocks)` · [lib/ruby_llm/providers/anthropic/tools.rb:L78-L95][f3]

Parses content blocks into tool calls.

Returns nil for nil input; wraps a single non-Array block into a one-element list. Iterates blocks, skipping nil blocks and any whose 'type' is not 'tool_use', and maps each matching block's 'id' to a ToolCall built from the block's id, name, and input. Returns nil when no tool calls were found, otherwise the hash.

calls: [ToolCall](r1-messaging-primitives.md#u-f564974b1732)

<a id="u-9e525859875e"></a>
### `RubyLLM.Providers.Anthropic.Tools.extract_tool_calls`

`def extract_tool_calls(data)` · [lib/ruby_llm/providers/anthropic/tools.rb:L70-L76][f3]

Extracts tool calls from a streaming event.

When json_delta?(data) is true (an input_json_delta) it returns a single-entry hash keyed nil holding a ToolCall with nil id and name and the partial JSON from data.dig('delta', 'partial_json'). Otherwise it parses complete tool calls from data['content_block'] via parse_tool_calls, which may return nil.

calls: [ToolCall](r1-messaging-primitives.md#u-f564974b1732)

**Uncertainties.**

- json_delta? is resolved by the graph to either Anthropic::Streaming or Bedrock ContentExtraction; which implementation applies here is not visible in this file.

<a id="u-b406c04d99ca"></a>
### `tools-rb-block-helpers`

`def find_tool_uses(blocks)` · [lib/ruby_llm/providers/anthropic/tools.rb:L10-L12][f3]

Block-level mappings.

find_tool_uses selects blocks whose 'type' == 'tool_use' from a response content list. format_tool_use_block turns a tool call into {type: 'tool_use', id:, name:, input: arguments}. format_tool_result_block turns a result message into {type: 'tool_result', tool_use_id: msg.tool_call_id, content: Media.format_content(msg.content)}.

calls: [RubyLLM.Providers.Anthropic.Media.format_content](r2-provider-anthropic.md#u-ec5dcd587029)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/providers/anthropic/chat.rb
[f2]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/providers/anthropic/media.rb
[f3]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/providers/anthropic/tools.rb
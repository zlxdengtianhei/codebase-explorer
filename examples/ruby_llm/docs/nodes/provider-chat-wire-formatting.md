# Provider chat wire formatting

**Capability.** Converts internal messages, content, and tools into Anthropic, Bedrock, and OpenAI request payloads and parses their completion responses back into Messages.

Come here to understand how a conversation is rendered to a specific provider's chat API and how responses become RubyLLM Messages. It contains per-provider message formatters, content-block builders, tool-declaration builders, and response parsers. Bedrock reuses Anthropic formatters for its Anthropic-compatible API.

**Depends on.**

- [Streaming and result objects](streaming-and-result-objects.md) · graph-only · 2 edge(s)
- [Core provider infrastructure](core-provider-infrastructure.md) · graph-only · 1 edge(s)
- [Tool definition and execution](tool-definition-and-execution.md) · graph-only · 1 edge(s)

**Depended on by.**

- [Gemini and media integrations](gemini-and-media-integrations.md) · graph-confirmed · 1 edge(s)
- [Chat conversation orchestration](chat-conversation-orchestration.md) · graph-only · 1 edge(s) · Chat orchestration renders conversation state into provider-specific chat payloads.
- [Streaming and result objects](streaming-and-result-objects.md) · graph-only · 1 edge(s)

Parent: [Chat Wire and Media Formats](chat-wire-and-media-formats.md)

## Units (18)

<a id="u-26f38d292c97"></a>
### `chat.rb-anthropic-message-formatting`

`def format_message(msg)` · [lib/ruby_llm/providers/anthropic/chat.rb:L99-L107][f1]

format_message dispatches on message kind: tool_call messages go to Tools.format_tool_call, tool_result messages to Tools.format_tool_result, everything else to format_basic_message, which emits {role, content} with content run through Media.format_content.

convert_role maps :tool and :user to 'user' and any other role to 'assistant'.

<a id="u-63ef3215c66e"></a>
### `chat.rb-anthropic-payload-assembly`

`def render_payload(messages, tools:, temperature:, model:, stream: false, schema: nil…` · [lib/ruby_llm/providers/anthropic/chat.rb:L14-L21][f1]

render_payload builds the Anthropic /v1/messages request body: it partitions messages into system vs chat, formats system content, then constructs the base payload (model id, formatted messages, stream flag, max_tokens defaulting to 4096) and adds optional fields.

add_optional_fields attaches tools (via Tools.function_for) only when tools are non-empty, system content only when non-empty, and temperature only when non-nil; the schema parameter is accepted but unused.

<a id="u-4f7d82cc9157"></a>
### `chat.rb-anthropic-response-parsing`

`def parse_completion_response(response)` · [lib/ruby_llm/providers/anthropic/chat.rb:L63-L71][f1]

parse_completion_response turns a completion response body into a Message: it selects 'text' blocks and joins their text, collects 'tool_use' blocks via Tools.find_tool_uses, then build_message constructs the Message with role :assistant, parsed tool calls, usage token counts, model id, and the raw response.

build_message reads cache_read_input_tokens directly and derives cache_creation_tokens either from cache_creation_input_tokens or, when that is nil and usage['cache_creation'] is a Hash, from the sum of its compacted values; missing usage defaults to an empty hash so token fields become nil.

<a id="u-314f5e94e518"></a>
### `chat.rb-chat-payload-rendering-2`

`def completion_url` · [lib/ruby_llm/providers/openai/chat.rb:L8-L10][f2]

Renders the chat/completions request payload.

completion_url returns 'chat/completions'. render_payload builds {model, messages, stream}, adds temperature only when non-nil, maps tools to OpenAI function definitions via tool_for when any are given, and, when a schema is supplied, sets response_format to a json_schema with name 'response', the schema itself, and strict true unless schema[:strict] == false. When streaming, it adds stream_options: {include_usage: true} so usage arrives in the stream.

<a id="u-8dd6d0a368c6"></a>
### `chat.rb-message-formatting`

`def format_message(msg)` · [lib/ruby_llm/providers/bedrock/chat.rb:L19-L27][f3]

Formats a chat message for Bedrock's Anthropic-compatible API: tool calls and tool results delegate to Anthropic::Tools formatters; otherwise it builds {role, content} with the role converted by Anthropic::Chat and content formatted by Media.format_content.

<a id="u-49a35ad4cc2b"></a>
### `chat.rb-message-formatting-2`

`def format_messages(messages)` · [lib/ruby_llm/providers/openai/chat.rb:L66-L75][f2]

Converts internal messages to OpenAI wire format: each becomes {role, content, tool_calls, tool_call_id} with nil-valued keys compacted away.

Content goes through Media.format_content; tool calls through format_tool_calls. format_role maps :system to 'system' or 'developer' depending on @config.openai_use_system_role (an instance-level config, so this method relies on the including class exposing @config), and passes any other role through as a string.

<a id="u-9c72eda3cdf1"></a>
### `chat.rb-payload-construction`

`def completion_url` · [lib/ruby_llm/providers/bedrock/chat.rb:L38-L40][f3]

Builds the invoke payload.

completion_url is "model/#{@model_id}/invoke" (an instance variable set by render_payload, so these rely on instance state despite module_function). render_payload stores the model ID, splits messages into system vs chat via Anthropic::Chat, builds the base payload, and adds optional fields (system content, tools, temperature). build_base_payload sets anthropic_version 'bedrock-2023-05-31', formatted messages, and max_tokens from the model or 4096. The stream and schema arguments are accepted but unused.

<a id="u-eff06d21dba5"></a>
### `content.rb-anthropic-content-block-builder`

`def new(text = nil, cache: false, cache_control: nil, parts: nil, **extras)` · [lib/ruby_llm/providers/anthropic/content.rb:L9-L19][f4]

Builds Anthropic-native content blocks wrapped in RubyLLM::Content::Raw from text, parts, or extras with optional prompt-caching control.

`new` resolves a payload and returns Raw.new(payload). resolve_payload returns Array(parts) verbatim when parts given; otherwise raises ArgumentError if text is nil; builds a {type:'text',text:} block merged with extras, and attaches cache_control when determine_cache_control yields one. determine_cache_control returns the explicit cache_control if given, else {type:'ephemeral'} when the cache flag is true, else nil (no caching).

<a id="u-debaa4eb8940"></a>
### `media.rb-anthropic-block-formatters`

`def format_text(text)` · [lib/ruby_llm/providers/anthropic/media.rb:L34-L39][f5]

Produce individual content blocks.

format_text wraps any string as {type:'text'}. format_image and format_pdf mirror each other: URL-backed attachments use a url source; otherwise a base64 source with mime_type and encoded data (images use type 'image', PDFs 'document'). format_text_file emits a text block using the attachment's for_llm representation.

<a id="u-395e693d71b4"></a>
### `message.rb-chat-message`

`class Message` · [lib/ruby_llm/message.rb:L6-L12][f6]

A single conversation message with role validation and content normalization.

initialize requires :role and :content options (KeyError otherwise), symbolizes the role, normalizes content (String becomes Content.new(string); Hash becomes Content.new(content[:text], content); anything else, including Content::Raw, is kept as-is), copies optional model_id, tool_calls, tool_call_id, and token counters, then validates the role against ROLES (system, user, assistant, tool), raising InvalidRoleError otherwise. content unwraps to the plain string when the stored Content has text and no attachments, else returns the stored object. tool_call? and tool_result? check non-nil, non-empty tool_calls/tool_call_id; tool_results returns content only when tool_result?. to_h builds a compacted hash of role, content, model_id, tool_calls, tool_call_id, and the four token fields (raw excluded). instance_variables overrides Object's to drop :@raw. The content attr_writer allows external mutation of the stored content.

calls: [content.rb-content-value-object](activerecord-persistence-bridge.md#u-c1e52bfd7115)

**Uncertainties.**

- Content.new with a Hash whose :text is nil plus attachments may raise ArgumentError from Content, propagating through Message.initialize.

<a id="u-0983038ae77d"></a>
### `tools.rb-anthropic-tool-call-parsing`

`def extract_tool_calls(data)` · [lib/ruby_llm/providers/anthropic/tools.rb:L70-L76][f7]

extract_tool_calls handles streaming deltas: when the payload is a content_block_delta with an input_json_delta (per json_delta?), it returns a single-key hash mapping nil to a ToolCall whose arguments are the partial JSON; otherwise it delegates to parse_tool_calls on data['content_block'].

parse_tool_calls normalizes a nil input to nil, wraps non-arrays, keeps only blocks typed 'tool_use', and builds a hash of ToolCall objects keyed by block id; returns nil when no tool_use blocks were found.

<a id="u-c188f69161ea"></a>
### `tools.rb-anthropic-tool-message-formatting`

`def format_tool_call(msg)` · [lib/ruby_llm/providers/anthropic/tools.rb:L14-L29][f7]

Formats tool-related messages for the API.

format_tool_call returns the Raw content value directly when present; otherwise it builds an assistant message whose content is an optional text block (skipped when content is nil or empty) followed by one tool_use block per tool call carrying id, name, and arguments. format_tool_result emits a user-role message: Raw content passes through as-is, otherwise a single tool_result block referencing msg.tool_call_id with content formatted by Media.format_content.

<a id="u-4fd1f565e1b2"></a>
### `RubyLLM.Providers.Anthropic.Chat.build_system_content`

`def build_system_content(system_messages)` · [lib/ruby_llm/providers/anthropic/chat.rb:L27-L46][f1]

Converts system messages into Anthropic system content, returning [] when there are none.

If more than one system message exists it logs a warning that they will be combined. Each message contributes its Raw content value directly, or Media.format_content output otherwise, flattened into one array.

<a id="u-ec5dcd587029"></a>
### `RubyLLM.Providers.Anthropic.Media.format_content`

`def format_content(content) # rubocop:disable Metrics/PerceivedComplexity` · [lib/ruby_llm/providers/anthropic/media.rb:L10-L32][f5]

Converts message content into an array of Anthropic content blocks.

Raw content passes through its value; Hash/Array content is JSON-serialized into a single text block; non-Content objects become a text block of their string form. For Content objects it emits a text block when text is present, then iterates attachments: images, PDFs, and text files get their formatters; any other attachment type raises UnsupportedAttachmentError with the attachment's mime type.

<a id="u-fb6ee3e04d04"></a>
### `RubyLLM.Providers.Anthropic.Tools.default_input_schema`

`def default_input_schema` · [lib/ruby_llm/providers/anthropic/tools.rb:L97-L105][f7]

Returns a strict default JSON Schema for Anthropic tool declarations when a tool provides neither params_schema nor a schema derived from its parameters: an object type with empty properties, empty required list, additionalProperties disabled, and strict enabled.

<a id="u-f6541c8c164e"></a>
### `RubyLLM.Providers.Anthropic.Tools.function_for`

`def function_for(tool)` · [lib/ruby_llm/providers/anthropic/tools.rb:L55-L68][f7]

Builds an Anthropic tool declaration from a tool: name, description, and an input_schema taken from params_schema or derived from the tool's parameters via SchemaDefinition, falling back to a strict empty-object schema.

If provider_params is non-empty, it deep-merges them over the declaration, letting providers override any field.

<a id="u-c56ce45ee286"></a>
### `RubyLLM.Providers.Bedrock.Chat.sync_response`

`def sync_response(connection, payload, additional_headers = {})` · [lib/ruby_llm/providers/bedrock/chat.rb:L10-L17][f3]

Sends a synchronous Bedrock invoke request and returns the parsed Anthropic completion.

It signs the full URL (connection url_prefix plus completion_url) with the payload, POSTs to completion_url merging the signature headers (plus a streaming flag when a block is given), then layers any additional_headers over the request headers, and delegates response parsing to Anthropic::Chat. Signing or HTTP failures propagate unchanged.

<a id="u-04c9213bd74e"></a>
### `RubyLLM.Providers.OpenAI.Chat.parse_completion_response`

`def parse_completion_response(response)` · [lib/ruby_llm/providers/openai/chat.rb:L41-L64][f2]

Parses a chat completion response into a RubyLLM Message.

Returns nil for an empty body; raises Error (with the API's error message) when the body carries error.message. Extracts choices[0].message and returns nil if absent. Builds the Message with role :assistant, the message content, tool calls parsed via parse_tool_calls, usage token counts (prompt/completion, cached tokens from prompt_tokens_details), cache_creation_tokens hardcoded to 0, the response's model id, and the raw response object.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/providers/anthropic/chat.rb
[f2]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/providers/openai/chat.rb
[f3]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/providers/bedrock/chat.rb
[f4]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/providers/anthropic/content.rb
[f5]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/providers/anthropic/media.rb
[f6]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/message.rb
[f7]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/providers/anthropic/tools.rb

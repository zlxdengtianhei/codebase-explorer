# Chat Message And Tool Formatting

**Capability.** Formats chat messages, tool calls, schemas, and provider payloads and parses completions into messages.

Observed units cover message and tool value objects plus provider-specific chat/tool formatting. Use this module for Anthropic, Bedrock, Gemini, OpenAI, and shared tool utilities.

**Depends on.**

- [Model Registry And Media](model-registry-and-media.md) · graph-only · 1 edge(s)
- [Provider Connection And Errors](provider-connection-and-errors.md) · graph-only · 1 edge(s)
- [Streaming Chunk Accumulation](streaming-chunk-accumulation.md) · graph-only · 1 edge(s)

**Depended on by.**

- [Streaming Chunk Accumulation](streaming-chunk-accumulation.md) · graph-only · 3 edge(s)
- [ActiveRecord Chat Persistence](activerecord-chat-persistence.md) · graph-only · 2 edge(s)
- [Model Metadata Value Objects](model-metadata-value-objects.md) · graph-only · 2 edge(s)
- [Attachment And Content Handling](attachment-and-content-handling.md) · graph-only · 1 edge(s)
- [Core Chat Configuration](core-chat-configuration.md) · graph-only · 1 edge(s)

Parent: [Chat Payload And Auxiliary APIs](chat-payload-and-auxiliary-apis.md)

## Units (29)

<a id="u-87876eae3c26"></a>
### `chat.rb-bedrock-chat-request-and-response-formatting`

`def sync_response(connection, payload, additional_headers = {})` · [lib/ruby_llm/providers/bedrock/chat.rb:L10-L17][f1]

These module functions format Bedrock chat payloads and parse responses through Anthropic helpers.

sync_response signs the full completion URL with the payload, posts to the relative completion URL, merges signed headers into the request, and then overlays additional headers only when non-empty; because it does additional_headers.merge(req.headers), request headers win on key conflicts. It passes streaming: block_given? to header building and parses the response with Anthropic::Chat.parse_completion_response. format_message routes tool-call messages to Anthropic::Tools.format_tool_call, tool-result messages to format_tool_result, and everything else to format_basic_message. format_basic_message returns role converted by Anthropic::Chat.convert_role and content formatted by Media.format_content. completion_url is model/<@model_id>/invoke. render_payload stores the model ID, separates system and chat messages, builds system content, then adds optional system/tools/temperature fields to the base payload; stream and schema are accepted but unused. build_base_payload sets anthropic_version 'bedrock-2023-05-31', maps messages through format_message, and uses model.max_tokens or 4096.

<a id="u-26302c2c9658"></a>
### `chat.rb-chat-message-formatting`

`def format_messages(messages)` · [lib/ruby_llm/providers/openai/chat.rb:L66-L75][f2]

Formats outgoing chat messages and roles.

Each message becomes a hash with formatted role, media-formatted content, formatted tool calls, and tool_call_id, with nil fields removed. Role formatting maps system to system when the config flag openai_use_system_role is true, otherwise to developer; every other role is converted to a string.

<a id="u-4eb5c2d2bd2c"></a>
### `chat.rb-chat-request-rendering`

`def completion_url` · [lib/ruby_llm/providers/gemini/chat.rb:L13-L15][f3]

Builds the Gemini generateContent URL and request payload for chat.

The URL uses the stored model. Rendering stores the model id, formats messages into contents, starts an empty generationConfig, adds temperature unless nil, merges structured-output config when a schema is present, and adds tools when any exist; the stream argument is unused.

<a id="u-eba733af3a2f"></a>
### `chat.rb-completion-response-parsing`

`def parse_completion_response(response)` · [lib/ruby_llm/providers/gemini/chat.rb:L63-L76][f3]

Parses a Gemini completion response into a Message with content, tool calls, and token counts.

It builds an assistant message with extracted tool calls, prompt token count, output tokens, model id from modelVersion or the URL path segment, and the raw response. Content is empty when there is no candidate, when any part has functionCall even if text parts are also present, or when there are no parts; otherwise response content is built from parts. Output tokens sum candidatesTokenCount and thoughtsTokenCount, each defaulting to zero.

<a id="u-fd66183f24f4"></a>
### `chat.rb-gemini-schema-converter`

`class GeminiSchema` · [lib/ruby_llm/providers/gemini/chat.rb:L250-L251][f3]

Converts JSON Schema into Gemini schema hashes, resolving definitions and references.

It deep-dups the raw schema, extracts $defs/definitions while symbolizing keys, then converts with a visited-reference set. Non-hash schemas become string schemas; strict and additionalProperties are stripped; $ref is resolved and merged with overrides when found; anyOf is normalized; object, array, number, integer, boolean, and string types map to Gemini shapes with allowed attributes and descriptions. Reference lookup splits the pointer, skips # and definitions markers, traverses the definitions hash, and returns a deep copy or nil. anyOf normalization uses the first non-null option, marks nullable when any null option exists, and falls back to a nullable string when no non-null option exists.

<a id="u-ffcb9f524e73"></a>
### `chat.rb-message-formatter`

`class MessageFormatter` · [lib/ruby_llm/providers/gemini/chat.rb:L175-L176][f3]

Formats a message list into Gemini contents, grouping consecutive tool results into function responses.

It walks messages by index, remembers tool-call names, and for each non-tool message emits a standard role/parts message. Consecutive tool messages are collected together, their tool-call ids are removed from the remembered map to recover names, and their formatted results become one function-role response. A missing remembered name is passed through as nil.

<a id="u-8dd6d0a368c6"></a>
### `chat.rb-message-formatting`

`def format_message(msg)` · [lib/ruby_llm/providers/anthropic/chat.rb:L99-L107][f4]

Formats one chat message for Anthropic.

Tool-call messages go to tool-call formatting, tool-result messages to tool-result formatting, and all others become a basic hash with converted role and media-formatted content. Role conversion maps tool and user to user, and every other role to assistant.

<a id="u-4f4c6437bbc2"></a>
### `chat.rb-message-formatting-entrypoints`

`def format_messages(messages)` · [lib/ruby_llm/providers/gemini/chat.rb:L34-L42][f3]

Delegates message formatting to MessageFormatter and maps roles and parts to Gemini shapes.

Roles map assistant to model, system to user, tool to function, and anything else to its string form. Parts use tool-call formatting for tool-call messages, tool-result formatting for tool-result messages, and media formatting otherwise.

<a id="u-13bfd0033c08"></a>
### `chat.rb-payload-rendering`

`def completion_url` · [lib/ruby_llm/providers/anthropic/chat.rb:L10-L12][f4]

Builds the Anthropic chat request payload.

It separates system messages, warns when more than one exists, and flattens each system message: raw content contributes its value, other content goes through media formatting. The base payload uses the model id, formatted chat messages, stream flag, and model max tokens or 4096; optional tools, non-empty system content, and non-nil temperature are added afterward. The completion URL is /v1/messages.

<a id="u-eda22c65ad08"></a>
### `chat.rb-response-parsing`

`def parse_completion_response(response)` · [lib/ruby_llm/providers/anthropic/chat.rb:L63-L71][f4]

Parses an Anthropic completion into a message.

It reads content blocks, joins text blocks, finds tool-use blocks, and builds an assistant message with parsed tool calls, usage token fields, model id, and the raw response. Cache-creation tokens come from the direct usage field, or if absent from a cache_creation hash, as the sum of its compact values.

<a id="u-6d2154ed18bb"></a>
### `chat.rb-structured-output-schema-selection`

`def convert_schema_to_gemini(schema)` · [lib/ruby_llm/providers/gemini/chat.rb:L78-L82][f3]

Chooses Gemini structured-output schema format based on model version and normalizes the schema.

Structured-output config always sets responseMimeType to application/json; it uses responseJsonSchema with a deep-duplicated, strict-stripped, string-keyed schema when the model version is at least 2.5, otherwise responseSchema through the Gemini schema converter. Version detection collects strings from model id, family, and metadata version/description, extracts the first numeric version, and returns nil on ArgumentError. Metadata lookup only reads a Hash metadata value and checks symbol then string keys.

<a id="u-395e693d71b4"></a>
### `message.rb-chat-message`

`class Message` · [lib/ruby_llm/message.rb:L5-L6][f5]

Represents one chat message with role, content, tool-call metadata, token counts, and raw provider data.

Initialization requires role and content options, converts role to a symbol, normalizes content, stores optional fields, and raises InvalidRoleError unless the role is one of system, user, assistant, or tool. Content normalization maps a String to content text, a Hash to content text plus the whole hash as attachments, and leaves other values unchanged. Reading content returns the text only when the stored content is a content object with text and no attachments; otherwise it returns the stored content. Tool-call detection is true for a non-nil, non-empty tool-call list; tool-result detection is true for a non-nil, non-empty tool-call id, and tool results return content only in that case. Serialization includes role, content, model id, tool calls, tool-call id, and token counts, removes nil values, and excludes raw data. Instance-variable inspection hides the raw field.

calls: [content.rb-content-container](attachment-and-content-handling.md#u-515477396b7a); raises: [InvalidRoleError](../../catalog.json.gz)

**Uncertainties.**

- InvalidRoleError definition and content attachment behavior are outside this file.

<a id="u-b66737e6d9b3"></a>
### `tool.rb-halt`

`class Halt` · [lib/ruby_llm/tool.rb:L21-L24][f6]

Wraps a tool result that should stop conversation continuation.

It stores content; to_s returns content.to_s.

<a id="u-4f560fa06461"></a>
### `tool.rb-parameter`

`class Parameter` · [lib/ruby_llm/tool.rb:L7-L10][f6]

Describes a tool parameter with name, type, description, and required flag.

initialize defaults type to string, description to nil, and required to true.

<a id="u-3d3e12a4d16b"></a>
### `tool.rb-schemadefinition`

`class SchemaDefinition` · [lib/ruby_llm/tool.rb:L120-L121][f6]

Wraps tool parameter schema handling for JSON Schema hashes, RubyLLM::Schema objects/classes, and DSL blocks.

from_parameters returns nil for nil/empty parameters; otherwise it builds properties with mapped types, compact descriptions, default string items for arrays, required keys, and an object schema with additionalProperties false and strict true. map_type maps integer/int, number/float/double, boolean, array, object, and defaults to string. default_items_schema returns a string type. initialize stores schema/block. present? is true when either exists. json_schema memoizes deep-stringified resolve_schema. resolve_schema uses a direct schema, a block, or nil. resolve_direct_schema extracts to_json_schema results, deep-dups hashes, instantiates classes with to_json_schema, or returns nil. build_from_block creates a RubyLLM::Schema from the block and extracts its new instance schema. extract_schema returns nil unless given a Hash, picks :schema, 'schema', or the whole hash, and deep-dups it.

<a id="u-ff9c7a4d2712"></a>
### `tool.rb-tool-class`

`class Tool # Stops conversation continuation after tool execution` · [lib/ruby_llm/tool.rb:L19-L21][f6]

Base class for AI-callable tools, with class-level parameter DSL and instance execution hooks.

Subclasses implement execute; call symbolizes arguments and logs. The class also contains Halt and SchemaDefinition helpers.

<a id="u-ff45b156f9db"></a>
### `tool.rb-tool-class-dsl`

`class << self` · [lib/ruby_llm/tool.rb:L33-L36][f6]

Defines class-level tool metadata and parameter/schema declarations.

description is a getter or setter when text is given. param stores a Parameter by name. parameters is a memoized hash. params stores a SchemaDefinition from schema/block and returns self. with_params stores provider params and returns self. provider_params is a memoized hash.

<a id="u-c78bfd001a27"></a>
### `tool.rb-tool-instance-behavior`

`def name` · [lib/ruby_llm/tool.rb:L65-L74][f6]

Exposes tool metadata, builds parameter schema, invokes execution, and creates halt results.

name normalizes the class name through UTF-8 NFKD, ASCII replacement, non-alphanumeric replacement, camel-boundary underscores, downcasing, and removal of a _tool suffix. description, parameters, and provider_params delegate to the class. params_schema memoizes the class schema definition when present, otherwise builds from parameters when any exist. call logs arguments, executes with symbolized keys, logs the result, and returns it. execute raises NotImplementedError. halt returns Halt.new(message).

<a id="u-edc9eb8350d2"></a>
### `tool_call.rb-tool-call-value`

`class ToolCall` · [lib/ruby_llm/tool_call.rb:L5-L8][f7]

Value object for a model-requested tool call.

Initialization stores id, name, and arguments, with arguments defaulting to an empty hash. Serialization returns those three fields as a hash.

<a id="u-34832232b9be"></a>
### `tools.rb-tool-call-extraction`

`def find_tool_uses(blocks)` · [lib/ruby_llm/providers/anthropic/tools.rb:L10-L12][f8]

Extracts and parses Anthropic tool calls.

It selects tool-use blocks, and for streaming JSON deltas creates a single tool call keyed by nil with partial JSON arguments; otherwise it parses the content block. Parsing returns nil for nil input, wraps a single block in an array, skips non-tool-use blocks, keys calls by id, and returns nil when no calls remain.

<a id="u-b086eef606df"></a>
### `tools.rb-tool-call-formatting-and-parsing`

`def format_tool_calls(tool_calls)` · [lib/ruby_llm/providers/openai/tools.rb:L52-L65][f9]

Converts tool calls between internal and OpenAI wire shapes.

Formatting returns nil unless there are calls, then maps each call to id, type function, and function name plus JSON-generated arguments. Argument parsing returns an empty hash for nil or empty arguments, otherwise JSON.parse. Call parsing returns nil unless there are calls, then builds a hash keyed by call id with ToolCall objects; when parse_arguments is true it parses arguments, otherwise it keeps the raw argument string.

<a id="u-483e66bb8b9e"></a>
### `tools.rb-tool-message-formatting`

`def format_tool_call(msg)` · [lib/ruby_llm/providers/anthropic/tools.rb:L14-L29][f8]

Formats Anthropic tool-call and tool-result messages.

A raw tool-call message returns an assistant hash whose content is the raw value; otherwise content is an array with optional text and one tool-use block per call. A tool result returns a user hash whose content is the raw value or a single tool-result block. Tool-use blocks carry id, name, and arguments; tool-result blocks carry tool_use_id and media-formatted content.

<a id="u-fde665ad4231"></a>
### `tools.rb-tool-request-formatting-and-extraction`

`def format_tools(tools)` · [lib/ruby_llm/providers/gemini/tools.rb:L8-L14][f10]

Formats tool declarations/calls/results and extracts tool calls from Gemini responses.

Empty tools produce an empty array; otherwise declarations are grouped under functionDeclarations. Tool-call messages include non-empty content through media formatting and each tool call as functionCall with name and arguments. Tool results use the supplied function name or the message tool-call id and wrap content in a functionResponse. Extraction returns nil without data, candidate, or parts array; each functionCall becomes a ToolCall with a random UUID, the name passed through as-is, and arguments defaulting to an empty hash; no calls yields nil.

<a id="u-2805b4f69dd2"></a>
### `tools.rb-tool-schema`

`def function_for(tool)` · [lib/ruby_llm/providers/anthropic/tools.rb:L55-L68][f8]

Builds an Anthropic tool declaration.

It uses the tool's params schema, or a schema derived from parameters, and falls back to a strict object schema with no properties. If provider params are present, they are deep-merged into the declaration; otherwise the declaration is returned unchanged.

<a id="u-7d7744779b83"></a>
### `tools.rb-tool-schema-construction`

`def parameters_schema_for(tool)` · [lib/ruby_llm/providers/openai/tools.rb:L18-L21][f9]

Builds OpenAI function definitions from tool metadata.

The parameter schema uses the tool's params_schema when present, otherwise it asks SchemaDefinition.from_parameters for a JSON schema and falls back to the empty object schema when that returns nil. The function definition contains type function, name, description, and parameters; if provider_params is non-empty, it deep-merges them into the definition. The single-parameter schema helper returns type and description with nil description removed.

<a id="u-6a75b341b6a8"></a>
### `tools.rb-tool-schema-conversion`

`def function_declaration_for(tool)` · [lib/ruby_llm/providers/gemini/tools.rb:L77-L91][f10]

Converts Ruby tool schemas into Gemini function-declaration parameter schemas.

Declarations use the tool schema or a schema derived from parameters, add converted parameters when present, and deep-merge provider params when non-empty. Top-level schemas must be objects or conversion raises ArgumentError. Property conversion normalizes anyOf, maps types, copies common attributes, recursively converts array items and object properties, and copies min/max item constraints. anyOf normalization returns nil without a non-empty array; exactly one non-null plus null yields that option with nullable true; multiple non-null options yield the first without nullable even when null is present; no non-null yields a nullable string. Type mapping defaults unknown types to STRING.

<a id="u-907fb557c5e2"></a>
### `utils.rb-data-utilities`

`def hash_get(hash, key)` · [lib/ruby_llm/utils.rb:L8-L10][f11]

Collection of module functions for safe lookup, array coercion, time/date parsing, and recursive hash/array transforms.

Hash lookup tries the symbolized key first, then the original key, using || so falsey values fall through. Safe array returns arrays unchanged, wraps hashes in a one-element array, and otherwise calls Array. Time and date conversion return nil for nil, return an existing Time or Date unchanged, and otherwise parse the string form. Deep merge recurses only when both values are hashes; otherwise the override wins. Deep duplication recursively duplicates hash keys and values and array items, and for other values attempts dup, returning the original on TypeError. Deep stringification recursively converts hash keys to strings, maps arrays, and converts symbols to strings. Deep symbolization recursively maps arrays and symbolizes nested hash keys when the key responds to to_sym, keeping other keys unchanged.

**Uncertainties.**

- Time.parse and Date.parse errors are not rescued.

<a id="u-04c9213bd74e"></a>
### `RubyLLM.Providers.OpenAI.Chat.parse_completion_response`

`def parse_completion_response(response)` · [lib/ruby_llm/providers/openai/chat.rb:L41-L64][f2]

Parses a chat-completion response body into a Message, returning nil for an empty body or missing first choice message.

If the body contains an error message, it raises Error with the response and that message. Otherwise it reads usage, cached prompt tokens, content, tool calls, prompt/completion token counts, model id, and raw response; cache_creation_tokens is set to 0.

<a id="u-dd4454ea38ce"></a>
### `RubyLLM.Providers.OpenAI.Chat.render_payload`

`def render_payload(messages, tools:, temperature:, model:, stream: false, schema: nil…` · [lib/ruby_llm/providers/openai/chat.rb:L14-L39][f2]

Builds the OpenAI chat-completions request payload.

It always includes model id, formatted messages, and stream. It adds temperature unless nil, adds tools mapped through tool_for when any exist, and adds a json_schema response_format when a schema is given; strict defaults to true unless schema[:strict] is exactly false. When streaming, it adds stream_options with include_usage true.

Look up code: the commands are under "Read further" in [INDEX.md](../INDEX.md); `cbe query` and `cbe source` take a unit title or anchor from this page.

[f1]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/providers/bedrock/chat.rb
[f2]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/providers/openai/chat.rb
[f3]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/providers/gemini/chat.rb
[f4]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/providers/anthropic/chat.rb
[f5]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/message.rb
[f6]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/tool.rb
[f7]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/tool_call.rb
[f8]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/providers/anthropic/tools.rb
[f9]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/providers/openai/tools.rb
[f10]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/providers/gemini/tools.rb
[f11]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/utils.rb

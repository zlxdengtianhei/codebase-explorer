# Gemini Chat & Schema

**Capability.** Builds generateContent requests (messages, tools, structured output), parses responses into Messages, and converts JSON-Schema-like hashes into Gemini schema format via GeminiSchema and its builder helpers.

Read request building for the payload shape and parse_completion_response for hydration. GeminiSchema recurses through schema builders and relies on shared utilities for normalization.

**Depends on.**

- [Gemini Media](r1-gemini-media.md) · graph-confirmed · 1 edge(s)
- [Gemini Tools](r1-gemini-tools.md) · graph-confirmed · 1 edge(s) · Gemini request building formats tools via Gemini.Tools before sending requests.
- [Message & ToolCall Value Objects](r1-messaging-primitives.md) · graph-confirmed · 1 edge(s)
- [Shared Utilities](r1-shared-utilities.md) · graph-confirmed · 8 edge(s)
- [Stream Accumulation](r1-streaming-accumulation.md) · graph-only · 1 edge(s)

Parent: [Gemini Adapter](r1-gemini-adapter.md)

## Units (8)

<a id="u-7eb1a8c76a9e"></a>
### `chat-request-building`

`def completion_url` · [lib/ruby_llm/providers/gemini/chat.rb:L13-L15][f1]

Groups request construction for chat completions.

completion_url returns 'models/<model>:generateContent' using the instance variable @model. render_payload stores model.id in @model, builds contents via format_messages and an always-present empty generationConfig hash, adds temperature only when non-nil, merges structured_output_config(schema, model) only when a schema is given, and adds tools formatted via format_tools only when the tools collection is non-empty. The stream and model parameters besides model.id are unused (marked by lint directive).

<a id="u-e86d73bc7100"></a>
### `chat-message-formatting-helpers`

`def format_messages(messages)` · [lib/ruby_llm/providers/gemini/chat.rb:L34-L42][f1]

Groups the module-level callbacks handed to MessageFormatter.

format_messages wraps the message list plus these three callbacks in a MessageFormatter and returns its format result. format_role maps :assistant to 'model', :system to 'user', :tool to 'function', and any other role to its string form. format_parts dispatches per message: tool_call? messages go to format_tool_call, tool_result? messages to format_tool_result, and everything else to Media.format_content on the message content.

<a id="u-313cd25acd8e"></a>
### `chat-messageformatter`

`class MessageFormatter` · [lib/ruby_llm/providers/gemini/chat.rb:L175-L176][f1]

MessageFormatter converts a RubyLLM conversation into Gemini 'contents' entries.

format walks messages by index: when the current message has role :tool it collects the consecutive run of tool messages via collect_tool_parts — for each, it looks up the originating tool name from @tool_call_names (populated by remember_tool_calls when an assistant tool_call? message is seen, mapping tool_call_id to name), formats each via the injected format_tool_result callback, and emits a single {role: 'function', parts: ...} entry; the index advances past the run. Any other message is emitted as {role: format_role(role), parts: format_parts(message)}, with tool calls remembered first. The loop stops when @messages[@index] is nil, so a nil entry mid-list also terminates it. A tool result whose tool_call_id was never remembered formats with a nil tool name, delegating that fallback to the Tools module callback.

<a id="u-a59ccca2f8d3"></a>
### `chat-structured-output`

`def convert_schema_to_gemini(schema)` · [lib/ruby_llm/providers/gemini/chat.rb:L78-L82][f1]

Groups structured-output support.

convert_schema_to_gemini returns nil for a nil schema, otherwise GeminiSchema.new(schema).to_h. structured_output_config always sets responseMimeType 'application/json', then chooses the schema carrier by version: response_json_schema_supported? extracts a Gemini version from the model via gemini_version and requires it to be at least Gem::Version '2.5'; when supported it stringifies a deep-duplicated schema minus :strict/'strict' (build_json_schema), otherwise it uses the Gemini-converted schema. gemini_version gathers candidate strings from model.id, model.family (when the object responds), and metadata values for :version, 'version', and :description, returning the first string from which extract_version pulls a version number; extract_version matches /(\d+\.\d+|\d+)/ and builds a Gem::Version, returning nil on no match or on ArgumentError. model_metadata_value reads model.metadata only when it is a Hash, checking both symbol and string keys; safe_string is a nil-safe to_s.

<a id="u-19f9615b0618"></a>
### `chat-content-parsing`

`def parse_content(data)` · [lib/ruby_llm/providers/gemini/chat.rb:L84-L94][f1]

Groups content extraction from a Gemini response body.

parse_content digs 'candidates'[0]; it returns '' when no candidate exists, '' when the candidate is a pure function call (detected by function_call?, i.e. any part containing 'functionCall'), and '' when the content parts array is missing or empty; otherwise it builds text/attachment content from the parts via build_response_content. calculate_output_tokens sums usageMetadata.candidatesTokenCount and thoughtsTokenCount, treating each missing value as 0.

<a id="u-2bb1d23335e2"></a>
### `RubyLLM.Providers.Gemini.Chat.parse_completion_response`

`def parse_completion_response(response)` · [lib/ruby_llm/providers/gemini/chat.rb:L63-L76][f1]

Converts a Gemini generateContent HTTP response into a Message.

Extracts tool calls from the response body, parses text content, and sets input_tokens from usageMetadata.promptTokenCount and output_tokens as candidatesTokenCount plus thoughtsTokenCount. model_id prefers the body's modelVersion and falls back to the fourth path segment of the request URL before the colon. The raw response is retained on the message.

uses: [chat-content-parsing](r1-gemini-chat.md#u-19f9615b0618), [RubyLLM.Providers.Gemini.Tools.extract_tool_calls](r1-gemini-tools.md#u-d8fa6008552e); calls: [Message](r1-messaging-primitives.md#u-cb349e033cb3)

<a id="u-9798e8adce31"></a>
### `chat-gemini-schema`

`class GeminiSchema` · [lib/ruby_llm/providers/gemini/chat.rb:L250-L251][f1]

GeminiSchema converts a JSON-Schema-like hash into Gemini's schema format.

initialize deep-duplicates the input and starts an empty definitions store. to_h returns nil for a nil schema; otherwise it symbolizes keys while extracting $defs/definitions subtrees (symbolize_and_extract_definitions recurses through Hashes — converting keys to symbols with a rescue that keeps the original key — and Arrays), then converts the result with an empty visited-ref set. convert returns a default {type: 'STRING'} for non-Hash input, strips :strict and :additionalProperties, resolves :$ref when present, normalizes :anyOf, then dispatches on :type: 'object' to build_object (converts each property, emits OBJECT with required string list when non-empty, passes through propertyOrdering and nullable), 'array' to build_array (converts :items or defaults to a string schema, copies minItems/maxItems/nullable), 'number'/'integer'/'boolean' to build_scalar with per-type allowed keys, and anything else to a STRING scalar; description is applied last. resolve_reference skips already-visited refs (cycle guard), looks the definition up, merges the referenced schema under any sibling keys of $ref (deep_merge), converts the merge, and removes the ref from visited in ensure. lookup_definition splits the ref on '/', drops a leading '#' and a $defs/definitions segment, walks the definitions hash symbolically, returns nil on a non-Hash hop or missing key, and deep-duplicates the hit. merge_definitions symbolizes raw definitions and either stores them or deep-merges into existing ones.

<a id="u-bbc4975d2047"></a>
### `chat-gemini-schema-builders`

`def normalize_any_of(schema)` · [lib/ruby_llm/providers/gemini/chat.rb:L382-L397][f1]

Groups the GeminiSchema helper builders.

normalize_any_of returns the schema unchanged without :anyOf; otherwise it symbolizes each option, partitions out type-'null' options (schema_type reads :type or 'type', downcased), takes the first non-null option (defaulting to {type: 'string'}), sets nullable: true when any null option existed, and merges that base into the schema minus :anyOf — so only the first non-null branch survives. schema_type stringifies an option's type. build_object/build_array/build_scalar construct Gemini-typed hashes copying only whitelisted attributes (copy_attribute copies when the source key exists); apply_description copies :description when present; default_string_schema returns {type: 'STRING'}.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/providers/gemini/chat.rb
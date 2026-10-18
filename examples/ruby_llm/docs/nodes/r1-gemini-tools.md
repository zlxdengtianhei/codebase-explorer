# Gemini Tools

**Capability.** Formats tools under a single functionDeclarations entry, converts JSON tool schemas (including anyOf collapsing) to Gemini's uppercase format, and extracts/formats tool calls and results.

Use Tools for both directions of Gemini function calling: declarations sent with requests and functionCall/functionResponse parts parsed from or rendered into conversations.

**Depends on.**

- [Gemini Media](r1-gemini-media.md) · model-inferred · 0 edge(s)
- [Tool Definition DSL](r1-tool-dsl.md) · graph-confirmed · 1 edge(s)
- [Shared Utilities](r1-shared-utilities.md) · graph-only · 4 edge(s)
- [Message & ToolCall Value Objects](r1-messaging-primitives.md) · graph-only · 1 edge(s)

**Depended on by.**

- [Gemini Chat & Schema](r1-gemini-chat.md) · graph-confirmed · 1 edge(s) · Gemini request building formats tools via Gemini.Tools before sending requests.

Parent: [Gemini Adapter](r1-gemini-adapter.md)

## Units (9)

<a id="u-f0e603b782c1"></a>
### `RubyLLM.Providers.Gemini.Tools.format_tools`

`def format_tools(tools)` · [lib/ruby_llm/providers/gemini/tools.rb:L8-L14][f1]

Wraps all tools under a single Gemini functionDeclarations entry.

It returns [] for an empty tool set; otherwise it maps each tool through function_declaration_for into one hash {functionDeclarations: [...]}, preserving the tools collection's value order.

calls: [RubyLLM.Providers.Gemini.Tools.function_declaration_for](r1-gemini-tools.md#u-487a79a98763)

<a id="u-487a79a98763"></a>
### `RubyLLM.Providers.Gemini.Tools.function_declaration_for`

`def function_declaration_for(tool)` · [lib/ruby_llm/providers/gemini/tools.rb:L77-L91][f1]

Builds one Gemini function declaration for a tool.

The parameters schema comes from tool.params_schema or, when absent, from SchemaDefinition.from_parameters(tool.parameters)'s json_schema (which may be nil). The declaration carries name and description, gains :parameters converted to Gemini form only when a schema exists, and is deep-merged with tool.provider_params when those are non-empty, letting provider params override or extend the declaration.

calls: [tool.rb-tool-and-parameter](r1-tool-dsl.md#u-00e41a176da0), [RubyLLM.Providers.Gemini.Tools.convert_tool_schema_to_gemini](r1-gemini-tools.md#u-918ee7e9164c)

<a id="u-918ee7e9164c"></a>
### `RubyLLM.Providers.Gemini.Tools.convert_tool_schema_to_gemini`

`def convert_tool_schema_to_gemini(schema)` · [lib/ruby_llm/providers/gemini/tools.rb:L93-L105][f1]

Converts a JSON tool schema to Gemini's uppercase format.

It returns nil for a nil schema, stringifies all keys via deep_stringify_keys, and raises ArgumentError with 'Gemini tool parameters must be objects' when the top-level type is not 'object'. Otherwise it emits OBJECT with each property recursively converted and required mapped to strings (defaulting to an empty list; missing 'properties' yields an empty hash).

**Notes.**

- failure: Non-object top-level schemas raise ArgumentError rather than being coerced.

calls: [RubyLLM.Providers.Gemini.Tools.convert_property](r1-gemini-tools.md#u-fd2bd0b786e0)

<a id="u-fd2bd0b786e0"></a>
### `RubyLLM.Providers.Gemini.Tools.convert_property`

`def convert_property(property_schema) # rubocop:disable Metrics/PerceivedComplexity` · [lib/ruby_llm/providers/gemini/tools.rb:L107-L136][f1]

Recursively converts one property schema.

It first normalizes anyOf (normalize_any_of_schema) and uses the normalized schema when present, mapping the working type via param_type_for_gemini. Common attributes are copied first from the original schema, then from the working one, so anyOf-normalized values win. For ARRAY it converts 'items' from working, original, or a default string schema, and copies minItems/maxItems from both sources. For OBJECT it converts each nested property and copies 'required' (working schema preferred, else original) as strings. Other types keep only the copied common attributes.

<a id="u-ecc4e8ceec5e"></a>
### `RubyLLM.Providers.Gemini.Tools.normalize_any_of_schema`

`def normalize_any_of_schema(schema) # rubocop:disable Metrics/PerceivedComplexity` · [lib/ruby_llm/providers/gemini/tools.rb:L151-L166][f1]

Collapses a property's anyOf into a single schema.

Returns nil unless anyOf (string or symbol key) is a non-empty Array. It partitions entries into null-typed and non-null; exactly one non-null entry plus nulls yields a deep-duplicated copy of that entry with nullable: true; multiple non-null entries yield a deep-duplicated first non-null entry, discarding the rest; only null entries yield {type: 'string', nullable: true}.

**Uncertainties.**

- When several non-null variants exist, all but the first are dropped — the caller cannot preserve union semantics.

<a id="u-4ee5d547021e"></a>
### `tools-schema-helpers`

`def copy_common_attributes(target, source)` · [lib/ruby_llm/providers/gemini/tools.rb:L138-L140][f1]

Groups small schema-conversion helpers.

copy_common_attributes copies description, enum, format, nullable, maximum, minimum, and multipleOf via copy_tool_attributes. copy_tool_attributes copies each listed attribute when schema_value finds a non-nil value, writing symbol keys onto the target. schema_value reads each attribute from string and symbol keys, and additionally accepts snake_case aliases for multipleOf, minItems, and maxItems. param_type_for_gemini downcases the type string and maps integer→INTEGER, number/float/double→NUMBER, boolean→BOOLEAN, array→ARRAY, object→OBJECT, and anything else→STRING. schema_type returns an entry's 'type' or :type. Tools-level, distinct from the GeminiSchema class helpers in chat.rb.

<a id="u-d8fa6008552e"></a>
### `RubyLLM.Providers.Gemini.Tools.extract_tool_calls`

`def extract_tool_calls(data) # rubocop:disable Metrics/PerceivedComplexity` · [lib/ruby_llm/providers/gemini/tools.rb:L50-L73][f1]

Extracts tool calls from a Gemini response body.

It returns nil for nil data, when data is not a Hash, when there is no first candidate, or when the content parts are missing or not an Array. Each part containing 'functionCall' becomes a ToolCall keyed by a fresh SecureRandom.uuid with the call's name and its args or {} for missing args. Returns nil when no tool calls were found, otherwise the id-keyed hash.

calls: [ToolCall](r1-messaging-primitives.md#u-f564974b1732)

<a id="u-cf4ccf1b4715"></a>
### `RubyLLM.Providers.Gemini.Tools.format_tool_call`

`def format_tool_call(msg)` · [lib/ruby_llm/providers/gemini/tools.rb:L16-L34][f1]

Formats an assistant message that issued tool calls into Gemini parts.

When the message content exists and is non-empty (checked via respond_to?(:empty?)), it is formatted through Media.format_content and concatenated, flattened to an array if needed. Each tool call then appends a functionCall part with its name and arguments hash. The result is a parts array mixing text/media parts with one functionCall per tool call.

<a id="u-f3ad378e6ea2"></a>
### `RubyLLM.Providers.Gemini.Tools.format_tool_result`

`def format_tool_result(msg, function_name = nil)` · [lib/ruby_llm/providers/gemini/tools.rb:L36-L48][f1]

Formats a tool result message as a single functionResponse part.

The function name defaults to the message's tool_call_id when not supplied; the payload nests the name twice (outer and inside response) with the message content formatted via Media.format_content as content. Returns a one-element array.

calls: [RubyLLM.Providers.Gemini.Media.format_content](r1-gemini-media.md#u-f090cebf0dbd)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/providers/gemini/tools.rb
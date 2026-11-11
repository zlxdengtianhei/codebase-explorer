# Tool definition and execution

**Capability.** Provides the Tool base class with its parameter DSL, schema resolution, invocation logic, and OpenAI tool-call wire conversion.

Come here to define model-callable tools: the DSL for parameters and schemas, name derivation, execution with symbolized keyword arguments, and the Halt mechanism for stopping the conversation loop. OpenAI function-tool definitions and bidirectional tool-call conversion also live here.

**Depends on.**

- [Chat Wire and Media Formats](chat-wire-and-media-formats.md) · graph-confirmed · 3 edge(s) · Tool definitions are converted into provider-specific tool declarations for chat requests.
- [Gemini and media integrations](gemini-and-media-integrations.md) · graph-only · 3 edge(s)
- [Streaming and result objects](streaming-and-result-objects.md) · graph-only · 1 edge(s)

**Depended on by.**

- [Chat Wire and Media Formats](chat-wire-and-media-formats.md) · graph-confirmed · 1 edge(s)
- [Provider chat wire formatting](provider-chat-wire-formatting.md) · graph-only · 1 edge(s)

Parent: [Provider Adapters and Tools](provider-adapters-and-tools.md)

## Units (17)

<a id="u-4f560fa06461"></a>
### `tool.rb-parameter`

`class Parameter` · [lib/ruby_llm/tool.rb:L7-L10][f1]

Value object describing a tool parameter: name, type (default 'string'), optional description, and required flag (default true).

<a id="u-9418b5dc23ff"></a>
### `tool.rb-schemadefinition-construction`

`class SchemaDefinition` · [lib/ruby_llm/tool.rb:L120-L121][f1]

SchemaDefinition wraps a tool parameter schema from a hash, Schema object, or DSL block.

from_parameters builds a strict JSON Schema (additionalProperties false, strict true) from Parameter objects, with required listing only required params and arrays getting a string-items default; map_type normalizes type aliases (int→integer, float/double→number, unknown→string); present? is true when a schema or block exists; initialize stores both.

<a id="u-105edb9356bb"></a>
### `tool.rb-tool-base-and-halt`

`class Tool # Stops conversation continuation after tool execution` · [lib/ruby_llm/tool.rb:L19-L21][f1]

Tool is the base class for model-callable tools; Halt is a simple wrapper whose content, when returned from execute, stops the conversation loop after tool execution (its content is used as the tool message content).

Halt exposes content and to_s delegating to the content's to_s.

<a id="u-ffc983657693"></a>
### `tool.rb-tool-dsl`

`class << self` · [lib/ruby_llm/tool.rb:L33-L36][f1]

Class-level DSL: description reads or sets the description; param adds a Parameter to the memoized parameters hash; params installs a SchemaDefinition from a schema and/or block; with_params stores provider-specific params; provider_params reads them (default {}).

These are inherited state per subclass.

<a id="u-e0087cc10f46"></a>
### `tool.rb-tool-instance-accessors`

`def description` · [lib/ruby_llm/tool.rb:L76-L78][f1]

Instance accessors delegating to class state: description, parameters, and provider_params read the class-level values.

<a id="u-b086eef606df"></a>
### `tools.rb-tool-call-formatting-and-parsing`

`def format_tool_calls(tool_calls)` · [lib/ruby_llm/providers/openai/tools.rb:L52-L65][f2]

Bidirectional tool-call conversion.

format_tool_calls returns nil when the collection is nil/empty, otherwise maps each to {id, type:'function', function:{name, arguments: JSON.generate(args)}}. parse_tool_calls likewise returns nil for empty input and otherwise builds an id-keyed hash of ToolCall objects; with parse_arguments true (the default) arguments are JSON-parsed via parse_tool_call_arguments, which turns nil/empty argument strings into {} and otherwise JSON.parse (raising on malformed JSON); with parse_arguments false the raw argument string is kept, which streaming uses to accumulate partial arguments.

<a id="u-7d7744779b83"></a>
### `tools.rb-tool-schema-construction`

`def parameters_schema_for(tool)` · [lib/ruby_llm/providers/openai/tools.rb:L18-L21][f2]

Builds OpenAI function-tool definitions.

parameters_schema_for prefers the tool's explicit params_schema, otherwise derives one from its parameter definitions via SchemaDefinition.from_parameters, falling back to a frozen empty-object strict schema when derivation yields nil. tool_for wraps {name, description, parameters} in {type:'function', function:…} and, when the tool carries provider_params, deep-merges them over the definition so provider-specific overrides win. param_schema builds a compact {type, description} pair for a single parameter.

<a id="u-2b84d7e90539"></a>
### `RubyLLM.Tool.SchemaDefinition.build_from_block`

`def build_from_block(&)` · [lib/ruby_llm/tool.rb:L196-L199][f1]

Builds a schema from a block by creating a RubyLLM::Schema class and unwrapping its to_json_schema via extract_schema.

<a id="u-0cc975de3419"></a>
### `RubyLLM.Tool.SchemaDefinition.extract_schema`

`def extract_schema(schema_hash)` · [lib/ruby_llm/tool.rb:L201-L206][f1]

Extracts the inner :schema/'schema' key from a hash-shaped schema (deep-duplicated), returning the hash itself when no such key exists, and nil for non-hash input.

<a id="u-c1db805e84c0"></a>
### `RubyLLM.Tool.SchemaDefinition.json_schema`

`def json_schema` · [lib/ruby_llm/tool.rb:L173-L175][f1]

Memoizes the resolved schema deep-stringified via Utils.deep_stringify_keys.

<a id="u-b1c653597502"></a>
### `RubyLLM.Tool.SchemaDefinition.resolve_direct_schema`

`def resolve_direct_schema(schema)` · [lib/ruby_llm/tool.rb:L186-L194][f1]

Resolves a direct schema: objects responding to to_json_schema (including classes with that instance method, instantiated) are unwrapped via extract_schema; Hash schemas are deep-duplicated; anything else yields nil.

<a id="u-037591b5b580"></a>
### `RubyLLM.Tool.SchemaDefinition.resolve_schema`

`def resolve_schema` · [lib/ruby_llm/tool.rb:L179-L184][f1]

Chooses the schema source: the direct schema when present, else the block; nil when neither.

<a id="u-fa2116efb4f0"></a>
### `RubyLLM.Tool.call`

`def call(args)` · [lib/ruby_llm/tool.rb:L101-L106][f1]

Invokes the tool: logs the call, symbolizes argument keys, calls execute with keyword arguments, logs and returns the result.

Missing keys or unimplemented execute raise (NotImplementedError by default).

<a id="u-49977bed8d94"></a>
### `RubyLLM.Tool.execute`

`def execute(...)` · [lib/ruby_llm/tool.rb:L108-L110][f1]

Abstract execution hook; subclasses must implement it or get NotImplementedError.

<a id="u-4b0b9080b7ea"></a>
### `RubyLLM.Tool.halt`

`def halt(message)` · [lib/ruby_llm/tool.rb:L114-L116][f1]

Constructs a Tool::Halt wrapping the given message, for use inside execute to stop the conversation loop.

<a id="u-448c0b836eda"></a>
### `RubyLLM.Tool.name`

`def name` · [lib/ruby_llm/tool.rb:L65-L74][f1]

Derives the tool name from the class name: NFKD-normalized, non-ASCII stripped, non-alphanumeric characters to '-', CamelCase split into snake_case, downcased, and a trailing '_tool' suffix removed.

<a id="u-24179d22cf50"></a>
### `RubyLLM.Tool.params_schema`

`def params_schema` · [lib/ruby_llm/tool.rb:L88-L99][f1]

Memoizes the JSON schema for the tool's parameters: prefers the class's SchemaDefinition (via params) when present, otherwise builds one from the legacy Parameter list; returns nil when neither defines parameters.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/tool.rb
[f2]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/providers/openai/tools.rb

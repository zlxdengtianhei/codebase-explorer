# OpenAI Tools

**Capability.** Serializes outgoing tool calls, parses incoming tool_call entries into ToolCall objects, and builds function-tool definitions with parameter-schema helpers.

Use these methods for OpenAI-format tool wiring; subclasses reuse them unless they override.

**Depends on.**

- [Shared Utilities](r1-shared-utilities.md) · graph-confirmed · 1 edge(s)
- [Tool Definition DSL](r1-tool-dsl.md) · graph-confirmed · 1 edge(s)
- [Message & ToolCall Value Objects](r1-messaging-primitives.md) · graph-only · 1 edge(s)

**Depended on by.**

- [OpenAI Adapter](r2-provider-openai.md) · graph-only · 1 edge(s)

Parent: [OpenAI Family](r1-openai-family.md)

## Units (4)

<a id="u-01c607ea44ab"></a>
### `RubyLLM.Providers.OpenAI.Tools.format_tool_calls`

`def format_tool_calls(tool_calls)` · [lib/ruby_llm/providers/openai/tools.rb:L52-L65][f1]

Serializes outgoing tool calls for the OpenAI API.

Returns nil when tool_calls is nil or empty (so the payload key is compacted away). Otherwise maps each id→tc pair to {id:, type: 'function', function: {name:, arguments: JSON.generate(tc.arguments)}}, encoding the arguments hash back to a JSON string for the wire format.

**Notes.**

- failure: Non-serializable arguments will raise from JSON.generate; no rescue is present.

<a id="u-1fd3512688a5"></a>
### `RubyLLM.Providers.OpenAI.Tools.parse_tool_calls`

`def parse_tool_calls(tool_calls, parse_arguments: true)` · [lib/ruby_llm/providers/openai/tools.rb:L77-L94][f1]

Converts OpenAI tool_call entries into a hash of id → ToolCall.

Returns nil when tool_calls is nil or empty. Each entry is keyed by tc['id'] and wrapped in ToolCall.new with id and function.name. Argument handling depends on parse_arguments: when true, parse_tool_call_arguments JSON-decodes the arguments string (empty/nil arguments become {}); when false, the raw arguments string is kept — used during streaming. Note tool_calls.to_h is used, so duplicate ids would keep the last occurrence.

**Notes.**

- failure: Malformed JSON arguments raise from JSON.parse when parse_arguments is true; the raw-string streaming path avoids this.

calls: [ToolCall](r1-messaging-primitives.md#u-f564974b1732), [RubyLLM.Providers.OpenAI.Tools.parse_tool_calls](r1-openai-tools.md#u-1fd3512688a5)

<a id="u-6b22fb38aebb"></a>
### `RubyLLM.Providers.OpenAI.Tools.tool_for`

`def tool_for(tool)` · [lib/ruby_llm/providers/openai/tools.rb:L28-L43][f1]

Builds the OpenAI function-tool definition sent with a chat request.

Gets the parameters schema via parameters_schema_for, then assembles {type: 'function', function: {name, description, parameters}}. If tool.provider_params is empty the definition is returned as-is; otherwise it is deep-merged with provider_params, letting provider-supplied keys override the generated structure at any depth. Name and description are taken from the tool object as-is.

calls: [utils-utils-helpers](r1-shared-utilities.md#u-add7cf7f30e5), [tools-rb-schema-helpers](r1-openai-tools.md#u-97972b8602a0)

<a id="u-97972b8602a0"></a>
### `tools-rb-schema-helpers`

`def parameters_schema_for(tool)` · [lib/ruby_llm/providers/openai/tools.rb:L18-L21][f1]

Parameter-schema helpers.

EMPTY_PARAMETERS_SCHEMA is a frozen strict empty object schema used when a tool has no parameters. parameters_schema_for prefers tool.params_schema when present, otherwise derives one via schema_from_parameters. schema_from_parameters delegates to RubyLLM::Tool::SchemaDefinition.from_parameters and returns its json_schema, falling back to EMPTY_PARAMETERS_SCHEMA when the definition (or its json_schema) is nil. param_schema builds {type:, description:}.compact for a single parameter — a legacy/small helper not referenced by the other methods in this file.

calls: [tool.rb-tool-and-parameter](r1-tool-dsl.md#u-00e41a176da0)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/providers/openai/tools.rb
# Tool Definition DSL

**Capability.** Tool definition DSL and JSON-schema construction for parameters, independent of any provider wire format.

Define tools with this DSL; providers then translate the built schema into their own formats. It depends on shared utilities for normalization.

**Depends on.**

- [Shared Utilities](r1-shared-utilities.md) · graph-confirmed · 3 edge(s)

**Depended on by.**

- [Chat Session & Completion Loop](r1-chat-session.md) · model-inferred · 0 edge(s) · Chat executes tool calls whose schemas are declared via the tool DSL.
- [Gemini Tools](r1-gemini-tools.md) · graph-confirmed · 1 edge(s)
- [OpenAI Tools](r1-openai-tools.md) · graph-confirmed · 1 edge(s)

Parent: [Conversation Core](r1-conversation-core.md)

## Units (1)

<a id="u-00e41a176da0"></a>
### `tool.rb-tool-and-parameter`

`class Parameter` · [lib/ruby_llm/tool.rb:L7-L10][f1]

Tool definition DSL and schema construction.

Parameter stores name, type (default 'string'), desc, and required (default true). Tool.Halt is a sentinel wrapping content whose to_s stringifies it; instances signal halt via the protected halt helper. Class-level DSL: description getter/setter, param registers a Parameter by name, params stores a SchemaDefinition built from an explicit schema or block, with_params sets provider_params. Instance methods delegate to the class; name derives a snake_case tool name from the class name via NFKD normalization, ASCII stripping, separator replacement, camelCase splitting, downcasing, and removal of a trailing '_tool'. call debug-logs, symbolizes argument keys, executes, and debug-logs the result; execute raises NotImplementedError for subclasses that omit it. SchemaDefinition.from_parameters builds strict JSON schema objects (type/properties/required/additionalProperties false/strict true) from Parameters, defaulting array items to string; map_type maps int/float/double etc. to schema types with a 'string' fallback. An instance resolves its schema lazily: a direct Hash is deep-duped, an object with to_json_schema or such a class has its [:schema]/'schema' key extracted, and a block is compiled through RubyLLM::Schema.create; json_schema memoizes the deep-stringified result. present? is true when a schema or block was given.

uses: [utils-utils-helpers](r1-shared-utilities.md#u-add7cf7f30e5)

**Uncertainties.**

- RubyLLM::Schema.create and to_json_schema are defined in ruby_llm/schema.rb, outside this batch

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/tool.rb
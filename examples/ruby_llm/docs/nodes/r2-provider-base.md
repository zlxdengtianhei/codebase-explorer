# Provider Base and Registry

**Capability.** Class-level provider metadata/registry plus the instance base class that owns config and a Connection and implements the shared request pipeline.

Read to learn how providers are registered and how common request execution works before per-provider overrides.

**Depends on.**

- [Provider Connection](r2-connection.md) · graph-confirmed · 7 edge(s) · The provider base class issues every request through its per-provider Connection.
- [Error Hierarchy and Middleware](r2-error-handling.md) · model-inferred · 0 edge(s)
- [OpenAI Adapter](r2-provider-openai.md) · graph-only · 2 edge(s)
- [Registry Catalog](r1-registry-catalog.md) · graph-only · 1 edge(s)

**Depended on by.**

- [Registry Catalog](r1-registry-catalog.md) · graph-only · 2 edge(s)
- [Bedrock Adapter](r2-provider-bedrock.md) · graph-only · 1 edge(s)

Parent: [HTTP Transport and Provider Base](r2-transport.md)

## Units (2)

<a id="u-528dbec87490"></a>
### `provider.rb-provider-class`

`def name` · [lib/ruby_llm/provider.rb:L138-L140][f1]

Class-level provider metadata and registry.

name is the demodulized class name and slug its downcased form; capabilities raises NotImplementedError, configuration_requirements defaults to [], local? defaults false and remote? is its negation, and configured? is true when every requirement reads truthy from a config. register stores a class under a symbol key in the memoized providers hash; resolve looks it up; for finds the model's registry entry and resolves its provider. local_providers, remote_providers, configured_providers, and configured_remote_providers filter the registry by local?, remote?, configured?, or the combination, returning provider classes.

calls: [models.rb-registry-instance](r1-registry-catalog.md#u-5bc7d7cbafe4)

<a id="u-961fc10a6a0f"></a>
### `provider.rb-provider-instance`

`def initialize(config)` · [lib/ruby_llm/provider.rb:L10-L14][f1]

Base class for provider instances: owns config and a Connection, and implements the shared request pipeline.

initialize validates configuration (ensure_configured! raises ConfigurationError listing missing requirement names) and builds the Connection. complete normalizes temperature via maybe_normalize_temperature (identity here), deep-merges params over the rendered payload, then streams via stream_response when a block is given or posts synchronously via sync_response (which posts to completion_url, prepends additional headers, and parses with parse_completion_response). list_models, embed, moderate, paint, and transcribe each render a payload, issue a GET/POST through the connection, and delegate parsing to a provider-specific parse method; transcribe wraps the audio file as a multipart FilePart with a Marcel-detected MIME type. configured? re-checks all configuration_requirements; local?/remote? and slug/name/capabilities/configuration_requirements delegate to the class. parse_error extracts messages from error bodies: empty body yields nil; a Hash digs 'error'.'message'; an Array joins per-part messages with '. '; anything else is returned raw. format_messages maps messages to role string plus content; format_tool_calls and parse_tool_calls default to nil. try_parse_json parses strings and returns the original value on JSON::ParserError.

uses: [connection.rb-connection](r2-connection.md#u-53be52e4979e); calls: [stream_response](r2-streaming-shared.md#u-c93f3bf995bc)

**Uncertainties.**

- The file's parse tree contains an ERROR node near line 1 per program diagnostics, though chunk coverage is preserved
- render_payload, completion_url, and the parse_* hooks are provider-side methods not visible in this batch

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/provider.rb
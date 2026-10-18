# Registry Catalog

**Capability.** Class-level registry operations (loading, refreshing, schema) plus the instance-side query API and resolution of a model id into [Model::Info, provider] pairs.

Use the singleton/class API to load and refresh the catalog, and the instance API to filter by provider, capabilities, or modalities. Resolve is the bridge used by Chat to pick a provider.

**Depends on.**

- [Model Metadata Objects](r1-model-metadata.md) · model-inferred · 0 edge(s)
- [Provider Connection](r2-connection.md) · graph-only · 2 edge(s)
- [Provider Base and Registry](r2-provider-base.md) · graph-only · 2 edge(s)
- [Error Hierarchy and Middleware](r2-error-handling.md) · graph-only · 1 edge(s)

**Depended on by.**

- [Chat Session & Completion Loop](r1-chat-session.md) · model-inferred · 0 edge(s) · Chat uses Models.resolve to pick a model and provider from the registry catalog.
- [Model Maintenance Rake Tasks](r1-model-maintenance-tasks.md) · model-inferred · 0 edge(s) · Rake tasks refresh the registry catalog and regenerate docs and aliases from it.
- [Bedrock Models & Capabilities](r1-bedrock-models-capabilities.md) · graph-only · 1 edge(s)
- [Provider Base and Registry](r2-provider-base.md) · graph-only · 1 edge(s)

Parent: [Model Registry](r1-model-registry.md)

## Units (3)

<a id="u-c1aaaef7b94e"></a>
### `models.rb-registry-singleton`

`def instance` · [lib/ruby_llm/models.rb:L9-L11][f1]

Class-level registry operations for the model catalog.

instance memoizes a Models instance. read_from_json returns [] when the registry file is missing or unparsable, otherwise maps entries to Model::Info; load_models reads the configured registry file. refresh! fetches models from providers and the Parsera API, merges them, and replaces the memoized instance with a new Models built from the merged list. fetch_from_providers selects configured remote providers (or all configured ones when remote_only is false), logs them, and flat-maps their list_models. fetch_from_parsera GETs api.parsera.org/v1/llm-specs over a basic JSON connection and drops entries with nil provider or id. merge_models indexes both sides by 'provider:id', takes the union of keys, prefers Parsera data when both exist (merging provider metadata on top via add_provider_metadata), keeps whichever side exists otherwise, and sorts by [provider, id]. find_parsera_model substitutes VertexAI requests with the Gemini Parsera spec, relabeling the provider as 'vertexai'. method_missing and respond_to_missing? delegate to the singleton instance so class-level calls reach instance methods.

**Notes.**

- side_effect: refresh! performs network requests to every configured provider and the Parsera API and then replaces the global instance

uses: [connection.rb-connection](r2-connection.md#u-53be52e4979e)

**Uncertainties.**

- Whether parsera fetch failures propagate or are rescued is not shown; no rescue surrounds the GET

<a id="u-5bc7d7cbafe4"></a>
### `models.rb-registry-instance`

`def initialize(models = nil)` · [lib/ruby_llm/models.rb:L156-L158][f1]

Instance-side query API over the loaded model list.

initialize accepts a model list or loads the configured registry JSON. load_from_json! replaces the list from a file; save_to_json pretty-writes all models to a file. find resolves an id with alias fallback: with a provider it tries exact (id, provider), then the alias-resolved id, raising ModelNotFoundError naming both; without a provider it tries exact id, then the alias resolution, raising ModelNotFoundError. each makes the instance Enumerable over all. chat_models, embedding_models, audio_models, image_models, by_family, and by_provider each return a new Models wrapping a filtered subset (embedding/audio/image also match modalities.output membership). refresh! and resolve simply delegate to the class methods.

uses: [models.rb-registry-singleton](r1-registry-catalog.md#u-c1aaaef7b94e)

**Uncertainties.**

- Aliases.resolve and Model::Info accessors (type, modalities, family) live outside this batch

<a id="u-3dcbba4582dc"></a>
### `RubyLLM.Models.resolve`

`def resolve(model_id, provider: nil, assume_exists: false, config: nil) # rubocop:dis…` · [lib/ruby_llm/models.rb:L49-L80][f1]

Resolves a model id plus optional provider into a [Model::Info, provider instance] pair.

If a provider symbol is given it looks up its class and, for local providers, forces assume_exists. With assume_exists, a missing provider symbol raises ArgumentError and an unregistered provider class raises Error; the model is looked up only for local providers, rescuing ModelNotFoundError to nil, and otherwise falls back to Model::Info.default built from the id and provider slug. Without assume_exists, it finds the model in the registry and resolves the provider class named by the model's provider, raising Error for unknown providers. Config defaults to RubyLLM.config when nil.

uses: [models.rb-registry-singleton](r1-registry-catalog.md#u-c1aaaef7b94e)

**Uncertainties.**

- Model::Info.default is defined outside this batch; its field defaults are unproven

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/models.rb
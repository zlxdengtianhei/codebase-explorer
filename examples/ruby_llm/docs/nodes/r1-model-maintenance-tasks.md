# Model Maintenance Rake Tasks

**Capability.** Rake workflow chaining models:update/docs/aliases: env-based provider configuration, registry refresh with JSON-schema validation, markdown doc generation (provider/capability/modality sections), and alias generation by cross-referencing providers and picking date-best Bedrock counterparts.

Run the `models` task for the full pipeline. generate_aliases groups Anthropic ids by base name and date suffix to pick representatives; the legacy aliases:generate namespace forwards here.

**Depends on.**

- [Model Aliases](r1-aliases.md) · model-inferred · 0 edge(s)
- [Registry Catalog](r1-registry-catalog.md) · model-inferred · 0 edge(s) · Rake tasks refresh the registry catalog and regenerate docs and aliases from it.

Parent: [Developer Tooling](r1-developer-tooling.md)

## Units (18)

<a id="u-8a567ea1f9f5"></a>
### `models.rake module code (L1–L39)`

`module_region` · [lib/tasks/models.rake:L1-L39][f1]

Defines the rake entry points for the models workflow: the `models` task chains models:update, models:docs, and models:aliases; models:update configures RubyLLM from environment, refreshes models, and prints stats; models:docs creates docs/_reference and writes the generated markdown there; models:aliases calls generate_aliases; a legacy aliases:generate namespace forwards to models:aliases for backwards compatibility.

The region also requires dotenv, ruby_llm, json, json-schema, and fileutils.

**Notes.**

- side_effect: models:docs writes docs/_reference/available-models.md via File.write after FileUtils.mkdir_p.
- contract: aliases:generate exists only as a backwards-compatible dependency on models:aliases.

calls: [configure_from_env](r1-model-maintenance-tasks.md#u-c58f82a3aede), [refresh_models](r1-model-maintenance-tasks.md#u-1536c212ef1c), [display_model_stats](r1-model-maintenance-tasks.md#u-b2c54aaacb86), [generate_models_markdown](r1-model-maintenance-tasks.md#u-41fcabd90960), [generate_aliases](r1-model-maintenance-tasks.md#u-0081cfb6256d)

<a id="u-c58f82a3aede"></a>
### `configure_from_env`

`def configure_from_env` · [lib/tasks/models.rake:L40-L54][f1]

Populates the global RubyLLM configuration from environment variables, defaulting every key to nil when absent: OpenAI, Anthropic, Gemini, DeepSeek, Perplexity, OpenRouter, and Mistral API keys, VertexAI location/project, Bedrock credentials via configure_bedrock, and a 30-second request timeout.

No key presence validation happens here; missing values simply become nil configuration.

calls: [configure_bedrock](r1-model-maintenance-tasks.md#u-8dbc976dd606)

<a id="u-8dbc976dd606"></a>
### `configure_bedrock`

`def configure_bedrock(config)` · [lib/tasks/models.rake:L56-L61][f1]

Sets Bedrock credentials on the given config object from the AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_REGION, and AWS_SESSION_TOKEN environment variables, each defaulting to nil when unset.

<a id="u-1536c212ef1c"></a>
### `refresh_models`

`def refresh_models` · [lib/tasks/models.rake:L63-L83][f1]

Refreshes the model registry and persists it after validation.

It records the cached count via RubyLLM.models.all.size, calls RubyLLM.models.refresh!, then branches: if the refreshed list is empty and the initial count was zero it prints an error and exits with status 1; if the size is unchanged and the initial count was positive it only prints a warning and keeps the stale data without saving; otherwise it validates via validate_models! and saves models.json with models.save_to_json. In all non-exiting cases the refreshed registry is memoized in the instance variable @models for later stats display.

**Notes.**

- failure: Empty refresh starting from an empty cache exits with code 1 before any validation or saving.
- side_effect: Stores the registry in @models, which display_model_stats later reads.

calls: [validate_models!](r1-model-maintenance-tasks.md#u-1420b00ee526)

**Uncertainties.**

- A shrunk-but-non-empty list falls into the success branch and overwrites models.json; whether that is intended is not stated in code.

<a id="u-1420b00ee526"></a>
### `validate_models!`

`def validate_models!(models)` · [lib/tasks/models.rake:L85-L105][f1]

Validates the refreshed model data against the JSON schema at RubyLLM::Models.schema_file using JSON::Validator.fully_validate over models.all.map(&:to_h).

On any validation error it dumps the full data pretty-printed to ../ruby_llm/models.failed.json relative to __dir__, prints the first 10 errors (plus a count of the remainder), and exits with status 1. On success it prints a confirmation and returns normally, letting refresh_models save.

**Notes.**

- side_effect: Failed data is persisted to models.failed.json before exiting for inspection.

**Uncertainties.**

- The failed-data path '../ruby_llm/models.failed.json' from __dir__ assumes a sibling ruby_llm directory exists; not verifiable from this file.

<a id="u-b2c54aaacb86"></a>
### `display_model_stats`

`def display_model_stats` · [lib/tasks/models.rake:L107-L119][f1]

Prints per-provider model counts after a refresh.

It groups @models.all by provider and counts each bucket, then iterates RubyLLM::Provider.providers printing each provider class name with its count (defaulting to 0 when absent) and a status suffix from status(sym), ending with 'Refresh complete.'

calls: [status](r1-model-maintenance-tasks.md#u-8e8c337b444c); uses: [refresh_models](r1-model-maintenance-tasks.md#u-1536c212ef1c)

**Uncertainties.**

- Reads @models set earlier by refresh_models in the same process; if invoked standalone, @models is nil and the group_by would raise.

<a id="u-8e8c337b444c"></a>
### `status`

`def status(provider_sym)` · [lib/tasks/models.rake:L121-L130][f1]

Returns a display suffix for a provider symbol: ' (LOCAL - SKIP)' when the provider class answers local?, ' (OK)' when provider_class.configured?(RubyLLM.config) is true, otherwise ' (NOT CONFIGURED)'.

<a id="u-41fcabd90960"></a>
### `generate_models_markdown`

`def generate_models_markdown` · [lib/tasks/models.rake:L132-L181][f1]

Builds the full Jekyll markdown page for available models as a single heredoc: front matter, a data-sources section, an UTC 'Last Updated' timestamp from Time.now, then interpolates generate_provider_sections, generate_capability_sections, and generate_modality_sections.

Returns the string; performs no file writes itself.

calls: [generate_provider_sections](r1-model-maintenance-tasks.md#u-8c74be726b05), [generate_capability_sections](r1-model-maintenance-tasks.md#u-701fe6e000e0), [generate_modality_sections](r1-model-maintenance-tasks.md#u-b679e76f4793)

<a id="u-8c74be726b05"></a>
### `generate_provider_sections`

`def generate_provider_sections` · [lib/tasks/models.rake:L183-L194][f1]

Iterates RubyLLM::Provider.providers and, for each provider with at least one model returned by RubyLLM.models.by_provider(provider), emits a '### <name> (<count>)' heading followed by models_table(models).

Providers with no models are skipped via filter_map; sections are joined with blank lines.

calls: [models_table](r1-model-maintenance-tasks.md#u-ffa189b21247)

<a id="u-701fe6e000e0"></a>
### `generate_capability_sections`

`def generate_capability_sections` · [lib/tasks/models.rake:L196-L213][f1]

Builds sections for four capability buckets selected from RubyLLM.models: function calling, structured output, streaming, and batch processing (the latter two via membership in model.capabilities).

Each non-empty bucket becomes a '### <capability> (<count>)' heading plus a models_table; empty buckets are skipped and remaining sections are joined with blank lines.

calls: [models_table](r1-model-maintenance-tasks.md#u-ffa189b21247)

<a id="u-b679e76f4793"></a>
### `generate_modality_sections`

`def generate_modality_sections # rubocop:disable Metrics/PerceivedComplexity` · [lib/tasks/models.rake:L215-L263][f1]

Emits up to four modality sections, each only when matching models exist: vision, audio, and PDF sections from 'image', 'audio', and 'pdf' in m.modalities.input (nil-safe via `|| []`), and an embedding section from 'embeddings' in m.modalities.output.

Each section carries a count, a one-line description, and a models_table; sections are joined with blank lines and returned.

calls: [models_table](r1-model-maintenance-tasks.md#u-ffa189b21247)

<a id="u-ffa189b21247"></a>
### `models_table`

`def models_table(models)` · [lib/tasks/models.rake:L265-L292][f1]

Renders a markdown table of models sorted by [provider, name] with columns Model, Provider, Context, Max Output, and Standard Pricing.

Returns the literal '*No models found*' when the input is empty; context_window and max_output_tokens fall back to '-' when nil, and pricing comes from standard_pricing_display. Emits header and alignment rows then one row per model.

calls: [standard_pricing_display](r1-model-maintenance-tasks.md#u-3cf599e0bf80)

<a id="u-3cf599e0bf80"></a>
### `standard_pricing_display`

`def standard_pricing_display(model)` · [lib/tasks/models.rake:L294-L312][f1]

Formats a model's standard text-token pricing as a comma-joined string.

It reads model.pricing.to_h[:text_tokens][:standard] (nil-safe via &.dig, defaulting to {}); when present it appends 'In: $X.XX' for input_per_million, 'Out: $X.XX' for output_per_million, and 'Cache: $X.XX' for cached_input_per_million, each only if the value exists. If no parts were produced (or pricing data is empty) it returns '-'.

<a id="u-0081cfb6256d"></a>
### `generate_aliases`

`def generate_aliases # rubocop:disable Metrics/PerceivedComplexity` · [lib/tasks/models.rake:L314-L434][f1]

Builds and writes the model alias registry by cross-referencing each provider's model ids against OpenRouter's.

Models are bucketed by provider into a defaulting hash. OpenAI models get an alias when 'openai/<id>' exists on OpenRouter, keyed with '-latest' stripped. Anthropic models are grouped by base name via group_anthropic_models_by_base_name; for each latest model several dotted naming variants are tried against OpenRouter, and a Bedrock match is found via find_best_bedrock_model; an alias is written only if an OpenRouter, Bedrock, or direct Anthropic match exists. Bedrock ids starting with 'anthropic.' are then matched back to Anthropic/OpenRouter names (dotted to dashed), skipping aliases already created. Gemini models get aliases mapping to OpenRouter 'google/<id>' variants and to vertexai when the same id exists there. VertexAI models absent from the Gemini list get their own aliases when an OpenRouter 'google/<id>' variant exists, skipping already-created keys. DeepSeek models alias when 'deepseek/<id>' exists on OpenRouter. Finally the sorted alias hash is pretty-generated into RubyLLM::Aliases.aliases_file and the count is printed.

**Notes.**

- side_effect: Overwrites the aliases JSON file at RubyLLM::Aliases.aliases_file with the sorted, pretty-generated mapping.
- failure: First-matching-alias wins: later providers skip keys already present in the aliases hash (Bedrock and VertexAI branches check aliases[...]).

calls: [group_anthropic_models_by_base_name](r1-model-maintenance-tasks.md#u-60d8d2d8f830), [find_best_bedrock_model](r1-model-maintenance-tasks.md#u-a5e792432a29); uses: [extract_base_name](r1-model-maintenance-tasks.md#u-420261550eef), [extract_date_from_model](r1-model-maintenance-tasks.md#u-f0d43f36b4f9)

**Uncertainties.**

- Exact alias-filename and write behavior depend on RubyLLM::Aliases.aliases_file, defined outside this file.
- Whether the OpenRouter naming-variant regexes cover every upstream naming scheme is not provable from this file.

<a id="u-60d8d2d8f830"></a>
### `group_anthropic_models_by_base_name`

`def group_anthropic_models_by_base_name(anthropic_models)` · [lib/tasks/models.rake:L436-L455][f1]

Groups Anthropic model ids by base name using extract_base_name, then for each group picks the representative model: the single member when the group has one, otherwise the member with the maximum extract_date_from_model value (string comparison, so YYYYMMDD suffixes order chronologically).

Returns a hash of base_name to latest model id.

calls: [extract_base_name](r1-model-maintenance-tasks.md#u-420261550eef), [extract_date_from_model](r1-model-maintenance-tasks.md#u-f0d43f36b4f9)

<a id="u-a5e792432a29"></a>
### `find_best_bedrock_model`

`def find_best_bedrock_model(anthropic_model, bedrock_models) # rubocop:disable Metric…` · [lib/tasks/models.rake:L473-L525][f1]

Chooses the best Bedrock counterpart for an Anthropic model id, returning nil when nothing matches.

The base pattern comes from a case mapping: claude-2.0/claude-2 map to 'claude-v2', claude-2.1 to 'claude-v2:1', claude-instant-v1/claude-instant to 'claude-instant', and anything else falls back to extract_base_name(anthropic_model). Bedrock candidates have any leading 'us.' or 'anthropic.' prefix removed and must start with the base pattern; an empty match set returns nil. If RubyLLM.models.find succeeds for the Anthropic id, its context_window is converted to k and candidates containing ':<k>k' or ':0:<k>k' win, first match returned; a failed lookup is rescued and treated as no target context. Without a context match, candidates are ranked by min_by on [has-context (ids containing 'k' preferred), largest context k (negated), largest version (negated)].

calls: [extract_base_name](r1-model-maintenance-tasks.md#u-420261550eef); uses: [group_anthropic_models_by_base_name](r1-model-maintenance-tasks.md#u-60d8d2d8f830)

**Uncertainties.**

- The rescue swallows any StandardError from RubyLLM.models.find, so lookup failures silently degrade to the priority ranking rather than surfacing an error.

<a id="u-420261550eef"></a>
### `extract_base_name`

`def extract_base_name(model)` · [lib/tasks/models.rake:L457-L463][f1]

Strips a trailing 8-digit date suffix from a model id: if the id matches /^(.+)-(\d{8})$/ it returns the prefix, otherwise the id unchanged.

<a id="u-f0d43f36b4f9"></a>
### `extract_date_from_model`

`def extract_date_from_model(model)` · [lib/tasks/models.rake:L465-L471][f1]

Returns the trailing 8-digit date of a model id via /-(\d{8})$/, or the sentinel '00000000' when the id has no date suffix, so undated models always sort oldest.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/tasks/models.rake
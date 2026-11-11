# Model Registry Rake Tooling

**Capability.** Rake tasks and alias resolution that refresh, validate, and document the model registry, plus VCR cassette management for tests.

Come here for build-time automation: updating model data, generating markdown docs and cross-provider aliases, validating models against schema, and re-recording test cassettes. It also provides runtime alias lookup from a lazily loaded JSON table.

Parent: [RubyLLM LLM Integration Gem](rubyllm-llm-integration-gem.md)

## Units (22)

<a id="u-2dffedbe942e"></a>
### `aliases.rb-model-alias-resolution`

`class Aliases` · [lib/ruby_llm/aliases.rb:L5-L6][f1]

Resolves provider-specific model IDs from a lazily loaded alias table stored in aliases.json next to the file.

resolve returns model_id unchanged when no alias exists; with a provider it returns that provider's mapping or falls back to model_id; without a provider it returns the first alias value or model_id. aliases memoizes load_aliases, which parses the JSON file or returns {} if the file is missing; reload! clears the memo by re-reading. Malformed JSON would propagate a parse error.

calls: [aliases.rb-model-alias-resolution](model-registry-rake-tooling.md#u-2dffedbe942e)

<a id="u-539923d6402d"></a>
### `models.rake-anthropic-model-grouping-helpers`

`def group_anthropic_models_by_base_name(anthropic_models)` · [lib/tasks/models.rake:L436-L455][f2]

group_anthropic_models_by_base_name maps each Anthropic model id to a base name (id minus a trailing 8-digit date, otherwise the id itself) and returns one model per base name: the single model, or the one with the max trailing date (models without a date sort as '00000000', i.e. oldest).

extract_base_name strips a trailing '-YYYYMMDD'; extract_date_from_model returns that date or '00000000'.

<a id="u-42d2006c60b8"></a>
### `models.rake-env-configuration`

`def configure_from_env` · [lib/tasks/models.rake:L40-L54][f2]

Configure RubyLLM from environment variables: API keys for OpenAI, Anthropic, Gemini, DeepSeek, Perplexity, OpenRouter, and Mistral; VertexAI location/project; Bedrock credentials via the helper; and a 30-second request timeout.

Missing keys become nil via ENV.fetch defaults, so no exception is raised here.

<a id="u-b23a32bdea06"></a>
### `models.rake-markdown-model-tables`

`def models_table(models)` · [lib/tasks/models.rake:L265-L292][f2]

models_table renders a markdown table of model id, provider, context window, max output tokens, and pricing, sorted by provider then name, with '-' placeholders for missing numeric fields and '*No models found*' for an empty list.

standard_pricing_display formats the model's standard text-token pricing as 'In: $X, Out: $Y, Cache: $Z' (two decimals), including each part only when present, and returns '-' when no pricing data or parts exist.

<a id="u-581c1db6b389"></a>
### `models.rake-model-stats-display`

`def display_model_stats` · [lib/tasks/models.rake:L107-L119][f2]

Prints per-provider model counts and configuration status.

Groups @models by provider, then iterates RubyLLM::Provider.providers, printing each provider's class name, its model count (0 if absent), and a status string: '(LOCAL - SKIP)' for local providers, '(OK)' when configured per RubyLLM.config, otherwise '(NOT CONFIGURED)'. Depends on @models being set by refresh_models.

<a id="u-335725c2a446"></a>
### `vcr.rake-vcr-namespace-and-helpers`

`group` · [lib/tasks/vcr.rake:L1-L4][f3]

The vcr namespace defines vcr:record taking a providers argument: it downcases and compacts the argument plus extras, ensures spec/fixtures/vcr_cassettes exists, and dispatches to record_all_cassettes for 'all' or record_for_providers otherwise.

Helper functions are documented in their own units.

<a id="u-a5e792432a29"></a>
### `find_best_bedrock_model`

`def find_best_bedrock_model(anthropic_model, bedrock_models) # rubocop:disable Metric…` · [lib/tasks/models.rake:L473-L525][f2]

Picks the best Bedrock model id corresponding to an Anthropic model.

Maps special names (claude-2.x, claude-instant) to legacy Bedrock prefixes, otherwise uses the base name; selects Bedrock ids whose anthropic prefix (optionally 'us.') is stripped and that start with that pattern, returning nil if none. If the Anthropic model's context window is known (via RubyLLM.models.find, rescued to nil on any StandardError), it prefers the first match embedding ':<k>k' or ':0:<k>k' for that window. Otherwise it returns the match minimizing a tuple: preferring ids containing 'k', then larger context numbers, then larger -vN: versions (via negated priorities).

<a id="u-0081cfb6256d"></a>
### `generate_aliases`

`def generate_aliases # rubocop:disable Metrics/PerceivedComplexity` · [lib/tasks/models.rake:L314-L434][f2]

Builds cross-provider alias mappings and writes them sorted to RubyLLM::Aliases.aliases_file as pretty JSON, printing the count.

Groups model ids by provider, then: OpenAI models with a matching 'openai/<model>' OpenRouter entry get an alias keyed by the model name without '-latest'; Anthropic models are grouped to their latest per base name and matched to OpenRouter variants (several dot/dash transformations) and a best Bedrock model, emitting an alias only if at least one match exists; Bedrock anthropic.* models matching claude-<version> get aliases keyed by the dash-form name unless already present, optionally adding anthropic and openrouter entries; Gemini models map to OpenRouter 'google/...' variants and identical vertexai ids; vertexai-only models (not in gemini) get aliases when an OpenRouter match exists, skipping already-created keys; DeepSeek models with an OpenRouter counterpart get aliases. Later loops can overwrite earlier alias keys (e.g. gemini vs vertexai) except where explicitly skipped.

<a id="u-701fe6e000e0"></a>
### `generate_capability_sections`

`def generate_capability_sections` · [lib/tasks/models.rake:L196-L213][f2]

Renders markdown subsections for four capability groups—function calling, structured output, streaming, and batch—selected from RubyLLM.models by predicate or capabilities array membership; empty groups are skipped and sections joined with blank lines.

<a id="u-b679e76f4793"></a>
### `generate_modality_sections`

`def generate_modality_sections # rubocop:disable Metrics/PerceivedComplexity` · [lib/tasks/models.rake:L215-L263][f2]

Renders markdown subsections for modality groups: vision (image input), audio input, PDF input, and embeddings (output modality), each guarded so empty groups produce no section; nil input modality arrays are treated as empty.

Sections are joined with blank lines.

<a id="u-41fcabd90960"></a>
### `generate_models_markdown`

`def generate_models_markdown` · [lib/tasks/models.rake:L132-L181][f2]

Builds the full available-models markdown document as a Jekyll page with front matter, TOC, data-source credits, a UTC 'last updated' date, and sections for providers, capabilities, and modalities, delegating each section body to the generator helpers.

Pure string assembly; the actual model data comes from RubyLLM.models at render time.

<a id="u-8c74be726b05"></a>
### `generate_provider_sections`

`def generate_provider_sections` · [lib/tasks/models.rake:L183-L194][f2]

Renders one markdown subsection per provider that has models, showing the provider class name, model count, and a table via models_table; providers with no models are skipped via filter_map.

Sections are joined with blank lines.

<a id="u-1536c212ef1c"></a>
### `refresh_models`

`def refresh_models` · [lib/tasks/models.rake:L63-L83][f2]

Refreshes the model registry and persists it conditionally.

Captures the initial cached count, calls RubyLLM.models.refresh!, then branches: if the result is empty and the cache was also empty it prints an error and exits 1; if the count is unchanged and positive it only warns; otherwise it validates the models and saves models.json. Stores the result in the instance variable @models for later display.

<a id="u-1420b00ee526"></a>
### `validate_models!`

`def validate_models!(models)` · [lib/tasks/models.rake:L85-L105][f2]

Validates all models against the JSON schema at RubyLLM::Models.schema_file using JSON::Validator.fully_validate.

On any validation error it writes the full model data to lib/ruby_llm/models.failed.json, prints up to 10 errors (plus a count of the remainder), and exits 1; otherwise prints a pass message. Side effect: may create a failed-models dump file.

<a id="u-8a567ea1f9f5"></a>
### `models.rake module code (L1–L39)`

`module_region` · [lib/tasks/models.rake:L1-L39][f2]

Defines the `models` task and its `models:update`, `models:docs`, and `models:aliases` subtasks, plus a legacy `aliases:generate` alias.

`models:update` configures RubyLLM from ENV, refreshes the model registry, and prints stats; `models:docs` creates docs/_reference and writes generated markdown; `models:aliases` regenerates the alias file. All run in the rake process and depend on ENV keys being set for live refresh.

<a id="u-8a9da7de6813"></a>
### `release.rake module code (L1–L67)`

`module_region` · [lib/tasks/release.rake:L1-L67][f4]

Defines release:prepare (invokes cassette refresh, runs overcommit, then the models task) and two cassette-freshness tasks.

refresh_stale_cassettes deletes any spec/fixtures/vcr_cassettes/**/*.yml older than 1 day and, if any were removed, re-runs 'bundle exec rspec' via system, exiting 1 if the run fails; with no stale files it just reports success. verify_cassettes collects the same stale set and exits 1 listing them with ages and a remediation hint, or reports all fresh. Side effects: file deletion and a full test-suite run.

<a id="u-0fffeb0c8dbb"></a>
### `ruby_llm.rake module code (L1–L15)`

`module_region` · [lib/tasks/ruby_llm.rake:L1-L15][f5]

Defines ruby_llm:load_models (with :environment prerequisite): if RubyLLM.config.model_registry_class is set, loads models from JSON into the registry, constantizes the configured class, calls save_to_database, and prints the loaded count; otherwise prints guidance to run the install generator.

No error handling around constantize or save_to_database.

<a id="u-cf9c35016d96"></a>
### `delete_cassettes`

`def delete_cassettes(cassettes)` · [lib/tasks/vcr.rake:L64-L70][f3]

Deletes the given cassette files, printing each basename and a count first.

No error handling around File.delete; missing files would raise.

<a id="u-343a4e83e281"></a>
### `find_matching_cassettes`

`def find_matching_cassettes(dir, providers)` · [lib/tasks/vcr.rake:L46-L62][f3]

Returns cassette file paths whose basename contains a provider name as a delimited segment—matching either a leading segment before '_<provider>_' (e.g. chat_openai_...) or a middle '_<provider>_x_' pattern.

Globs <dir>/**/*.yml and stops at the first matching provider per file.

<a id="u-984cd01d6966"></a>
### `record_all_cassettes`

`def record_all_cassettes(cassette_dir)` · [lib/tasks/vcr.rake:L5-L12][f3]

Wipes and recreates the cassette directory, then runs the full test suite to re-record all cassettes, printing progress messages.

Destructive: rm_rf removes every existing cassette before recording.

<a id="u-20cff4ee712b"></a>
### `record_for_providers`

`def record_for_providers(providers, cassette_dir)` · [lib/tasks/vcr.rake:L14-L44][f3]

Re-records cassettes for given provider names.

Returns with usage help if the provider list is empty, or with an invalid-provider message if any name is not a known RubyLLM provider. Otherwise finds matching cassettes, deletes them if any (or notes none found), runs the test suite, and prints a reminder to review for sensitive data. Delegates to find_matching_cassettes, delete_cassettes, and run_tests.

<a id="u-d706b33dacce"></a>
### `run_tests`

`def run_tests` · [lib/tasks/vcr.rake:L72-L74][f3]

Runs 'bundle exec rspec' via system and aborts with 'Tests failed' if the command returns falsy.

Side effect: executes the full test suite as a subprocess.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/aliases.rb
[f2]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/tasks/models.rake
[f3]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/tasks/vcr.rake
[f4]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/tasks/release.rake
[f5]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/tasks/ruby_llm.rake

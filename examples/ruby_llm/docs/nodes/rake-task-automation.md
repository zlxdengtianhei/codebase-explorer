# Rake Task Automation

**Capability.** Defines rake tasks for model refresh, docs, aliases, release prep, database loading, and VCR cassette recording.

Observed units show maintenance and release automation tasks. They include model documentation/validation, alias generation, and cassette recording helpers.

Parent: [RubyLLM Multi-Provider Library](rubyllm-multi-provider-library.md)

## Units (17)

<a id="u-22fb7accc9c8"></a>
### `models.rake-anthropic-grouping-helpers`

`def group_anthropic_models_by_base_name(anthropic_models)` · [lib/tasks/models.rake:L436-L455][f1]

Group Anthropic model ids by base name and select the latest variant.

Base-name extraction strips a trailing eight-digit date suffix and otherwise leaves the id unchanged; date extraction returns that suffix or a zero date when absent. For a group with one model it keeps that model; for multiple models it picks the maximum by extracted date string.

<a id="u-219ce705bd99"></a>
### `models.rake-environment-configuration`

`def configure_from_env` · [lib/tasks/models.rake:L40-L54][f1]

Configures RubyLLM from environment variables with nil defaults for provider API keys, Vertex AI location/project, and Bedrock credentials/region/session token, then sets request timeout to 30 seconds.

Missing variables become nil; no validation or fallback is performed. The Bedrock helper only assigns its four AWS-related fields. Both mutate global RubyLLM configuration.

<a id="u-db12ee83c1a9"></a>
### `models.rake-markdown-section-generators`

`def generate_provider_sections` · [lib/tasks/models.rake:L183-L194][f1]

Produce Markdown sections for the model document.

Provider sections iterate known providers, skip providers with no models, and render a heading with count plus a model table. Capability sections cover function calling, structured output, streaming, and batch, skipping empty groups. Modality sections cover image input, audio input, PDF input, and embedding output, treating missing input modality lists as empty and skipping empty groups. Each generator joins non-empty sections with blank lines.

<a id="u-581c1db6b389"></a>
### `models.rake-model-stats-display`

`def display_model_stats` · [lib/tasks/models.rake:L107-L119][f1]

Prints per-provider model counts and configuration status after a refresh.

It groups the refreshed registry by provider, then iterates all known providers, using zero for absent counts and appending a status: local providers are marked skip before configuration is checked; otherwise configured providers are OK and unconfigured ones are not configured. It ends with a completion message. It assumes the refreshed registry instance variable is set.

<a id="u-5e5c8e0ff3a1"></a>
### `models.rake-model-table-rendering`

`def models_table(models)` · [lib/tasks/models.rake:L265-L292][f1]

Renders a Markdown table for a model collection, or a no-models placeholder when empty.

Rows are sorted by provider then name and show id, provider, context window or dash, max output tokens or dash, and standard text-token pricing. Pricing display reads standard text-token data, formats input, output, and cached input per million when present, omits missing parts, and returns a dash when no pricing parts exist.

<a id="u-07ce9acf2618"></a>
### `vcr.rake-cassette-matching-deletion-and-test-runner`

`def find_matching_cassettes(dir, providers)` · [lib/tasks/vcr.rake:L46-L62][f2]

Support helpers for provider cassette recording.

Matching scans YAML files and includes a file when its basename matches a provider in the first segment or in a middle segment, stopping after the first matching provider. Deletion prints each basename and deletes the file. The test runner executes the RSpec command and aborts with a failure message when the command fails.

<a id="u-a5e792432a29"></a>
### `find_best_bedrock_model`

`def find_best_bedrock_model(anthropic_model, bedrock_models) # rubocop:disable Metric…` · [lib/tasks/models.rake:L473-L525][f1]

Selects a Bedrock model id matching an Anthropic model.

It derives a base pattern, with special cases for Claude 2, Claude 2.1, and Claude Instant, otherwise using the Anthropic base name. It filters Bedrock ids after removing an optional 'us.' and 'anthropic.' prefix to those starting with the pattern; no matches returns nil. It tries to read the Anthropic model's context window, rescuing any error to nil. If a context window exists, it first returns a matching Bedrock id containing the corresponding ':Nk' or ':0:Nk' marker. Otherwise it chooses the minimum by a priority tuple: ids containing 'k' first, then larger context-k values, then larger version numbers. The rescue only covers the context lookup.

<a id="u-0081cfb6256d"></a>
### `generate_aliases`

`def generate_aliases # rubocop:disable Metrics/PerceivedComplexity` · [lib/tasks/models.rake:L314-L434][f1]

Builds provider alias mappings from the current registry and writes them as pretty JSON to the aliases file, printing the alias count.

It groups model ids by provider, then adds aliases by provider family; alias keys generally strip a trailing '-latest' except Anthropic base names. OpenRouter matching tries several dot/hyphen and version-separator variants.
- OpenAI and DeepSeek: aliases are created only when the matching OpenRouter id exists.
- Anthropic: models are grouped by base name and the latest dated variant is chosen; the guard also accepts the Anthropic model itself, which is always present, so every grouped Anthropic base name gets an alias, with OpenRouter and Bedrock mappings added only when found.
- Bedrock Anthropic ids not already aliased: create aliases from their parsed base name, adding Anthropic/OpenRouter mappings when present.
- Gemini: aliases require an OpenRouter variant or the same id in Vertex AI.
- Vertex AI models already present in Gemini: skipped; for the remaining ones the same-model Gemini check is therefore always nil, so only an OpenRouter variant can satisfy the guard.
Later assignments can overwrite earlier aliases except where an explicit skip exists. Side effects are file write and stdout.

<a id="u-41fcabd90960"></a>
### `generate_models_markdown`

`def generate_models_markdown` · [lib/tasks/models.rake:L132-L181][f1]

Builds the available-models Markdown document as a string.

It emits front matter, table of contents, data-source notes, a UTC last-updated date, and interpolates provider, capability, and modality sections. It does not write the file; the caller handles persistence. The date is taken at generation time.

<a id="u-1536c212ef1c"></a>
### `refresh_models`

`def refresh_models` · [lib/tasks/models.rake:L63-L83][f1]

Refreshes the model registry and decides whether to validate and persist it.

It records the cached count, calls refresh, then:
- refreshed list empty and initial count zero: prints an error and exits 1.
- refreshed count equals a positive initial count: prints an unchanged warning and skips validation/save.
- otherwise: validates and saves JSON.
A positive initial count with an empty refreshed list falls through to validation/save. When it does not exit, it assigns the refreshed registry to an instance variable. Side effects are stdout, possible exit, JSON save, and instance state.

<a id="u-1420b00ee526"></a>
### `validate_models!`

`def validate_models!(models)` · [lib/tasks/models.rake:L85-L105][f1]

Validates all refreshed models against the registry JSON schema.

It converts each model to a hash, runs full schema validation, and on any errors writes pretty-printed model data to a failed-models file, prints the first ten errors plus a count of remaining errors, and exits 1. On success it prints a pass message. Side effects are file write, stdout, and possible process exit.

<a id="u-8a567ea1f9f5"></a>
### `models.rake module code (L1–L39)`

`module_region` · [lib/tasks/models.rake:L1-L39][f1]

Defines the aggregate models task and the models/aliases namespaces that drive model refresh, documentation, and alias generation.

The aggregate task declares update, docs, and aliases as prerequisites; update prints, configures from environment, refreshes, and displays stats; docs creates the reference directory, writes generated markdown, and prints the path; aliases calls alias generation. A compatibility task maps alias generation to the models alias task. Only the update task configures from environment and refreshes; docs and aliases do not. Side effects include stdout, file writes, and possible process exit from refresh/validation.

<a id="u-8a9da7de6813"></a>
### `release.rake module code (L1–L67)`

`module_region` · [lib/tasks/release.rake:L1-L67][f3]

Defines release preparation and cassette freshness tasks.

Preparation invokes stale-cassette refresh, runs overcommit, then invokes the aggregate models task. Stale refresh deletes cassette files older than one day, then runs the test suite if any were deleted; a test failure exits 1. Verification scans for cassettes older than one day, lists them and exits 1 if any exist, otherwise reports all fresh. Both freshness tasks use file modification time and a one-day threshold.

<a id="u-0fffeb0c8dbb"></a>
### `ruby_llm.rake module code (L1–L15)`

`module_region` · [lib/tasks/ruby_llm.rake:L1-L15][f4]

Defines a Rails-environment task that loads models from JSON into the configured database registry.

If a model registry class is configured, it loads JSON, constantizes the class, saves models to the database, and prints the count; otherwise it prints an installation hint. Database side effects occur only in the configured branch.

<a id="u-984cd01d6966"></a>
### `record_all_cassettes`

`def record_all_cassettes(cassette_dir)` · [lib/tasks/vcr.rake:L5-L12][f2]

Deletes and recreates the cassette directory, then runs the test suite to record all provider cassettes.

It prints start and completion messages; if the test runner aborts, the completion message is not reached. Side effects are directory removal/recreation and test execution.

<a id="u-20cff4ee712b"></a>
### `record_for_providers`

`def record_for_providers(providers, cassette_dir)` · [lib/tasks/vcr.rake:L14-L44][f2]

Records cassettes for selected providers.

It compares requested providers against known provider keys:
- empty request: prints usage and available providers, then returns.
- any invalid provider: prints invalid and available lists, then returns.
- otherwise: finds matching cassettes; if none exist it prints that and runs tests, otherwise it deletes matches and runs tests.
It finishes with a review reminder. No deletion occurs when no cassettes match.

<a id="u-d6775079b96e"></a>
### `vcr.rake module code (L74–L92)`

`module_region` · [lib/tasks/vcr.rake:L74-L92][f2]

Defines the VCR record task.

It normalizes provider arguments by taking the first provider plus extras, compacting, and downcasing, ensures the cassette directory exists, then routes to all-provider recording when 'all' is present or to selected-provider recording otherwise. It requires file utilities and the library inside the task.

Look up code: the commands are under "Read further" in [INDEX.md](../INDEX.md); `cbe query` and `cbe source` take a unit title or anchor from this page.

[f1]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/tasks/models.rake
[f2]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/tasks/vcr.rake
[f3]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/tasks/release.rake
[f4]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/tasks/ruby_llm.rake

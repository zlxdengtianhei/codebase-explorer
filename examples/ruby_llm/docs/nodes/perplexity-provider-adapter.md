# Perplexity provider adapter

**Capability.** Implements the Perplexity provider: fixed API base and headers, hardcoded model list, and sonar-family capability, pricing, and display-name lookups.

A self-contained OpenAI-compatible adapter for Perplexity. Notable because the model list is served from a hardcoded registry rather than an API call, and pricing includes citation and reasoning surcharges.

Parent: [Per-Provider Capability Lookups](per-provider-capability-lookups.md)

## Units (9)

<a id="u-2af5075a0030"></a>
### `capabilities.rb-perplexity-context-and-token-limits`

`def context_window_for(model_id)` · [lib/ruby_llm/providers/perplexity/capabilities.rb:L10-L15][f1]

Returns fixed limits by ID: sonar-pro gets a 200,000 context window; everything else 128,000.

Max tokens is 8,192 for sonar-pro and sonar-reasoning-pro, otherwise 4,096.

<a id="u-0f9e4feb1feb"></a>
### `capabilities.rb-perplexity-feature-predicates`

`def supports_vision?(model_id)` · [lib/ruby_llm/providers/perplexity/capabilities.rb:L32-L37][f1]

Vision is true for any ID matching sonar, sonar-pro, sonar-reasoning, or sonar-reasoning-pro, false otherwise.

Function calling is never supported. JSON mode is supported for all IDs.

<a id="u-1dcddb4a6ce2"></a>
### `capabilities.rb-perplexity-modalities-and-capabilities`

`def modalities_for(_model_id)` · [lib/ruby_llm/providers/perplexity/capabilities.rb:L76-L81][f1]

All models are text-in/text-out.

capabilities_for starts with streaming and json_mode and adds vision when supports_vision? is true for the ID.

<a id="u-5122038b3b06"></a>
### `capabilities.rb-perplexity-names-type-and-family`

`def format_display_name(model_id)` · [lib/ruby_llm/providers/perplexity/capabilities.rb:L47-L59][f1]

format_display_name maps the five known sonar IDs to friendly names, defaulting to hyphen-split capitalization.

model_type always returns 'chat'. model_family maps exact ID strings to symbols (:sonar, :sonar_pro, :sonar_reasoning, :sonar_reasoning_pro, :sonar_deep_research), defaulting to :unknown — note the family match is exact, so versioned IDs fall to :unknown.

<a id="u-29e693c4260c"></a>
### `capabilities.rb-perplexity-price-lookups`

`def input_price_for(model_id)` · [lib/ruby_llm/providers/perplexity/capabilities.rb:L24-L26][f1]

Resolves per-million input and output prices by exact model family from the frozen PRICES hash, falling back to 1.0 for both when the family is unknown.

<a id="u-844526483931"></a>
### `models.rb-perplexity-static-model-catalog`

`def list_models(**)` · [lib/ruby_llm/providers/perplexity/models.rb:L8-L12][f2]

Serves a hardcoded Perplexity model list instead of an API call: list_models ignores all arguments and calls parse_list_models_response(nil, 'perplexity', Perplexity::Capabilities), which builds Model::Info for sonar, sonar-pro, sonar-reasoning, sonar-reasoning-pro, and sonar-deep-research via create_model_info.

create_model_info fills display name, family (to_s), context window, max tokens, modalities, capabilities, and pricing from the capabilities module, and stamps created_at as Time.now (not a real release date).

<a id="u-9b2b17fcd7d9"></a>
### `perplexity.rb-perplexity-provider`

`class Perplexity < OpenAI` · [lib/ruby_llm/providers/perplexity.rb:L6-L10][f3]

OpenAI-compatible Perplexity provider with Chat and Models modules, fixed api_base https://api.perplexity.ai, and headers carrying Bearer auth plus an explicit JSON Content-Type.

`parse_error` returns nil for an empty body; when the body is HTML (Perplexity's auth-error format, detected by containing '<html>' and '<title>'), it extracts the <title> text, strips a leading status code and spaces, and returns it; otherwise it defers to super. Class capabilities returns Perplexity::Capabilities; configuration requires :perplexity_api_key.

<a id="u-512e5bf33f98"></a>
### `RubyLLM.Providers.Perplexity.Capabilities.pricing_for`

`def pricing_for(model_id)` · [lib/ruby_llm/providers/perplexity/capabilities.rb:L89-L107][f1]

Builds {text_tokens: {standard: {...}}} from the family's PRICES entry (defaulting to 1.0/1.0 for unknown families): input_per_million and output_per_million always, plus citation_per_million, reasoning_per_million, and search_per_thousand only when the family entry defines them (only sonar_deep_research does).

<a id="u-95f14c24e10f"></a>
### `RubyLLM.Providers.Perplexity.Chat.format_role`

`def format_role(role)` · [lib/ruby_llm/providers/perplexity/chat.rb:L10-L12][f4]

Perplexity chat role formatter: converts the role symbol to its string form via to_s.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/providers/perplexity/capabilities.rb
[f2]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/providers/perplexity/models.rb
[f3]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/providers/perplexity.rb
[f4]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/providers/perplexity/chat.rb

# Perplexity Adapter

**Capability.** Perplexity subclasses OpenAI with sonar-specific family/display-name tables, constant text-only modalities, fixed capability lists, and pricing/limit lookups.

Use this subtree for sonar model metadata; unknown ids map to :unknown so PRICES lookups fall back.

**Depends on.**

- [OpenAI Adapter](r1-openai-core.md) · model-inferred · 0 edge(s)

Parent: [OpenAI Family](r1-openai-family.md)

## Units (6)

<a id="u-c4e49a066541"></a>
### `Perplexity`

`class Perplexity < OpenAI` · [lib/ruby_llm/providers/perplexity.rb:L6-L10][f1]

Perplexity subclasses OpenAI and includes Perplexity::Chat and Models.

api_base is the constant 'https://api.perplexity.ai'. headers sends Authorization bearer from @config.perplexity_api_key plus a fixed Content-Type 'application/json'. parse_error returns nil for an empty body; when the body contains both '<html>' and '<title>' (Perplexity serves HTML on auth errors) it extracts the first <title> text, strips a leading numeric prefix followed by whitespace via sub(/^\d+\s+/, ''), and returns that message; in every other case, including HTML without a title match, it falls back to the OpenAI parent's parse_error via super. Singleton capabilities returns Perplexity::Capabilities; configuration_requirements lists only :perplexity_api_key.

**Notes.**

- failure: An HTML error page whose <title> cannot be matched falls through to super instead of returning a message.

inherits: [OpenAI](r1-openai-core.md#u-cbb3f359bee0)

<a id="u-99c09184c013"></a>
### `perplexity-capabilities-rb-limits-prices`

`def context_window_for(model_id)` · [lib/ruby_llm/providers/perplexity/capabilities.rb:L10-L15][f2]

Token limits and pricing lookups.

context_window_for gives 200,000 for ids matching /sonar-pro/ and 128,000 otherwise; max_tokens_for gives 8,192 for /sonar-(?:pro|reasoning-pro)/ and 4,096 otherwise. input_price_for and output_price_for read PRICES via model_family (Symbol keys, so lookups match) with a literal 1.0 fallback. pricing_for fetches the family's PRICES entry (fallback {input: 1.0, output: 1.0}) and builds text_tokens.standard with input_per_million/output_per_million, conditionally adding citation_per_million, reasoning_per_million, and search_per_thousand when the family defines :citation, :reasoning, or :search_queries (only sonar_deep_research does).

calls: [RubyLLM.Providers.Perplexity.Capabilities.model_family](r1-perplexity-adapter.md#u-1132c3746ec8)

<a id="u-8624f23c98d0"></a>
### `perplexity-capabilities-rb-model-profile`

`def modalities_for(_model_id)` · [lib/ruby_llm/providers/perplexity/capabilities.rb:L76-L81][f2]

Constant modalities ({input: ['text'], output: ['text']} for every id) and capabilities: ['streaming', 'json_mode'] plus 'vision' exactly when supports_vision?(model_id) is true.

calls: [perplexity-capabilities-rb-predicates](r1-perplexity-adapter.md#u-87d6690c36a8)

<a id="u-87d6690c36a8"></a>
### `perplexity-capabilities-rb-predicates`

`def supports_vision?(model_id)` · [lib/ruby_llm/providers/perplexity/capabilities.rb:L32-L37][f2]

Capability predicates.

supports_vision? is true for every id whose case matches sonar variants (ordered /sonar-reasoning-pro/, /sonar-reasoning/, /sonar-pro/, /sonar/), false for anything else — the final /sonar/ branch makes the earlier ones redundant for true results. supports_functions? is always false. supports_json_mode? is always true. model_type always returns 'chat'.

<a id="u-99122b852302"></a>
### `RubyLLM.Providers.Perplexity.Capabilities.format_display_name`

`def format_display_name(model_id)` · [lib/ruby_llm/providers/perplexity/capabilities.rb:L47-L59][f2]

Exact-match table for the five sonar ids ('sonar' through 'sonar-deep-research') to their display names; any other id is split on '-', capitalized per part, and joined with spaces.

<a id="u-1132c3746ec8"></a>
### `RubyLLM.Providers.Perplexity.Capabilities.model_family`

`def model_family(model_id)` · [lib/ruby_llm/providers/perplexity/capabilities.rb:L65-L74][f2]

Exact-match table mapping the five sonar ids to Symbols (:sonar, :sonar_pro, :sonar_reasoning, :sonar_reasoning_pro, :sonar_deep_research); every other id becomes :unknown, so PRICES lookups for unknown ids miss and fall back.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/providers/perplexity.rb
[f2]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/providers/perplexity/capabilities.rb
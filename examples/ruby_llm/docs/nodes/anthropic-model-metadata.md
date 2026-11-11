# Anthropic model metadata

**Capability.** Resolves Anthropic model ids to families and provides fixed context limits, capability booleans, pricing, and the models-list endpoint parsing.

Visit for Anthropic model metadata: regex-based family mapping for Claude 2/3 variants, per-family pricing with batch discounts, and the models list URL plus Model::Info parsing. Extended-thinking support is gated on claude-3-7-sonnet.

Parent: [Per-Provider Capability Lookups](per-provider-capability-lookups.md)

## Units (7)

<a id="u-ddcd02fb4c67"></a>
### `capabilities.rb-anthropic-context-and-token-limits`

`def determine_context_window(_model_id)` · [lib/ruby_llm/providers/anthropic/capabilities.rb:L10-L12][f1]

Returns fixed context-window and max-output-token limits for Anthropic model IDs.

Context window is always 200,000. Max tokens is 8,192 for IDs matching claude-3-7-sonnet or claude-3-5, otherwise 4,096.

<a id="u-6a5fcb6458f0"></a>
### `capabilities.rb-anthropic-family-and-type`

`def model_family(model_id)` · [lib/ruby_llm/providers/anthropic/capabilities.rb:L45-L55][f1]

model_family maps an ID to a family string via ordered regex cases (claude-3-7-sonnet, claude-3-5-sonnet, claude-3-5-haiku, claude-3-opus, claude-3-sonnet, claude-3-haiku), defaulting to 'claude-2'.

model_type always returns 'chat' regardless of input.

<a id="u-e642ffe3cae8"></a>
### `capabilities.rb-anthropic-feature-predicates`

`def supports_vision?(model_id)` · [lib/ruby_llm/providers/anthropic/capabilities.rb:L29-L31][f1]

Boolean capability checks keyed on ID regexes: vision is true unless the ID matches claude-[12]; functions and JSON mode require claude-3; extended thinking requires claude-3-7-sonnet.

<a id="u-0a8802d2ab7d"></a>
### `capabilities.rb-anthropic-modalities-and-capabilities`

`def modalities_for(model_id)` · [lib/ruby_llm/providers/anthropic/capabilities.rb:L78-L90][f1]

Builds modality and capability lists from ID regexes.

Base modalities are text in/out; image and pdf inputs are added unless the ID matches claude-[12]. Capabilities start with 'streaming'; claude-3 adds function_calling and batch; reasoning is added for claude-3-7 or -4; citations for claude-3.5 or claude-3-7 (note the dot vs hyphen patterns differ).

<a id="u-74d4d9dd3a40"></a>
### `capabilities.rb-anthropic-price-lookups`

`def get_input_price(model_id)` · [lib/ruby_llm/providers/anthropic/capabilities.rb:L21-L23][f1]

Resolves per-million input and output prices by mapping the model ID to a family via model_family, then digging the family's price from the frozen PRICES hash; falls back to defaults (input 3.0, output 15.0) when the family is absent.

<a id="u-9a70399f9e67"></a>
### `models.rb-anthropic-models-listing-and-usage-extraction`

`def models_url` · [lib/ruby_llm/providers/anthropic/models.rb:L10-L12][f2]

Provides the Anthropic models list URL, converts the API's model list into Model::Info records, and extracts model id and token-usage fields from message payloads.

models_url is '/v1/models'. parse_list_models_response maps response.body['data'] (Array() coerces nil to empty) to Model::Info using the passed capabilities object for family, context window, max tokens, modalities, capabilities, and pricing, with Time.parse of 'created_at'. extract_model_id digs 'message'.'model'. extract_input_tokens digs message.usage.input_tokens. extract_output_tokens and extract_cached_tokens each try message.usage first, then top-level usage. extract_cache_creation_tokens tries cache_creation_input_tokens at either location; failing that, if the cache_creation entry is a Hash it sums its compacted values, else returns nil.

calls: [determine_context_window](../../catalog.json.gz), [determine_max_tokens](../../catalog.json.gz)

<a id="u-216602ceefeb"></a>
### `RubyLLM.Providers.Anthropic.Capabilities.pricing_for`

`def pricing_for(model_id)` · [lib/ruby_llm/providers/anthropic/capabilities.rb:L105-L130][f1]

Builds a nested pricing hash: standard and batch per-million prices from the family's PRICES entry (batch at 50%), defaulting to 3.0/15.0 for unknown families.

For claude-3-7 IDs it adds reasoning_output_per_million at 2.5x output for standard and 1.25x for batch. Result shape is {text_tokens: {standard:, batch:}}.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/providers/anthropic/capabilities.rb
[f2]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/providers/anthropic/models.rb

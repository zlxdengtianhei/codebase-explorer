# DeepSeek Adapter

**Capability.** DeepSeek subclasses OpenAI and overrides capabilities: a two-family model (reasoner/chat), token limits, per-token prices, display names, and model profile builders.

Use this subtree for DeepSeek-specific model metadata; everything else inherits from OpenAI.

**Depends on.**

- [OpenAI Adapter](r1-openai-core.md) · model-inferred · 0 edge(s)

Parent: [OpenAI Family](r1-openai-family.md)

## Units (6)

<a id="u-72a37c66707b"></a>
### `DeepSeek`

`class DeepSeek < OpenAI` · [lib/ruby_llm/providers/deepseek.rb:L6-L9][f1]

DeepSeek subclasses OpenAI (inheriting OpenAI's mixins and request behavior) and includes DeepSeek::Chat.

api_base is the constant 'https://api.deepseek.com'. headers returns only an Authorization bearer header built from @config.deepseek_api_key, dropping OpenAI's organization/project headers and header filtering. Singleton capabilities returns DeepSeek::Capabilities; configuration_requirements lists only :deepseek_api_key.

inherits: [OpenAI](r1-openai-core.md#u-cbb3f359bee0)

**Uncertainties.**

- All chat/request behavior is inherited from OpenAI and DeepSeek::Chat, outside this file.

<a id="u-b75a76e66d00"></a>
### `deepseek-capabilities-rb-limits-prices`

`def context_window_for(model_id)` · [lib/ruby_llm/providers/deepseek/capabilities.rb:L10-L15][f2]

Token limits, per-token prices, and family-based lookups for DeepSeek.

context_window_for gives 64,000 for ids matching /deepseek-(?:chat|reasoner)/ and 32,768 otherwise; max_tokens_for gives 8,192 for that same match and 4,096 otherwise. model_family maps /deepseek-reasoner/ to :reasoner and everything else to :chat. input_price_for reads PRICES[family][:input_miss], output_price_for reads [:output], cache_hit_price_for reads [:input_hit], each falling back to the literals 0.27, 1.10, and 0.07 via the default_* methods. model_type always returns 'chat'.

calls: [RubyLLM.Providers.DeepSeek.Capabilities.model_family](r1-deepseek-adapter.md#u-db782950f4f4)

<a id="u-f248e7587f2e"></a>
### `deepseek-capabilities-rb-model-info`

`def modalities_for(_model_id)` · [lib/ruby_llm/providers/deepseek/capabilities.rb:L95-L100][f2]

Model profile builders.

modalities_for returns a constant {input: ['text'], output: ['text']} regardless of id. capabilities_for starts from ['streaming'] and appends 'function_calling' only for ids matching /deepseek-chat/. pricing_for resolves the family, fetches PRICES with a fallback {input_miss: 0.27, output: 1.10}, and builds standard pricing of input_per_million (input_miss) and output_per_million; when the family has an :input_hit value it additionally adds cached_input_per_million. The result is nested under text_tokens.standard; no batch pricing is produced.

calls: [RubyLLM.Providers.DeepSeek.Capabilities.model_family](r1-deepseek-adapter.md#u-db782950f4f4)

<a id="u-c47d5ce1a308"></a>
### `deepseek-capabilities-rb-predicates`

`def supports_vision?(_model_id)` · [lib/ruby_llm/providers/deepseek/capabilities.rb:L36-L38][f2]

Capability predicates.

supports_vision? is always false for every model id. supports_functions? is true only for ids containing 'deepseek-chat'. supports_json_mode? is always false.

<a id="u-0afbf6b0f7b5"></a>
### `RubyLLM.Providers.DeepSeek.Capabilities.format_display_name`

`def format_display_name(model_id)` · [lib/ruby_llm/providers/deepseek/capabilities.rb:L48-L57][f2]

Maps ids to display names: exactly 'deepseek-chat' becomes 'DeepSeek V3' and 'deepseek-reasoner' becomes 'DeepSeek R1'; any other id is split on '-', each part capitalized, and joined with spaces.

<a id="u-db782950f4f4"></a>
### `RubyLLM.Providers.DeepSeek.Capabilities.model_family`

`def model_family(model_id)` · [lib/ruby_llm/providers/deepseek/capabilities.rb:L63-L68][f2]

Returns :reasoner for ids matching /deepseek-reasoner/ and :chat for everything else, as Symbols suitable for direct PRICES lookups.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/providers/deepseek.rb
[f2]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/providers/deepseek/capabilities.rb
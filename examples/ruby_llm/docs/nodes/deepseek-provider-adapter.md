# DeepSeek provider adapter

**Capability.** Implements the DeepSeek provider: fixed API base and auth header, ID-regex capability and limit lookups, pricing, and a role-stringifying chat formatter.

A small OpenAI-compatible adapter for DeepSeek chat and reasoner models. Capabilities are static per ID pattern (no vision or JSON mode; function calling only for deepseek-chat).

Parent: [Per-Provider Capability Lookups](per-provider-capability-lookups.md)

## Units (8)

<a id="u-6ecaaf7c865c"></a>
### `capabilities.rb-deepseek-context-and-token-limits`

`def context_window_for(model_id)` · [lib/ruby_llm/providers/deepseek/capabilities.rb:L10-L15][f1]

Returns fixed limits by ID regex: deepseek-chat and deepseek-reasoner get a 64,000-token context window and 8,192 max tokens; all other IDs get 32,768 and 4,096.

<a id="u-b4b5135ab3da"></a>
### `capabilities.rb-deepseek-feature-predicates`

`def supports_vision?(_model_id)` · [lib/ruby_llm/providers/deepseek/capabilities.rb:L36-L38][f1]

DeepSeek models support neither vision nor JSON mode (always false regardless of ID); function calling is true only for IDs matching deepseek-chat.

<a id="u-4e7ddfce2af9"></a>
### `capabilities.rb-deepseek-modalities-and-capabilities`

`def modalities_for(_model_id)` · [lib/ruby_llm/providers/deepseek/capabilities.rb:L95-L100][f1]

All DeepSeek models are text-in/text-out.

Capabilities start with 'streaming' and add 'function_calling' only for deepseek-chat IDs; nothing else is added.

<a id="u-2656971c24d7"></a>
### `capabilities.rb-deepseek-names-type-and-family`

`def format_display_name(model_id)` · [lib/ruby_llm/providers/deepseek/capabilities.rb:L48-L57][f1]

format_display_name maps deepseek-chat to 'DeepSeek V3' and deepseek-reasoner to 'DeepSeek R1'; other IDs are hyphen-split and capitalized.

model_type always returns 'chat'. model_family returns :reasoner for deepseek-reasoner IDs and :chat for everything else.

<a id="u-8e6e483a1071"></a>
### `capabilities.rb-deepseek-price-lookups`

`def input_price_for(model_id)` · [lib/ruby_llm/providers/deepseek/capabilities.rb:L24-L26][f1]

Resolves per-million prices by family (:chat or :reasoner).

Input price uses the input_miss key (cache miss), cache-hit price the input_hit key, and output the output key, each falling back to defaults (0.27 miss input, 1.10 output, 0.07 cache hit) when the family entry is missing.

<a id="u-4cd167fc4442"></a>
### `deepseek.rb-deepseek-provider`

`class DeepSeek < OpenAI` · [lib/ruby_llm/providers/deepseek.rb:L6-L9][f2]

OpenAI-compatible provider for DeepSeek: fixed api_base https://api.deepseek.com and a Bearer header from deepseek_api_key, plus the DeepSeek::Chat module.

Class-level capabilities returns DeepSeek::Capabilities; configuration requires :deepseek_api_key.

<a id="u-e5b06da20fbe"></a>
### `RubyLLM.Providers.DeepSeek.Capabilities.pricing_for`

`def pricing_for(model_id)` · [lib/ruby_llm/providers/deepseek/capabilities.rb:L110-L126][f1]

Builds {text_tokens: {standard: {...}}} using the family's PRICES entry (or defaults for unknown families): input_per_million from input_miss, output_per_million from output.

When the entry has an input_hit price it adds cached_input_per_million; there is no batch pricing.

<a id="u-37e1aa41e1ae"></a>
### `RubyLLM.Providers.DeepSeek.Chat.format_role`

`def format_role(role)` · [lib/ruby_llm/providers/deepseek/chat.rb:L10-L12][f3]

DeepSeek chat role formatter: converts the role symbol to its string form via to_s.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/providers/deepseek/capabilities.rb
[f2]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/providers/deepseek.rb
[f3]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/providers/deepseek/chat.rb

# OpenAI Adapter

**Capability.** The OpenAI provider class with mixins, plus capabilities logic (family detection, context/max tokens, modalities, pricing, display names, temperature normalization) keyed on model-id regexes.

Read the provider class to see the mixin composition; use Capabilities methods to derive per-model context windows, token limits, pricing, and capability lists.

**Depended on by.**

- [DeepSeek Adapter](r1-deepseek-adapter.md) · model-inferred · 0 edge(s)
- [Mistral Adapter](r1-mistral-adapter.md) · model-inferred · 0 edge(s)
- [Perplexity Adapter](r1-perplexity-adapter.md) · model-inferred · 0 edge(s)

Parent: [OpenAI Family](r1-openai-family.md)

## Units (11)

<a id="u-cbb3f359bee0"></a>
### `OpenAI`

`class OpenAI < Provider` · [lib/ruby_llm/providers/openai.rb:L6-L17][f1]

OpenAI subclasses Provider and includes Chat, Embeddings, Models, Moderation, Streaming, Tools, Images, Media, and Transcription.

api_base prefers @config.openai_api_base and falls back to 'https://api.openai.com/v1'. headers builds Authorization bearer from @config.openai_api_key plus OpenAI-Organization and OpenAI-Project from their config values, then compacts, so unset optional values are omitted but a nil API key still yields a nil Authorization entry. maybe_normalize_temperature delegates to OpenAI::Capabilities.normalize_temperature(temperature, model.id). Singleton capabilities returns OpenAI::Capabilities; configuration_requirements lists only :openai_api_key.

calls: [RubyLLM.Providers.OpenAI.Capabilities.normalize_temperature](r1-openai-core.md#u-0b2a636e88ec); inherits: [provider.rb-provider-instance](r2-provider-base.md#u-961fc10a6a0f)

**Uncertainties.**

- The exact normalization rules in Capabilities.normalize_temperature lie outside this batch.

<a id="u-1b26134a08d8"></a>
### `capabilities-rb-family-and-pricing`

`def model_family(model_id)` · [lib/ruby_llm/providers/openai/capabilities.rb:L149-L154][f2]

Family detection and price lookup.

MODEL_PATTERNS is a frozen hash of family symbol → Regexp; model_family iterates it in insertion order and returns the first matching family name as a string, or 'other' when nothing matches — earlier entries win for overlapping ids (e.g. gpt-4o-mini variants precede gpt4o). PRICES is a frozen hash of family → per-million price data; chat models use :input/:output, some add :cached_input or audio prices, while embedding/tts/whisper/moderation use a single :price. input_price_for and output_price_for fetch the family's prices (defaulting the whole hash to {input: 0.50} / {output: 1.50} for unknown families), then fall back through :input||:price||default and :output||:price||default. cached_input_price_for returns the family's :cached_input or nil. default_input_price/default_output_price return the 0.50/1.50 constants used for unknown families.

**Notes.**

- contract: PRICES contains a gpt45 entry, but no MODEL_PATTERNS regex yields the family 'gpt45', so its prices are unreachable through model_family.

<a id="u-aff276460461"></a>
### `capabilities-rb-support-predicates`

`def supports_vision?(model_id)` · [lib/ruby_llm/providers/openai/capabilities.rb:L81-L88][f2]

Four boolean capability predicates, each delegating to model_family and returning per-family results.

supports_vision? is true for gpt-5/gpt-4.1/chatgpt-4o/gpt-4/turbo/4o/4o-mini/o1/o1-pro/moderation and 4o-search families, false otherwise. supports_functions? is true for gpt-5, gpt-4.1, gpt-4/turbo, 4o, 4o-mini, o1, o1-pro, o3-mini; false for chatgpt4o, gpt-3.5-turbo, o1-mini, tts/transcribe/search families; false for anything else. supports_structured_output? is true for gpt-5, gpt-4.1, chatgpt4o, 4o, 4o-mini, o1, o1-pro, o3-mini; false otherwise. supports_json_mode? simply calls supports_structured_output?, so both share identical results.

**Uncertainties.**

- supports_vision? marks the 'moderation' family as vision-capable, which may be intentional or a listing artifact; the source gives no rationale.

<a id="u-8663d176d59f"></a>
### `capabilities-rb-display-name-formatting`

`def format_display_name(model_id)` · [lib/ruby_llm/providers/openai/capabilities.rb:L192-L195][f2]

Turns a raw model id into a human display name.

format_display_name pipes the id through humanize then apply_special_formatting. humanize replaces hyphens with spaces and capitalizes each word. apply_special_formatting then runs a chain of gsubs: collapses date-like 'YYYY MM DD' groups into one token; rewrites leading 'Gpt', 'Chatgpt', 'Tts', 'Dall E' via special_prefix_format (GPT-, ChatGPT-, TTS-, DALL-E-); turns leading 'O1 '/'O3 ' into 'O1-'/'O3-'; hyphenates 'O1 Mini'/'O3 Mini' and version-number prefixes like '4.5'; hyphenates '4o' before Mini/Preview/Turbo/Audio/Realtime/Transcribe/Tts; uppercases a standalone 'Hd' to 'HD'; hyphenates 'Omni/Text Moderation'; and lowercases 'Text Embedding' to 'text-embedding-'. Cases with no matching prefix return nil from special_prefix_format, leaving the name untouched by that gsub (String#gsub with a nil block result keeps the match).

<a id="u-8f01e95afa47"></a>
### `RubyLLM.Providers.OpenAI.Capabilities.capabilities_for`

`def capabilities_for(model_id) # rubocop:disable Metrics/PerceivedComplexity` · [lib/ruby_llm/providers/openai/capabilities.rb:L256-L272][f2]

Derives a list of capability strings from regex matches on the raw model id and the support predicates.

'streaming' is added unless the id matches /moderation|embedding/; 'function_calling' if supports_functions?; 'structured_output' if supports_json_mode?; 'batch' if the id matches /embedding|batch/; 'reasoning' if /o\d|gpt-5|codex/. Only when the id matches /gpt-4-turbo|gpt-4o/ are 'image_generation' (id contains 'vision') and 'speech_generation'/'transcription' (id contains 'audio') considered. Returns the accumulated array, possibly empty. Note 'reasoning' matches any id containing the substring 'o' followed by a digit (e.g. 'gpt-4o' qualifies).

calls: [capabilities-rb-support-predicates](r1-openai-core.md#u-aff276460461)

<a id="u-6393b43fdd5e"></a>
### `RubyLLM.Providers.OpenAI.Capabilities.context_window_for`

`def context_window_for(model_id)` · [lib/ruby_llm/providers/openai/capabilities.rb:L47-L61][f2]

Maps an OpenAI model id to its context window size in tokens via model_family.

Each case branch returns a fixed limit: gpt-4.1 family 1,047,576; gpt-5/chatgpt-4o/turbo/4o family and o1-mini 128,000; gpt4 8,192; gpt4o_mini_transcribe 16,000; o1/o1-pro/o3-mini 200,000; gpt-3.5-turbo 16,385. Audio/tts/whisper/moderation/embedding families return nil (no context window). Any unmatched family falls back to 4,096. Outcome depends entirely on model_family's regex matching, so ids outside MODEL_PATTERNS get the 4,096 default.

calls: [capabilities-rb-family-and-pricing](r1-openai-core.md#u-1b26134a08d8)

**Uncertainties.**

- The branch listing includes 'gpt4o_mini_search', which no MODEL_PATTERNS regex produces, so that value is unreachable from pattern-derived families.

<a id="u-6ba30631f4d8"></a>
### `RubyLLM.Providers.OpenAI.Capabilities.max_tokens_for`

`def max_tokens_for(model_id)` · [lib/ruby_llm/providers/openai/capabilities.rb:L63-L79][f2]

Maps an OpenAI model id to its maximum output tokens via model_family.

Branch outcomes: gpt-5 family 400,000; gpt-4.1 family 32,768; chatgpt-4o/4o/4o-mini (and the unreachable 'gpt4o_mini_search') plus babbage/davinci 16,384; gpt4 8,192; gpt-3.5-turbo 4,096; gpt-4-turbo and realtime variants 4,096; gpt4o_mini_transcribe 2,000; o1/o1-pro/o3-mini 100,000; o1-mini 65,536. Audio/tts/whisper/moderation/embedding families return nil. Unknown families default to 16,384.

calls: [capabilities-rb-family-and-pricing](r1-openai-core.md#u-1b26134a08d8)

<a id="u-f450f6a19b0c"></a>
### `RubyLLM.Providers.OpenAI.Capabilities.modalities_for`

`def modalities_for(model_id)` · [lib/ruby_llm/providers/openai/capabilities.rb:L238-L254][f2]

Builds an input/output modality list for a model id.

Starts with text→text. Input gains 'image' and 'pdf' when supports_vision? is true, and 'audio' when the id matches /whisper|audio|tts|transcribe/. Output gains 'audio' if the id matches /tts|audio/, 'image' if /dall-e|image/, 'embeddings' if /embedding/, 'moderation' if /moderation/. Matching is on the raw id string, not the family, so ids like 'gpt-4o-audio' add audio to both sides.

calls: [capabilities-rb-support-predicates](r1-openai-core.md#u-aff276460461)

<a id="u-5c9fd553fe1a"></a>
### `RubyLLM.Providers.OpenAI.Capabilities.model_type`

`def model_type(model_id)` · [lib/ruby_llm/providers/openai/capabilities.rb:L174-L182][f2]

Classifies a model id into a coarse type string using model_family.

Matching is case-based on the family: families containing 'embedding' → 'embedding'; family matching /^tts|whisper|gpt4o_(?:mini_)?(?:transcribe|tts)$/ → 'audio'; family 'moderation' → 'moderation'; families containing 'dall' → 'image'; everything else → 'chat'. Note the tts regex alternation means any family starting with 'tts' or containing 'whisper' is audio; other families (e.g. gpt4o_audio) fall through to 'chat'.

calls: [capabilities-rb-family-and-pricing](r1-openai-core.md#u-1b26134a08d8)

**Uncertainties.**

- Whether families like 'gpt4o_audio' or 'gpt4o_realtime' should be 'audio' is ambiguous: the regex does not match them, so they return 'chat'.

<a id="u-0b2a636e88ec"></a>
### `RubyLLM.Providers.OpenAI.Capabilities.normalize_temperature`

`def self.normalize_temperature(temperature, model_id)` · [lib/ruby_llm/providers/openai/capabilities.rb:L226-L236][f2]

Adjusts a requested temperature for OpenAI reasoning/search models.

If the model id matches /^(o\d|gpt-5)/ it logs a debug message and returns 1.0, discarding the caller's value; else if the id contains '-search' it logs and returns nil, signaling the parameter should be removed; otherwise it returns the temperature unchanged. It is a singleton method on the module (def self.), uses RubyLLM.logger for the side-effect messages, and does not raise.

**Notes.**

- side_effect: Emits a debug log line whenever it overrides or drops a temperature value.

uses: [RubyLLM](../../catalog.json)

<a id="u-592f0cd26fbd"></a>
### `RubyLLM.Providers.OpenAI.Capabilities.pricing_for`

`def pricing_for(model_id)` · [lib/ruby_llm/providers/openai/capabilities.rb:L274-L295][f2]

Builds a nested pricing hash from the per-price lookups.

Standard pricing holds input_per_million and output_per_million from input_price_for/output_price_for; if the module responds to cached_input_price_for and it returns a non-nil value, that becomes cached_input_per_million. The result is {text_tokens: {standard: ...}}. When the model id matches /embedding|batch/, a :batch entry halves both input and output prices arithmetically. Unmatched model ids inherit the 0.50/1.50 defaults from the price lookups.

calls: [capabilities-rb-family-and-pricing](r1-openai-core.md#u-1b26134a08d8)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/providers/openai.rb
[f2]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/providers/openai/capabilities.rb
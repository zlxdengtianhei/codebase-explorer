# OpenAI model capabilities

**Capability.** Resolves OpenAI model ids to families and derives context limits, pricing, modalities, capabilities, display names, and temperature constraints.

Visit to look up what an OpenAI model id implies: window sizes, per-million prices, supported modalities, and capability flags, all keyed off regex-based family resolution. It also adjusts temperature for constrained model families like o-series and gpt-5.

**Depended on by.**

- [Provider class composition](provider-class-composition.md) · graph-only · 1 edge(s)

Parent: [Per-Provider Capability Lookups](per-provider-capability-lookups.md)

## Units (10)

<a id="u-a35ba059aab0"></a>
### `capabilities.rb-capability-predicates-2`

`def supports_vision?(model_id)` · [lib/ruby_llm/providers/openai/capabilities.rb:L81-L88][f1]

Boolean capability lookups keyed on the resolved model family.

Vision is true for GPT-5/4.1/4o families, gpt-4, gpt-4-turbo, o1, o1-pro, moderation and search variants; false otherwise. Function calling is true only for GPT-5/4.1, gpt-4, gpt-4-turbo, gpt-4o, gpt-4o-mini, o1, o1-pro and o3-mini; chatgpt-4o, gpt-3.5-turbo, o1-mini and all audio/transcribe/search/tts variants are false, as is anything else. Structured output is true for GPT-5/4.1, chatgpt-4o, gpt-4o, gpt-4o-mini, o1, o1-pro and o3-mini; json mode simply delegates to the structured-output predicate.

<a id="u-3ae4f232a35e"></a>
### `capabilities.rb-context-window-and-output-token-limits`

`def context_window_for(model_id)` · [lib/ruby_llm/providers/openai/capabilities.rb:L47-L61][f1]

Map a model id to its context window and maximum output tokens by first resolving the model family via regex patterns, then switching on that family.

GPT-4.1 variants get 1,047,576 context and 32,768 output; GPT-5 family 128,000 context and 400,000 output; o1/o1-pro/o3-mini 200,000/100,000; gpt-4 8,192/8,192; gpt-3.5-turbo 16,385/4,096; gpt-4o-mini-transcribe 16,000/2,000. Non-generative families (tts, whisper, moderation, embeddings) return nil for both. Any unrecognized family falls back to 4,096 context and 16,384 output tokens.

<a id="u-e28c4b3ff61e"></a>
### `capabilities.rb-display-name-formatting`

`def format_display_name(model_id)` · [lib/ruby_llm/providers/openai/capabilities.rb:L192-L195][f1]

Builds a human-readable display name: hyphens become spaces, each word capitalized, then a chain of regex fixups restores brand styling.

Special prefixes map 'Gpt'→'GPT-', 'Chatgpt'→'ChatGPT-', 'Tts'→'TTS-', 'Dall E'→'DALL-E-' (special_prefix_format returns nil for other strings, which gsub then substitutes as an empty string). Additional rules rejoin dates, 'O1 '/'O3 '→'O1-'/'O3-', 'O1 Mini'→'O1-Mini', decimal versions like '4.1' get hyphenated, '4o Mini/Preview/...'→'4o-…', 'Hd'→'HD', moderation names hyphenated, and 'Text Embedding'→'text-embedding-'.

<a id="u-ddd4ce5d0ab2"></a>
### `capabilities.rb-price-lookups`

`def input_price_for(model_id)` · [lib/ruby_llm/providers/openai/capabilities.rb:L156-L160][f1]

Per-million-token price lookups driven by the PRICES table keyed on model family.

Input price uses the family's :input, falling back to :price (for flat-priced families like embeddings or tts), then to a 0.50 default; output price mirrors this with a 1.50 default. Cached input price returns only the family's :cached_input, so families without it yield nil rather than a default. Unknown families fetch with the default-filled hash, never raising.

<a id="u-8f01e95afa47"></a>
### `RubyLLM.Providers.OpenAI.Capabilities.capabilities_for`

`def capabilities_for(model_id) # rubocop:disable Metrics/PerceivedComplexity` · [lib/ruby_llm/providers/openai/capabilities.rb:L256-L272][f1]

Builds a capability-string list for a model id.

'streaming' is added unless the id matches /moderation|embedding/; 'function_calling' and 'structured_output' follow the supports_functions?/supports_json_mode? predicates; 'batch' for /embedding|batch/; 'reasoning' for /o\d|gpt-5|codex/. For ids matching /gpt-4-turbo|gpt-4o/, it additionally adds 'image_generation' when the id contains 'vision', and both 'speech_generation' and 'transcription' when it contains 'audio'.

<a id="u-f450f6a19b0c"></a>
### `RubyLLM.Providers.OpenAI.Capabilities.modalities_for`

`def modalities_for(model_id)` · [lib/ruby_llm/providers/openai/capabilities.rb:L238-L254][f1]

Computes input/output modality lists for a model id.

Both start as ['text']. Input gains 'image' and 'pdf' when supports_vision? is true, and 'audio' when the id matches /whisper|audio|tts|transcribe/. Output gains 'audio' for /tts|audio/, 'image' for /dall-e|image/, 'embeddings' for /embedding/, and 'moderation' for /moderation/.

<a id="u-ff3e07430c80"></a>
### `RubyLLM.Providers.OpenAI.Capabilities.model_family`

`def model_family(model_id)` · [lib/ruby_llm/providers/openai/capabilities.rb:L149-L154][f1]

Resolves a model id string to a family name by testing it against the ordered frozen MODEL_PATTERNS regex table and returning the first matching family as a string; returns 'other' when nothing matches.

Order matters: earlier patterns (e.g. gpt-4.1 before gpt-4) win, and negative lookaheads keep suffixed variants (mini, nano, audio, realtime, transcribe, tts, search) out of the base families.

<a id="u-5c9fd553fe1a"></a>
### `RubyLLM.Providers.OpenAI.Capabilities.model_type`

`def model_type(model_id)` · [lib/ruby_llm/providers/openai/capabilities.rb:L174-L182][f1]

Classifies a model id into a type string via its family: families matching /embedding/ are 'embedding'; tts, whisper, and transcribe families are 'audio'; moderation is 'moderation'; families matching /dall/ are 'image'; everything else (including 'other') is 'chat'.

<a id="u-0b2a636e88ec"></a>
### `RubyLLM.Providers.OpenAI.Capabilities.normalize_temperature`

`def self.normalize_temperature(temperature, model_id)` · [lib/ruby_llm/providers/openai/capabilities.rb:L226-L236][f1]

Adjusts the temperature parameter for model constraints: ids matching /^(o\d|gpt-5)/ force 1.0 (logging a debug message that the provided value is ignored); ids containing '-search' return nil (parameter removed, also logged); otherwise the temperature passes through unchanged.

Note it is defined as a singleton method (self.) unlike the module_function siblings, and is invoked from the provider's maybe_normalize_temperature.

<a id="u-592f0cd26fbd"></a>
### `RubyLLM.Providers.OpenAI.Capabilities.pricing_for`

`def pricing_for(model_id)` · [lib/ruby_llm/providers/openai/capabilities.rb:L274-L295][f1]

Assembles a pricing hash: text_tokens.standard with input/output per-million prices, plus cached_input_per_million when cached_input_price_for returns a truthy value (guarded by respond_to?, so it degrades if the method is absent).

For ids matching /embedding|batch/, it adds text_tokens.batch at half the standard input and output prices. The half-price batch entries are computed from the standard prices, so unknown families inherit the defaults at 50%.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/providers/openai/capabilities.rb

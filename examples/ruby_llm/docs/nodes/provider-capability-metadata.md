# Provider Capability Metadata

**Capability.** Derives model capabilities, limits, pricing, modalities, and display names for Anthropic, Gemini, and OpenAI.

Observed units show regex- and table-based metadata helpers plus OpenAI provider composition. Come here for capability, pricing, limit, and modality derivation.

Parent: [Capability And Model Metadata](capability-and-model-metadata.md)

## Units (23)

<a id="u-e28c4c929a17"></a>
### `capabilities.rb-capability-predicates`

`def supports_vision?(model_id)` · [lib/ruby_llm/providers/gemini/capabilities.rb:L49-L53][f1]

Answers Gemini capability questions by regex allow/deny lists over the model id.

- supports_vision?: false for text-embedding, embedding-001, aqa; otherwise true if id matches gemini, flash, pro, or imagen. gemini-embedding-exp matches gemini and returns true; flash-lite is not excluded.
- supports_video?: true only if id matches gemini; flash-lite is not excluded.
- supports_functions?: false for text-embedding, embedding-001, aqa, flash-lite, imagen, gemini-2.0-flash-lite; otherwise true if matches gemini, pro, or flash.
- supports_json_mode?: false for text-embedding, embedding-001, aqa, imagen, gemini-2.0-flash-lite, gemini-2.5-pro-exp-03-25; otherwise true if matches gemini, pro, or flash.
- supports_caching?: false for flash-lite, gemini-2.5-pro-exp-03-25, aqa, imagen, text-embedding, embedding-001; otherwise true if matches gemini, pro, or flash.
- supports_tuning?: true only for gemini-1.5-flash or gemini-1.5-flash-8b.
- supports_audio?: true if id matches gemini, pro, or flash; flash-lite is not excluded.

<a id="u-a35ba059aab0"></a>
### `capabilities.rb-capability-predicates-2`

`def supports_vision?(model_id)` · [lib/ruby_llm/providers/openai/capabilities.rb:L81-L88][f2]

Answers boolean capability questions by model family; json mode delegates to structured output.

Vision is true for gpt5/gpt5_mini/gpt5_nano/gpt41/gpt41_mini/gpt41_nano/chatgpt4o/gpt4/gpt4_turbo/gpt4o/gpt4o_mini/o1/o1_pro/moderation/gpt4o_search/gpt4o_mini_search and false otherwise, including gpt4o_audio, gpt4o_realtime, gpt4o_transcribe, gpt4o_mini_audio, gpt4o_mini_realtime, gpt4o_mini_transcribe, and gpt4o_mini_tts. Functions are true for gpt5/gpt5_mini/gpt5_nano/gpt41/gpt41_mini/gpt41_nano/gpt4/gpt4_turbo/gpt4o/gpt4o_mini/o1/o1_pro/o3_mini; false for chatgpt4o/gpt35_turbo/o1_mini/gpt4o_mini_tts/gpt4o_transcribe/gpt4o_search/gpt4o_mini_search and all other families. Structured output is true for gpt5/gpt5_mini/gpt5_nano/gpt41/gpt41_mini/gpt41_nano/chatgpt4o/gpt4o/gpt4o_mini/o1/o1_pro/o3_mini; false otherwise, so gpt4 and gpt4_turbo are false. JSON mode returns the structured-output result.

<a id="u-d86e2f518d54"></a>
### `capabilities.rb-capability-predicates-and-modalities`

`def supports_vision?(model_id)` · [lib/ruby_llm/providers/anthropic/capabilities.rb:L29-L31][f3]

Derives Anthropic capability flags, modalities, and model type from the id.

Vision is true unless the id matches claude-1 or claude-2; function calling and JSON mode require claude-3; extended thinking requires claude-3-7-sonnet; type is always chat. Modalities start text/text and add image and pdf input unless the id matches claude-1 or claude-2. Capabilities start with streaming; claude-3 adds function_calling and batch; claude-3-7 or -4 adds reasoning; claude-3.5 or claude-3-7 adds citations.

<a id="u-e69f2c50c919"></a>
### `capabilities.rb-context-and-output-limits`

`def context_window_for(model_id)` · [lib/ruby_llm/providers/gemini/capabilities.rb:L10-L21][f1]

Resolves Gemini model context windows, output-token limits, and the context-length alias from model-id patterns.

- context_window_for: 2.5-pro-exp-03-25, 2.0-flash, 2.0-flash-lite, 1.5-flash, 1.5-flash-8b -> 1,048,576; 1.5-pro -> 2,097,152; gemini-embedding-exp -> 8,192; text-embedding-004/embedding-001 -> 2,048; aqa -> 7,168; imagen-3 -> nil; else 32,768.
- max_tokens_for: 2.5-pro-exp-03-25 -> 64,000; 2.0-flash, 2.0-flash-lite, 1.5-flash, 1.5-flash-8b, 1.5-pro -> 8,192; gemini-embedding-exp -> nil; text-embedding-004/embedding-001 -> 768; imagen-3 -> 4; else 4,096.
- context_length delegates to context_window_for.

<a id="u-cb3152fd0e54"></a>
### `capabilities.rb-context-and-output-token-limits`

`def context_window_for(model_id)` · [lib/ruby_llm/providers/openai/capabilities.rb:L47-L61][f2]

Maps a model id to context-window and max-output-token limits by first resolving its family.

Context: gpt41/gpt41_mini/gpt41_nano -> 1,047,576; gpt5/gpt5_mini/gpt5_nano/chatgpt4o/gpt4_turbo/gpt4o/gpt4o_audio/gpt4o_mini/gpt4o_mini_audio/gpt4o_mini_realtime/gpt4o_realtime/gpt4o_search/gpt4o_transcribe/gpt4o_mini_search/o1_mini -> 128,000; gpt4 -> 8,192; gpt4o_mini_transcribe -> 16,000; o1/o1_pro/o3_mini -> 200,000; gpt35_turbo -> 16,385; gpt4o_mini_tts/tts1/tts1_hd/whisper/moderation/embedding3_large/embedding3_small/embedding_ada -> nil; else 4,096. Max output: gpt5/gpt5_mini/gpt5_nano -> 400,000; gpt41/gpt41_mini/gpt41_nano -> 32,768; chatgpt4o/gpt4o/gpt4o_mini/gpt4o_mini_search -> 16,384; babbage/davinci -> 16,384; gpt4 -> 8,192; gpt35_turbo -> 4,096; gpt4_turbo/gpt4o_realtime/gpt4o_mini_realtime -> 4,096; gpt4o_mini_transcribe -> 2,000; o1/o1_pro/o3_mini -> 100,000; o1_mini -> 65,536; gpt4o_mini_tts/tts1/tts1_hd/whisper/moderation/embedding3_large/embedding3_small/embedding_ada -> nil; else 16,384. Families not listed in a max branch, such as gpt4o_audio, gpt4o_search, gpt4o_transcribe, gpt4o_mini_audio, fall to the else value.

<a id="u-b0e5cd6f3fd1"></a>
### `capabilities.rb-context-and-token-limits`

`def determine_context_window(_model_id)` · [lib/ruby_llm/providers/anthropic/capabilities.rb:L10-L12][f3]

Returns fixed Anthropic context and output-token limits.

Context is always 200,000; max output is 8,192 when the id matches claude-3-7-sonnet or claude-3-5, otherwise 4,096.

<a id="u-e28c4b3ff61e"></a>
### `capabilities.rb-display-name-formatting`

`def format_display_name(model_id)` · [lib/ruby_llm/providers/openai/capabilities.rb:L192-L195][f2]

Builds a human-readable display name from a model id.

Humanize replaces hyphens with spaces, splits, capitalizes each word, and joins with spaces. Special formatting then collapses yyyy mm dd digit groups, maps Gpt/Chatgpt/Tts/Dall E prefixes to GPT-/ChatGPT-/TTS-/DALL-E-, turns O1/O3 prefixes into O1-/O3-, hyphenates O1/O3 Mini, digit.digit followed by space, 4o before Mini/Preview/Turbo/Audio/Realtime/Transcribe/Tts, Omni/Text Moderation, and Text Embedding, and uppercases Hd to HD. The prefix helper returns the mapped replacement for those four prefixes.

<a id="u-51b50e10ab45"></a>
### `capabilities.rb-long-context-pricing`

`def input_price_for(model_id)` · [lib/ruby_llm/providers/gemini/capabilities.rb:L35-L40][f1]

Computes input/output per-token base prices and doubles them for long-context models above 128k context.

- base price: PRICES.dig(pricing_family(model_id), :input or :output) or default 0.075 input / 0.30 output.
- long_context_model? matches gemini-1.5-pro, gemini-1.5-flash, gemini-1.5-flash-8b.
- not long-context -> base price; long-context and context_window_for > 128,000 -> base * 2; long-context at or below 128,000 -> base price.

<a id="u-773258e4d15f"></a>
### `capabilities.rb-model-classification`

`def model_type(model_id)` · [lib/ruby_llm/providers/gemini/capabilities.rb:L101-L107][f1]

Classifies model ids into type, family, and pricing family using ordered regex cases.

- model_type: text-embedding/embedding/gemini-embedding -> embedding; imagen -> image; else chat.
- model_family: ordered cases return gemini25_pro_exp, gemini20_flash_lite, gemini20_flash, gemini15_flash_8b, gemini15_flash, gemini15_pro, gemini_embedding_exp, embedding4, embedding1, aqa, imagen3; else other.
- pricing_family: ordered cases return :pro_2_5, :flash_lite_2, :flash_2, :flash_8b, :flash, :pro, :gemini_embedding, :embedding for text-embedding/embedding, :imagen, :aqa; else :base. Order matters where patterns overlap.

<a id="u-9a009b649a52"></a>
### `capabilities.rb-pricing-and-family`

`def get_input_price(model_id)` · [lib/ruby_llm/providers/anthropic/capabilities.rb:L21-L23][f3]

Computes Anthropic pricing and maps model ids to families.

The family helper returns strings, while the price table is symbol-keyed, so the two direct price lookups miss and fall back to 3.0 input and 15.0 output; the aggregate pricing path converts the family to a symbol, hits the table, halves prices for batch, and for claude-3-7 adds reasoning output at 2.5x standard output and 1.25x batch output.

<a id="u-a667a5713f12"></a>
### `capabilities.rb-pricing-lookup-and-aggregation`

`def input_price_for(model_id)` · [lib/ruby_llm/providers/openai/capabilities.rb:L156-L160][f2]

Looks up per-million token prices by family and assembles the pricing hash.

Input price uses the family entry's input value, then its price value, then the default 0.50; output price uses output, then price, then the default 1.50. Cached input price returns only the family's cached_input value and is nil when absent. Unknown families use the defaults for input/output and nil for cached. The pricing hash always contains standard input/output; it adds cached_input_per_million only when cached input is non-nil. If the model id matches embedding or batch, it also adds batch text-token prices at half the standard input/output values. The default input price is 0.50 and the default output price is 1.50.

<a id="u-0dae8eb13bcc"></a>
### `content.rb-anthropic-content-blocks`

`class Anthropic # Helper for constructing Anthropic native content blocks.` · [lib/ruby_llm/providers/anthropic/content.rb:L5-L7][f4]

Builds Anthropic-native text content blocks and wraps them as raw content.

The constructor delegates payload resolution; if parts are supplied it returns Array(parts) unchanged. Otherwise it raises ArgumentError when text is nil, merges extra keyword arguments into a text block, and attaches cache control when requested. Cache control uses an explicit value first, otherwise an ephemeral marker when the cache flag is true. The result is wrapped in RubyLLM::Content::Raw.

<a id="u-8dced6210d4b"></a>
### `models.rb-anthropic-model-listing-and-token-extraction`

`class Anthropic # Models methods of the Anthropic API integration` · [lib/ruby_llm/providers/anthropic/models.rb:L5-L7][f5]

Lists Anthropic models and extracts token/model fields from streaming or response data.

The URL is fixed. Listing maps each body data entry into Model::Info, using the entry id and display name, the supplied provider slug, capability lookups for family/context/max/modalities/capabilities/pricing, and Time.parse on created_at; Time.parse is not guarded. Token extractors read nested message usage first and fall back to top-level usage for output and cached tokens. Cache-creation tokens prefer a direct count, then sum non-nil values from a cache_creation hash; they return nil when neither exists. Model id reads message.model.

<a id="u-9da6d221a66b"></a>
### `openai.rb-openai-provider`

`class OpenAI < Provider` · [lib/ruby_llm/providers/openai.rb:L6-L17][f6]

OpenAI is a provider integration composing chat, embeddings, models, moderation, streaming, tools, images, media, and transcription modules.

Its API base uses the configured OpenAI base when present, otherwise a fixed default. Headers send a Bearer API key plus organization and project headers, with nil values removed by compact. Temperature normalization delegates to the OpenAI capabilities normalizer with the model id. The class-level capabilities method returns the OpenAI capabilities class, and configuration requires an OpenAI API key.

<a id="u-39927ed91517"></a>
### `RubyLLM.Providers.Gemini.Capabilities.capabilities_for`

`def capabilities_for(model_id)` · [lib/ruby_llm/providers/gemini/capabilities.rb:L232-L241][f1]

Builds the capability list for a model id, always including streaming.

It adds function_calling when supports_functions? is true, structured_output when supports_json_mode? is true, batch when the id matches embedding or flash, caching when supports_caching? is true, and fine_tuning when supports_tuning? is true.

<a id="u-e71c85aecd17"></a>
### `RubyLLM.Providers.Gemini.Capabilities.format_display_name`

`def format_display_name(model_id)` · [lib/ruby_llm/providers/gemini/capabilities.rb:L73-L83][f1]

Builds a human-readable display name from a Gemini model id.

It removes a models/ prefix, splits on hyphens, capitalizes each token, joins with spaces, inserts a space before decimal versions, collapses whitespace, replaces Aqa with AQA, and strips.

<a id="u-35f4cb3c9289"></a>
### `RubyLLM.Providers.Gemini.Capabilities.modalities_for`

`def modalities_for(model_id)` · [lib/ruby_llm/providers/gemini/capabilities.rb:L213-L230][f1]

Builds input/output modality lists for a Gemini model id.

It starts with text input and text output, adds image and pdf input when supports_vision? is true, adds video input when supports_video? is true, adds audio input when the id matches audio, adds embeddings output when the id matches embedding or gemini-embedding, and replaces output with image when the id matches imagen.

<a id="u-8c1e405cf91e"></a>
### `RubyLLM.Providers.Gemini.Capabilities.pricing_for`

`def pricing_for(model_id)` · [lib/ruby_llm/providers/gemini/capabilities.rb:L243-L277][f1]

Builds standard and batch token pricing hashes for a model id.

It fetches PRICES by pricing_family with default input/output prices, copies input/output into standard pricing, adds cached input only when the family has input_hit, halves standard values for batch, halves cached batch when present, and adds embeddings standard input pricing for embedding or gemini-embedding ids using the family price or 0.002.

<a id="u-8f01e95afa47"></a>
### `RubyLLM.Providers.OpenAI.Capabilities.capabilities_for`

`def capabilities_for(model_id) # rubocop:disable Metrics/PerceivedComplexity` · [lib/ruby_llm/providers/openai/capabilities.rb:L256-L272][f2]

Builds a capability-name array for a model id.

It adds streaming unless the id matches moderation or embedding; function_calling when functions are supported; structured_output when json mode is supported; batch when the id matches embedding or batch; and reasoning when the id matches o followed by a digit, gpt-5, or codex. For ids matching gpt-4-turbo or gpt-4o, it additionally adds image_generation when the id contains vision, and adds speech_generation and transcription when the id contains audio.

<a id="u-f450f6a19b0c"></a>
### `RubyLLM.Providers.OpenAI.Capabilities.modalities_for`

`def modalities_for(model_id)` · [lib/ruby_llm/providers/openai/capabilities.rb:L238-L254][f2]

Builds input and output modality lists for a model id.

Both start with text. Input adds image and pdf when vision is supported, and adds audio when the id matches whisper, audio, tts, or transcribe. Output adds audio for tts or audio, image for dall-e or image, embeddings for embedding, and moderation for moderation. The result is a hash with input and output arrays; additions are not deduplicated beyond the initial text entries.

<a id="u-ff3e07430c80"></a>
### `RubyLLM.Providers.OpenAI.Capabilities.model_family`

`def model_family(model_id)` · [lib/ruby_llm/providers/openai/capabilities.rb:L149-L154][f2]

Resolves a model id to the first matching family name from the ordered pattern table, or other when none match.

Patterns are checked in insertion order, so gpt5 matches gpt-5-mini and gpt-5-nano before their specific patterns, and those two families are never returned. Negative lookaheads keep gpt41 separate from mini/nano, gpt4o separate from mini/audio/realtime/transcribe/tts/search, gpt4o_mini separate from audio/realtime/transcribe/tts/search, o1 separate from mini/pro, and tts1 separate from hd. There is no pattern for gpt4o_mini_search, so that family is not produced.

<a id="u-5c9fd553fe1a"></a>
### `RubyLLM.Providers.OpenAI.Capabilities.model_type`

`def model_type(model_id)` · [lib/ruby_llm/providers/openai/capabilities.rb:L174-L182][f2]

Classifies a model id into embedding, audio, moderation, image, or chat by family.

Family names containing embedding become embedding; names starting with tts, containing whisper, or matching gpt4o_(mini_)?(transcribe|tts) become audio; moderation becomes moderation; names containing dall become image; everything else becomes chat. Thus gpt4o_audio and gpt4o_realtime are chat under this classifier.

<a id="u-0b2a636e88ec"></a>
### `RubyLLM.Providers.OpenAI.Capabilities.normalize_temperature`

`def self.normalize_temperature(temperature, model_id)` · [lib/ruby_llm/providers/openai/capabilities.rb:L226-L236][f2]

Normalizes a requested temperature for models that reject or ignore it.

If the model id starts with o followed by a digit or with gpt-5, it logs a debug message and returns 1.0. Otherwise, if the id contains -search, it logs a debug message and returns nil. Otherwise it returns the input unchanged. The first condition wins, so a gpt-5 search model returns 1.0 rather than nil.

Look up code: the commands are under "Read further" in [INDEX.md](../INDEX.md); `cbe query` and `cbe source` take a unit title or anchor from this page.

[f1]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/providers/gemini/capabilities.rb
[f2]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/providers/openai/capabilities.rb
[f3]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/providers/anthropic/capabilities.rb
[f4]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/providers/anthropic/content.rb
[f5]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/providers/anthropic/models.rb
[f6]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/providers/openai.rb

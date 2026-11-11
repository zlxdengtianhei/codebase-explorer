# Gemini model capabilities

**Capability.** Derives Gemini model metadata: regex-based capability booleans, context and output limits, model typing, pricing, and display-name formatting.

Come here for Gemini model-id classification (embedding, imagen, or chat) and the associated limits and prices. Display names are built by hyphen-splitting and capitalizing id segments.

Parent: [Per-Provider Capability Lookups](per-provider-capability-lookups.md)

## Units (6)

<a id="u-e28c4c929a17"></a>
### `capabilities.rb-capability-predicates`

`def supports_vision?(model_id)` · [lib/ruby_llm/providers/gemini/capabilities.rb:L49-L53][f1]

Regex-based capability booleans.

Vision: false for embedding/aqa ids, true for gemini/flash/pro/imagen. Video: any id containing gemini. Functions: false for embeddings, aqa, flash-lite, imagen; otherwise gemini/pro/flash. JSON mode: same exclusions plus gemini-2.5-pro-exp-03-25, then gemini/pro/flash. Caching: false for flash-lite, 2.5-pro-exp, aqa, imagen, embeddings; else gemini/pro/flash. Tuning: only 1.5-flash and 1.5-flash-8b. Audio: gemini/pro/flash. Note flash-lite ids match /flash/ so they pass the positive checks unless explicitly excluded, which each predicate does.

<a id="u-6acd8e7f26f1"></a>
### `capabilities.rb-context-window-and-token-limits`

`def context_window_for(model_id)` · [lib/ruby_llm/providers/gemini/capabilities.rb:L10-L21][f1]

Maps model id patterns to context window and max output token limits via regex case statements.

2.0/1.5 flash variants and the 2.5-pro-exp get 1,048,576 context; 1.5-pro gets 2,097,152; embedding models get 8,192 or 2,048; aqa 7,168; imagen-3 nil; anything else 32,768. Max tokens: 64,000 for 2.5-pro-exp, 8,192 for flash/1.5-pro, nil for gemini-embedding-exp, 768 for text-embedding-004/embedding-001, 4 for imagen-3, else 4,096. long_context_model? is true only for 1.5 pro/flash/flash-8b ids; context_length is an alias of context_window_for.

<a id="u-71a6018d4497"></a>
### `capabilities.rb-modalities-capabilities-and-pricing-assembly`

`def modalities_for(model_id)` · [lib/ruby_llm/providers/gemini/capabilities.rb:L213-L230][f1]

Builds model metadata structures.

modalities_for starts with text in/out, adds image and pdf input when vision is supported, video when the id contains gemini, audio input when the id matches /audio/, embeddings output for embedding ids, and replaces output with ['image'] for imagen. capabilities_for always includes 'streaming', then adds function_calling/structured_output/caching per the predicates, batch for embedding or flash ids, and fine_tuning for tunable models. pricing_for fetches family prices (defaulting to the default input/output prices), builds standard and half-price batch text-token pricing, copies cached_input_per_million only when a truthy :input_hit price exists (no PRICES entry currently sets it), and adds an embeddings pricing block with input_per_million from prices[:price] or 0.002 for embedding-family ids.

<a id="u-969f8813467f"></a>
### `capabilities.rb-model-type-and-family`

`def model_type(model_id)` · [lib/ruby_llm/providers/gemini/capabilities.rb:L101-L107][f1]

model_type classifies ids: embedding for text-embedding/embedding/gemini-embedding patterns, image for imagen, else chat.

model_family maps specific id patterns to snake_case family strings (gemini25_pro_exp, gemini20_flash_lite, gemini20_flash, gemini15_flash_8b, gemini15_flash, gemini15_pro, gemini_embedding_exp, embedding4, embedding1, aqa, imagen3) with 'other' as fallback; order matters since broader patterns come after narrower ones.

<a id="u-6c213c69e3bf"></a>
### `capabilities.rb-pricing-lookup`

`def input_price_for(model_id)` · [lib/ruby_llm/providers/gemini/capabilities.rb:L35-L40][f1]

Resolves per-million input/output prices by pricing_family, falling back to defaults 0.075/0.30 when the family is absent from PRICES.

For long-context 1.5 models the base price is doubled when the model's context window exceeds 128,000 tokens, so 1.5-pro doubles but 1.5-flash (1M window) also doubles; non-long-context models never double. pricing_family maps id patterns to symbols (:pro_2_5, :flash_lite_2, :flash_2, :flash_8b, :flash, :pro, :gemini_embedding, :embedding, :imagen, :aqa, else :base).

<a id="u-e71c85aecd17"></a>
### `RubyLLM.Providers.Gemini.Capabilities.format_display_name`

`def format_display_name(model_id)` · [lib/ruby_llm/providers/gemini/capabilities.rb:L73-L83][f1]

Formats a model id into a human display name: strips the models/ prefix, splits on hyphens, capitalizes each segment, rejoins with spaces, inserts a space before decimal numbers, collapses whitespace, fixes 'Aqa' to 'AQA', and strips.

E.g. 'models/gemini-1.5-pro' becomes 'Gemini 1.5 Pro'.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/providers/gemini/capabilities.rb

# Content and Result Value Objects

**Capability.** Defines the data shapes exchanged with providers: text-plus-attachments Content (and Raw escape hatch), plus moderation, transcription, embedding, and model metadata (modalities, pricing) results.

Consult these when you need the exact fields a provider response is normalized into. Provider adapters construct these objects; ActiveRecord and user code consume them.

**Depends on.**

- [Model Metadata Objects](r1-model-metadata.md) · graph-only · 2 edge(s)
- [Attachments & Images](r1-content-media.md) · graph-only · 1 edge(s)
- [Shared Utilities](r1-shared-utilities.md) · graph-only · 1 edge(s)

**Depended on by.**

- [Anthropic Adapter](r2-provider-anthropic.md) · model-inferred · 0 edge(s)
- [Gemini Adapter](r2-provider-gemini.md) · graph-confirmed · 1 edge(s)
- [OpenAI Adapter](r2-provider-openai.md) · graph-confirmed · 1 edge(s)
- [VertexAI Adapter](r2-provider-vertexai.md) · graph-confirmed · 1 edge(s)
- [Legacy acts\_as Support](r1-legacy-acts-as.md) · graph-only · 2 edge(s)
- [Message Conversion](r1-message-methods.md) · graph-only · 2 edge(s)
- [Model Metadata Objects](r1-model-metadata.md) · graph-only · 2 edge(s)
- [Gemini Embeddings & Images](r1-gemini-embeddings-images.md) · graph-only · 1 edge(s)
- [Mistral Adapter](r1-mistral-adapter.md) · graph-only · 1 edge(s)

Parent: [Core Runtime](r2-core-runtime.md)

## Units (8)

<a id="u-fb6f20b3ce1b"></a>
### `Content`

`class Content` · [lib/ruby_llm/content.rb:L5-L8][f1]

Wraps message text plus optional attachments exchanged with an LLM.

`initialize(text, attachments)` stores text and an empty attachment list, then normalizes the attachments argument: a Hash has each value processed in turn (keys ignored); anything else goes through `Utils.to_safe_array` (Array passes through, a Hash becomes one element, other values via `Array()`) and each entry becomes `Attachment.new(source, filename: nil)`. Raises ArgumentError 'Text and attachments cannot be both nil' when text is nil and no attachments resulted; other errors from Attachment construction propagate. `add_attachment` appends an Attachment and returns self for chaining. `format` returns the bare text string only when text is present and attachments are empty, otherwise the Content itself. `to_h` returns `{text:, attachments: [each attachment's to_h]}` for Rails serialization.

calls: [utils-utils-helpers](r1-shared-utilities.md#u-add7cf7f30e5)

<a id="u-0c5bb605478e"></a>
### `Raw`

`class Raw` · [lib/ruby_llm/content.rb:L55-L58][f1]

Wraps a provider-specific payload that bypasses RubyLLM's content formatting.

`initialize` raises ArgumentError 'Raw content payload cannot be nil' when the value is nil, otherwise stores it. Both `format` and `to_h` return the stored value unchanged, so consumers that would otherwise flatten Content receive the payload as-is.

<a id="u-7cc22e915a93"></a>
### `Modalities`

`class Modalities` · [lib/ruby_llm/model/modalities.rb:L6-L9][f2]

initialize(data) wraps data[:input] and data[:output] in Array and maps each entry with to_s, so nil becomes [] and symbols become strings; attr_reader exposes the stored arrays directly, so callers can mutate them in place.

to_h returns { input:, output: } with those same arrays.

<a id="u-923e8405cbf7"></a>
### `Pricing`

`class Pricing` · [lib/ruby_llm/model/pricing.rb:L6-L7][f3]

initialize(data) creates a PricingCategory for a category only when the key is present and private empty_pricing?

deems it non-empty. empty_pricing? returns true for falsy data; otherwise it scans the standard and batch tiers and returns false as soon as any tier value is truthy and not 0.0, so all-nil or all-zero payloads are dropped. method_missing answers a known category name with the stored PricingCategory when built, else a fresh empty PricingCategory — known accessors never raise and never return nil; unknown methods call super, propagating NoMethodError. respond_to_missing? claims exactly the four category names and defers to super otherwise. to_h serializes only constructed categories via transform_values(&:to_h), so dropped categories are absent from the hash yet still answer method_missing.

**Notes.**

- condition: A category whose tiers are all nil/0.0 is excluded from to_h yet still returns a fresh empty PricingCategory on access.

<a id="u-f57bee6fccf5"></a>
### `PricingCategory`

`class PricingCategory` · [lib/ruby_llm/model/pricing_category.rb:L6-L9][f4]

initialize(data = {}) builds @standard and @batch as PricingTier objects only when private empty_tier?

finds the tier non-empty: empty_tier? returns true for nil tier data and otherwise true when all tier values are nil or 0.0. input, output, and cached_input delegate to standard with safe navigation (standard&.input_per_million etc.), returning nil when the standard tier was omitted. []\(key) returns batch for :batch and standard for anything else, including nil or unknown keys, both yielding the standard tier or nil. to_h includes only the tiers that were constructed, each serialized via its to_h.

uses: [PricingTier](r1-model-metadata.md#u-925c3e76d00e)

<a id="u-665bdee2e65d"></a>
### `Moderation`

`class Moderation` · [lib/ruby_llm/moderation.rb:L6-L9][f5]

Represents an OpenAI-style content-moderation result and its dispatch entry point.

`initialize(id:, model:, results:)` stores all three keywords. Class method `moderate(input, model:, provider:, assume_model_exists:, context:)` selects the context config or global `RubyLLM.config`, defaults the model to `config.default_moderation_model` falling back to 'omni-moderation-latest', resolves the model via `Models.resolve` to obtain a provider instance, then returns `provider_instance.moderate(input, model: model_id)`. Instance readers interpret `results` (an array of result hashes): `content` is just `results`; `flagged?` is true when any result's 'flagged' entry is truthy; `flagged_categories` flat-maps each result's 'categories' hash selecting truthy entries and uniqs the keys, yielding [] when 'categories' is absent; `category_scores` digs 'category_scores' from the first result ({} when absent/empty); `categories` digs 'categories' from the first result ({} when absent/empty). Results are expected to be string-keyed hashes; symbol-keyed data would return nil/[] fallbacks.

**Notes.**

- failure: String-key access ('flagged', 'categories', 'category_scores') means symbol-keyed results silently produce false/[]/{} rather than raising.

<a id="u-76c340bea812"></a>
### `lib/ruby_llm/transcription.rb:Transcription`

`class Transcription` · [lib/ruby_llm/transcription.rb:L5-L8][f6]

Represents an audio transcription result and its dispatch entry point.

`initialize(text:, model:, **attributes)` stores required text and model, then pulls language, duration, segments, input_tokens, and output_tokens from the remaining attributes (nil when absent; other keys are silently ignored). Class method `transcribe(audio_file, **kwargs)` deletes :model, :language, :provider, :assume_model_exists (default false via delete's block), and :context from kwargs, leaving the rest as provider `options`. It picks the context config or global `RubyLLM.config`, defaults the model to `config.default_transcription_model`, resolves via `Models.resolve` to obtain the provider instance, then calls `provider_instance.transcribe(audio_file, model: model_id, language:, **options)` and returns its result; resolve and provider errors propagate uncaught.

<a id="u-0061f299adf1"></a>
### `embedding.rb-embedding`

`def initialize(vectors:, model:, input_tokens: 0)` · [lib/ruby_llm/embedding.rb:L8-L12][f7]

Value object and entry point for embedding results.

initialize stores vectors, model, and input_tokens (default 0) behind readers. The class method embed resolves the model (defaulting to config.default_embedding_model, honoring an optional context's config) through Models.resolve, then calls the resolved provider instance's embed with the model id and requested dimensions; its return value is returned unchanged.

calls: [RubyLLM.Models.resolve](r1-registry-catalog.md#u-3dcbba4582dc)

**Uncertainties.**

- The provider's embed return shape is provider-specific and not visible in this file

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/content.rb
[f2]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/model/modalities.rb
[f3]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/model/pricing.rb
[f4]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/model/pricing_category.rb
[f5]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/moderation.rb
[f6]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/transcription.rb
[f7]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/embedding.rb
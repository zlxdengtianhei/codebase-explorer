# Model info value objects

**Capability.** Defines immutable value objects describing a model's identity, type, modalities, and nested pricing structures with empty-data skipping.

Come here for the data shapes returned by model listings: Model::Info and its type classification from output modalities, plus the modalities normalizer and the pricing/category/tier hierarchy that omits empty entries.

**Depends on.**

- [Gemini and media integrations](gemini-and-media-integrations.md) · graph-only · 2 edge(s)

Parent: [Model Metadata and Embeddings](model-metadata-and-embeddings.md)

## Units (6)

<a id="u-9ef410650d6a"></a>
### `info.rb-info-type-and-to-h`

`def type # rubocop:disable Metrics/PerceivedComplexity` · [lib/ruby_llm/model/info.rb:L79-L91][f1]

`type` classifies the model from output modalities: 'embedding' if output has 'embeddings' but not 'text'; else 'image' if 'image' without 'text'; else 'audio' if 'audio' without 'text'; else 'moderation' if output includes 'moderation'; otherwise 'chat'.

Note text output dominates: a model emitting both text and embeddings is 'chat'. `to_h` returns a flat symbol-keyed hash of all attributes, delegating modalities and pricing to their own to_h.

<a id="u-cc87afe4e61d"></a>
### `info.rb-model-info`

`class Info` · [lib/ruby_llm/model/info.rb:L6-L11][f1]

Immutable value object describing one AI model's identity, capabilities, modalities, pricing, and metadata.

`default` builds an Info for an unknown model id, assuming function_calling/streaming/vision/structured_output capabilities, text+image input, and a metadata warning that capabilities may be inaccurate. `initialize` reads a data hash, normalizing created_at via Utils.to_time and knowledge_cutoff via Utils.to_date, wrapping modalities in Modalities, pricing in Pricing, and defaulting capabilities/metadata to empty. `supports?` checks string membership in the capabilities array; the metaprogrammed block defines `function_calling?`, `structured_output?`, `batch?`, `reasoning?`, `citations?`, `streaming?` predicates delegating to supports?. Trivial accessors: display_name returns name, max_tokens aliases max_output_tokens, supports_vision?/supports_video? check modalities input for 'image'/'video', supports_functions? aliases function_calling?, input/output_price_permillion read pricing.text_tokens input/output, provider_class resolves the provider via RubyLLM::Provider.resolve.

<a id="u-ed270a30298e"></a>
### `modalities.rb-model-modalities`

`class Modalities` · [lib/ruby_llm/model/modalities.rb:L6-L9][f2]

Normalizes a modalities hash into string arrays for input and output; Array() coerces nil to [] and non-array scalars wrap, and each element is stringified.

`to_h` returns {input:, output:} with those arrays.

<a id="u-42c32d16611b"></a>
### `pricing.rb-model-pricing`

`class Pricing` · [lib/ruby_llm/model/pricing.rb:L6-L7][f3]

Collection of pricing categories keyed by :text_tokens, :images, :audio_tokens, :embeddings; a category is stored only if the input data has that key and is not 'empty' (nil, or all standard/batch values nil or 0.0).

`method_missing` returns the stored PricingCategory for those four known keys, or a fresh empty PricingCategory if absent; unknown methods fall through to super (NoMethodError). `respond_to_missing?` claims the four category names then defers to super. `to_h` maps each stored category through its to_h, so absent categories are omitted entirely.

<a id="u-7935890af885"></a>
### `pricing_category.rb-model-pricingcategory`

`class PricingCategory` · [lib/ruby_llm/model/pricing_category.rb:L6-L9][f4]

Holds standard and batch PricingTiers, skipping construction for nil or 'empty' tier data (all values nil or 0.0), leaving the reader nil.

`input`, `output`, `cached_input` read the corresponding per-million fields from the standard tier via safe navigation, returning nil when no standard tier exists. `[]` returns batch for :batch, standard otherwise (any other key yields standard). `to_h` includes only present tiers under :standard/:batch.

<a id="u-fa54092cdda1"></a>
### `pricing_tier.rb-model-pricingtier`

`class PricingTier` · [lib/ruby_llm/model/pricing_tier.rb:L6-L7][f5]

Dynamic attribute bag that stores only truthy, non-zero values, symbolizing keys at construction.

`method_missing`: for a writer name ending in '=', stores args.first only if truthy and != 0.0 (returns nil otherwise, silently dropping); for readers, returns the stored value when the key exists, otherwise falls to the implicit nil return (no super call, so unknown readers return nil rather than raising). `respond_to_missing?` accepts any '='-suffixed name or known key, then super. `to_h` exposes the raw values hash.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/model/info.rb
[f2]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/model/modalities.rb
[f3]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/model/pricing.rb
[f4]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/model/pricing_category.rb
[f5]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/model/pricing_tier.rb

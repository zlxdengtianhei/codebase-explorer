# Model Metadata Value Objects

**Capability.** Stores model metadata, modalities, pricing categories, tiers, and capability predicates as mutable value objects.

Observed units define containers and derived predicates for model info and pricing structures. Use this module when inspecting or serializing model metadata; runtime behavior beyond construction is not shown.

**Depends on.**

- [Chat Message And Tool Formatting](chat-message-and-tool-formatting.md) · graph-only · 2 edge(s)

Parent: [Capability And Model Metadata](capability-and-model-metadata.md)

## Units (7)

<a id="u-8b23ff732269"></a>
### `info.rb-capability-predicates`

`def supports?(capability)` · [lib/ruby_llm/model/info.rb:L37-L39][f1]

Capability predicates answer whether a model supports a named capability or specific input modality.

The generic check converts the requested capability to a string and tests membership in the capabilities array. Dynamically defined predicates for function_calling, structured_output, batch, reasoning, citations, and streaming delegate to that generic check. Vision and video checks inspect the input modality list for image and video respectively; the functions predicate delegates to the function_calling predicate.

<a id="u-daf7fc1df824"></a>
### `info.rb-derived-attributes`

`def input_price_per_million` · [lib/ruby_llm/model/info.rb:L67-L69][f1]

Derived attributes expose text-token prices, resolve the provider class, and classify the model by output modality.

Input and output price per million read the standard text-token tier values, which can be nil when that tier is absent. Provider resolution delegates to the provider resolver with the stored provider. Type classification returns embedding when output includes embeddings and not text, image when output includes image and not text, audio when output includes audio and not text, moderation when output includes moderation regardless of text, and chat otherwise.

<a id="u-44964b62040d"></a>
### `info.rb-info-construction-and-serialization`

`class Info` · [lib/ruby_llm/model/info.rb:L6-L11][f1]

Info is a mutable model-metadata container that builds from a hash, can synthesize a default model, and serializes its fields.

It is not immutable: attr_reader and to_h expose mutable arrays and hashes without freezing. The default factory derives a display name from the id by replacing hyphens with spaces and capitalizing, and supplies assumed capabilities, text/image input, text output, and warning metadata. Initialization copies scalar fields, converts created_at and knowledge_cutoff through utility converters, wraps modalities and pricing with empty-hash defaults so missing or nil values do not raise, and defaults capabilities to an empty array and metadata to an empty hash. Serialization returns all fields, converts modalities and pricing to hashes, and returns capabilities and metadata as stored references.

<a id="u-1f21a43399e6"></a>
### `modalities.rb-modalities-value`

`class Modalities` · [lib/ruby_llm/model/modalities.rb:L6-L9][f2]

Modalities stores input and output modality names as string arrays and serializes them.

Initialization wraps each side with Array and maps every element to a string, so missing or nil input becomes an empty array. Serialization returns a hash containing the same input and output arrays, without freezing them.

<a id="u-0a843077f7ce"></a>
### `pricing.rb-pricing-collection`

`class Pricing` · [lib/ruby_llm/model/pricing.rb:L6-L7][f3]

Pricing is a category collection that stores only non-empty pricing categories and exposes them dynamically.

Initialization considers text_tokens, images, audio_tokens, and embeddings, storing a PricingCategory only when the source category exists and is not empty. Dynamic access returns the stored category for a known name or a new empty PricingCategory when absent; unknown names delegate to super. The collection reports support for the four known category names. Serialization converts stored categories to hashes. The private emptiness check treats missing data as empty, inspects standard and batch tiers, and returns false if any tier value is truthy and not 0.0; otherwise it returns true.

<a id="u-3494dfc17896"></a>
### `pricing_category.rb-pricingcategory-tiers`

`class PricingCategory` · [lib/ruby_llm/model/pricing_category.rb:L6-L9][f4]

PricingCategory holds optional standard and batch pricing tiers and exposes standard-tier convenience values.

Initialization defaults its input to an empty hash and creates a PricingTier for standard or batch only when that tier is not empty; missing tier data is treated as empty. Input, output, and cached-input convenience methods delegate to the standard tier and return nil when no standard tier exists. Indexing returns batch only for the batch key and standard otherwise. Serialization includes standard and batch only when present. The private emptiness check treats missing tier data as empty and considers a tier empty when all values are nil or 0.0.

<a id="u-0e9fded7c8ea"></a>
### `pricing_tier.rb-pricingtier-dynamic-values`

`class PricingTier` · [lib/ruby_llm/model/pricing_tier.rb:L6-L7][f5]

PricingTier stores non-zero pricing values with dynamic getter and setter access.

Initialization copies each key to a symbol and stores only truthy values not equal to 0.0. Dynamic setter names ending in equals store the first argument only when it is truthy and not 0.0; existing getter names return the stored value; unknown getter names return nil rather than delegating to super. The object reports support for setter names and existing keys. Serialization returns the underlying mutable hash.

Look up code: the commands are under "Read further" in [INDEX.md](../INDEX.md); `cbe query` and `cbe source` take a unit title or anchor from this page.

[f1]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/model/info.rb
[f2]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/model/modalities.rb
[f3]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/model/pricing.rb
[f4]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/model/pricing_category.rb
[f5]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/model/pricing_tier.rb

# Model Metadata Objects

**Capability.** Model::Info and PricingTier value objects that normalize symbol-keyed metadata with safe defaults and drop zero/nil prices.

These are the records stored in and returned by the registry. Missing modalities, capabilities, pricing, and metadata become empty defaults; timestamps flow through Utils coercion.

**Depends on.**

- [Shared Utilities](r1-shared-utilities.md) · graph-confirmed · 2 edge(s)
- [Content and Result Value Objects](r2-content-value-objects.md) · graph-only · 2 edge(s)

**Depended on by.**

- [Anthropic Adapter](r1-anthropic-adapter.md) · model-inferred · 0 edge(s)
- [Registry Record Sync](r1-model-registry-sync.md) · model-inferred · 0 edge(s)
- [Registry Catalog](r1-registry-catalog.md) · model-inferred · 0 edge(s)
- [Content and Result Value Objects](r2-content-value-objects.md) · graph-only · 2 edge(s)

Parent: [Model Registry](r1-model-registry.md)

## Units (2)

<a id="u-ae4caa9aa506"></a>
### `Info`

`class Info` · [lib/ruby_llm/model/info.rb:L6-L11][f1]

initialize reads a symbol-keyed hash: created_at and knowledge_cutoff pass through Utils.to_time and Utils.to_date; missing modalities, capabilities, pricing, and metadata become an empty Modalities, [], Pricing, and {}.

The class method default(model_id, provider) builds an Info with a synthesized name (hyphens to spaces, capitalized), assumed capabilities function_calling/streaming/vision/structured_output, text+image input and text output, and a metadata warning that capabilities may be inaccurate; other fields stay unset. supports?(capability) stringifies the argument and tests membership in capabilities; a define_method loop generates ?-predicates for function_calling, structured_output, batch, reasoning, citations, and streaming. display_name and max_tokens alias name and max_output_tokens; supports_vision?/supports_video? check modalities.input for 'image'/'video'; supports_functions? delegates to function_calling?; input_price_per_million and output_price_per_million read pricing.text_tokens.input/output. provider_class resolves the provider name via RubyLLM::Provider.resolve. type classifies output modalities in order: 'embedding', 'image', or 'audio' only when present without 'text'; 'moderation' whenever present; else 'chat'. to_h serializes every field, recursing into modalities and pricing.

**Notes.**

- condition: type's first three branches exclude 'text' output, so a model outputting text and images is 'chat', while moderation output is 'moderation' regardless of text.
- failure: Pricing drops empty categories, so pricing.text_tokens may be a fresh empty PricingCategory and input_price_per_million returns nil rather than raising.

calls: [function::RubyLLM.Utils.to_time::515][f2], [utils-utils-helpers](r1-shared-utilities.md#u-add7cf7f30e5); uses: [Modalities](r2-content-value-objects.md#u-7cc22e915a93), [Pricing](r2-content-value-objects.md#u-923e8405cbf7)

**Uncertainties.**

- provider_class depends on RubyLLM::Provider.resolve, whose implementation is outside this batch; behavior for unknown provider names is unproven.

<a id="u-925c3e76d00e"></a>
### `PricingTier`

`class PricingTier` · [lib/ruby_llm/model/pricing_tier.rb:L6-L7][f3]

initialize(data = {}) copies entries into @values keyed by symbol only when the value is truthy and not 0.0, dropping zero and nil prices.

method_missing has three cases: a setter name ending in '=' stores args.first in @values only when it is truthy and not 0.0 (a zero/nil write is silently ignored and never deletes an existing value); otherwise, if @values has the method name, it returns that value; otherwise it returns nil without calling super, so unknown readers yield nil instead of raising NoMethodError. respond_to_missing? answers true for setter-shaped names and for stored keys, deferring to super otherwise. to_h returns the internal @values hash itself.

**Notes.**

- condition: method_missing does not call super for unknown non-setter names, so misspelled price accessors silently return nil rather than raising.
- side_effect: to_h exposes the internal hash by reference; external mutation changes the tier's values.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/model/info.rb
[f2]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/utils.rb
[f3]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/model/pricing_tier.rb
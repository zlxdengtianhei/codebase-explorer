# Registry Record Sync

**Capability.** Class-level registry maintenance for model-registry records and conversion of a registry row into a RubyLLM::Model::Info with deep-symbolized fallbacks.

Use ModelMethods to keep ActiveRecord-backed registry rows in sync and to hydrate them into Model::Info objects for the catalog.

**Depends on.**

- [Model Metadata Objects](r1-model-metadata.md) · model-inferred · 0 edge(s)

Parent: [ActiveRecord & Rails Integration](r1-active-record-integration.md)

## Units (2)

<a id="u-20f33157d371"></a>
### `lib/ruby_llm/active_record/model_methods.rb:to_llm`

`def to_llm` · [lib/ruby_llm/active_record/model_methods.rb:L60-L75][f1]

Converts a registry row into a RubyLLM::Model::Info, passing id/name/provider/family/tokens/knowledge_cutoff through and building created_at from model_created_at; modalities, pricing and metadata are deep-symbolized with {} fallbacks and capabilities passed as stored.

Delegates supports?, supports_vision?, supports_functions?, type, input_price_per_million, output_price_per_million, function_calling?, structured_output?, batch?, reasoning?, citations?, streaming? and provider_class to to_llm, so all capability queries go through this conversion.

**Uncertainties.**

- Behavior of the delegated methods on Info is defined in the Model::Info class, not here.

<a id="u-bb5579e0ed14"></a>
### `model_methods-registry-sync`

`def refresh!` · [lib/ruby_llm/active_record/model_methods.rb:L10-L22][f1]

Class-level registry maintenance for model-registry records.

refresh! first refreshes the in-memory RubyLLM.models catalog, then inside a transaction iterates every model info and find_or_initialize_by(model_id, provider) followed by update! with from_llm_attributes, so failures roll back the whole sync. save_to_database performs the identical upsert loop without refreshing the catalog first. from_llm builds a new, unsaved record from a model info via from_llm_attributes. from_llm_attributes (private) maps the info into column values: model_id, name, provider, family, model_created_at, context_window, max_output_tokens, knowledge_cutoff, modalities and pricing via to_h, capabilities, and metadata. Update/validation failures inside the transaction abort the sync and propagate.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/active_record/model_methods.rb
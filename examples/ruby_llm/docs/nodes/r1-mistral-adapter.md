# Mistral Adapter

**Capability.** Mistral subclasses OpenAI, strips :stream_options from payloads, and maps its own models-list and embeddings responses.

Use this subtree for Mistral-specific payload tweaks and response parsing; chat behavior otherwise inherits OpenAI.

**Depends on.**

- [OpenAI Adapter](r1-openai-core.md) · model-inferred · 0 edge(s)
- [Content and Result Value Objects](r2-content-value-objects.md) · graph-only · 1 edge(s)
- [Mistral Capabilities](r2-provider-mistral-capabilities.md) · graph-only · 1 edge(s)

Parent: [OpenAI Family](r1-openai-family.md)

## Units (4)

<a id="u-5897395444ae"></a>
### `Mistral`

`class Mistral < OpenAI` · [lib/ruby_llm/providers/mistral.rb:L6-L11][f1]

Mistral subclasses OpenAI and includes Mistral::Chat, Models, and Embeddings.

api_base is the constant 'https://api.mistral.ai/v1'. headers returns a single Authorization bearer header from @config.mistral_api_key; a nil key still produces a nil bearer value since no compaction occurs. Singleton capabilities returns Mistral::Capabilities; configuration_requirements lists only :mistral_api_key.

inherits: [OpenAI](r1-openai-core.md#u-cbb3f359bee0)

<a id="u-d7ae7dfe3206"></a>
### `RubyLLM.Providers.Mistral.Chat.render_payload`

`def render_payload(messages, tools:, temperature:, model:, stream: false, schema: nil)` · [lib/ruby_llm/providers/mistral/chat.rb:L15-L19][f2]

Builds the Mistral chat payload by calling the superclass implementation with the full parameter list, then removes the :stream_options key from the resulting hash before returning it.

All other payload content is whatever super produces; the deletion makes the payload acceptable to Mistral, which does not take OpenAI's stream_options field.

**Uncertainties.**

- The superclass render_payload is defined outside this file; its output shape and argument handling are unproven here.

<a id="u-4f984522e290"></a>
### `RubyLLM.Providers.Mistral.Embeddings.parse_embedding_response`

`def parse_embedding_response(response, model:, text:)` · [lib/ruby_llm/providers/mistral/embeddings.rb:L21-L29][f3]

Converts a Mistral embeddings HTTP response into an Embedding.

It reads usage prompt_tokens (defaulting to 0 when absent) and maps each entry of data['data'] to its 'embedding' vector. When exactly one vector is returned and the requested text was not an array, the vector list is unwrapped to the single vector. It constructs Embedding.new with vectors:, model:, and input_tokens:.

uses: [RubyLLM.Providers.Mistral.Embeddings.parse_embedding_response](r1-mistral-adapter.md#u-4f984522e290)

**Uncertainties.**

- Embedding's constructor contract and behavior when data['data'] is nil are defined outside this file.

<a id="u-8db0846872c1"></a>
### `RubyLLM.Providers.Mistral.Models.parse_list_models_response`

`def parse_list_models_response(response, slug, capabilities)` · [lib/ruby_llm/providers/mistral/models.rb:L20-L44][f4]

Maps the Mistral models-list response into Model::Info records.

For each entry of Array(response.body['data']) it resolves a release date via capabilities.release_date_for, parses it with Time.parse only when present (otherwise created_at is nil), and fills name, family, context_window, max_output_tokens, modalities, capabilities, and pricing from the capabilities module. metadata records the raw 'object' and 'owned_by' fields.

**Uncertainties.**

- capabilities.format_display_name, model_family, context_window_for, max_tokens_for, modalities_for, capabilities_for, and pricing_for are defined outside this file; Time.parse raises on malformed release dates.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/providers/mistral.rb
[f2]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/providers/mistral/chat.rb
[f3]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/providers/mistral/embeddings.rb
[f4]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/providers/mistral/models.rb
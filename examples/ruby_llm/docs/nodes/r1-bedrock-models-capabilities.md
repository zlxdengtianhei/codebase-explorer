# Bedrock Models & Capabilities

**Capability.** Fetches and signs the regional foundation-models endpoint, filters summaries to claude model ids, and derives context windows, modalities, capabilities, families, and standard/batch pricing per model id.

Use list_models plus parse_list_models_response for catalog hydration, and the Capabilities methods for per-id metadata with MODEL_FAMILIES regex lookup.

**Depends on.**

- [SigV4 Signing](r1-bedrock-signing.md) · model-inferred · 0 edge(s)
- [Registry Catalog](r1-registry-catalog.md) · graph-only · 1 edge(s)
- [Provider Connection](r2-connection.md) · graph-only · 1 edge(s)

Parent: [Bedrock Adapter](r1-bedrock-adapter.md)

## Units (8)

<a id="u-f7193af023e2"></a>
### `RubyLLM.Providers.Bedrock.Models.list_models`

`def list_models` · [lib/ruby_llm/providers/bedrock/models.rb:L8-L17][f1]

Fetches the Bedrock foundation-model catalog: it constructs the regional management endpoint https://bedrock.<bedrock_region>.amazonaws.com/foundation-models, signs the full URL for GET, performs @connection.get merging the signature's headers into the request, then parses via parse_list_models_response(response, slug, capabilities).

Note it runs as an instance method before module_function in this module, so it relies on instance state (@config, @connection, slug, capabilities) provided by the including class. Signing and connection errors propagate to the caller; only successful responses reach the parser.

uses: [signing-rb-signer](r1-bedrock-signing.md#u-ef4167d839ba); calls: [connection.rb-connection](r2-connection.md#u-53be52e4979e)

**Uncertainties.**

- Which sign_request implementation runs (Bedrock provider vs Signing::Signer) is not resolvable from this file.

<a id="u-98c56ad03612"></a>
### `RubyLLM.Providers.Bedrock.Models.parse_list_models_response`

`def parse_list_models_response(response, slug, capabilities)` · [lib/ruby_llm/providers/bedrock/models.rb:L25-L51][f1]

Turns the Bedrock model-list response into Model::Info entries, keeping only summaries whose modelId includes 'claude'.

For each surviving entry it reads model_data['modelId'], rewrites the id with model_id_with_region (which can add a region prefix such as 'us.'), and fills every field from the Capabilities helpers: display name (falling back to capabilities.format_display_name when modelName is missing), family, context window, max output tokens, modalities, capabilities, and pricing. Metadata carries providerName plus per-model arrays, using || defaults ([] or false) when the API omits inference types, streaming support, or modality lists; created_at is always nil.

**Notes.**

- condition: model_id_with_region returns the id unchanged unless inferenceTypesSupported includes INFERENCE_PROFILE without ON_DEMAND; otherwise it strips a leading two-letter region prefix and prepends the prefix derived from bedrock_region ('us' when the region is empty).

**Uncertainties.**

- model_id_with_region and create_model_info read @config even though the region helper is module_function; the containing object must expose @config for these paths to work.

<a id="u-c89c9b6c537d"></a>
### `capabilities-rb-capabilities-helpers`

`def max_tokens_for(_model_id)` · [lib/ruby_llm/providers/bedrock/capabilities.rb:L17-L19][f2]

Collects the Bedrock capability lookups that are single expressions or regex predicates.

max_tokens_for always returns 4096 and model_type always returns 'chat', ignoring the model id. The seven supports_* predicates (chat, streaming, images, vision, functions, json_mode) each return true only when the model id matches /anthropic\.claude/, so non-Claude ids report false; supports_audio? and supports_structured_output? return false unconditionally. input_price_for/output_price_for delegate to model_family and fall back to the 0.1/0.2 defaults when PRICES has no entry for the family. format_display_name humanizes the id (dashes to spaces, keeps only the segment after the last dot, capitalizes words); default_input_price/default_output_price return the literal fallback prices. The frozen MODEL_FAMILIES and PRICES constants are declared inside this module.

calls: [RubyLLM.Providers.Bedrock.Capabilities.model_family](r1-bedrock-models-capabilities.md#u-d616ea5c4986)

<a id="u-538234723903"></a>
### `RubyLLM.Providers.Bedrock.Capabilities.capabilities_for`

`def capabilities_for(model_id)` · [lib/ruby_llm/providers/bedrock/capabilities.rb:L126-L141][f2]

Builds the capability string list for a model id through four independent conditions: 'streaming' is appended when the id matches /anthropic\.claude/; 'function_calling' when supports_functions?

is true (same Claude regex); 'reasoning' when the id matches /claude-3-7/; and both 'batch' and 'citations' when the id matches /claude-3\.5|claude-3-7/. Ids outside these patterns return an empty array. Conditions compose, so a claude-3-7 id receives streaming, function_calling, reasoning, batch, and citations.

<a id="u-5c59c354a184"></a>
### `RubyLLM.Providers.Bedrock.Capabilities.context_window_for`

`def context_window_for(model_id)` · [lib/ruby_llm/providers/bedrock/capabilities.rb:L10-L15][f2]

Returns the Bedrock context-window size for a model id: 100,000 for ids matching /anthropic\.claude-2/, and 200,000 for everything else, including Claude 3+ and unknown ids.

Pure function of the id string.

<a id="u-7a5c0066cc58"></a>
### `RubyLLM.Providers.Bedrock.Capabilities.modalities_for`

`def modalities_for(model_id)` · [lib/ruby_llm/providers/bedrock/capabilities.rb:L112-L124][f2]

Builds the modality hash {input: ['text'], output: ['text']} for a model id.

When the id matches /anthropic\.claude/ and supports_vision?(model_id) is true (which itself requires the same /anthropic\.claude/ match), 'image' and 'pdf' are appended to the input list. Non-Claude ids get text-only modalities. The input list is mutated in place, so the returned hash for Claude ids always has four input entries.

**Uncertainties.**

- Because supports_vision? uses the same regex as the outer condition, the extra vision check is currently redundant; any behavioral change to supports_vision? would alter which ids gain image/pdf.

<a id="u-d616ea5c4986"></a>
### `RubyLLM.Providers.Bedrock.Capabilities.model_family`

`def model_family(model_id)` · [lib/ruby_llm/providers/bedrock/capabilities.rb:L81-L83][f2]

Maps a Bedrock model id to a pricing/capability family symbol by scanning the frozen MODEL_FAMILIES regex table with find; the first matching pattern's family wins.

Note the table order means /claude-3-sonnet/ and later 3.5/3.7 sonnet patterns all resolve to :claude3_sonnet. Ids matching no pattern return :other. Ordering matters: /claude-3-5-sonnet/ also matches /claude-3-sonnet/? No — the patterns include version digits, but ids such as 'anthropic.claude-3-5-sonnet' match /anthropic\.claude-3-5-sonnet/ before reaching earlier patterns only because pattern order is preserved; ids like 'claude-3-5-haiku' match the opus/sonnet/haiku patterns in listed order.

**Uncertainties.**

- Exact match precedence depends on Hash iteration order, which Ruby guarantees as insertion order, but callers relying on overlapping patterns (e.g., a 3.7 sonnet id also matching the plain 3-sonnet pattern) inherit that ordering.

<a id="u-b42ad68cc99e"></a>
### `RubyLLM.Providers.Bedrock.Capabilities.pricing_for`

`def pricing_for(model_id)` · [lib/ruby_llm/providers/bedrock/capabilities.rb:L143-L163][f2]

Produces the pricing structure for a model id as {text_tokens: {standard: {...}, batch: {...}}}.

It resolves the family via model_family and looks PRICES up with fetch, falling back to the default 0.1/0.2 per-million prices for unknown families (e.g., :other). Standard pricing uses the raw input/output prices; batch pricing halves both values. Output is purely derived; nothing is memoized or mutated.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/providers/bedrock/models.rb
[f2]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/providers/bedrock/capabilities.rb
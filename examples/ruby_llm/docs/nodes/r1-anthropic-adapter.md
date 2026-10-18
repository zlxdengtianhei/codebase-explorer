# Anthropic Adapter

**Capability.** The Anthropic provider: claude-family capability derivation and pricing, native content payload building, a deliberate embeddings unsupported stub, models-list parsing with usage extractors, and streaming chunk/error handling that reuses the chat endpoint.

Use this subtree for all Anthropic wire-format and metadata behavior. Capabilities are regex-driven per Claude family; Content.new wraps payloads in RubyLLM::Content::Raw; embed raises unconditionally.

**Depends on.**

- [Model Metadata Objects](r1-model-metadata.md) · model-inferred · 0 edge(s)
- [Shared Streaming](r2-streaming-shared.md) · graph-only · 1 edge(s)

Parent: [Provider Framework](r1-provider-framework.md)

## Units (18)

<a id="u-3366212c86dc"></a>
### `Anthropic`

`class Anthropic < Provider` · [lib/ruby_llm/providers/anthropic.rb:L6-L14][f1]

Anthropic subclasses Provider and mixins Chat, Embeddings, Media, Models, Streaming, and Tools from the Anthropic namespace.

api_base is the constant 'https://api.anthropic.com'. headers returns 'x-api-key' from @config.anthropic_api_key and a pinned 'anthropic-version' of '2023-06-01'; there is no filtering, so a nil key is passed through as a nil header value. The singleton capabilities returns the Anthropic::Capabilities module and configuration_requirements lists only :anthropic_api_key.

inherits: [provider.rb-provider-instance](r2-provider-base.md#u-961fc10a6a0f)

**Uncertainties.**

- Behavior of the included Chat/Embeddings/Streaming/Tools mixins lies outside this batch.

<a id="u-89f70f7c6401"></a>
### `capabilities-rb-predicates`

`def supports_vision?(model_id)` · [lib/ruby_llm/providers/anthropic/capabilities.rb:L29-L31][f2]

Capability predicates keyed on model-id substrings.

supports_vision? is true unless the id matches /claude-[12]/, so Claude 1/2 ids lack vision while unknown ids claim it. supports_functions? and supports_json_mode? are identical: true only for ids containing 'claude-3'. supports_extended_thinking? is true only for /claude-3-7-sonnet/. model_type ignores its argument and always returns 'chat'.

<a id="u-3ff92a404db0"></a>
### `capabilities-rb-price-lookups`

`def get_input_price(model_id)` · [lib/ruby_llm/providers/anthropic/capabilities.rb:L21-L23][f2]

Price lookups and literal defaults.

get_input_price and get_output_price call PRICES.dig(model_family(model_id), :input/:output) with fallbacks to default_input_price (3.0) and default_output_price (15.0). As written the dig never matches: model_family returns Strings while PRICES keys are Symbols (e.g. :'claude-3-7-sonnet'), so both getters always return the defaults.

calls: [RubyLLM.Providers.Anthropic.Capabilities.model_family](r1-anthropic-adapter.md#u-1cf2f807f577)

**Uncertainties.**

- The String-vs-Symbol key mismatch makes the PRICES branch unreachable in these getters; intent cannot be established from this file.

<a id="u-70271394f430"></a>
### `RubyLLM.Providers.Anthropic.Capabilities.capabilities_for`

`def capabilities_for(model_id)` · [lib/ruby_llm/providers/anthropic/capabilities.rb:L92-L103][f2]

Accumulates a capability list from ['streaming'] with independent conditions: ids matching /claude-3/ add 'function_calling' and 'batch'; /claude-3-7|-4/ adds 'reasoning'; /claude-3\.5|claude-3-7/ adds 'citations'.

A claude-3-7-sonnet id collects all five entries; a claude-2 id returns only streaming. No deduplication is applied.

<a id="u-26aca9ad9658"></a>
### `RubyLLM.Providers.Anthropic.Capabilities.determine_context_window`

`def determine_context_window(_model_id)` · [lib/ruby_llm/providers/anthropic/capabilities.rb:L10-L12][f2]

Returns a fixed 200,000-token context window for every Anthropic model id, ignoring the argument.

<a id="u-6af72bcab9e3"></a>
### `RubyLLM.Providers.Anthropic.Capabilities.determine_max_tokens`

`def determine_max_tokens(model_id)` · [lib/ruby_llm/providers/anthropic/capabilities.rb:L14-L19][f2]

Chooses default max output tokens by substring match: ids containing 'claude-3-7-sonnet' or 'claude-3-5' get 8192; every other id, including unknown families, gets 4096.

<a id="u-cd84f4f1c031"></a>
### `RubyLLM.Providers.Anthropic.Capabilities.modalities_for`

`def modalities_for(model_id)` · [lib/ruby_llm/providers/anthropic/capabilities.rb:L78-L90][f2]

Returns a fresh modalities hash with text input and text output for every call.

When the id does not match /claude-[12]/, 'image' and 'pdf' are appended to the input list; ids containing 'claude-1' or 'claude-2' fragments stay text-only.

<a id="u-1cf2f807f577"></a>
### `RubyLLM.Providers.Anthropic.Capabilities.model_family`

`def model_family(model_id)` · [lib/ruby_llm/providers/anthropic/capabilities.rb:L45-L55][f2]

Maps a model id to a family name via ordered regex cases: claude-3-7-sonnet, claude-3-5-sonnet, claude-3-5-haiku, claude-3-opus, claude-3-sonnet, claude-3-haiku, in that order.

Everything else — including claude-2 and unrecognized ids — falls to 'claude-2'. Returns Strings, which is why PRICES.dig in the price getters never matches its Symbol keys.

<a id="u-216602ceefeb"></a>
### `RubyLLM.Providers.Anthropic.Capabilities.pricing_for`

`def pricing_for(model_id)` · [lib/ruby_llm/providers/anthropic/capabilities.rb:L105-L130][f2]

Builds per-million pricing from PRICES using model_family(model_id).to_sym, so unlike the get_*_price getters this lookup does hit PRICES; families without an entry (e.g. id 'claude-3-sonnet', family 'claude-2' key present but Symbol mismatch aside, fetch falls back) use defaults input 3.0, output 15.0.

Output always contains text_tokens.standard and text_tokens.batch, with batch at exactly half the standard input/output rates. Only when the id matches /claude-3-7/ does it additionally add reasoning_output_per_million = output * 2.5 (standard) and output * 1.25 (batch).

calls: [RubyLLM.Providers.Anthropic.Capabilities.model_family](r1-anthropic-adapter.md#u-1cf2f807f577)

<a id="u-859b8da27b76"></a>
### `content.rb-payload-resolution`

`def resolve_payload(text:, parts:, cache:, cache_control:, extras:)` · [lib/ruby_llm/providers/anthropic/content.rb:L23-L33][f3]

Private singleton helpers behind Anthropic::Content.new.

resolve_payload returns Array(parts) when parts is truthy, bypassing text entirely; raises ArgumentError 'text or parts must be provided' when text is nil and parts is absent; otherwise builds a text block merged with extras. determine_cache_control returns the explicit cache_control argument when truthy, else {type: 'ephemeral'} when the cache flag is set, else nil, in which case no :cache_control key is added.

<a id="u-b83ca443131a"></a>
### `RubyLLM.Providers.Anthropic.Content.new`

`def new(text = nil, cache: false, cache_control: nil, parts: nil, **extras)` · [lib/ruby_llm/providers/anthropic/content.rb:L9-L19][f3]

Builds an Anthropic-native content payload and wraps it in RubyLLM::Content::Raw.

It delegates payload construction to the private resolve_payload helper: when parts is provided the payload is Array(parts) and text is ignored; otherwise a single {type: 'text', text: ...} block merged with extras is wrapped in a one-element array, with :cache_control added only when a value is determined. An ArgumentError is raised when neither text nor parts is given. The Raw wrapper is returned on all success paths; no state is mutated.

calls: [content.rb-payload-resolution](r1-anthropic-adapter.md#u-859b8da27b76)

**Uncertainties.**

- How RubyLLM::Content::Raw is consumed downstream is defined outside this file.

<a id="u-f3ed357903a2"></a>
### `RubyLLM.Providers.Anthropic.Embeddings.embed`

`def embed` · [lib/ruby_llm/providers/anthropic/embeddings.rb:L10-L12][f4]

Unconditionally raises an Error stating that Anthropic does not support embeddings; it is a deliberate unsupported-operation stub.

The source uses the non-parenthesized form `Error "Anthropic doesn't support embeddings"`. Aliases route embedding_url, render_embedding_payload, and parse_embedding_response to this method, so any embeddings operation against Anthropic raises here.

**Notes.**

- failure: All three embedding lifecycle names (embedding_url, render_embedding_payload, parse_embedding_response) are aliases of this raising method.

raises: [RubyLLM.Providers.Anthropic.Embeddings.embed](r1-anthropic-adapter.md#u-f3ed357903a2)

**Uncertainties.**

- The `Error` constant resolved here is not defined in this file; its class hierarchy and message handling are unproven.

<a id="u-8f764a3cab85"></a>
### `RubyLLM.Providers.Anthropic.Models.parse_list_models_response`

`def parse_list_models_response(response, slug, capabilities)` · [lib/ruby_llm/providers/anthropic/models.rb:L14-L32][f5]

Maps the Anthropic models-list response into Model::Info records.

It iterates Array(response.body['data']); for each entry it reads 'id' and 'display_name' and fills family, created_at (Time.parse of the 'created_at' string, which raises on malformed input), context_window, max_output_tokens, modalities, capabilities, and pricing by delegating to the passed capabilities object. metadata is always {}. The result is an array whose content for unknown ids depends entirely on the capabilities methods.

uses: [models.rb-anthropic-usage-extractors](r1-anthropic-adapter.md#u-7061400b76a0)

**Uncertainties.**

- The capabilities argument's methods (model_family, determine_context_window, determine_max_tokens, modalities_for, capabilities_for, pricing_for) are defined outside this file; their failure modes here are unproven.
- Time.parse raises ArgumentError on unparseable created_at strings; response shape guarantees are not visible.

<a id="u-7061400b76a0"></a>
### `models.rb-anthropic-usage-extractors`

`def extract_model_id(data)` · [lib/ruby_llm/providers/anthropic/models.rb:L34-L36][f5]

Dig-based extractors over Anthropic event/usage payloads in the Models module.

extract_model_id reads data['message']['model']; extract_input_tokens reads ['message']['usage']['input_tokens']; extract_output_tokens and extract_cached_tokens try the message-nested usage first, falling back to top-level ['usage'][key]. extract_cache_creation_tokens reads cache_creation_input_tokens at either nesting; when absent it takes the cache_creation Hash (message-nested then top-level) and, only if it is a Hash, returns the sum of its compact values, otherwise nil. All are nil-safe through dig.

<a id="u-862f622f3596"></a>
### `RubyLLM.Providers.Anthropic.Streaming.build_chunk`

`def build_chunk(data)` · [lib/ruby_llm/providers/anthropic/streaming.rb:L14-L25][f6]

Constructs a Chunk from one Anthropic streaming event.

It always sets role :assistant and pulls model_id, content (delta text), input/output token counts, cached and cache-creation token counts, and tool calls from the event data via the Models extractors and extract_tool_calls. Missing fields surface as whatever those extractors return for absent keys.

calls: [models.rb-anthropic-usage-extractors](r1-anthropic-adapter.md#u-7061400b76a0)

**Uncertainties.**

- extract_tool_calls is not defined in this file; its return values and nil behavior here are unproven.

<a id="u-52a621a3f239"></a>
### `RubyLLM.Providers.Anthropic.Streaming.json_delta?`

`def json_delta?(data)` · [lib/ruby_llm/providers/anthropic/streaming.rb:L27-L29][f6]

Returns true only when the event type is 'content_block_delta' and the nested delta type is 'input_json_delta'; false otherwise.

<a id="u-449fc8ec10ba"></a>
### `RubyLLM.Providers.Anthropic.Streaming.parse_streaming_error`

`def parse_streaming_error(data)` · [lib/ruby_llm/providers/anthropic/streaming.rb:L31-L41][f6]

Detects errors inside Anthropic streaming payloads.

It parses the input as JSON — JSON.parse raises on invalid JSON and that exception propagates — and returns nil unless the payload's 'type' equals 'error'. For error payloads it maps 'overloaded_error' to [529, message] and every other error type to [500, message], where message is error_data['error']['message'].

<a id="u-666bac0f17c3"></a>
### `RubyLLM.Providers.Anthropic.Streaming.stream_url`

`def stream_url` · [lib/ruby_llm/providers/anthropic/streaming.rb:L10-L12][f6]

Returns the streaming endpoint by delegating to completion_url, which is defined outside this file; streaming therefore reuses the non-streaming chat endpoint path.

**Uncertainties.**

- completion_url's value depends on code not present in this batch.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/providers/anthropic.rb
[f2]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/providers/anthropic/capabilities.rb
[f3]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/providers/anthropic/content.rb
[f4]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/providers/anthropic/embeddings.rb
[f5]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/providers/anthropic/models.rb
[f6]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/providers/anthropic/streaming.rb
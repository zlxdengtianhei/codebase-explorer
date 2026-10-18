# Gemini Adapter

**Capability.** Implements Gemini chat, streaming, model listing, and audio transcription, plus a regex-driven static capability/pricing profile keyed by model id.

Read the capabilities unit to see how model-id patterns map to context windows, prices, and modalities; the transcription and streaming units cover the remaining endpoints. VertexAI builds on this subtree.

**Children.**

- [VertexAI Adapter](r2-provider-vertexai.md) `r2-provider-vertexai` · 8 unit(s)

**Depends on.**

- [Provider Connection](r2-connection.md) · graph-confirmed · 2 edge(s)
- [Content and Result Value Objects](r2-content-value-objects.md) · graph-confirmed · 1 edge(s)
- [Attachments & Images](r1-content-media.md) · graph-only · 1 edge(s)
- [Shared Streaming](r2-streaming-shared.md) · graph-only · 1 edge(s)

**Depended on by.**

- [acts\_as Declarations](r2-acts-as-declarations.md) · model-inferred · 0 edge(s)
- [VertexAI Adapter](r2-provider-vertexai.md) · containment · → 0 / ← 0 edge(s) (ancestor direct units and descendant subtree; → follows ` r2-provider-vertexai ` → ` r2-provider-gemini `) · VertexAI subclasses Gemini, reusing its mixins and changing URLs and embeddings.

Parent: [Provider Adapters](r2-providers.md)

## Units (22)

<a id="u-88ddd80133ac"></a>
### `RubyLLM.Providers.Gemini.Capabilities.context_window_for`

`def context_window_for(model_id)` · [lib/ruby_llm/providers/gemini/capabilities.rb:L10-L21][f1]

Maps a Gemini model id to its context window size via ordered regex case match.

Returns 1,048,576 for gemini-2.5-pro-exp-03-25, the 2.0-flash variants, and 1.5-flash ids; 2,097,152 for gemini-1.5-pro; 8,192 for gemini-embedding-exp; 2,048 for text-embedding-004/embedding-001; 7,168 for aqa; nil for imagen-3; 32,768 for anything else.

**Uncertainties.**

- Case order sets precedence; an id matching several patterns takes the first branch.

<a id="u-13806071c534"></a>
### `capabilities-capability-predicates`

`def supports_vision?(model_id)` · [lib/ruby_llm/providers/gemini/capabilities.rb:L49-L53][f1]

Groups the boolean capability predicates for Gemini model ids; all are pure regex checks.

supports_vision? returns false for embedding/aqa ids, otherwise true when the id matches /gemini|flash|pro|imagen/. supports_video? is true only for ids matching /gemini/. supports_functions? excludes embedding, aqa, flash-lite, imagen, and gemini-2.0-flash-lite ids, then matches /gemini|pro|flash/. supports_json_mode? excludes embedding, aqa, imagen, gemini-2.0-flash-lite, and gemini-2.5-pro-exp-03-25, then matches /gemini|pro|flash/. supports_caching? excludes flash-lite, gemini-2.5-pro-exp-03-25, aqa, imagen, and embedding ids, then matches /gemini|pro|flash/. supports_tuning? is true only for gemini-1.5-flash and gemini-1.5-flash-8b. supports_audio? is true for any id matching /gemini|pro|flash/ with no exclusions. Each predicate's first-match/exclusion order determines the outcome for overlapping patterns.

<a id="u-db3e29495e18"></a>
### `RubyLLM.Providers.Gemini.Capabilities.max_tokens_for`

`def max_tokens_for(model_id)` · [lib/ruby_llm/providers/gemini/capabilities.rb:L23-L33][f1]

Maps a Gemini model id to its maximum output token count by ordered regex case: 64,000 for gemini-2.5-pro-exp-03-25; 8,192 for the 2.0-flash variants and 1.5-flash/8b/pro ids; nil for gemini-embedding-exp; 768 for text-embedding-004/embedding-001; 4 for imagen-3; 4,096 otherwise.

<a id="u-cbfe974cc5bd"></a>
### `capabilities-defaults`

`def context_length(model_id)` · [lib/ruby_llm/providers/gemini/capabilities.rb:L146-L148][f1]

Groups three trivial accessors: context_length delegates to context_window_for(model_id) unchanged; default_input_price returns the constant 0.075; default_output_price returns 0.30.

The defaults act as fallbacks for price families missing from PRICES.

<a id="u-cfbdbf93a3e1"></a>
### `RubyLLM.Providers.Gemini.Capabilities.input_price_for`

`def input_price_for(model_id)` · [lib/ruby_llm/providers/gemini/capabilities.rb:L35-L40][f1]

Resolves the per-million input price from the PRICES table keyed by pricing family, falling back to default_input_price when the family lacks :input.

If the id is a long-context model and its context window exceeds 128,000 tokens, the base price is doubled; otherwise the base price is returned.

calls: [RubyLLM.Providers.Gemini.Capabilities.pricing_family](r2-provider-gemini.md#u-a3916e297c7b), [RubyLLM.Providers.Gemini.Capabilities.long_context_model?](r2-provider-gemini.md#u-7c833c47ade4), [RubyLLM.Providers.Gemini.Capabilities.context_window_for](r2-provider-gemini.md#u-88ddd80133ac)

**Uncertainties.**

- For a long-context id whose context_window_for returns nil, the nil > 128_000 comparison would raise; no such long-context id currently maps to nil in context_window_for.

<a id="u-50e91544e3c9"></a>
### `RubyLLM.Providers.Gemini.Capabilities.output_price_for`

`def output_price_for(model_id)` · [lib/ruby_llm/providers/gemini/capabilities.rb:L42-L47][f1]

Same structure as input_price_for but reads :output from the PRICES family entry with default_output_price as fallback, doubling the base output price for long-context ids whose context window exceeds 128,000 tokens.

calls: [RubyLLM.Providers.Gemini.Capabilities.pricing_family](r2-provider-gemini.md#u-a3916e297c7b)

<a id="u-7c833c47ade4"></a>
### `RubyLLM.Providers.Gemini.Capabilities.long_context_model?`

`def long_context_model?(model_id)` · [lib/ruby_llm/providers/gemini/capabilities.rb:L142-L144][f1]

True when the id matches gemini-1.5-pro, gemini-1.5-flash, or gemini-1.5-flash-8b; false otherwise.

Used by the price methods to decide context-length doubling.

<a id="u-a3916e297c7b"></a>
### `RubyLLM.Providers.Gemini.Capabilities.pricing_family`

`def pricing_family(model_id)` · [lib/ruby_llm/providers/gemini/capabilities.rb:L126-L140][f1]

Maps a model id to a PRICES key in priority order: :pro_2_5, :flash_lite_2, :flash_2, :flash_8b, :flash, :pro, :gemini_embedding, :embedding, :imagen, :aqa, else :base.

:base has no PRICES entry, so price lookups on it fall back to default pricing.

**Uncertainties.**

- /embedding/ precedes /imagen/, so an id matching both yields :embedding.

<a id="u-8c1e405cf91e"></a>
### `RubyLLM.Providers.Gemini.Capabilities.pricing_for`

`def pricing_for(model_id)` · [lib/ruby_llm/providers/gemini/capabilities.rb:L243-L277][f1]

Builds a nested pricing hash.

Standard input/output prices come from the PRICES entry for the pricing family or, on fetch failure, the input/output defaults. A batch tier at 50% of standard is always produced, treating missing standard values as 0. cached_input_per_million is added only when prices[:input_hit] exists — a key no PRICES entry defines — so that branch is unreachable with the supplied table. Ids matching /embedding|gemini-embedding/ additionally get an :embeddings tier using prices[:price] or 0.002. Unlike input_price_for/output_price_for, long-context pricing is not doubled here.

calls: [RubyLLM.Providers.Gemini.Capabilities.pricing_family](r2-provider-gemini.md#u-a3916e297c7b)

<a id="u-35f4cb3c9289"></a>
### `RubyLLM.Providers.Gemini.Capabilities.modalities_for`

`def modalities_for(model_id)` · [lib/ruby_llm/providers/gemini/capabilities.rb:L213-L230][f1]

Builds input/output modality lists starting from text-only and appending conditionally: 'image' and 'pdf' to input when supports_vision?

holds, 'video' when supports_video? holds, 'audio' when the id matches /audio/, 'embeddings' to output when the id matches /embedding|gemini-embedding/. For imagen ids the output list is replaced entirely with ['image'].

calls: [capabilities-capability-predicates](r2-provider-gemini.md#u-13806071c534)

<a id="u-39927ed91517"></a>
### `RubyLLM.Providers.Gemini.Capabilities.capabilities_for`

`def capabilities_for(model_id)` · [lib/ruby_llm/providers/gemini/capabilities.rb:L232-L241][f1]

Returns a feature list that always starts with 'streaming', appending 'function_calling' when supports_functions?

is true, 'structured_output' when supports_json_mode? is true, 'batch' when the id matches /embedding|flash/, 'caching' when supports_caching? is true, and 'fine_tuning' when supports_tuning? is true.

calls: [capabilities-capability-predicates](r2-provider-gemini.md#u-13806071c534)

<a id="u-7335c63554a9"></a>
### `RubyLLM.Providers.Gemini.Capabilities.model_family`

`def model_family(model_id)` · [lib/ruby_llm/providers/gemini/capabilities.rb:L109-L124][f1]

Maps a model id to a family label via ordered regex cases: the specific gemini 2.5-pro-exp, 2.0-flash(-lite), and 1.5 variants first, then gemini-embedding-exp, text-embedding-004 ('embedding4'), embedding-001 ('embedding1'), aqa, imagen-3; any unmatched id returns 'other'.

**Uncertainties.**

- Case order decides overlaps such as gemini-1.5-flash-8b before gemini-1.5-flash.

<a id="u-20305b5833cc"></a>
### `RubyLLM.Providers.Gemini.Capabilities.model_type`

`def model_type(model_id)` · [lib/ruby_llm/providers/gemini/capabilities.rb:L101-L107][f1]

Classifies a model id as 'embedding' when it matches /text-embedding|embedding|gemini-embedding/, 'image' when it matches /imagen/, else 'chat'.

The embedding branch is checked first, so an id containing both patterns classifies as embedding.

<a id="u-e71c85aecd17"></a>
### `RubyLLM.Providers.Gemini.Capabilities.format_display_name`

`def format_display_name(model_id)` · [lib/ruby_llm/providers/gemini/capabilities.rb:L73-L83][f1]

Derives a display name from a model id: strips a leading 'models/' prefix, splits on hyphens, capitalizes each segment, inserts a space before version-number substrings, collapses whitespace, rewrites 'Aqa' to 'AQA', and strips the result.

**Uncertainties.**

- Exact spacing for ids with unusual digit placement depends on the gsub chain and is not verified.

<a id="u-8669c0b7f7d4"></a>
### `models-url`

`def models_url` · [lib/ruby_llm/providers/gemini/models.rb:L10-L12][f2]

models_url returns the constant string 'models', the collection endpoint for listing Gemini models.

<a id="u-80ea2d67ccaf"></a>
### `RubyLLM.Providers.Gemini.Models.parse_list_models_response`

`def parse_list_models_response(response, slug, capabilities)` · [lib/ruby_llm/providers/gemini/models.rb:L14-L36][f2]

Converts a Gemini models list response into Model::Info records.

Each entry of body['models'] has its 'name' stripped of the 'models/' prefix for the id; context and output limits prefer the API's inputTokenLimit/outputTokenLimit and fall back to the Capabilities tables. Family, modalities, capabilities, and pricing all come from the Capabilities module for the resolved id, and metadata carries version, description, and supportedGenerationMethods. created_at is always nil.

uses: [lib/ruby_llm/providers/gemini/capabilities.rb:Capabilities][f1]

**Uncertainties.**

- Behavior when 'name' is missing relies on Hash#gsub raising; not guarded here.

<a id="u-22b42902bc83"></a>
### `streaming-chunk`

`def stream_url` · [lib/ruby_llm/providers/gemini/streaming.rb:L8-L10][f3]

Groups streaming request setup and chunk construction.

stream_url returns 'models/<model>:streamGenerateContent?alt=sse' using @model for SSE streaming. build_chunk builds a Chunk with role :assistant, model_id from data['modelVersion'], content from the first candidate's text parts joined (nil when no candidates, no parts, or no text parts), input_tokens from usageMetadata.promptTokenCount, output_tokens as candidatesTokenCount plus thoughtsTokenCount when positive else nil, and tool_calls extracted from the chunk data.

<a id="u-1cb7f51208f9"></a>
### `streaming-extractors`

`def extract_model_id(data)` · [lib/ruby_llm/providers/gemini/streaming.rb:L25-L27][f3]

Groups the streaming field extractors and error parsing.

extract_model_id returns data['modelVersion'] directly. extract_content returns nil when candidates are absent or empty, digs the first candidate's content parts, returns nil when parts are missing, and joins the text of text-bearing parts, returning nil if none. extract_input_tokens reads usageMetadata.promptTokenCount (nil when absent). extract_output_tokens sums candidatesTokenCount and thoughtsTokenCount (missing counts as 0) and returns nil when the total is zero. parse_streaming_error JSON-parses the payload and returns [code, message] from error_data['error']; on JSON::ParserError it logs a debug message and returns [500, "Failed to parse error: <raw>"] so callers always receive a code/message pair.

<a id="u-a199f66ada8b"></a>
### `RubyLLM.Providers.Gemini.Transcription.transcribe`

`def transcribe(audio_file, model:, language:, **options)` · [lib/ruby_llm/providers/gemini/transcription.rb:L10-L15][f4]

Transcribes an audio file through Gemini's generateContent endpoint.

It wraps the input in an Attachment, renders the payload (which validates the attachment is audio), posts it via @connection to models/<model>:generateContent, and parses the response into a RubyLLM::Transcription. Language and option keys pass through render_transcription_payload.

uses: [lib/ruby_llm/transcription.rb][f5]; calls: [connection.rb-connection](r2-connection.md#u-53be52e4979e), [transcription-payload](r2-provider-gemini.md#u-292deb37f1b0)

<a id="u-292deb37f1b0"></a>
### `transcription-payload`

`def transcription_url(model)` · [lib/ruby_llm/providers/gemini/transcription.rb:L19-L21][f4]

Groups request construction for transcription.

transcription_url returns 'models/<model>:generateContent'. render_transcription_payload builds a user turn containing the prompt text and the inline audio part, raising UnsupportedAttachmentError with the mime type when the attachment is not audio; it adds generationConfig only when non-empty and safetySettings only when options supply them. build_generation_config sets responseMimeType from options (default 'text/plain', omitted when nil), temperature only when the key is present, and maxOutputTokens only when truthy. build_prompt starts from DEFAULT_PROMPT, appends ' Respond in the <language> language.' when a language is given and a custom prompt when supplied. format_audio_part emits {inline_data: {mime_type:, data: encoded}}.

<a id="u-48025de1f3fa"></a>
### `RubyLLM.Providers.Gemini.Transcription.parse_transcription_response`

`def parse_transcription_response(response, model:)` · [lib/ruby_llm/providers/gemini/transcription.rb:L75-L87][f4]

Converts a transcription response into a RubyLLM::Transcription carrying the model id.

Text comes from the first candidate's text parts joined (nil when absent), and usage from usageMetadata: input_tokens is promptTokenCount and output_tokens is candidatesTokenCount plus thoughtsTokenCount. Missing usageMetadata yields nil token counts.

group: [transcription-response-extraction](r2-provider-gemini.md#u-4aa1cf4d2c6f)

<a id="u-4aa1cf4d2c6f"></a>
### `transcription-response-extraction`

`def extract_text(data)` · [lib/ruby_llm/providers/gemini/transcription.rb:L89-L96][f4]

Groups response field extraction.

extract_text returns nil when data is not a Hash or has no first candidate; otherwise it joins the text of parts containing 'text', returning nil when none. extract_usage returns {input_tokens: nil, output_tokens: nil} when data is not a Hash or usageMetadata is missing; otherwise it reports promptTokenCount as input and sum_output_tokens (candidatesTokenCount plus thoughtsTokenCount, each defaulting to 0) as output.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/providers/gemini/capabilities.rb
[f2]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/providers/gemini/models.rb
[f3]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/providers/gemini/streaming.rb
[f4]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/providers/gemini/transcription.rb
[f5]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/transcription.rb
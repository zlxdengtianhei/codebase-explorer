# Bedrock AWS integration

**Capability.** Implements Bedrock model listing with signed management-API requests and the AWS event-stream binary framing parser for streaming chunks.

Visit for Bedrock's AWS-specific plumbing: SigV4-signed foundation-model listing with region-adjusted inference-profile IDs, and the byte-buffer parser that decodes AWS event-stream frames into JSON payloads for streaming. Streaming submodules split prelude, payload, and message processing.

**Depends on.**

- [Core provider infrastructure](core-provider-infrastructure.md) · graph-confirmed · 1 edge(s) · Bedrock integration builds on the abstract provider base and connection management.
- [Streaming and result objects](streaming-and-result-objects.md) · graph-confirmed · 1 edge(s)

**Depended on by.**

- [Streaming and result objects](streaming-and-result-objects.md) · graph-confirmed · 1 edge(s) · 1 inferred relation(s)

Parent: [Streaming and Provider Core](streaming-and-provider-core.md)

## Units (11)

<a id="u-8f6e73e77785"></a>
### `content_extraction.rb-bedrock-streaming-content-extraction`

`def json_delta?(data)` · [lib/ruby_llm/providers/bedrock/streaming/content_extraction.rb:L9-L11][f1]

Extracts text content from Bedrock streaming event hashes.

json_delta? is true for content_block_delta events whose delta type is input_json_delta. extract_streaming_content returns '' for non-Hash input; otherwise it dispatches on data['type']: content_block_start yields content_block.text, content_block_delta yields delta.text, and any other type yields '' — both dig results are stringified so nil becomes an empty string.

<a id="u-28f700cacf60"></a>
### `content_extraction.rb-bedrock-usage-and-metadata-extractors`

`def extract_tool_calls(data)` · [lib/ruby_llm/providers/bedrock/streaming/content_extraction.rb:L19-L21][f1]

Small accessors over streaming event hashes, each preferring the nested 'message' path and falling back to a top-level one.

Tool calls come from message.tool_calls or data['tool_calls']; model id from message.model or the instance's @model_id; input tokens only from message.usage; output and cached tokens check both usage locations. cache_creation_tokens checks both cache_creation_input_tokens paths, then sums the values of a Hash cache_creation breakdown (either location), returning nil when neither form is present.

<a id="u-668f26439813"></a>
### `message_processing.rb-bedrock-event-stream-message-processing`

`def process_chunk(chunk, &)` · [lib/ruby_llm/providers/bedrock/streaming/message_processing.rb:L9-L15][f2]

Parses AWS event-stream framed chunks inside a byte buffer, validating prelude lengths and payload shape before dispatching payloads.

process_chunk iterates from offset 0, repeatedly calling process_message while offset < chunk.bytesize, and rescues any StandardError by logging the error message and chunk size (swallowing it). process_message returns chunk.bytesize (skip whole chunk) unless can_read_prelude?; otherwise extract_message_info reads the prelude and, if lengths/positions are invalid or the chunk is shorter than the message end, returns nil causing find_next_message(chunk, offset) as the new offset. process_valid_message slices the payload between headers_end and payload_end; if it is nil/empty or lacks a '{' before a '}', it also falls back to find_next_message; otherwise it calls process_payload with the block and advances by total_length. extract_message_info returns the position hash only when valid_lengths? and valid_positions? both hold and the full message is buffered.

**Notes.**

- failure: Any StandardError during chunk processing is logged and suppressed, so malformed chunks do not propagate.

calls: [can_read_prelude?](../../catalog.json.gz), [read_prelude](../../catalog.json.gz), [process_payload](../../catalog.json.gz), [find_next_message](../../catalog.json.gz)

**Uncertainties.**

- Prelude-reading helpers and process_payload are not visible in this batch; framing semantics beyond the checks shown are unproven.

<a id="u-9f03e6f7b8ec"></a>
### `payload_processing.rb-bedrock-payload-processing-pipeline`

`def process_payload(payload, &)` · [lib/ruby_llm/providers/bedrock/streaming/payload_processing.rb:L11-L18][f3]

process_payload takes a raw payload string, extracts the substring from the first '{' to the last '}', JSON-parses it, and only when the parsed object has a 'bytes' field base64-decodes and JSON-parses that to build and yield a Chunk to the caller's block.

Chunks are built with role :assistant and attributes pulled by the ContentExtraction helpers (model id, content, token counts, tool calls). All failures are swallowed: JSON::ParserError logs the error and offending payload at debug level, any other StandardError logs a debug message; nothing is re-raised and no chunk is yielded on failure. If 'bytes' is absent the payload is silently ignored.

<a id="u-3a4a66348012"></a>
### `prelude_handling.rb-bedrock-event-stream-prelude-handling`

`def can_read_prelude?(chunk, offset)` · [lib/ruby_llm/providers/bedrock/streaming/prelude_handling.rb:L9-L11][f4]

Parses the AWS event-stream binary framing embedded in Bedrock chunks.

can_read_prelude? requires at least 12 bytes remaining after the offset. read_prelude unpacks two big-endian 32-bit lengths (total, headers) at the offset. valid_lengths? delegates to valid_length_constraints?, which rejects nil, non-positive, or over-1,000,000 total lengths and header lengths that are non-positive or not strictly less than total. calculate_positions computes headers_end (offset+12+headers_length) and payload_end (offset+total_length-4, excluding the 4-byte CRC); valid_positions? requires headers_end < payload_end, headers_end < chunk size, and payload_end <= chunk size. find_next_message scans from offset+4 for the next position whose 8-byte candidate lengths satisfy the constraints, returning that position or the chunk's byte size if none found.

<a id="u-3a126b4a8d5c"></a>
### `RubyLLM.Providers.Bedrock.Models.create_model_info`

`def create_model_info(model_data, slug, _capabilities)` · [lib/ruby_llm/providers/bedrock/models.rb:L53-L69][f5]

Alternative Model::Info factory returning a fixed record for a model datum: region-adjusted ID, modelName or raw ID, family 'claude', 200_000 context, 4_096 max tokens, text-only modalities, and empty capabilities, pricing, and metadata.

The capabilities argument is ignored.

<a id="u-92e50c366619"></a>
### `RubyLLM.Providers.Bedrock.Models.inference_profile_region_prefix`

`def inference_profile_region_prefix # Extract region prefix from bedrock_region (e.g.…` · [lib/ruby_llm/providers/bedrock/models.rb:L87-L94][f5]

Derives the inference-profile region prefix from @config.bedrock_region: the first two characters of the region string, or 'us' when the region is empty/nil.

Depends on instance state despite being a module_function.

<a id="u-f7193af023e2"></a>
### `RubyLLM.Providers.Bedrock.Models.list_models`

`def list_models` · [lib/ruby_llm/providers/bedrock/models.rb:L8-L17][f5]

Lists Bedrock foundation models: builds the management-API URL from the configured bedrock_region, signs it with a GET request, fetches it with the signature headers merged in, and parses the response with the provider slug and capabilities module.

HTTP or signing errors propagate.

<a id="u-c2f6c73d51ce"></a>
### `RubyLLM.Providers.Bedrock.Models.model_id_with_region`

`def model_id_with_region(model_id, model_data)` · [lib/ruby_llm/providers/bedrock/models.rb:L71-L85][f5]

Adjusts a model ID for inference profiles.

It returns the ID unchanged if inferenceTypesSupported includes 'INFERENCE_PROFILE' or 'ON_DEMAND', or if the ID already starts with the desired region prefix. Otherwise it strips a leading two-letter region prefix (e.g. 'us.') and prepends the desired prefix, yielding e.g. 'eu.claude-...'.

<a id="u-98c56ad03612"></a>
### `RubyLLM.Providers.Bedrock.Models.parse_list_models_response`

`def parse_list_models_response(response, slug, capabilities)` · [lib/ruby_llm/providers/bedrock/models.rb:L25-L51][f5]

Converts a Bedrock list-models response into Model::Info records, keeping only IDs containing 'claude'.

Each record gets region-adjusted ID, display name (modelName or humanized fallback), provider slug, and family, context window, max tokens, modalities, capabilities, and pricing from the capabilities module, plus metadata (provider name, inference types, streaming support, input/output modalities) with nil/[]/false defaults for missing fields.

<a id="u-23cb33935710"></a>
### `lib/ruby_llm/providers/bedrock/streaming.rb:Streaming`

`module Streaming` · [lib/ruby_llm/providers/bedrock/streaming.rb:L13-L15][f6]

Streaming support for Bedrock, composed by requiring five streaming submodules (base, content_extraction, message_processing, payload_processing, prelude_handling) and including Base into the module; all streaming behavior lives in those required files, not here.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/providers/bedrock/streaming/content_extraction.rb
[f2]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/providers/bedrock/streaming/message_processing.rb
[f3]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/providers/bedrock/streaming/payload_processing.rb
[f4]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/providers/bedrock/streaming/prelude_handling.rb
[f5]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/providers/bedrock/models.rb
[f6]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/providers/bedrock/streaming.rb

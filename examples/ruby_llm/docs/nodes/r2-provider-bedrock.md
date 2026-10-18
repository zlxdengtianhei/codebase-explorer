# Bedrock Adapter

**Capability.** Sends AWS Bedrock invoke requests with signing, reuses Anthropic message/tool formats, and decodes Bedrock's binary event-stream into messages.

Read to understand Bedrock's unusual binary streaming pipeline and its dependency on Anthropic tool formatting. stream_url depends on @model_id set during payload rendering.

**Depends on.**

- [Provider Connection](r2-connection.md) · graph-confirmed · 2 edge(s)
- [Anthropic Adapter](r2-provider-anthropic.md) · model-inferred · 0 edge(s) · Bedrock reuses Anthropic tool formatting mixins for messages and tool calls.
- [Shared Streaming](r2-streaming-shared.md) · graph-confirmed · 1 edge(s)
- [Bedrock Event-Stream Streaming](r1-bedrock-streaming.md) · graph-only · 8 edge(s)
- [Stream Accumulation](r1-streaming-accumulation.md) · graph-only · 3 edge(s)
- [Provider Base and Registry](r2-provider-base.md) · graph-only · 1 edge(s)

**Depended on by.**

- [Bedrock Event-Stream Streaming](r1-bedrock-streaming.md) · graph-only · 1 edge(s)

Parent: [Provider Adapters](r2-providers.md)

## Units (15)

<a id="u-1433f99a11c5"></a>
### `Bedrock`

`class Bedrock < Provider` · [lib/ruby_llm/providers/bedrock.rb:L9-L17][f1]

Bedrock subclasses Provider and mixes in Bedrock::Chat, Streaming, Models, Signing, Media, and Anthropic::Tools.

api_base interpolates @config.bedrock_region into https://bedrock-runtime.<region>.amazonaws.com. parse_error returns nil for an empty body; otherwise it JSON-parses via try_parse_json and, per parsed shape, returns body['message'] for a Hash, all parts' 'message' values joined with '. ' for an Array, or the parsed value itself otherwise. sign_request builds a Signing::Signer from create_signer (configured with bedrock_api_key, bedrock_secret_key, bedrock_session_token, bedrock_region, service 'bedrock') and signs a request built by build_request. build_request returns a hash with the connection, http method, url or completion_url fallback, and JSON-generated payload (nil when payload is absent). build_headers merges Content-Type 'application/json' and an Accept header that switches to 'application/vnd.amazon.eventstream' when streaming, else 'application/json', over the given signature headers. Singleton capabilities returns Bedrock::Capabilities; configuration_requirements lists :bedrock_api_key, :bedrock_secret_key, :bedrock_region (session token not required).

calls: [provider.rb-provider-instance](r2-provider-base.md#u-961fc10a6a0f); uses: [Anthropic](r1-anthropic-adapter.md#u-3366212c86dc)

**Uncertainties.**

- completion_url is inherited from an included Chat module outside this batch; its exact URL is unproven.
- Behavior of Signing::Signer is defined in the Bedrock::Signing module, not in this batch.

<a id="u-162920becdb4"></a>
### `RubyLLM.Providers.Bedrock.Chat.render_payload`

`def render_payload(messages, tools:, temperature:, model:, stream: false, schema: nil…` · [lib/ruby_llm/providers/bedrock/chat.rb:L42-L51][f2]

Builds the Bedrock invoke payload and records the model id as mutable state: it assigns @model_id = model.id, which completion_url later reads to form 'model/<id>/invoke'.

It splits messages with Anthropic::Chat.separate_messages, joins system messages via Anthropic::Chat.build_system_content, then constructs the base payload (anthropic_version 'bedrock-2023-05-31', formatted messages, max_tokens falling back to 4096 when model.max_tokens is nil) and appends optional system/tools/temperature fields through Anthropic::Chat.add_optional_fields. The stream and schema parameters are accepted but unused. Because state lives on the module, concurrent renders would race on @model_id.

**Uncertainties.**

- Concurrency safety of the @model_id instance variable on the module is not guaranteed by anything in this file.

<a id="u-17da8da4e48c"></a>
### `RubyLLM.Providers.Bedrock.Chat.format_message`

`def format_message(msg)` · [lib/ruby_llm/providers/bedrock/chat.rb:L19-L27][f2]

Converts a message into Bedrock/Anthropic wire format by role-kind dispatch: tool_call messages go through Anthropic::Tools.format_tool_call, tool_result messages through Anthropic::Tools.format_tool_result, and all other messages through format_basic_message.

The first matching branch wins, so a message cannot be both. It reuses the Anthropic formatting helpers unchanged, so their output shape (Anthropic content blocks) is what Bedrock receives.

calls: [RubyLLM.Providers.Bedrock.Media.format_content](r1-bedrock-adapter.md#u-15d22633b933)

**Uncertainties.**

- Graph shows format_tool_call/format_tool_result resolved across multiple provider implementations; whether the Anthropic variants are the ones loaded at runtime is not provable from this file.

<a id="u-c56ce45ee286"></a>
### `RubyLLM.Providers.Bedrock.Chat.sync_response`

`def sync_response(connection, payload, additional_headers = {})` · [lib/ruby_llm/providers/bedrock/chat.rb:L10-L17][f2]

Executes a synchronous Bedrock invoke: it signs the completion URL, POSTs the payload, and delegates response parsing to Anthropic::Chat.

The URL is the connection's url_prefix joined with completion_url ('model/<id>/invoke'); the model id comes from render_payload's stored @model_id state. build_headers(signature.headers, streaming: block_given?) merges SigV4 headers onto the request; non-empty additional_headers replace the request headers via additional_headers.merge(req.headers), so additional headers take precedence over signed ones on key collisions. The response is parsed by Anthropic::Chat.parse_completion_response; failure paths (signing errors, HTTP errors) propagate unchanged from the sign/parse layers.

uses: [signing-rb-signer](r1-bedrock-signing.md#u-ef4167d839ba); calls: [connection.rb-connection](r2-connection.md#u-53be52e4979e)

**Uncertainties.**

- The exact sign_request/build_headers receivers are ambiguous in this file (Bedrock provider methods vs Signing module classes per graph evidence); behavior is inferred from the Signing implementations when the Signing variants apply.

<a id="u-79ce64355b8d"></a>
### `RubyLLM.Providers.Bedrock.Streaming.Base.included`

`def self.included(base)` · [lib/ruby_llm/providers/bedrock/streaming/base.rb:L9-L14][f3]

Hook that wires Bedrock streaming support into any including class by pulling in the ContentExtraction, MessageProcessing, PayloadProcessing, and PreludeHandling modules; those modules supply the methods stream_response and handle_stream rely on.

<a id="u-6f9bca42043e"></a>
### `RubyLLM.Providers.Bedrock.Streaming.Base.stream_response`

`def stream_response(connection, payload, additional_headers = {}, &block)` · [lib/ruby_llm/providers/bedrock/streaming/base.rb:L20-L35][f3]

Performs the streaming POST to Bedrock and folds the event stream into a message.

It signs the absolute request URL (connection URL prefix plus stream_url), creates a StreamAccumulator, posts stream_url with the payload, merges signature headers plus streaming flag into request headers, and merges additional_headers so that already-set request headers take precedence over them (the merge is skipped entirely when additional_headers is empty). The on_data callback runs the proc from handle_stream: each delivered chunk is added to the accumulator and forwarded to the caller's block. After the response completes, accumulator.to_message(response) is returned.

calls: [RubyLLM.Providers.Bedrock.Streaming.Base.handle_stream](r2-provider-bedrock.md#u-bd2781073d92), [RubyLLM.Providers.Bedrock.Streaming.Base.stream_url](r2-provider-bedrock.md#u-1e7c827f0fb0)

**Uncertainties.**

- sign_request, build_headers, StreamAccumulator#add, and to_message are defined outside this file; their failure behavior here is unproven.

<a id="u-bd2781073d92"></a>
### `RubyLLM.Providers.Bedrock.Streaming.Base.handle_stream`

`def handle_stream(&block)` · [lib/ruby_llm/providers/bedrock/streaming/base.rb:L37-L46][f3]

Builds the raw-response callback used during Bedrock streaming.

It closes over an empty String buffer; the returned proc receives each raw chunk plus the response environment. When env is present and its status is not 200, it delegates to handle_failed_response with the chunk, buffer, and env; otherwise it forwards the chunk to process_chunk with the caller's block. The buffer exists for the failure path, which is implemented outside this file.

calls: [RubyLLM.Providers.Bedrock.Streaming.MessageProcessing.process_chunk](r2-provider-bedrock.md#u-ad521c7e7d6b)

**Uncertainties.**

- handle_failed_response is defined outside this file; how it uses buffer and env is unproven here.

<a id="u-1e7c827f0fb0"></a>
### `RubyLLM.Providers.Bedrock.Streaming.Base.stream_url`

`def stream_url` · [lib/ruby_llm/providers/bedrock/streaming/base.rb:L16-L18][f3]

Returns the Bedrock invoke-with-response-stream endpoint path built from the instance variable @model_id; depends on @model_id being set by the including class.

<a id="u-ad521c7e7d6b"></a>
### `RubyLLM.Providers.Bedrock.Streaming.MessageProcessing.process_chunk`

`def process_chunk(chunk, &)` · [lib/ruby_llm/providers/bedrock/streaming/message_processing.rb:L9-L15][f4]

Drives binary-frame parsing for one Bedrock streaming chunk.

Starting at offset 0, it repeatedly calls process_message, which returns the offset of the next message, until the offset reaches chunk.bytesize. Any StandardError raised during parsing is rescued and logged at debug level (error message and chunk size); parsing failures are swallowed rather than propagated, so a malformed chunk yields no content and no exception.

**Notes.**

- failure: StandardError during any stage is logged at debug and suppressed; the block is never called for the failed chunk portion.

calls: [RubyLLM.Providers.Bedrock.Streaming.MessageProcessing.process_message](r2-provider-bedrock.md#u-b062f5a43051)

**Uncertainties.**

- Whether RubyLLM.logger is always configured is not visible here.

<a id="u-b062f5a43051"></a>
### `RubyLLM.Providers.Bedrock.Streaming.MessageProcessing.process_message`

`def process_message(chunk, offset, &)` · [lib/ruby_llm/providers/bedrock/streaming/message_processing.rb:L17-L24][f4]

Parses one framed message beginning at the given offset and returns the next offset.

If can_read_prelude? is false the message is incomplete, so chunk.bytesize is returned, ending the loop for this chunk. Otherwise extract_message_info validates the frame; when it returns nil, find_next_message locates the next plausible offset. A valid frame goes to process_valid_message.

calls: [RubyLLM.Providers.Bedrock.Streaming.MessageProcessing.extract_message_info](r2-provider-bedrock.md#u-6734bfe9f3b5), [RubyLLM.Providers.Bedrock.Streaming.MessageProcessing.process_valid_message](r2-provider-bedrock.md#u-57649e20a358)

**Uncertainties.**

- can_read_prelude? and find_next_message are defined in PreludeHandling outside this file.

<a id="u-57649e20a358"></a>
### `RubyLLM.Providers.Bedrock.Streaming.MessageProcessing.process_valid_message`

`def process_valid_message(chunk, offset, message_info, &)` · [lib/ruby_llm/providers/bedrock/streaming/message_processing.rb:L26-L32][f4]

Extracts the payload slice for a validated frame and processes it.

It slices chunk between message_info[:headers_end] and message_info[:payload_end]; if the payload fails valid_payload? it falls back to find_next_message for the next offset. A valid payload is passed to process_payload (which invokes the caller's block) and the returned offset is offset + message_info[:total_length].

uses: [message_processing.rb-payload-validation](r2-provider-bedrock.md#u-f7c4c3e38894); contract: [RubyLLM.Providers.Bedrock.Streaming.MessageProcessing.extract_message_info](r2-provider-bedrock.md#u-6734bfe9f3b5)

**Uncertainties.**

- extract_payload, valid_payload?, process_payload, and find_next_message behavior is partly defined in other modules of this batch or outside it.

<a id="u-6734bfe9f3b5"></a>
### `RubyLLM.Providers.Bedrock.Streaming.MessageProcessing.extract_message_info`

`def extract_message_info(chunk, offset)` · [lib/ruby_llm/providers/bedrock/streaming/message_processing.rb:L36-L47][f4]

Validates a Bedrock event frame at the given offset and returns its geometry or nil.

It reads total_length and headers_length via read_prelude and returns nil unless valid_lengths?. It returns nil when the chunk does not yet contain the full message (chunk.bytesize < offset + total_length). It computes headers_end and payload_end via calculate_positions and returns nil unless valid_positions? passes against chunk.bytesize. On success it returns a hash with total_length, headers_length, headers_end, payload_end.

**Uncertainties.**

- read_prelude, valid_lengths?, calculate_positions, and valid_positions? live in PreludeHandling outside this file; their exact validity rules are unproven here.

<a id="u-f7c4c3e38894"></a>
### `message_processing.rb-payload-validation`

`def extract_payload(chunk, headers_end, payload_end)` · [lib/ruby_llm/providers/bedrock/streaming/message_processing.rb:L49-L51][f4]

Payload slicing and validation helpers.

extract_payload returns the substring chunk[headers_end...payload_end], which is nil when headers_end exceeds the chunk bounds. valid_payload? rejects nil or empty payloads, and rejects payloads whose first '{' or last '}' is missing or whose '{' appears at or after the last '}' (json_start >= json_end); only then does it return true.

<a id="u-21af9e32aa3b"></a>
### `RubyLLM.Providers.Bedrock.Streaming.ContentExtraction.json_delta?`

`def json_delta?(data)` · [lib/ruby_llm/providers/bedrock/streaming/content_extraction.rb:L9-L11][f5]

True only when the event type is 'content_block_delta' and the nested delta type is 'input_json_delta'; any other shape returns false.

<a id="u-0d5d57c66bf6"></a>
### `content-extraction-rb-getters`

`def extract_streaming_content(data)` · [lib/ruby_llm/providers/bedrock/streaming/content_extraction.rb:L13-L17][f5]

Field extraction from Bedrock streaming events.

extract_streaming_content returns '' for non-Hash data and otherwise dispatches by data['type']: 'content_block_start' yields data.dig('content_block','text').to_s, 'content_block_delta' yields data.dig('delta','text').to_s, everything else ''. extract_tool_calls reads data.dig('message','tool_calls') falling back to data['tool_calls']. extract_model_id reads the message model or falls back to @model_id (instance state of the including object). The usage getters read nested or top-level usage fields; extract_output_tokens and extract_cached_tokens try data.dig('message','usage',...) then data.dig('usage',...). extract_cache_creation_tokens first tries 'cache_creation_input_tokens' at either level; if absent it looks up a 'cache_creation' breakdown at either level and, only when that is a Hash, sums its non-nil values, otherwise returns nil.

**Uncertainties.**

- extract_model_id depends on @model_id state set elsewhere; when it is set and to what value is outside this file.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/providers/bedrock.rb
[f2]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/providers/bedrock/chat.rb
[f3]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/providers/bedrock/streaming/base.rb
[f4]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/providers/bedrock/streaming/message_processing.rb
[f5]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/providers/bedrock/streaming/content_extraction.rb
# Streaming and result objects

**Capability.** Implements SSE stream processing, chunk accumulation into final Messages, in-stream error handling, and the Chunk, ToolCall, and Transcription value objects.

Visit for how streaming works: the generic SSE parser and error handling, the StreamAccumulator that merges chunks and tool-call fragments into a Message, and per-provider chunk builders for Anthropic, Bedrock, Gemini, and OpenAI. Also hosts the Rails railtie hook and moderation wrapper.

**Depends on.**

- [Bedrock AWS integration](bedrock-aws-integration.md) · graph-confirmed · 1 edge(s) · 1 inferred relation(s)
- [Core provider infrastructure](core-provider-infrastructure.md) · graph-confirmed · 2 edge(s)
- [Provider chat wire formatting](provider-chat-wire-formatting.md) · graph-only · 1 edge(s)

**Depended on by.**

- [Bedrock AWS integration](bedrock-aws-integration.md) · graph-confirmed · 1 edge(s)
- [Gemini and media integrations](gemini-and-media-integrations.md) · graph-only · 2 edge(s)
- [Provider chat wire formatting](provider-chat-wire-formatting.md) · graph-only · 2 edge(s)
- [Tool definition and execution](tool-definition-and-execution.md) · graph-only · 1 edge(s)

Parent: [Streaming and Provider Core](streaming-and-provider-core.md)

## Units (28)

<a id="u-88b7d2e77fd5"></a>
### `base.rb-bedrock-streaming-base`

`def self.included(base)` · [lib/ruby_llm/providers/bedrock/streaming/base.rb:L9-L14][f1]

Wires Bedrock streaming: composes the processing submodules on inclusion, builds the invoke-with-response-stream URL, performs the signed streaming POST, and routes raw chunks.

included mixes ContentExtraction, MessageProcessing, PayloadProcessing, and PreludeHandling into the host. stream_url is "model/#{@model_id}/invoke-with-response-stream". stream_response signs the request against connection.url_prefix + stream_url, POSTs via connection.post with signed headers (streaming flag set when a block is given), merges additional_headers under existing headers (existing take precedence), sets an on_data callback that both accumulates the chunk and forwards it to the caller's block, and finally returns accumulator.to_message(response). handle_stream returns a proc: if env is present with non-200 status it calls handle_failed_response(chunk, buffer, env); otherwise it forwards the chunk to process_chunk with the caller's block.

**Notes.**

- side_effect: Each streamed chunk is both accumulated into the final message and yielded to the caller's block.

calls: [Connection.post](../../catalog.json.gz), [StreamAccumulator.add](../../catalog.json.gz), [handle_failed_response](../../catalog.json.gz), [message_processing.rb-bedrock-event-stream-message-processing](bedrock-aws-integration.md#u-668f26439813)

**Uncertainties.**

- sign_request, build_headers, and handle_failed_response are not visible in this batch; their exact effects on headers and error handling are unproven.

<a id="u-67897d0d9d75"></a>
### `moderation.rb-moderation-result`

`class Moderation` · [lib/ruby_llm/moderation.rb:L6-L9][f2]

Wraps moderation API results and provides the class-level entry point.

moderate resolves config (context's or global), defaults the model to config.default_moderation_model or 'omni-moderation-latest', resolves model/provider via Models.resolve, and delegates to provider_instance.moderate with the model id. The instance is a value object over id, model, and results: content returns results; flagged? is true if any result's 'flagged' key is truthy; flagged_categories flat-maps each result's 'categories', selecting truthy entries and taking keys, uniq'd, tolerating a nil categories hash; category_scores and categories dig into the first result only, defaulting to {} when absent. All accessors use string keys, matching OpenAI-style JSON.

calls: [Models.resolve](../../catalog.json.gz)

**Uncertainties.**

- provider_instance.moderate's return shape is outside this batch; the accessors assume an array of string-keyed hashes.

<a id="u-4fde39f3b31d"></a>
### `stream_accumulator.rb-streamaccumulator`

`class StreamAccumulator` · [lib/ruby_llm/stream_accumulator.rb:L5-L8][f3]

Accumulates streaming chunks into a final Message.

initialize prepares an empty mutable content string, empty tool_calls hash, nil token counters, and nil latest_tool_call_id.

<a id="u-7a74a4f0d535"></a>
### `streaming.rb-anthropic-streaming-helpers`

`def stream_url` · [lib/ruby_llm/providers/anthropic/streaming.rb:L10-L12][f4]

Builds streaming chunks and detects/errors for the Anthropic SSE stream.

stream_url delegates to completion_url. build_chunk constructs a Chunk with role :assistant, model id, delta text, and token counts from the extract_* helpers; tool_calls come from extract_tool_calls (not in this batch). json_delta? is true only for a content_block_delta event whose delta type is input_json_delta. parse_streaming_error JSON.parses the raw data and returns nil unless type=='error'; it returns [529, message] for error type 'overloaded_error' and [500, message] otherwise. JSON.parse failures propagate uncaught.

**Notes.**

- failure: JSON.parse on non-JSON data raises before the type check.

calls: [Chunk](../../catalog.json.gz), [models.rb-anthropic-models-listing-and-usage-extraction](anthropic-model-metadata.md#u-9a70399f9e67)

**Uncertainties.**

- extract_tool_calls is not visible in this batch, so tool_calls content of the chunk is unproven.
- completion_url is not visible here, so the concrete stream endpoint is unproven.

<a id="u-9fe950996e08"></a>
### `streaming.rb-stream-parser-setup`

`def faraday_1?` · [lib/ruby_llm/streaming.rb:L39-L41][f5]

faraday_1?

checks the Faraday version prefix. to_json_stream creates an EventStreamParser with a mutable buffer and delegates to create_stream_processor, which picks the legacy (Faraday 1) or modern processor.

<a id="u-d86d15473ad1"></a>
### `streaming.rb-stream-processor-callbacks`

`def legacy_stream_processor(parser, &block)` · [lib/ruby_llm/streaming.rb:L68-L72][f5]

legacy_stream_processor wraps process_stream_chunk with a nil env (Faraday 1).

stream_processor (Faraday 2+) only processes chunks when env status is 200, otherwise buffers the chunk into handle_failed_response to surface a non-200 error body.

<a id="u-3d1d22813996"></a>
### `streaming.rb-streaming`

`def stream_url` · [lib/ruby_llm/providers/gemini/streaming.rb:L8-L10][f6]

Builds Chunk objects from SSE stream events.

stream_url is "models/{@model}:streamGenerateContent?alt=sse". build_chunk extracts the model id from modelVersion, content by joining text parts of the first candidate (nil when no candidates or no text parts), input tokens from promptTokenCount, and output tokens as candidatesTokenCount plus thoughtsTokenCount, returning nil when the sum is zero. parse_streaming_error JSON-parses an error payload and returns [code, message]; on JSON::ParserError it logs and returns [500, "Failed to parse error: {data}"].

<a id="u-004fe75a393a"></a>
### `streaming.rb-streaming-2`

`def stream_url` · [lib/ruby_llm/providers/openai/streaming.rb:L10-L12][f7]

OpenAI streaming support.

stream_url delegates to completion_url. build_chunk converts a stream event into a Chunk with role :assistant, the event's model, delta content, tool calls parsed with parse_arguments: false (arguments stay as raw JSON strings), and usage token counts including cached tokens; cache_creation_tokens is 0. parse_streaming_error JSON-parses the event data and returns nil when there is no 'error' key; otherwise maps error type 'server_error' to [500, message], 'rate_limit_exceeded'/'insufficient_quota' to [429, message], and anything else to [400, message]. Malformed JSON would propagate JSON::ParserError.

<a id="u-6a48321ccf9c"></a>
### `tool_call.rb-tool-call-record`

`class ToolCall` · [lib/ruby_llm/tool_call.rb:L5-L8][f8]

Value object for a model-requested function call: id, name, and arguments (defaulting to {}).

to_h returns the three fields as a hash; arguments are passed through unmodified.

<a id="u-504350bf7b5b"></a>
### `transcription.rb-transcription-entry-point`

`class Transcription` · [lib/ruby_llm/transcription.rb:L5-L8][f9]

Value object for audio transcription results (text, model, plus optional language, duration, segments, input_tokens, output_tokens from **attributes).

The class method transcribe pops :model, :language, :provider, :assume_model_exists (default false), and :context from kwargs, leaving the rest as provider options; resolves config from context or globally, defaults the model to config.default_transcription_model, resolves via Models.resolve, and delegates to provider_instance.transcribe with the audio file, model id, language (possibly nil), and remaining options.

calls: [Models.resolve](../../catalog.json.gz)

**Uncertainties.**

- provider_instance.transcribe's return type is outside this batch; presumably a Transcription instance.

<a id="u-ec2920a443c8"></a>
### `Chunk`

`class Chunk < Message end` · [lib/ruby_llm/chunk.rb:L4-L5][f10]

Empty subclass of Message used by provider streaming code to represent a single streamed event; inherits all Message behavior and adds nothing.

<a id="u-acb5d0270dbf"></a>
### `Railtie`

`class Railtie < Rails::Railtie` · [lib/ruby_llm/railtie.rb:L6-L33][f11]

Rails integration hook, defined only when Rails::Railtie exists.

Registers an initializer that inflects the acronym 'RubyLLM', and an active_record initializer that, on ActiveRecord load, includes either the new ActsAs module (when config.use_new_acts_as) or the legacy ActsAsLegacy module plus a deprecation warning pointing to the 1.7 migration guide. Also loads rake tasks from tasks/ruby_llm.rake. The legacy branch logs via Rails.logger.warn.

**Notes.**

- condition: The entire file is a no-op outside a Rails application.

**Uncertainties.**

- The required acts_as modules and the rake file are outside this batch.

<a id="u-040152b070f8"></a>
### `RubyLLM.StreamAccumulator.accumulate_tool_calls`

`def accumulate_tool_calls(new_tool_calls)` · [lib/ruby_llm/stream_accumulator.rb:L66-L83][f3]

Merges streamed tool-call fragments: a chunk with an (even empty) id starts a new ToolCall keyed by that id (empty ids get a SecureRandom uuid, empty arguments start as a mutable empty string) and becomes the latest; id-less chunks append their arguments to the latest tool call's arguments, silently skipped if none exists yet.

<a id="u-4ce14f98c91b"></a>
### `RubyLLM.StreamAccumulator.add`

`def add(chunk)` · [lib/ruby_llm/stream_accumulator.rb:L18-L30][f3]

Adds a chunk: logs it when config.log_stream_debug; memoizes model_id from the first chunk; routes tool-call chunks into accumulate_tool_calls and other chunks by appending chunk content (nil-safe) to the accumulated string; then updates token counters via count_tokens and logs the accumulator state in debug mode.

<a id="u-804cfcb6320d"></a>
### `RubyLLM.StreamAccumulator.count_tokens`

`def count_tokens(chunk)` · [lib/ruby_llm/stream_accumulator.rb:L94-L99][f3]

Overwrites the input/output/cached/cache-creation token counters whenever the chunk provides non-nil values.

<a id="u-3bf81ac9cb59"></a>
### `RubyLLM.StreamAccumulator.find_tool_call`

`def find_tool_call(tool_call_id)` · [lib/ruby_llm/stream_accumulator.rb:L85-L92][f3]

Looks up a tool call by id, tracking @latest_tool_call_id; a nil id reads @latest_tool_call (a variable never assigned elsewhere in this file, so it returns nil) — likely an intended @latest_tool_call_id.

<a id="u-7c4ee249523a"></a>
### `RubyLLM.StreamAccumulator.to_message`

`def to_message(response)` · [lib/ruby_llm/stream_accumulator.rb:L32-L44][f3]

Builds the final assistant Message from the accumulated state: content is nil when empty; tool calls are rebuilt via tool_calls_from_stream; token counters and the raw response are attached.

<a id="u-8e96e13a9ad1"></a>
### `RubyLLM.StreamAccumulator.tool_calls_from_stream`

`def tool_calls_from_stream` · [lib/ruby_llm/stream_accumulator.rb:L48-L64][f3]

Converts accumulated tool calls into final ToolCall objects, parsing string arguments as JSON; empty-string arguments become {} and non-string arguments pass through.

JSON::ParserError on non-empty strings would propagate.

<a id="u-6838061ae56e"></a>
### `error_chunk?`

`def error_chunk?(chunk)` · [lib/ruby_llm/streaming.rb:L84-L86][f5]

Predicate: true when a raw chunk starts with 'event: error'.

<a id="u-47f9202abd77"></a>
### `handle_data`

`def handle_data(data)` · [lib/ruby_llm/streaming.rb:L124-L128][f5]

Parses an SSE data payload as JSON; JSON::ParserError is rescued and debug-logged, yielding nil to the caller's block.

<a id="u-f94dd66c137a"></a>
### `handle_error_chunk`

`def handle_error_chunk(chunk, env)` · [lib/ruby_llm/streaming.rb:L88-L102][f5]

Handles in-stream error chunks: extracts the data line, parses status via parse_streaming_error (always 500) and the JSON body, builds a response object (Struct for Faraday 1, merged env otherwise), and raises via ErrorMiddleware.parse_error with the including provider.

JSON::ParserError is rescued and only debug-logged, so malformed error chunks are swallowed.

<a id="u-5707fb56c8f6"></a>
### `handle_error_event`

`def handle_error_event(data, env)` · [lib/ruby_llm/streaming.rb:L130-L143][f5]

Handles SSE error events identically to error chunks: parse status (always 500) and JSON body, build a Faraday-1 Struct or merged env response, and raise via ErrorMiddleware.parse_error; JSON::ParserError is rescued and debug-logged.

<a id="u-9807417a4b69"></a>
### `handle_failed_response`

`def handle_failed_response(chunk, buffer, env)` · [lib/ruby_llm/streaming.rb:L104-L111][f5]

Accumulates chunks of a failed (non-200) response into the buffer, parses the full body as JSON, and raises via ErrorMiddleware.parse_error with the merged env.

JSON::ParserError is rescued and debug-logged, so parsing is retried on subsequent chunks until the body is complete.

<a id="u-815c501b29ea"></a>
### `handle_sse`

`def handle_sse(chunk, parser, env, &block)` · [lib/ruby_llm/streaming.rb:L113-L122][f5]

Feeds a chunk to the SSE parser: :error events go to handle_error_event; any other event's data is yielded through handle_data unless it is the '[DONE]' sentinel.

<a id="u-c0c2c766679b"></a>
### `handle_stream`

`def handle_stream(&block)` · [lib/ruby_llm/streaming.rb:L31-L35][f5]

Returns a callback that parses each raw data event and yields build_chunk(data) to the block when data is present; build_chunk is provider-supplied via the Streaming inclusion.

<a id="u-45a802b69826"></a>
### `parse_streaming_error`

`def parse_streaming_error(data)` · [lib/ruby_llm/streaming.rb:L145-L151][f5]

Parses streaming error data, returning [500, message] with the embedded 'message' or a fallback; JSON::ParserError yields [500, a 'Failed to parse error' message].

The status is hardcoded 500 regardless of the actual error.

<a id="u-e7d5755cd8ca"></a>
### `process_stream_chunk`

`def process_stream_chunk(chunk, parser, env, &)` · [lib/ruby_llm/streaming.rb:L58-L66][f5]

Processes one raw chunk: logs it in debug mode; if it starts with 'event: error' it is routed to handle_error_chunk (no yield), otherwise it is fed through handle_sse whose per-event results are yielded to the caller's block.

<a id="u-c93f3bf995bc"></a>
### `stream_response`

`def stream_response(connection, payload, additional_headers = {}, &block)` · [lib/ruby_llm/streaming.rb:L8-L29][f5]

Drives a streaming completion: posts the payload to stream_url with additional headers merged and an on_data callback (Faraday 1 style via req.options[:on_data], otherwise req.options.on_data) that accumulates each chunk into a StreamAccumulator and forwards it to the caller's block.

After the response completes, builds and logs the final Message from the accumulator and returns it. Error chunks inside the stream raise via the error handlers.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/providers/bedrock/streaming/base.rb
[f2]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/moderation.rb
[f3]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/stream_accumulator.rb
[f4]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/providers/anthropic/streaming.rb
[f5]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/streaming.rb
[f6]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/providers/gemini/streaming.rb
[f7]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/providers/openai/streaming.rb
[f8]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/tool_call.rb
[f9]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/transcription.rb
[f10]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/chunk.rb
[f11]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/railtie.rb

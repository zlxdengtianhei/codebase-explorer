# Streaming Chunk Accumulation

**Capability.** Streams provider responses, adapts provider events into chunks, and accumulates chunks into complete messages.

Observed units show streaming flow, provider streaming adapters, and chunk accumulation. They include Bedrock, Gemini, OpenAI, Anthropic helpers, and shared accumulator behavior.

**Depends on.**

- [Chat Payload And Auxiliary APIs](chat-payload-and-auxiliary-apis.md) · graph-confirmed · 3 edge(s) · 1 inferred relation(s) · Streaming chunk accumulation uses chat payload and auxiliary APIs to turn accumulated chunks into chat messages.
- [Provider Connection And Errors](provider-connection-and-errors.md) · graph-confirmed · 2 edge(s)
- [Chat Message And Tool Formatting](chat-message-and-tool-formatting.md) · graph-only · 3 edge(s)

**Depended on by.**

- [Chat Payload And Auxiliary APIs](chat-payload-and-auxiliary-apis.md) · graph-confirmed · 1 edge(s)
- [Chat Message And Tool Formatting](chat-message-and-tool-formatting.md) · graph-only · 1 edge(s)

Parent: [Provider Transport And Streaming](provider-transport-and-streaming.md)

## Units (17)

<a id="u-88b7d2e77fd5"></a>
### `base.rb-bedrock-streaming-base`

`class Bedrock` · [lib/ruby_llm/providers/bedrock/streaming/base.rb:L5-L6][f1]

Sets up Bedrock streaming modules and performs signed streaming POSTs with chunk accumulation.

Inclusion pulls in content extraction, message processing, payload processing, and prelude handling. The stream URL embeds the model id. The response method signs the full URL using the connection's connection.url_prefix plus the stream URL, creates an accumulator, posts the stream URL, merges built headers, lets additional headers be overridden by existing headers, and installs an on_data handler that accumulates and yields each chunk. It returns the accumulator's message. The handler dispatches non-200 responses to the failure handler and otherwise processes chunks.

**Uncertainties.**

- The failure handler and accumulator behavior are outside this source; the local buffer is initialized but not modified here.

<a id="u-18e5d5abb23c"></a>
### `content_extraction.rb-streaming-content-extraction`

`def json_delta?(data)` · [lib/ruby_llm/providers/bedrock/streaming/content_extraction.rb:L9-L11][f2]

Extracts content, tool calls, model id, and token usage from Bedrock streaming data.

JSON delta is true only for content_block_delta with input_json_delta. Streaming content returns empty unless the data is a hash; block-start uses content_block.text, delta uses delta.text, and other types return empty. Tool calls come from message.tool_calls or top-level tool_calls; model id from message.model or the stored model id. Input tokens come only from message.usage; output and cached tokens also fall back to top-level usage. Cache-creation tokens use the direct field, else sum compact values from a cache_creation hash.

<a id="u-c059859d8f5f"></a>
### `message_processing.rb-bedrock-message-processing`

`class Bedrock` · [lib/ruby_llm/providers/bedrock/streaming/message_processing.rb:L5-L6][f3]

Parses Bedrock streaming chunks into payloads and dispatches valid payloads for processing.

Chunk processing loops over the byte string by offset, rescues StandardError, logs debug details, and swallows the error. Message processing stops at the chunk end when a prelude cannot be read, returns the next-message position when message info is missing, and otherwise processes a valid message. Valid-message processing extracts the payload, skips to the next message when the payload is invalid, and otherwise processes the payload and advances by the message total length. Message info requires valid prelude lengths, a complete message in the buffer, and valid calculated positions. Payload validity rejects nil/empty payloads and requires a '{' before a '}'.

**Uncertainties.**

- The prelude, payload, and next-message helpers are outside this source, so their exact failure behavior is not established here.

<a id="u-d6f16b7f4716"></a>
### `payload_processing.rb-payload-processing`

`def process_payload(payload, &)` · [lib/ruby_llm/providers/bedrock/streaming/payload_processing.rb:L11-L18][f4]

Processes Bedrock streaming payloads into yielded chunks.

It slices from the first { to the last }, parses JSON, ignores data without bytes, base64-decodes and parses the bytes, then yields a chunk built with assistant role, model id, content, token fields, and tool calls. JSON parse errors log the error and attempted payload at debug; other standard errors log a debug message; neither is re-raised.

<a id="u-2a720a70f135"></a>
### `prelude_handling.rb-prelude-handling`

`def can_read_prelude?(chunk, offset)` · [lib/ruby_llm/providers/bedrock/streaming/prelude_handling.rb:L9-L11][f5]

Reads and validates Bedrock message preludes.

A prelude is readable when at least 12 bytes remain; total and header lengths are big-endian 32-bit values. Lengths are valid when total is positive and at most 1,000,000 and headers are positive and less than total. Positions are valid only when headers end before payload end, headers end before chunk size, and payload end is within chunk size. Next-message search starts four bytes after the offset and returns the found position or chunk size. The scan range is exclusive of chunk size minus 8, so the final possible 8-byte window is never checked.

<a id="u-8acb785a9a83"></a>
### `stream_accumulator.rb-streamaccumulator-class`

`class StreamAccumulator` · [lib/ruby_llm/stream_accumulator.rb:L5-L8][f6]

Accumulates streaming chunks into a complete assistant message with content, tool calls, and token counts.

initialize sets a mutable content string, empty tool-call hash, nil token counts, and nil latest tool-call id. Private helpers assemble tool calls and update token counts.

<a id="u-97cdd276f588"></a>
### `stream_accumulator.rb-tool-call-and-token-accumulation`

`def tool_calls_from_stream` · [lib/ruby_llm/stream_accumulator.rb:L48-L64][f6]

Parses accumulated tool-call arguments and records token counts.

tool_calls_from_stream parses nonempty String arguments as JSON, turns empty String arguments into {}, leaves other arguments as is, and returns ToolCall objects. accumulate_tool_calls stores calls with ids, replacing empty ids with SecureRandom.uuid and empty arguments with a mutable empty string, and appends id-less arguments to the latest stored call when present. find_tool_call with a nil id reads @tool_calls[@latest_tool_call], while a non-nil id updates the latest id and returns that call. count_tokens updates each token count when the chunk value is truthy.

**Uncertainties.**

- find_tool_call's nil-id branch reads @latest_tool_call, which is not initialized in this source; its intended behavior is not established.

<a id="u-b13f2b500e9a"></a>
### `streaming.rb-anthropic-streaming`

`class Anthropic # Streaming methods of the Anthropic API integration` · [lib/ruby_llm/providers/anthropic/streaming.rb:L5-L7][f7]

Adapts Anthropic streaming events into chunks and streaming errors.

The stream URL is the completion URL. Chunk building always sets assistant role and pulls model id, delta text, token counts, cache counts, and tool calls from the event. A JSON delta is recognized only for content_block_delta with delta.type input_json_delta. Error parsing parses JSON, returns nil unless the top-level type is error, maps overloaded_error to status 529, and maps every other error type to 500 with the error message.

<a id="u-73635a5c9f64"></a>
### `streaming.rb-stream-entrypoints`

`def stream_response(connection, payload, additional_headers = {}, &block)` · [lib/ruby_llm/streaming.rb:L8-L29][f8]

Streams a provider response while accumulating chunks and forwarding them to a block.

stream_response creates an accumulator, POSTs stream_url with merged headers, installs an on_data handler using the Faraday-version branch, adds each chunk to the accumulator and calls the block, then builds and returns the final message. handle_stream wraps to_json_stream and calls the block with each non-nil parsed chunk.

<a id="u-92cc88e9fef4"></a>
### `streaming.rb-stream-error-handling`

`def handle_error_chunk(chunk, env)` · [lib/ruby_llm/streaming.rb:L88-L102][f8]

Parses streaming error payloads and raises mapped RubyLLM errors through ErrorMiddleware.

handle_error_chunk extracts the data line, parses status/message, JSON-parses the payload, builds a Struct for Faraday 1 or merges body/status into env, and calls ErrorMiddleware.parse_error; JSON::ParserError is logged. handle_failed_response appends to the buffer, parses the buffer, merges body into env, and calls ErrorMiddleware.parse_error; JSON::ParserError is logged. handle_sse feeds the parser, routes :error to handle_error_event, and yields handle_data for other data unless it is [DONE]. handle_data JSON-parses and logs ParserError. handle_error_event parses status/message, JSON-parses, builds an error response, and calls ErrorMiddleware.parse_error; ParserError is logged. parse_streaming_error returns [500, message or Unknown streaming error], or [500, Failed to parse error: data] on ParserError.

**Uncertainties.**

- The streaming error handlers pass the Streaming module itself as provider to ErrorMiddleware.parse_error; this module does not define parse_error, so provider-specific message extraction is not established.

<a id="u-6334c011a3b6"></a>
### `streaming.rb-stream-processing-pipeline`

`def faraday_1?` · [lib/ruby_llm/streaming.rb:L39-L41][f8]

Selects Faraday-version-specific stream processors and routes chunks to SSE or error handling.

faraday_1? checks whether Faraday::VERSION starts with 1. to_json_stream creates a buffer and EventStreamParser::Parser, then create_stream_processor. create_stream_processor chooses legacy_stream_processor for Faraday 1 or stream_processor otherwise. process_stream_chunk logs debug, handles error chunks, or yields handle_sse. legacy_stream_processor passes a nil env; stream_processor processes only when env status is 200, otherwise calls handle_failed_response. error_chunk? is true when a chunk starts with event: error.

<a id="u-bd66f3624fbf"></a>
### `streaming.rb-streaming-chunks-and-errors`

`def stream_url` · [lib/ruby_llm/providers/gemini/streaming.rb:L8-L10][f9]

Builds Gemini streaming URLs and Chunk objects, and parses streaming errors.

The URL targets streamGenerateContent with SSE. Chunks carry assistant role, model id, content, input tokens, output tokens, and extracted tool calls. Content is nil without candidates or parts, otherwise joined text parts when any exist. Output tokens sum candidatesTokenCount and thoughtsTokenCount, each defaulting to zero, and return nil when the total is not positive. Error parsing returns the error code and message; JSON parse failure logs debug and returns status 500 with the raw data, while other malformed shapes are not rescued.

<a id="u-866061fde719"></a>
### `streaming.rb-streaming-helpers`

`def stream_url` · [lib/ruby_llm/providers/openai/streaming.rb:L10-L12][f10]

Provides the streaming URL, chunk construction, and streaming-error mapping.

The URL delegates to the chat completion URL. Chunk construction reads usage and cached prompt tokens, then builds a Chunk with assistant role, model id, delta content, tool calls parsed without argument parsing, prompt/completion tokens, cached tokens, and cache_creation_tokens 0. Error parsing JSON-parses the data, returns nil when there is no error, and maps server_error to [500, message], rate_limit_exceeded or insufficient_quota to [429, message], and any other error type to [400, message].

<a id="u-6ef8c1712c19"></a>
### `streaming.rb-streaming-module`

`module Streaming` · [lib/ruby_llm/streaming.rb:L5-L8][f8]

Provides streaming response handling and SSE/error processing for providers.

It uses module_function; public entrypoints stream_response and handle_stream; private helpers select Faraday-version-specific processors and map streaming errors through ErrorMiddleware.

<a id="u-ec2920a443c8"></a>
### `Chunk`

`class Chunk < Message end` · [lib/ruby_llm/chunk.rb:L4-L5][f11]

Empty subclass of the message type; it adds no methods or state and inherits message behavior.

inherits: [message.rb-chat-message](chat-message-and-tool-formatting.md#u-395e693d71b4)

<a id="u-4ce14f98c91b"></a>
### `RubyLLM.StreamAccumulator.add`

`def add(chunk)` · [lib/ruby_llm/stream_accumulator.rb:L18-L30][f6]

Adds one streaming chunk to the accumulator.

It logs the chunk when log_stream_debug is set, sets model_id from the first chunk, accumulates tool calls when the chunk is a tool call or appends content otherwise, updates token counts, and logs the accumulator inspect when debug is enabled.

<a id="u-7c4ee249523a"></a>
### `RubyLLM.StreamAccumulator.to_message`

`def to_message(response)` · [lib/ruby_llm/stream_accumulator.rb:L32-L44][f6]

Builds an assistant Message from accumulated content, tool calls, token counts, and raw response.

Content is nil when empty; tool_calls_from_stream supplies parsed tool calls; raw is the response.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/providers/bedrock/streaming/base.rb
[f2]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/providers/bedrock/streaming/content_extraction.rb
[f3]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/providers/bedrock/streaming/message_processing.rb
[f4]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/providers/bedrock/streaming/payload_processing.rb
[f5]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/providers/bedrock/streaming/prelude_handling.rb
[f6]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/stream_accumulator.rb
[f7]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/providers/anthropic/streaming.rb
[f8]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/streaming.rb
[f9]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/providers/gemini/streaming.rb
[f10]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/providers/openai/streaming.rb
[f11]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/chunk.rb

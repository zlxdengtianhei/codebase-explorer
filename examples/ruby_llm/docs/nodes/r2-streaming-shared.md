# Shared Streaming

**Capability.** SSE parsing, Faraday 1/2 handling, stream-to-Message/chunk plumbing, and the Chunk type used by all provider streaming implementations.

Use this to understand the provider-agnostic half of streaming; providers supply build_chunk and error parsing on top.

**Depends on.**

- [Provider Connection](r2-connection.md) · graph-confirmed · 1 edge(s)
- [Error Hierarchy and Middleware](r2-error-handling.md) · model-inferred · 0 edge(s)
- [Stream Accumulation](r1-streaming-accumulation.md) · graph-only · 4 edge(s)

**Depended on by.**

- [Anthropic Adapter](r2-provider-anthropic.md) · model-inferred · 0 edge(s)
- [Bedrock Adapter](r2-provider-bedrock.md) · graph-confirmed · 1 edge(s)
- [OpenAI Adapter](r2-provider-openai.md) · graph-confirmed · 1 edge(s)
- [Anthropic Adapter](r1-anthropic-adapter.md) · graph-only · 1 edge(s)
- [Bedrock Event-Stream Streaming](r1-bedrock-streaming.md) · graph-only · 1 edge(s)
- [Gemini Adapter](r2-provider-gemini.md) · graph-only · 1 edge(s)

Parent: [HTTP Transport and Provider Base](r2-transport.md)

## Units (4)

<a id="u-1662928ce9be"></a>
### `streaming.rb-processing`

`def faraday_1?` · [lib/ruby_llm/streaming.rb:L39-L41][f1]

SSE parsing and error handling shared by streaming, with Faraday 1/2 differences.

faraday_1? checks Faraday::VERSION's leading '1'. to_json_stream pairs an EventStreamParser with a string buffer, and create_stream_processor picks legacy_stream_processor (proc over chunk only, no env) for Faraday 1 or stream_processor (proc over chunk/bytes/env) otherwise; the v2 processor only processes chunks when env.status is 200, otherwise accumulating the buffer and raising through handle_failed_response once the JSON error body parses completely (partial bodies are debug-logged and buffered). process_stream_chunk debug-logs, routes chunks starting with 'event: error' to handle_error_chunk, and otherwise feeds the chunk through handle_sse, which parses SSE events: :error events go to handle_error_event, other data is JSON-parsed by handle_data (parse failures debug-logged, yielding nothing) and skipped for the '[DONE]' sentinel. handle_error_chunk and handle_error_event both parse the error JSON, build a fake response (Struct on Faraday 1, env.merge otherwise) with status from parse_streaming_error, and raise the mapped error via ErrorMiddleware.parse_error, rescuing JSON::ParserError to a debug log. parse_streaming_error always returns status 500 with the 'message' field, or a parse-failure string.

calls: [RubyLLM.ErrorMiddleware.parse_error](r2-error-handling.md#u-f775c1bd477e)

**Uncertainties.**

- handle_error_chunk derives the data line by splitting the chunk on newlines; multi-line error payloads beyond line two are ignored

<a id="u-c93f3bf995bc"></a>
### `stream_response`

`def stream_response(connection, payload, additional_headers = {}, &block)` · [lib/ruby_llm/streaming.rb:L8-L29][f1]

Streams a completion request into both a final Message and per-chunk callbacks.

Creates a StreamAccumulator, posts the payload to stream_url with additional headers merged ahead of the request headers when present, and installs an on_data handler with the Faraday-1 or Faraday-2 option syntax depending on faraday_1?. Each parsed chunk is fed to accumulator.add and then to the caller's block. After the post completes, the accumulated message (role, content, tool calls, token counts) is returned and its content debug-logged.

uses: [stream_accumulator.rb-rest](r1-streaming-accumulation.md#u-bd937899bd89); calls: [handle_stream](r2-streaming-shared.md#u-c0c2c766679b)

<a id="u-c0c2c766679b"></a>
### `handle_stream`

`def handle_stream(&block)` · [lib/ruby_llm/streaming.rb:L31-L35][f1]

Adapts raw SSE data into chunks for a block: wraps to_json_stream so each non-nil parsed data payload is converted with build_chunk and passed to the block.

build_chunk itself is provider-side and not in this file.

**Uncertainties.**

- build_chunk is not defined in this batch; its failure modes are unproven

<a id="u-ec2920a443c8"></a>
### `Chunk`

`class Chunk < Message end` · [lib/ruby_llm/chunk.rb:L4-L5][f2]

Empty Message subclass that types streaming chunks.

It declares no attributes or methods; all Message behavior is inherited unchanged. Graph evidence shows provider streaming code (Anthropic, Bedrock, Gemini, OpenAI `build_chunk`) constructs it.

inherits: [Message](r1-messaging-primitives.md#u-cb349e033cb3)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/streaming.rb
[f2]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/chunk.rb
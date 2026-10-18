# Bedrock Event-Stream Streaming

**Capability.** Decodes the Bedrock event-stream wire format: 12-byte prelude reading and resynchronization scanning, plus staged JSON decoding of event payloads with debug logging in rescue branches.

Use prelude handling to frame raw bytes and payload processing to decode each event; process_payload is the entry point per payload.

**Depends on.**

- [Message & ToolCall Value Objects](r1-messaging-primitives.md) · model-inferred · 0 edge(s)
- [Bedrock Adapter](r2-provider-bedrock.md) · graph-only · 1 edge(s)
- [Shared Streaming](r2-streaming-shared.md) · graph-only · 1 edge(s)

**Depended on by.**

- [Bedrock Adapter](r2-provider-bedrock.md) · graph-only · 8 edge(s)

Parent: [Bedrock Adapter](r1-bedrock-adapter.md)

## Units (5)

<a id="u-ce096607b18b"></a>
### `prelude-handling-rb-prelude-reading`

`def can_read_prelude?(chunk, offset)` · [lib/ruby_llm/providers/bedrock/streaming/prelude_handling.rb:L9-L11][f1]

Reading and validating the 12-byte event prelude of the Bedrock event-stream framing.

can_read_prelude? is true when at least 12 bytes remain after the offset. read_prelude unpacks two big-endian 32-bit integers: total_length at offset, headers_length at offset+4. valid_lengths? delegates to valid_length_constraints?. calculate_positions computes headers_end = offset + 12 + headers_length and payload_end = offset + total_length - 4, subtracting 4 bytes for the message CRC. valid_positions? rejects headers_end >= payload_end, headers_end >= chunk_size, and payload_end > chunk_size; all other combinations pass.

**Uncertainties.**

- read_prelude raises on short slices; whether callers guard with can_read_prelude? first is determined outside this file.

<a id="u-3e4d0120d1ac"></a>
### `prelude-handling-rb-scanning`

`def find_next_message(chunk, offset)` · [lib/ruby_llm/providers/bedrock/streaming/prelude_handling.rb:L37-L40][f1]

Resynchronizing on the byte stream after an unparseable position.

find_next_message scans for the next plausible prelude starting at offset+4 and returns that position, or chunk.bytesize when none is found. find_next_prelude iterates scan_range (start_offset until bytesize - 8, so an 8-byte prelude read stays in bounds) and returns the first position passing valid_prelude_at_position?. That check reads two candidate big-endian lengths at the position and applies valid_length_constraints?: both must be non-nil, total_length must be in (0, 1_000_000], and headers_length must be positive and strictly less than total_length.

**Uncertainties.**

- Plausibility is heuristic (length constraints only); a false-positive position passing these checks cannot be excluded from this file.

<a id="u-9fcff8569795"></a>
### `RubyLLM.Providers.Bedrock.Streaming.PayloadProcessing.process_payload`

`def process_payload(payload, &)` · [lib/ruby_llm/providers/bedrock/streaming/payload_processing.rb:L11-L18][f2]

Entry point for one raw Bedrock event payload.

It slices the JSON object out of the payload via extract_json_payload, parses and processes it with parse_and_process_json (which ultimately yields Chunk objects to the block). Rescue order: JSON::ParserError is logged at debug level with the payload via log_json_parse_error and swallowed; any other StandardError is logged at debug level via log_general_error and swallowed. Failures therefore never propagate and never yield a chunk.

calls: [payload-processing-rb-json-steps](r1-bedrock-streaming.md#u-e74f9d83adba); raises: [payload-processing-rb-error-logging](r1-bedrock-streaming.md#u-18f7eebeeb0d)

<a id="u-e74f9d83adba"></a>
### `payload-processing-rb-json-steps`

`def extract_json_payload(payload)` · [lib/ruby_llm/providers/bedrock/streaming/payload_processing.rb:L22-L26][f2]

Staged decoding of a Bedrock event.

extract_json_payload slices payload from the first '{' to the last '}' (nil bounds produce nil/short slices if no braces exist). parse_and_process_json runs JSON.parse and forwards to process_json_data. process_json_data returns without yielding when json_data['bytes'] is falsy; otherwise decode_and_parse_data Base64.strict_decode64's the bytes and JSON.parses the result, and create_and_yield_chunk calls the block with build_chunk(data). build_chunk constructs Chunk.new(**extract_chunk_attributes(data)) where the attributes are role :assistant plus the ContentExtraction getters: model_id, streaming content, input/output/cached/cache-creation tokens, and tool calls.

calls: [Chunk](r2-streaming-shared.md#u-ec2920a443c8); uses: [content-extraction-rb-getters](r2-provider-bedrock.md#u-0d5d57c66bf6)

**Uncertainties.**

- Base64 and JSON failures inside decode_and_parse_data propagate to process_payload's rescues; behavior beyond that is defined there.
- A payload with no '{'/'}' makes extract_json_payload return nil or a partial slice, whose JSON.parse outcome is only handled upstream.

<a id="u-18f7eebeeb0d"></a>
### `payload-processing-rb-error-logging`

`def log_json_parse_error(error, json_payload)` · [lib/ruby_llm/providers/bedrock/streaming/payload_processing.rb:L68-L71][f2]

Debug-level loggers used by process_payload's rescue branches.

log_json_parse_error logs the parser error message plus the inspect of the attempted payload; log_general_error logs only the error message. Neither re-raises nor returns meaningful values.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/providers/bedrock/streaming/prelude_handling.rb
[f2]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/providers/bedrock/streaming/payload_processing.rb
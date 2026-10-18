# Stream Accumulation

**Capability.** Accumulates streamed chunks into running state and finalizes them into a complete assistant Message, including merged tool-call fragments.

Feed each chunk to StreamAccumulator#add; read the finished Message from the support methods. Tool-call fragments are merged by accumulate_tool_calls.

**Depends on.**

- [Message & ToolCall Value Objects](r1-messaging-primitives.md) · graph-confirmed · 3 edge(s) · StreamAccumulator finalizes accumulated chunks into Message and ToolCall objects.

**Depended on by.**

- [Shared Streaming](r2-streaming-shared.md) · graph-only · 4 edge(s)
- [Bedrock Adapter](r2-provider-bedrock.md) · graph-only · 3 edge(s)
- [Gemini Chat & Schema](r1-gemini-chat.md) · graph-only · 1 edge(s)

Parent: [Conversation Core](r1-conversation-core.md)

## Units (3)

<a id="u-4ce14f98c91b"></a>
### `RubyLLM.StreamAccumulator.add`

`def add(chunk)` · [lib/ruby_llm/stream_accumulator.rb:L18-L30][f1]

Ingests one streamed chunk into running state, optionally debug-logging the chunk and the accumulator when config.log_stream_debug is on.

Records the model id from the first chunk only. If the chunk carries tool calls they are accumulated; otherwise the chunk's content string (or '' when nil) is appended to the accumulated content. count_tokens then updates input/output/cached/cache-creation token counts whenever the chunk supplies them.

calls: [RubyLLM.StreamAccumulator.accumulate_tool_calls](r1-streaming-accumulation.md#u-040152b070f8)

<a id="u-040152b070f8"></a>
### `RubyLLM.StreamAccumulator.accumulate_tool_calls`

`def accumulate_tool_calls(new_tool_calls)` · [lib/ruby_llm/stream_accumulator.rb:L66-L83][f1]

Merges streamed tool-call fragments.

Fragments with an id create or replace a ToolCall keyed by the raw chunk id (storing a SecureRandom.uuid as the ToolCall id when the chunk id is empty), seed arguments to '' when absent, and record that id as the latest. Fragments without an id are argument deltas appended to the ToolCall tracked by the latest id, silently dropped if none exists.

**Notes.**

- condition: @tool_calls is keyed by the raw chunk id even when the stored ToolCall id is a generated uuid, so later lookups by that uuid would miss

uses: [ToolCall](r1-messaging-primitives.md#u-f564974b1732)

<a id="u-bd937899bd89"></a>
### `stream_accumulator.rb-rest`

`def initialize` · [lib/ruby_llm/stream_accumulator.rb:L8-L16][f1]

Support methods turning streamed chunks into a finished assistant Message.

initialize starts with empty content and tool-call map and nil token counters. to_message builds an assistant Message whose content is nil when nothing accumulated, carrying the resolved model id, tool calls, token counts, and the raw response. tool_calls_from_stream converts each accumulated ToolCall: JSON-string arguments are parsed, empty strings become {}, and non-strings pass through. find_tool_call updates @latest_tool_call_id and returns the matching call when an id is given, but for a nil id it looks up @latest_tool_call — a different, never-assigned variable — so nil-id lookups always return nil. count_tokens copies each token field from a chunk only when present, so later chunks can override earlier ones.

**Notes.**

- failure: find_tool_call's nil-id branch reads the unassigned @latest_tool_call, so it can never find a tool call

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/crmne/ruby_llm/blob/1e315ab4b3f3a150c443dc9a17f504756c2aad6f/lib/ruby_llm/stream_accumulator.rb
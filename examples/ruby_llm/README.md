# RubyLLM: CBE example

A unified Ruby interface to LLM providers, with conversation handling, model metadata, HTTP transport, provider adapters and ActiveRecord integration. Language: **Ruby**. This description follows the generated [RubyLLM](docs/nodes/ruby-llm.md) overview.

Pinned upstream commit: `1e315ab4b3f3a150c443dc9a17f504756c2aad6f`. Input scope: `lib/`. Input metadata is in [inputs.json](../../evaluation/inputs/inputs.json). This snapshot was generated at CBE `a87674d`; it is a showcase, not a scored question-answering experiment.

## Read the map

Start at [docs/INDEX.md](docs/INDEX.md) for the responsibility tree. Then open [Chat Session & Completion Loop](docs/nodes/r1-chat-session.md), then [Model Registry](docs/nodes/r1-model-registry.md), then [Provider Adapters](docs/nodes/provider-framework.md). Choose a unit on a node page and use its id to inspect the catalog explanation.

## Search and inspect

Install CBE from the repository root, then work in this example directory. Decompress the catalog before running commands. `$RUN` below stands for this directory's absolute path; replace it with your local path.

```sh
gzip -dk catalog.json.gz
RUN="$PWD"
cbe find --run-dir "$RUN" --term 'StreamAccumulator.add'
cbe query --run-dir "$RUN" --id 'lib/ruby_llm/stream_accumulator.rb::method::RubyLLM.StreamAccumulator.add::414'
```

The following excerpts are real outputs from a copied snapshot, using `python -m cbe` (the same CLI). Only the leading lines are shown; local absolute paths, if present, are replaced by `<EXAMPLE_DIR>` or `<SOURCE_ROOT>`. The first column of a find result is its display name; the next column is the id usable by query.

`find --term 'StreamAccumulator.add'`:

```text
RubyLLM.Providers.Bedrock.Streaming.Base.stream_response | lib/ruby_llm/providers/bedrock/streaming/base.rb::method::RubyLLM.Providers.Bedrock.Streaming.Base.stream_response::519 | method | lib/ruby_llm/providers/bedrock/streaming/base.rb:L20-L35 | Performs the streaming POST to Bedrock and folds the event stream into a message. | match: outgoing
RubyLLM.Providers.Gemini.Chat.GeminiSchema.resolve_reference | lib/ruby_llm/providers/gemini/chat.rb::method::RubyLLM.Providers.Gemini.Chat.GeminiSchema.resolve_reference::10177 | method | lib/ruby_llm/providers/gemini/chat.rb:L343-L357 | GeminiSchema converts a JSON-Schema-like hash into Gemini's schema format. | match: outgoing
```

`query --id 'lib/ruby_llm/stream_accumulator.rb::method::RubyLLM.StreamAccumulator.add::414'`:

```text
RubyLLM.StreamAccumulator.add  lib/ruby_llm/stream_accumulator.rb::method::RubyLLM.StreamAccumulator.add::414
signature: def add(chunk)
ranges: lib/ruby_llm/stream_accumulator.rb:L18-L30
explain: Ingests one streamed chunk into running state, optionally debug-logging the chunk and the accumulator when config.log_stream_debug is on. Records the model id from the first chunk only. If the chunk carries tool calls they are accumulated; otherwise the chunk's content string (or '' when nil) is appended to the accumulated content. count_tokens then updates input/output/cached/cache-creation token counts whenever the chunk supplies them.
relations: {"target": "lib/ruby_llm/stream_accumulator.rb::method::RubyLLM.StreamAccumulator.accumulate_tool_calls::1688", "kind": "call", "basis": "add delegates tool-call chunks to accumulate_tool_calls"}
internal_edge_counts: {'cfg': 91, 'dataflow': 0}
outgoing: call (<tmp-1> = RubyLLM.logger).debug(chunk.inspect) None [unresolved] lib/ruby_llm/stream_accumulator.rb:L19 id=cpg:rubysrc/call/30064790751
outgoing: call accumulate_tool_calls lib/ruby_llm/stream_accumulator.rb::method::RubyLLM.StreamAccumulator.accumulate_tool_calls::1688 [resolved] lib/ruby_llm/stream_accumulator.rb:L23 id=cpg:rubysrc/call/30064790762
```

## This generation

| Measure | Recorded value |
|---|---:|
| Final status / verify | complete / pass |
| Source tokens (`o200k_base`) | 74,885 |
| Gateway requests, including resumes | 29 |
| Gateway cost, USD (gateway price table) | 0.292913 |
| Model-written text / source | 54.174% |
| Published Markdown / source | 141.219% |
| First pass complete / resumes | yes / 0 |

The import graph is empty: 0 resolved imports and 46 imports without a path. Reaching definitions hit the 50,000-edge cap; 38,310 edges were omitted.

Readings follow [Showcase and Generation runs](../../evaluation/README.md#showcase-e6), which take precedence over [summary.json](summary.json) and [STATUS.md](STATUS.md).  Model-written text and published Markdown are different measures: the latter includes program-written navigation and source-reference lines. Query-layer JSON and graphs are outside these ratios. Verify checks structure, coverage, references and navigation; passing does not establish semantic correctness.

The generated documents describe upstream code; see [LICENSE](LICENSE) for the upstream code's copyright and license. RubyLLM also carries [NOTICE](NOTICE).

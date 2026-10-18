# fmt: CBE example

A formatting library with a compiled runtime engine and extensions for compile-time formats, dates, colors, ranges and OS I/O. Language: **C++**. This description follows the generated [fmt Formatting Library](docs/nodes/fmt-lib.md) overview.

Pinned upstream commit: `b4ffa39b9994c961418406f47358791d89a5aa48`. Input scope: `include/` and `src/`, with `--header-language cpp`. Input metadata is in [inputs.json](../../evaluation/inputs/inputs.json). This snapshot was generated at CBE `a87674d`; it is a showcase, not a scored question-answering experiment.

## Read the map

Start at [docs/INDEX.md](docs/INDEX.md) for the responsibility tree. Then open [Core Format Engine](docs/nodes/core-format-engine.md), then [Duration Formatting](docs/nodes/chrono-duration.md), then [Compile-Time Parser](docs/nodes/compile-parser.md). Choose a unit on a node page and use its id to inspect the catalog explanation.

## Search and inspect

Install CBE from the repository root, then work in this example directory. Decompress the catalog before running commands. `$RUN` below stands for this directory's absolute path; replace it with your local path.

```sh
gzip -dk catalog.json.gz
RUN="$PWD"
cbe find --run-dir "$RUN" --term 'assert_fail'
cbe query --run-dir "$RUN" --id 'include/fmt/format-inl.h::function::assert_fail::1007'
```

The following excerpts are real outputs from a copied snapshot, using `python -m cbe` (the same CLI). Only the leading lines are shown; local absolute paths, if present, are replaced by `<EXAMPLE_DIR>` or `<SOURCE_ROOT>`. The first column of a find result is its display name; the next column is the id usable by query.

`find --term 'assert_fail'`:

```text
assert_fail | include/fmt/format-inl.h::function::assert_fail::1007 | function | include/fmt/format-inl.h:L49-L54 | Reports a failed assertion by writing file, line, and message to stderr, then aborts. | match: id,signatures,signature,reverse_relations,outgoing,incoming,name,unit,unit_id,display_name
include/fmt/args.h:FMT_BEGIN_NAMESPACE (6) | include/fmt/args.h::function::FMT_BEGIN_NAMESPACE::433::s7 | function | include/fmt/args.h:L201-L205 | Pre-allocates capacity for at least new_cap total arguments and new_cap_named named arguments. | match: explain,relations
```

`query --id 'include/fmt/format-inl.h::function::assert_fail::1007'`:

```text
assert_fail  include/fmt/format-inl.h::function::assert_fail::1007
signature: FMT_FUNC void assert_fail(const char* file, int line, const char* message)
ranges: include/fmt/format-inl.h:L49-L54
explain: Reports a failed assertion by writing file, line, and message to stderr, then aborts. It deliberately calls std::fprintf unchecked so that a failure writing to stderr cannot trigger a recursive assertion. It never returns; the process terminates via abort.
reverse_relations: {"source": "include/fmt/args.h::function::FMT_BEGIN_NAMESPACE.reserve::6790", "target": "include/fmt/format-inl.h::function::assert_fail::1007", "kind": "raise", "basis": "graph edge from reserve to assert_fail; FMT_ASSERT guard on new_cap >= new_cap_named"}
reverse_relations: {"source": "grp:color.h-text-style", "target": "include/fmt/format-inl.h::function::assert_fail::1007", "kind": "raise", "basis": "get_foreground/get_background/get_emphasis use FMT_ASSERT"}
internal_edge_counts: {'cfg': 6, 'dataflow': 36}
outgoing: call <unresolvedNamespace>.fprintf:<unresolvedSignature>(5) cpg:c/ext/<unresolvedNamespace>.fprintf:<unresolvedSignature>(5) [external] include/fmt/format-inl.h:L52 id=cpg:c/call/30064776237
```

## This generation

| Measure | Recorded value |
|---|---:|
| Final status / verify | partial / fail |
| Source tokens (`o200k_base`) | 185,053 |
| Gateway requests, including resumes | 30 |
| Gateway cost, USD (gateway price table) | 0.544564 |
| Model-written text / source | 17.060% |
| Published Markdown / source | 39.363% |
| First pass complete / resumes | no (still partial) / 2 |

The run stayed partial after two resumes. `format.h` and `core.h` have no published unit: 73,397 tokens, 39.663% of the source. Both resumes exited 2 with tasks still leased; the root cause was not located. After the resumes, 28 node pages lost dependency notes. The summary under-counts 6 requests. The first `format.h` response hit the 49,152-token output limit; `FMT_END_EXPORT` was indexed as a function covering lines 928–1755. Nineteen files reported `syntax_error`. Generation ran under Python 3.13.

Readings follow [Showcase and Generation runs](../../evaluation/README.md#showcase-e6), which take precedence over [summary.json](summary.json) and [STATUS.md](STATUS.md). Those artifacts still say `running` and the summary records 24 tasks; the evaluation reports the final partial outcome and 30 gateway requests. Model-written text and published Markdown are different measures: the latter includes program-written navigation and source-reference lines. Query-layer JSON and graphs are outside these ratios. Verify checks structure, coverage, references and navigation; passing does not establish semantic correctness.

The generated documents describe upstream code; see [LICENSE](LICENSE) for the upstream code's copyright and license.

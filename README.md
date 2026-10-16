# Codebase Explorer

Codebase Explorer (CBE) turns source code and code graphs into structured explanations, a semantic module tree, and a searchable documentation index. It freezes the source, splits it at syntax boundaries, and supplies the relevant code and graph evidence to the model. The same generation state supports host-agent subagents and an OpenAI-compatible API.

This checkout contains **2.2.0.dev0**. It is a development version; see [CHANGELOG.md](CHANGELOG.md) for the changes from 2.1.1. Python 3.12 or 3.13 is required.

## Install and inspect a repository

From this checkout:

```sh
uv tool install --python 3.13 .
cbe --version
cbe languages
```

The standard installation includes Tree-sitter grammars for C, C++, Python, JavaScript, TypeScript/TSX, Java, and Go. The `languages` extra adds Ruby, Rust, PHP, and C#; `languages-community` adds the community grammars for Kotlin and Swift:

```sh
uv tool install --python 3.13 '.[graphs,languages,languages-community]'
cbe languages
```

All use the same context interface. `cbe languages` reports extensions, grammar versions, provenance, availability, and plugin errors. Missing grammars and parse errors remain visible in diagnostics. ABAP, Jimple bytecode, and Ghidra output do not currently have a matching source grammar in this interface. A `.h` file defaults to C with an ambiguity diagnostic. Pass `--header-language cpp` to `context build`, `graph build`, `host plan`, or `generate` for C++ headers (`c` also selects C explicitly). A resumed run keeps its original language choice.

Build a source context without making a model call:

```sh
cbe context build /absolute/path/to/repo --output /absolute/path/to/context.json
cbe context query --context /absolute/path/to/context.json --path src/example.py
```

Chunks have stable identifiers within a snapshot, original byte and line ranges, source text, hashes, and declaration context. Nested declarations do not duplicate their parent's source. Joining a file's chunks in byte order reconstructs that file. Large declarations are segmented at syntax boundaries; indivisible large tokens and unsupported inputs are reported explicitly.

## Generate and query code graphs

Tree-sitter provides syntax and code boundaries. Import resolution, calls, control flow, and data flow come from external analyzers. Each graph records the backend version, input hashes, capabilities, unresolved targets, and analysis conditions. A graph that does not match the current source is rejected when building a context.

The graph adapters use [Joern](https://joern.io/), [Grimp](https://grimp.readthedocs.io/), and [dependency-cruiser](https://github.com/sverweij/dependency-cruiser) according to the language and graph type. The selected integration versions are Joern 4.0.654, Grimp 3.17, and dependency-cruiser 16. Install the `graphs` extra for Grimp (`uv tool install --python 3.13 '.[graphs]'`). Joern and dependency-cruiser are separate installations. The CBE package does not include Joern, a JDK, or Node dependencies.

| Source language | Import backend | Call / CFG / local definition-use backend | Relevant conditions |
|---|---|---|---|
| C / C++ | Joern include declarations | Joern | Include paths, macros and compilation settings affect results; virtual calls may bind to a static base target. |
| Python | Grimp, plus Joern declarations | Joern | Package layout affects imports; dynamic and external calls can remain unresolved. |
| JavaScript / TypeScript / TSX | dependency-cruiser, plus Joern declarations | Joern | Dynamic imports, CommonJS and external targets may remain partial. |
| Java | Joern declarations | Joern | Project types and dependencies affect resolution. |
| Go | Joern declarations | Joern | Cross-package calls may remain unresolved or external. |
| Ruby | Joern declarations | Joern | The frontend excludes `test`, `tests` and `spec` paths by default. |
| Rust | Joern declarations | Joern | The frontend requires a Cargo project layout; a flat source directory can fail. |
| PHP | Joern declarations | Joern | An external PHP runtime (7 or later) is required. The local trial without it reported a failed analysis. |
| C# | Joern declarations | Joern | Namespace and project layout affect resolution; the bundled AST generator must run on the host platform. |
| Kotlin | Joern declarations | Joern | Project dependencies and build conditions affect resolution. |
| Swift | Joern declarations | Joern | The frontend parses per file; the tested cross-file call remained external. |

Joern import declarations do not establish a resolved file dependency. Capabilities describe the actual run, including frontend failures; a registered source language alone does not establish semantic graph coverage. Use an installed Joern distribution and, when needed, a local dependency-cruiser executable:

```sh
cbe graph build /absolute/path/to/repo \
  --output /absolute/path/to/graph.json \
  --joern-home /absolute/path/to/joern-cli \
  --depcruise-bin /absolute/path/to/node_modules/.bin/depcruise
cbe graph capabilities --graph /absolute/path/to/graph.json
cbe graph query --graph /absolute/path/to/graph.json --path src/example.py --kind call
cbe context build /absolute/path/to/repo \
  --graph /absolute/path/to/graph.json --output /absolute/path/to/context.json
```

`--language` can limit analysis to a language. `--max-methods` limits only CFG export per frontend (default: unlimited); method identities and calls remain complete, diagnostics report the exact omitted method count, and CFG capability is `partial` when methods are omitted. `--max-reaching-defs` bounds reaching-definition edges; `--dataflow-path-method` opts into sampled value-flow paths. `--joern-heap 8g` sets the Joern JVM maximum heap through `JAVA_TOOL_OPTIONS`, preserving other JVM options; without it, JVM settings are inherited. Backend failures retain their cause in graph diagnostics and print a line to stderr. Partial builds succeed when another backend completes; if every backend fails, the command exits nonzero and retains a diagnostic graph when possible. Joern JSON is written compactly to a writer to avoid an extra whole-document string and byte array. `graph query` accepts `import`, `call`, `cfg`, or `dataflow`, a node ID, and an edge direction (`in`, `out`, or `both`). A local query retains boundary endpoints and identifies omitted scope. It can read the graph embedded in a generation run's frozen `context.json` for manual inspection of the evidence used at planning. Host detail tasks receive a bounded excerpt and a separate complete evidence file when the batch has graph nodes. The full graph stays in the output file; `graph build` prints a compact result and capability report.

The graph's `quality` audit reports edge status counts, integrity issues, and incomplete capabilities; `cbe graph capabilities --graph /absolute/path/to/graph.json --repo /absolute/path/to/repo` refreshes the audit against current repository files.

Graphs produced by CBE record the registered source set and recognized repository configuration files. Context building and generation check their hashes and reject additions, removals, edits, or unstable builds. These checks run before and after analysis of the repository; they do not create an isolated filesystem snapshot. External graphs without configuration provenance retain source-manifest validation, with configuration identity unknown.

Graph kinds have different meanings:

- **Import** edges identify static module, package, or include dependencies according to the selected resolver.
- **Call** edges are static analysis results. Dynamic dispatch, reflection, unresolved imports, and external code can leave targets unknown or conditional.
- **CFG** edges describe the analyzer's control-flow nodes. They are not a runtime execution trace.
- **Dataflow** edges or paths describe the analyzer's definition/use or value-flow analysis, with its stated scope and library models. A local definition/use graph does not prove complete interprocedural data flow.

C/C++ include paths, macros, build configuration, and generated sources affect analysis. Dynamic languages also require explicit uncertainty. Consult the generated `capabilities` and `diagnostics` instead of treating a nonempty graph as complete coverage.

## Generate through a host agent

Install the bundled skill in the project where the agent will run:

```sh
cbe-install install --host claude-code   # or --host codex
```

The host uses its existing subagent facility and subscription. It drives the CLI's durable task loop:

```sh
cbe host plan /absolute/path/to/repo --graph /absolute/path/to/graph.json \
  --run-dir /absolute/path/to/run --review sample --jobs 4 --host claude-code
cbe host next --run-dir /absolute/path/to/run
# Dispatch the returned task instructions to a subagent, then submit its JSON result.
cbe host submit --run-dir /absolute/path/to/run --task TASK
cbe host verify --run-dir /absolute/path/to/run
```

The skill describes the complete loop and the result contracts. `host plan` accepts `.` or any path for the repository; `--run-dir`, `--repo`, and `--graph` need absolute paths. The skill's commands avoid quoted shell variables, because Claude Code asks for confirmation before it runs a command with quoted text it cannot check, even when `cbe` is on the allow list. The `tasks` count that `plan` prints covers the planned tasks only; each review finding adds one repair task later. `next` leases every task it returns, including the re-ask of a rejected task, so each one needs a subagent; attempts at one task share a label and their usage adds up. `submit` prints one JSON object and exits 0 whether it accepts or rejects: `accepted: true` carries `normalized` and `flags`, and `accepted: false` carries `error`, `attempts`, and `task_status` (`pending` for a queued re-ask, `failed` when the attempts are used up). `progress.log` records both.

Detail authors receive their assigned frozen source chunks and local graph evidence. The tree stage receives responsibility summaries, source locations and counted unit edges; it assigns each unit one primary place in a semantic tree. Static resolved edges retain their analyzer kind. Detail authors' relations are a separate `kind=relation` category with `provenance=model_inferred`; they do not become static call evidence. Reports count the categories separately. A directory or a dense set of import edges does not by itself define a module's responsibility.

Large trees use program-selected candidate regions, one `tree_region-*` task per region, then a `tree` merge that attaches their accepted subtrees. Set `CBE_TREE_MAX_UNITS` and `CBE_TREE_MAX_TOKENS` before the first tree dispatch to configure the region limits; defaults are defined in `cbe.aggregation.Limits`. The plan records the chosen limits and each region's initial completion input tokens in `host/state.json`. Files are indivisible; a unit spanning multiple files joins those files into one block. Unit count is a packing target that an indivisible block may exceed, while the token ceiling is strict. Regions are balanced using incremental summary and edge weights, directory locality and import affinity, then their complete prompts are measured. A file block larger than the token budget produces an explicit planning error with the configuration remedy. Region tasks wait for detail review and repair to settle, including reviews whose source module failed; small runs keep one tree task.

Region node ids use compact prefixes (`r1-`, `r2-`, …). A region submission whose prefixed id exceeds 64 characters is rejected with the allowed length. A failed region gets a mechanical subtree. A failed merge retains all accepted region subtrees beneath a mechanical upper tree, and INDEX distinguishes these two failures. The merge completion input is also measured: if it exceeds the configured budget, the merge fails explicitly and the system overview can still finish from the retained tree. The current implementation does not introduce another merge layer automatically; increase the budget and make a new plan after inspecting this error.

The defaults are 300 units and 64,000 input tokens. The token ceiling leaves room for whole files and inferred relations: an offline replay of accepted Flask answers measured 42,870 tokens for 254 units and 49,971 for 294 units, so both remain single-tree runs. At an explicit 32,000 ceiling the 294-unit snapshot splits into 171 and 123 units (26,677 and 20,250 tokens), with no file split. On celery's 12,106 synthetic units the largest indivisible file needs 44,422 tokens; the old 32,000 ceiling cannot hold it. At the defaults, 41 regions fit (largest 53,503 tokens), and the synthetic merge needs about 50,600 tokens. These are measured input sizes, not a guarantee of model context capacity or semantic grouping quality; configure the limits for the chosen model. Detail records are cached by accepted-answer content, with cache integrity checked before reuse; unchanged `next` calls skip rebuilding records and planning. Caches over 10 MB are compressed.

P1–P7 diagnostics appear in `summary.json` and at the end of INDEX. They are advisory and never request a rewrite. Set `CBE_TREE_MIN_GRAIN`, `CBE_TREE_MAX_GRAIN`, and `CBE_TREE_SHARED_MIN_EDGES` to adjust granularity and shared-utility reporting. P5 reports dependency signals even when a utility already has its own module. Product P7 compares the prior rendering within this run for identical detail input: it says `re-render identical` or `re-render changed`, with no stability pass. Its first observation is `not_checked`. Cross-run id/title stability is assessed only by replay scripts that supply a previous report from another run with the same detail fingerprint; repeated rendering does not test a fresh model completion.

`--graph` is optional. Without it the context explicitly records that no analyzed graph was supplied. The model must not invent missing relations. `--review` selects `none`, `sample`, or `all`. Operational completion, structural validity, and semantic review are separate results.

## Generate through an API

Use any configured OpenAI-compatible chat-completions endpoint:

```sh
# Supply the credential through the named environment variable using your normal secret setup.
cbe generate /absolute/path/to/repo --host api \
  --base-url https://your-endpoint.example/v1 --api-key-env CBE_API_KEY \
  --model your-model-id --graph /absolute/path/to/graph.json \
  --run-dir /absolute/path/to/run --review sample
```

`--config /absolute/path/to/config.json` provides host configuration. API credentials stay in environment variables or the supported credential-file reference. If no credential is configured, CBE omits the Authorization header for endpoints that allow unauthenticated requests. Do not put credentials in a URL. The API client records returned usage and preserves unknown values when usage is absent. Failed completions retain a bounded, redacted provider response, available usage, and finish reason before text extraction; truncation is explicit. A response with only reasoning and no answer remains a failed attempt. Reported token counts are transport/accounting evidence; they do not prove that a model understood the code.

For `--host api`, exact model `zai/glm-5.3-flash` selects resource defaults from
`cbe/model_settings.py`: 1,800 seconds per call, `output_max_tokens: 49152` (including
reasoning), `reasoning_effort: "low"`, JSON object response mode, and reading-batch target/max of
8,000/10,000 source tokens. Whole files stay intact; a single file may exceed
the batch maximum up to the existing 60,000-token file limit. Other API model
IDs retain 420 seconds, no explicit output/reasoning limit, and the original
20,000/25,000 batch sizes. OpenCode and Devin keep their existing defaults.

Set API resource values with `--config`; explicit `--timeout` takes precedence
over the config, which takes precedence over model defaults. For example:

```json
{
  "timeout": 1800,
  "output_max_tokens": 60000,
  "reasoning_effort": "low",
  "response_format": {"type": "json_object"},
  "batch_target_tokens": 8000,
  "batch_max_tokens": 10000
}
```

The endpoint must support the configured request fields. Batch limits apply to
new plans; `--resume` keeps the frozen batches. A response ending with `length`
(or `max_tokens`/`max_output_tokens`) fails with `output_limit`, even if its JSON
parses. Module and repair detail tasks allow 3 answers; other tasks allow 2.
Each rejection includes the error; on the final invalid answer the driver
normalizes usable content or fails the task for resume. Truncated attempts
cannot be accepted by final normalization. Increase
`output_max_tokens` for resume or start a fresh run with smaller batch limits if needed.
`output_max_tokens` caps API output (sent as the provider's `max_tokens` field);
`batch_max_tokens` caps source input per reading batch.
CLI help reads the model defaults table directly.

API config is parsed and validated before planning or sending model requests.
Malformed JSON or invalid resource settings exit 2 without a generated summary.
Timeout and token limits must be positive integers (numeric strings and zero are
rejected); prices must be three finite nonnegative numbers. An explicit batch
target must not exceed its maximum. For models without a default batch target,
setting only `batch_max_tokens` lowers the fallback target to that maximum when
necessary; unspecified limits use the constants from `batching`.

Timeouts and provider failures remain visible as their own errors. Only a
source-bearing response whose reported input is too small is marked
`source_not_delivered`. The rejected answer is not published; the status names
failed tasks and suggests fixing the cause, then using `--resume`.

API `summary.json` sums observed input/output tokens, including returned failed
calls. The observed-total and missing-call conventions also apply to OpenCode
and Devin summaries. Missing-call counters and `usage_complete: false` identify an incomplete
sum; absent usage is never estimated. Cache totals remain unknown when any
cache counter is missing, with the known portion in `observed_cache_tokens`.
API price is unknown (`priced_usd: null`) unless config supplies
`"price_per_million": [INPUT, OUTPUT, CACHE]` in USD per million tokens; missing
usage still prevents pricing. The raw API record includes `actual_model` from
the provider response so gateway fallback can be distinguished from the
requested model.

The signed-in OpenCode and Devin drivers remain available:

```sh
cbe generate /absolute/path/to/repo --host opencode --model provider/model
cbe generate /absolute/path/to/repo --host devin --model your-supported-model
```

Choose a model that your own account can use. CBE does not promise that a provider, model, or subscription is free.

## Read, resume, and verify

Open the `index` path in the generation result. The output includes the semantic navigation tree, detail explanations with source anchors, and a machine-readable catalogue. Use exact IDs returned by `find`:

```sh
cbe find --run-dir /absolute/path/to/run --term Serializer
cbe query --run-dir /absolute/path/to/run --id 'ID-FROM-FIND'
cbe host status --run-dir /absolute/path/to/run
```

Queries return each symbol's disposition. Grouped symbols link to their owning unit's page and anchor; `grp:` unit IDs are searchable too. An `index_only` result has no explanation page and includes its reason. Existing semantic catalogues can be queried without regenerating model output.

Run state, task leases, attempts, accepted results, and the frozen context live inside the run directory. `STATUS.md` and `progress.log` expose progress. A failed task does not discard completed work. Continue after an interruption with:

```sh
cbe host resume --run-dir /absolute/path/to/run
# Or use the same script driver and configuration:
cbe generate /absolute/path/to/repo --host api --model your-model-id \
  --base-url https://your-endpoint.example/v1 --api-key-env CBE_API_KEY \
  --run-dir /absolute/path/to/run --resume
```

Source or graph drift is a reason to make a new plan. An old graph cannot silently become evidence for a new source revision. Verification checks the structure, coverage, source references, catalogue navigation to actual page anchors, and recorded review state; independent semantic review remains responsible for whether the explanations are correct and useful.

`cbe host verify --run-dir /absolute/path/to/run` prints JSON and exits 0 only
when `ok` is true; failed checks exit 3. Scripts can use the exit code or inspect
`ok`. Verification updates `summary.json` (`deterministic_checks_ok` and `status`)
and `STATUS.md`; a finished run with failed checks is `partial`, with failing
check names in the status document. `cbe generate` likewise exits 3 for a partial
run. Fix the reported cause and verify again; source drift requires a new plan.

Detail answers may use inventory IDs from their own batch or `grp:` IDs for
model-defined groups. Normalization must pass the same strict checks before an
answer is published; unrepaired answers stay failed for resume. Model prose that
looks like an inline Markdown link is rendered as literal text, including code
such as `environ['werkzeug.debug.preserve_context'](ctx)`. Code spans and fenced
code remain verbatim; source and navigation links are generated by CBE.

When a detail ID uniquely matches a batch inventory entry by path, kind and
qualified name, final normalization can correct the ID (including suffixes such
as `_full`). A corrected unit definition has a notice beside its body: CBE shows
the original and inventory IDs and warns that the model wrote the body under the
wrong ID, so it may be inaccurate. Reference-only corrections do not add a unit
notice. The same notice is stored in each corrected catalog unit's
`id_corrections` and returned by `query` in text and JSON; `find` marks the row
and directs the reader to `query`. Notices count as program-written `node_text`, not `model_body`, in the
Markdown token breakdown. `STATUS.md` lists `id_corrected` separately from shape
normalization; `summary.json` contains `id_corrected_count` and `id_corrected`
rows with `task`, `original`, `corrected` and `location`. The existing `normalized`
task list remains available. If an extra disposition key corrects to an existing
key, CBE keeps the existing disposition, drops the extra key and records flags.

Automatic `index_only` coverage repair is bounded: a partially supplied detail
answer may need one inventory disposition filled, or two when its batch has at
least 40 inventory symbols. Missing dispositions and entries with invalid `how`
share this allowance; an answer requiring every disposition to be filled is
rejected. Retry diagnostics name missing or invalid IDs and the repair count.
If the final answer still exceeds the allowance, the task fails
and the run stays partial for resume; CBE does not silently replace it with
index-only entries or an older answer. Explicit model-authored `index_only`
choices and complete group dispositions are unaffected.

`STATUS.md` and `summary.json` list `index_only_filled` separately from
`id_corrected`; JSON includes `index_only_filled_count` and rows with `task`,
`symbol`, and `reason` (`missing` or `invalid`). These count only entries made
by normalization and exclude the model's own
`index_only` choices. INDEX notes identify the affected active module/repair;
the note counts as program-written `index` text, outside `model_body`.

Usage reports distinguish known counters, estimates, and missing values. Host-agent usage can be imported where the harness provides the corresponding session records. Unknown model prices remain `null` in JSON and `unknown` in the cost report, even when token counts are exact. `cbe host cost --price INPUT,OUTPUT,CACHE_WRITE,CACHE_READ` accepts supplied rates in USD per million tokens. `cbe host cost` prices exact rows by the model recorded in each transcript; `--model MODEL` prices only the rows that are still estimates, which `import-usage` lists as `tasks_without_exact_usage`. Claude Code reports a subagent's usage in a completion notification after its final reply; a task submitted before that notification still gets exact usage from `import-usage`. Price equivalents are not subscription invoices.

## Development

```sh
uv sync --python 3.13 --group dev
uv run pytest -q
```

The external graph tools are optional at installation time. Tests that require a real analyzer need that analyzer configured; ordinary package tests also exercise missing backends and invalid inputs. Platform support must be assessed for both CBE and the chosen analyzer.

The generated files can be consumed by other tools through explicit paths. CBE does not require a shared database or a second task scheduler. To remove the isolated command, run `uv tool uninstall codebase-explorer`. The product license is [MIT](LICENSE); external analyzers and grammar packages retain their own licenses.

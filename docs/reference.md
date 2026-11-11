# Reference: install, languages, code graph, find / query / source

This page holds the command-level detail that the [README](../README.md) leaves out. For running a generation, resuming it and reading the run directory, see [running.md](running.md). Sections:

- [Install and inspect a repository](#install-and-inspect-a-repository)
- [Optional graph analyzers](#optional-graph-analyzers)
- [Generate and query code graphs](#generate-and-query-code-graphs)
- [Find and query](#find-and-query)
- [Command details](#command-details)
- [Named declaration coverage](#named-declaration-coverage)
- [Worked example: cJSON, step by step](#worked-example-cjson-step-by-step)

## Install and inspect a repository

Install CBE from PyPI, or from a checkout of this repository:

```sh
uv tool install codebase-explorer        # or: pipx install codebase-explorer
uv tool install --python 3.13 .          # from a checkout
cbe --version
cbe languages
```

`cbe --version` prints `cbe 2.2.0`. When `cbe` runs from a source tree without installed package metadata, it prints `cbe source` instead.

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

### Optional graph analyzers

Context building and generation work without any analyzer. A graph adds static import, call and control-flow evidence to the detail tasks and to the dependency view. Dataflow is exported only when you ask for it (`--with-dataflow`). Without a graph, the run records that no graph was supplied, and no dependency pair can be graph-confirmed.

| Analyzer | What it adds | How to install | How CBE finds it |
|---|---|---|---|
| Joern 4.0.654 and Java 21 or newer | Calls, CFG and, on request, dataflow; include and import declarations. The next section lists the languages and their conditions. | `cbe graph setup` downloads the pinned Joern release (about 1.9 GB in total with the Java runtime) and, when no Java 21+ is found, a Temurin 21 JRE into the user cache directory (`~/.cache/cbe/tools` on Linux, `~/Library/Caches/cbe/tools` on macOS), after checking SHA-256 values pinned in the code. Linux x86_64 and macOS (arm64, x86_64) are supported; on other platforms install by hand (below). `cbe graph setup --check` downloads nothing and reports what it finds; `--force` and `--with-java` are the other options. | Joern: `--joern-home DIR`, then `CBE_JOERN_HOME`, then the cache directory, then `joern-parse` on `PATH`. `DIR` is the directory that holds `joern` and `joern-parse`; CBE also looks in `DIR/joern-cli`. A `--joern-home` or `CBE_JOERN_HOME` that does not hold `joern-parse` is an error naming that path; CBE does not fall back to the next place. Java: `JAVA_HOME`, then `java` on `PATH`, then the cache directory. |
| dependency-cruiser 16 and Node.js | JavaScript and TypeScript import graph | `npm install dependency-cruiser@16` in a tools directory. Tested with 16.10.4 on Node.js 22.20.0. | `--depcruise-bin PATH` (for example `.../node_modules/.bin/depcruise`), then `CBE_DEPCRUISE_BIN`, then `depcruise` on `PATH` |
| Grimp 3.17 | Python import graph | `uv tool install --python 3.13 '.[graphs]'` | Imported from the CBE environment |

<details>
<summary>Install Joern by hand</summary>

`cbe graph setup` is the short way. To install yourself, download the `joern-cli-<os>-<arch>.zip` asset for your platform (for example `joern-cli-linux-x86_64.zip` or `joern-cli-macos-arm64.zip`) from the [Joern v4.0.654 release](https://github.com/joernio/joern/releases/tag/v4.0.654), unzip it, and pass the resulting `joern-cli` directory as `--joern-home DIR` or set `CBE_JOERN_HOME`. Each asset has a `.sha512` file next to it. Install Java 21 or newer yourself (Joern's [installation page](https://docs.joern.io/installation/) asks for JDK 19 and says newer JDKs might work; an earlier cJSON test graph was built on JDK 21.0.9) and keep it on `PATH` or in `JAVA_HOME`. The macOS assets are pinned from upstream metadata and have not been exercised by us yet. Do not use a Joern version other than 4.0.654: the graph classification is tested against its output.

</details>

Check what ran with `cbe graph capabilities --graph /absolute/path/to/graph.json`. The `backend.components` list names each analyzer and its version, and every `capabilities` row gives a language, a graph kind and a status, for example `resolved`, `partial`, `empty`, `failed` or `unavailable`. A graph built with Joern 4.0.654 reports:

```text
"backend": {"name": "joern", "version": "4.0.654", "components": [{"name": "joern", "version": "4.0.654"}]}
```

What a missing analyzer costs:

- **No Joern:** no calls, CFG or dataflow for any language, and no Joern import declarations. `graph build` records `backend_unavailable` ("Joern CLI not found; call/cfg/dataflow/import graph skipped; run `cbe graph setup` (downloads about 1.9 GB)"). When no other analyzer covers the requested languages, as for a C-only input, `graph build` exits 2 with `no graph backend was available for the requested languages`.
- **No dependency-cruiser:** the JavaScript and TypeScript import graph is skipped with `backend_unavailable`. If Joern ran, it still records import declarations, but these do not establish a resolved file dependency.
- **No Grimp:** the Python import graph is skipped with `backend_unavailable` ("grimp is not installed; Python import graph skipped (install the 'graphs' extra)").

## Generate and query code graphs

Tree-sitter provides syntax and code boundaries. Import resolution, calls, control flow, and data flow come from external analyzers. Each graph records the backend version, input hashes, capabilities, unresolved targets, and analysis conditions. A graph that does not match the current source is rejected when building a context.

The graph adapters use [Joern](https://joern.io/), [Grimp](https://grimp.readthedocs.io/), and [dependency-cruiser](https://github.com/sverweij/dependency-cruiser) according to the language and graph type. The selected integration versions are Joern 4.0.654, Grimp 3.17, and dependency-cruiser 16. Install the `graphs` extra for Grimp (`uv tool install --python 3.13 '.[graphs]'`). Joern and dependency-cruiser are separate installations; `cbe graph setup` installs Joern and a JRE for you. The CBE package does not include Joern, Java, or Node dependencies.

| Source language | Import backend | Call graph with Joern 4.0.654 (`cbe languages`: `call_graph`) | Relevant conditions |
|---|---|---|---|
| C / C++ | Joern include declarations | works | No preprocessor runs: a header with many macros is cut into coarse chunks, and a macro can be taken for a function name. Include paths and compilation settings affect results; virtual calls may bind to a static base target. Macro uses are not counted as calls. |
| Python | Grimp, plus Joern declarations | works | Package layout affects imports; dynamic and external calls can remain unresolved. |
| JavaScript / TypeScript | dependency-cruiser, plus Joern declarations | works | Dynamic imports, CommonJS and external targets may remain partial. |
| TSX | dependency-cruiser, plus Joern declarations | untested | Uses the same Joern frontend as JavaScript and TypeScript. |
| Java | Joern declarations | works | Project types and dependencies affect resolution. |
| Go | Joern declarations | works | Cross-package calls may remain unresolved or external. |
| Ruby | Joern declarations | works | CBE passes `--no-default-exclude`, so `test`, `tests` and `spec` paths are analyzed. Dynamic dispatch can bind a call to a method of the same name on another class; CBE marks such calls ambiguous, and some wrong bindings remain. |
| Rust | Joern declarations | needs `cargo` | The frontend runs `cargo` (on `PATH`) and needs a Cargo project layout; a flat source directory can fail. |
| PHP | Joern declarations | needs `php` | An external PHP runtime (7 or later) must be on `PATH`. The local trial without it reported a failed analysis. |
| C# | Joern declarations | builds, calls partly resolved | On a real 55-file repository the build completes. Calls whose containing method Joern does not record (361 there, attribute operators) are left out and counted in the `calls_without_owner_omitted` diagnostic. Joern's C# frontend names repository types without their namespace in a call and with it in the method, so C# calls are also matched with namespaces removed inside the signature; an overloaded name gives an ambiguous edge to all its overloads, because the frontend's argument types are not reliable (it types `-1L` and `0.0` as `Int32`). Of the 2,322 exported calls, 689 resolve, 394 are ambiguous, 246 external and 993 unresolved. Joern numbers C# lines from 0; CBE adds 1. |
| Kotlin | Joern declarations | known failure | Joern 4.0.654 failed on a real 146-file repository: `joern-parse` stopped with `key not found: MethodRef`, and the build recorded a failed capability. A two-file test fixture works, so small inputs may succeed. |
| Swift | Joern declarations | untested | The frontend parses per file; the tested cross-file call remained external. |

"works" means a real repository of that language produced a call graph with Joern 4.0.654; resolution quality still depends on the code. Source parsing and chunking support every language in the table whatever the call-graph column says.

Joern import declarations do not establish a resolved file dependency. Capabilities describe the actual run, including frontend failures; a registered source language alone does not establish semantic graph coverage. `graph build` finds the Joern and Java that `cbe graph setup` installed. Pass `--joern-home` to use another Joern, and `--depcruise-bin` for a local dependency-cruiser executable:

```sh
cbe graph build /absolute/path/to/repo \
  --output /absolute/path/to/graph.json \
  --depcruise-bin /absolute/path/to/node_modules/.bin/depcruise
cbe graph capabilities --graph /absolute/path/to/graph.json
cbe graph query --graph /absolute/path/to/graph.json --path src/example.py --kind call
cbe context build /absolute/path/to/repo \
  --graph /absolute/path/to/graph.json --output /absolute/path/to/context.json
```

`--language` can limit analysis to a language. `--max-methods` limits only CFG export per frontend (default: unlimited); method identities and calls remain complete, diagnostics report the exact omitted method count, and CFG capability is `partial` when methods are omitted. Dataflow (reaching definitions) is not exported by default, because nothing in a generation run reads its content and it was over half of `graph.json` on flask (23 of 41 MB). `--with-dataflow` exports it; giving `--max-reaching-defs` (cap on reaching-definition edges, default 50,000) or `--dataflow-path-method` (sampled value-flow paths) also turns it on. Without it the dataflow capability is `not_requested`, and `cbe graph query --kind dataflow` and `cbe query --edges dataflow` answer "this graph was built without dataflow; rebuild with `cbe graph build --with-dataflow`". CFG is exported by default because its node labels feed the graph evidence in detail prompts. `--joern-heap 8g` sets the Joern JVM maximum heap through `JAVA_TOOL_OPTIONS`, preserving other JVM options; without it, JVM settings are inherited. Backend failures retain their cause in graph diagnostics and print a line to stderr. Partial builds succeed when another backend completes; if every backend fails, the command exits nonzero and retains a diagnostic graph when possible. Joern JSON is written compactly to a writer to avoid an extra whole-document string and byte array. `graph query` accepts `import`, `call`, `cfg`, or `dataflow`, a node ID, and an edge direction (`in`, `out`, or `both`). A local query retains boundary endpoints and identifies omitted scope. It can read the graph embedded in a generation run's frozen `context.json` for manual inspection of the evidence used at planning. Host detail tasks receive a bounded excerpt and a separate complete evidence file when the batch has graph nodes. The full graph stays in the output file; `graph build` prints a compact result and capability report.

The graph's `quality` audit reports edge status counts, integrity issues, and incomplete capabilities; `cbe graph capabilities --graph /absolute/path/to/graph.json --repo /absolute/path/to/repo` refreshes the audit against current repository files. A graph without this audit is refused, whatever made it; build the graph with the current `cbe graph build`.

Graphs produced by CBE record the registered source set and recognized repository configuration files. Context building and generation check their hashes and reject additions, removals, edits, or unstable builds. These checks run before and after analysis of the repository; they do not create an isolated filesystem snapshot. A `cbe-graph/1` file made by another tool is not a supported input: it is read only if it carries the same `quality` audit, and no command adds one. If it has the audit but no configuration provenance, its source manifest is still checked and its configuration identity is reported as unknown.

Graph kinds have different meanings:

- **Import** edges identify static module, package, or include dependencies according to the selected resolver.
- **Call** edges are static analysis results. Dynamic dispatch, reflection, unresolved imports, and external code can leave targets unknown or conditional.
- **CFG** edges describe the analyzer's control-flow nodes. They are not a runtime execution trace.
- **Dataflow** edges or paths describe the analyzer's definition/use or value-flow analysis, with its stated scope and library models. A local definition/use graph does not prove complete interprocedural data flow.

C/C++ include paths, macros, build configuration, and generated sources affect analysis. Dynamic languages also require explicit uncertainty. Consult the generated `capabilities` and `diagnostics` instead of treating a nonempty graph as complete coverage.

## Find and query

`find` searches the catalogue and `query` returns one entry by exact ID. Both read only `catalog.json`, so they work on any rendered run, complete or partial, without a model call. Both need an absolute `--run-dir`.

`cbe find --run-dir RUN --term TEXT [--limit N] [--json]` matches TEXT, ignoring case, against every catalogue field of each symbol: its ID, name, explanation, signatures, relations and graph edges. Exact name or ID matches come first; the other rows keep catalogue order. `--limit` defaults to 25. A search without a match prints nothing and exits 0. For Python files it also matches the concrete facts the program reads from the syntax tree (parameter defaults, named constants, option tables, format templates, literal raises); a hit there shows `match: facts`, and `cbe query` prints the facts of a symbol. Other languages have no facts table. On the evaluation's cJSON run:

```text
$ cbe find --run-dir /absolute/path/to/run --term cJSON_Parse --limit 3
cJSON_Parse | cJSON.c::function::cJSON_Parse::33515 | function | cJSON.c:L1227-L1230 | Convenience wrappers: cJSON_Parse parses a NUL-terminated string with no return_parse_end and no null-termination requirement; cJSON_ParseWithLength parses exactly buffer_length bytes with the same defaults. | match: id,explain,members,summary,signatures,signature,folded_members,outgoing,name,reason,display_name
cJSON_New_Item | cJSON.c::function::cJSON_New_Item::6059 | function | cJSON.c:L241-L250 | Allocates one cJSON node via the given hooks and memsets it to zero, so type is cJSON_Invalid and all pointers are NULL. | match: incoming
cJSON_Delete | cJSON.c::function::cJSON_Delete::6306 | function | cJSON.c:L253-L276 | Frees an item and its entire ->next sibling chain. | match: incoming
```

Each line is `name | id | kind | location | summary | match: fields`. Only the first row is `cJSON_Parse` itself. `cJSON_New_Item` and `cJSON_Delete` match only in `incoming`: the parser calls them, so they are neighbors, not the symbol you searched for. `--json` prints the same rows as objects with `id`, `name`, `kind`, `location`, `summary` and `matched_fields`.

`cbe query --run-dir RUN --id ID [--json] [--edges all|import,call,cfg,dataflow]` takes an ID: an inventory symbol ID or unit ID from `find`, a `grp:` group ID, a file path, or a responsibility-node ID (the node page name without `.md`, for example `core-parsing`). It also takes the names a page shows, tried in this order: a group unit's heading without the `grp:` prefix; a unit heading or its anchor (`u-…`, with or without `#`); a symbol name. When one ID matches, the output starts with `resolved: NAME -> ID`; when several match, it lists them and exits 2 without choosing. `cbe source` resolves names the same way. The text view prints the explanation once, then one line per relation or edge:

```text
$ cbe query --run-dir /absolute/path/to/run --id 'cJSON.c::function::cJSON_Parse::33515'
cJSON_Parse  cJSON.c::function::cJSON_Parse::33515
signature: CJSON_PUBLIC(cJSON *) cJSON_Parse(const char *value)
signatures: {"id": "cJSON.c::function::cJSON_Parse::33515", "signature": "CJSON_PUBLIC(cJSON *) cJSON_Parse(const char *value)"}
signatures: {"id": "cJSON.c::function::cJSON_ParseWithLength::33618", "signature": "CJSON_PUBLIC(cJSON *) cJSON_ParseWithLength(const char *value, size_t buffer_length)"}
ranges: cJSON.c:L1227-L1230
explain: Convenience wrappers: cJSON_Parse parses a NUL-terminated string with no return_parse_end and no null-termination requirement; cJSON_ParseWithLength parses exactly buffer_length bytes with the same defaults. Both forward to cJSON_ParseWithLengthOpts and inherit its failure semantics.
folded_members: "cJSON.c::function::cJSON_Parse::33515"
folded_members: "cJSON.c::function::cJSON_ParseWithLength::33618"
internal_edge_counts: {'cfg': 4, 'dataflow': 10}
outgoing: call cJSON_ParseWithOpts cJSON.c::function::cJSON_ParseWithOpts::31069 [resolved] cJSON.c:L1229 id=cpg:c/call/30064772040
```

Calls and imports keep their analyzer status (`resolved`, `unresolved`, `external`, `ambiguous`). CFG and dataflow edges inside the unit are only counted in `internal_edge_counts` (a graph built without dataflow shows no `dataflow` entry rather than 0); `--edges cfg,dataflow` or `--edges all` lists them from the frozen graph in `context.json`. `--edges dataflow` on a graph built without dataflow says to rebuild with `cbe graph build --with-dataflow`.

**Grouped symbols.** The text view does not print a symbol's disposition, owning unit or page. Here `cJSON_Parse` has no unit of its own: the model folded it with `cJSON_ParseWithLength` into a group. `--json` shows this (excerpt):

```text
"node": "core-parsing",
"page": "nodes/core-parsing.md",
"anchor": "#u-0d57b2c47d88",
"how": "grouped",
"unit": "grp:cJSON.c-parse-entrypoints",
"reason": "One-line wrapper folded with cJSON_ParseWithLength.",
"unit_id": "grp:cJSON.c-parse-entrypoints",
```

Query the `unit_id` to get the whole group, with both members' ranges (`cJSON.c:L1227-L1230, cJSON.c:L1232-L1235`) and both outgoing calls. `grp:` IDs also appear in `find` results.

**Index-only symbols.** A symbol with `"how": "index_only"` has no explanation page: no unit lists it, so CBE indexes it without prose and records a `reason` (for example `not explained; indexed without prose`). The text view prints that reason as `explain:`, and the JSON view has `"page": null` and the same `reason`. The example below is from an earlier run, where the model gave its own reason; the output shape is the same:

```text
$ cbe query --run-dir /absolute/path/to/run --id 'cJSON.c::function::cast_away_const::54779'
cast_away_const  cJSON.c::function::cast_away_const::54779
signature: static void* cast_away_const(const void* string)
ranges: cJSON.c:L2073-L2076
explain: One-expression const cast helper, no behavior worth prose.
internal_edge_counts: {'cfg': 3, 'dataflow': 9}
incoming: call add_item_to_object cJSON.c::function::add_item_to_object::55010 [resolved] cJSON.c:L2094 id=cpg:c/call/30064773003
...
```

`STATUS.md` and `summary.json` list the symbols that stayed unexplained after the last answer (`unexplained_count`, `unexplained`).

**Answer-time grounding.** When an explanation answer arrives, CBE takes the identifiers each explanation names: words in backticks, code-like words (snake_case, camelCase, a word followed by `(`) and words equal to a symbol name of the repository. An explanation is suspect when it names at least one identifier and none of them occurs, ignoring case, in the unit's own frozen source, its file path or its IDs. One suspect explanation is not acted on. When at least three explanations of one answer, and at least 30% of them, are suspect, the answer is refused as a whole and asked again: this is the pattern of explanations attached to the wrong symbol numbers. If the last allowed answer is still like that, CBE keeps it and marks each suspect unit: `ungrounded` on the unit in `catalog.json`, a `check:` line in `cbe query` and on the node page, a task flag, and `ungrounded_count` in `summary.json`. A run without such units has none of these.

What it catches and what it does not, from a replay on the seven example runs (no model call): in the one run where a model had attached explanations to the wrong symbols (27 wrong out of 46), 22 of the 37 explanations of that answer were suspect (21 of the 27 wrong ones), so the answer would have been refused; in the 56 answers of the other six runs at most 14% were suspect, so none would have been refused. Taken one at a time, 53 of the 1,790 explanations in those six runs (3.0%) were suspect, which is why a single suspect is not acted on. The check does not catch an explanation that uses the right names and describes the behaviour wrongly, and it has been measured on one wrong answer only.

**Common mistakes.** Each of these exits 2 and prints the error on stderr (the message text is shortened here):

| You wrote | Error | Write instead |
|---|---|---|
| `cbe query --run-dir RUN --id cJSON_Pars` | `unknown unit, symbol or file: cJSON_Pars; first use cbe find --run-dir RUN --term cJSON_Pars` | Run `find` first and copy the ID from its second column. |
| `cbe query --run-dir RUN --id parse` (a name several symbols share) | `parse matches 2 IDs; query one of them:` and the IDs, one per line | Query one of the listed IDs. |
| `cbe find --run-dir runs/cjson/run --term x` | `cbe find: error: argument --run-dir: expected an absolute path, got runs/cjson/run` | Give the absolute run directory. |

`find` and `query` also accept the search term or the ID as a bare argument; the flag forms `--term` and `--id` stay the stable interface.

In the curl evaluation, at an earlier version that required the flag forms, all 5 failed `find`/`query` commands of the answering agent returned 2: 4 passed the search term or unit ID as a positional argument, and 1 named an unknown unit ([Q-A: curl](../evaluation/README.md#q-a-curl-e5)).

`cbe source --run-dir RUN --id ID [--context N]` prints the frozen source behind an ID. It checks each file's SHA-256 against the snapshot before it prints any line:

```text
$ cbe source --run-dir /absolute/path/to/run --id 'cJSON.c::function::cJSON_Parse::33515'
# cJSON.c:L1227-L1230
1227: CJSON_PUBLIC(cJSON *) cJSON_Parse(const char *value)
1228: {
1229:     return cJSON_ParseWithOpts(value, 0, 0);
1230: }
```

## Command details

| Host command | Purpose |
|---|---|
| `cbe host update-graph --run-dir RUN --graph GRAPH` | Replace the frozen graph of a completed run without rerunning model tasks. |

Use `update-graph` to add or remove dataflow after a run: build the graph again with `cbe graph build --with-dataflow` (the whole build took 93 and 103 seconds on two of the example repositories, against 86 and 52 without dataflow), then run it. The explanations are not written again, and they do not need to be: the prompts never used dataflow. The run must be complete, must have been
planned with a graph, and must have an intact frozen context. The new graph must pass the usual
source and quality checks. Its `source_manifest` must match. After removing dataflow nodes and
edges, both graphs must have exactly the same nodes and edges in the same order. Otherwise the
command exits 2 without changing the run; start a new plan for that graph. An identical graph
prints `nothing to update`. A successful update refreshes the context fingerprints and renders
the documents again.

`cbe find --run-dir "$RUN" LIMIT` accepts the same search term as `--term LIMIT`.
`cbe query --run-dir "$RUN" "$ID"` accepts the same ID as `--id "$ID"`.
The flag forms and JSON output remain compatible. If both forms are supplied,
their values must match; omitting both is an error. An unknown query ID suggests
using `cbe find` first.

`summary.json` has a `basis` object, also printed under `Generation basis` in `RUN.md`.
It records the CBE version and the distinct model names found in task usage or API call records.
The model list is empty when no actual model was recorded. `source` contains the file count and
the SHA-256 of the canonical JSON list of ordered `path` and `digest` records from the plan.
`graph` is null without a graph. Otherwise it contains the frozen graph digest, backend record,
edge counts by kind, whether the graph was replaced, and the latest replacement time.

For script generation, `summary.json` records `wall_seconds` as the cumulative
running time of all process segments, excluding idle time between segments.
Each plan and resume appends a record to `runtime_environments` in
`host/state.json`: UTC time, Python version, platform, CBE version, and installed
versions of the runtime dependencies declared by the package, including extras.
An optional dependency that is not installed has a null version.
`cbe --version` prints `cbe <version>`.

A resumed detail answer can introduce a grouped unit before the responsibility
tree has been rebuilt. Flow steps for these units link to the catalog and say
`not assigned to a node`; resume the tree/system tasks to complete navigation.
Until a new system answer is accepted, rendering keeps the last accepted overview,
dependency descriptions and key flows. RUN.md notes that this overview predates
some completed modules and will update when the resumed system task completes.
Without an accepted system answer, rendering uses a mechanical overview.
Joern nodes with filenames outside the source manifest retain their identity
and relations but have an unknown location, with `unknown_node_location`
diagnostics. A graph whose capabilities all failed is reported as failed unless
a component explicitly records successful completion.

## Named declaration coverage

Newly built source contexts index these declarations as `module_region` candidates, so `cbe find` can locate their names, `cbe query` can inspect their ids and ranges, and `cbe source` can read their frozen source:

| Language | Additional named declarations |
|---|---|
| C / C++ | Object and function macros, including continuations and conditional branches; file and namespace variables (`static`, `extern`, globals, `constexpr`); C/C++ `typedef` and C++ `using` aliases |
| Go | Every name in grouped `type` declarations; package `var` and `const`, including groups |
| JavaScript / TypeScript / TSX | Ordinary top-level `const`, `let` and `var`, including exports |
| Java | Class fields and interface constants |
| Ruby | Constant assignments at file, module and class scope |

Adjacent value declarations of the same category and scope share one region when only whitespace or comments separate them. The region's name, qualified name and canonical id use the first declared name and its anchor; the other names remain searchable through the existing signature metadata, without repeating a name list in the prompt inventory or published query signature. Querying the shared id returns the run's source. A declaration with several variable names also exposes every name. JavaScript and TypeScript destructuring exposes bound names, excluding property keys and default-value expressions. Function prototypes and macro-prefixed functions do not become variable regions; function pointer variables remain eligible. An ordinary declaration enclosing an existing function, type or other declaration yields to that unit and the residual source. Type aliases are not coalesced with adjacent declarations. A typedef enclosing a struct, union or enum definition adds its alias names to that existing type unit's searchable signature instead of creating a separate region. The type keeps its original id and full byte range, including for `typedef struct { int x; } Point;`. Typedefs without a definition, such as `typedef unsigned long Size;` or `typedef struct Foo Foo;`, remain separate named regions.

Macros are indexed as written, including definitions inside functions: CBE does not expand them, evaluate conditions or synthesize calls. Ordinary C/C++ declarations require a confirmed file or namespace scope; error nodes, function bodies, parameter lists and type bodies exclude them. For ambiguous C++ `.h` files parsed as C, a C++ tree confirms declaration scope when the C tree has syntax errors; declarations whose scope cannot be confirmed remain residual source. When C++ header parsing has syntax errors, individual declarations can be assigned the wrong scope, including with `--header-language cpp`. Function-local variables (including local `static` variables), C/C++ function prototypes, C/C++ struct fields and enum members do not become additional named regions. Python assignment behavior is unchanged. A mixed JavaScript declaration such as `export const value=1, helper=()=>2` keeps the existing function unit's id and range; `value` is searchable through that unit's signature rather than receiving a separate region. New child regions can change a containing namespace/class/module's exclusive source ranges and segment ids; existing declaration canonical ids and full spans remain stable when rebuilding the same source.

## Worked example: cJSON, step by step

This is the step-by-step run that the README's earlier Quickstart documented. It was written and run at an earlier version of CBE (before the program-built module tree), on four files of [cJSON](https://github.com/DaveGamble/cJSON) at commit `6d9f244`. Steps 1–3 run locally and make no model call. Step 5 needs a model. The outputs shown are from that earlier run; the graph counts and the generation figures in particular differ at the current version (see the README, "How well does it work").

1. Install CBE and check the grammars:

   ```sh
   uv tool install --python 3.13 /path/to/codebase-explorer   # a checkout; or `uv tool install codebase-explorer` from PyPI
   cbe --version    # prints: cbe 2.2.0
   cbe languages    # c, cpp, python, javascript, typescript, tsx, java and go show "available": true
   ```

2. Get the input:

   ```sh
   git clone https://github.com/DaveGamble/cJSON.git "$HOME/cbe-demo/cJSON"
   mkdir -p "$HOME/cbe-demo/cjson"
   git -C "$HOME/cbe-demo/cJSON" archive 6d9f2443ab071f86e5d9b43025a40929ec41c46c \
     cJSON.c cJSON.h cJSON_Utils.c cJSON_Utils.h | tar -x -C "$HOME/cbe-demo/cjson"
   ```

3. Check how CBE reads the source. This takes under a second here:

   ```sh
   cbe context build "$HOME/cbe-demo/cjson" --output "$HOME/cbe-demo/context.json"
   ```

   ```text
   {
     "output": "<HOME>/cbe-demo/context.json",
     "schema": "cbe-context/1",
     "files": 4,
     "chunks": 326,
     "diagnostics": [
       {
         "path": "cJSON.c",
         "code": "syntax_error",
         "message": "tree contains an ERROR node near line 1; chunk coverage is preserved"
       },
       {
         "path": "cJSON.h",
         "code": "ambiguous_language",
         "message": "'.h' is valid in c, cpp; parsed with c. Register a mapping or use a unique extension to remove the ambiguity."
       },
       ...
     ]
   }
   ```

   The full output lists five diagnostics: `syntax_error` for `cJSON.c`, `cJSON.h` and `cJSON_Utils.h`, and `ambiguous_language` for both headers. The `syntax_error` entries come from cJSON's macros; see [Known limitations](../README.md#known-limitations). Generation does not need this file, because `generate` and `host plan` freeze their own copy. Use it to see the file list, chunk count and diagnostics before you spend model calls.

4. Optional: build a code graph with Joern ([Optional graph analyzers](#optional-graph-analyzers) says how to install it; `cbe graph setup` downloads Joern and a Java runtime once, about 1.9 GB). The graph in this run was built with dataflow, hence `--with-dataflow`. The build took 28 seconds here and makes no model call:

   ```sh
   cbe graph setup
   cbe graph build "$HOME/cbe-demo/cjson" --output "$HOME/cbe-demo/graph.json" --with-dataflow
   cbe graph capabilities --graph "$HOME/cbe-demo/graph.json"
   ```

   The earlier run's graph had 21,106 nodes and 33,164 edges. Its `capabilities` reported C imports `resolved`, calls `partial`, and CFG and dataflow `resolved`. The per-status call counts of that run (350 resolved, 307 unresolved, 84 external) are no longer valid: the 307 "unresolved" were macros, which are no longer counted as calls.

5. Generate the documents. This needs one of the following:

   - **A host agent with subagents (Claude Code or Codex).** The subagents run on your own subscription. Run `cbe-install install --host claude-code` (or `--host codex`) in `$HOME/cbe-demo/cjson`, start the agent there, and ask: "Use the codebase-explorer skill to generate documentation for this repository." The agent plans the run first; for these four files `cbe host plan` prints `"modules": 4` and `"tasks": 8`, and each review finding adds one repair task later. See [Generate through a host agent](running.md#generate-through-a-host-agent).
   - **An OpenAI-compatible endpoint, an API key and a model ID.** `cbe generate` talks only to such an endpoint.

     ```sh
     cbe generate "$HOME/cbe-demo/cjson" \
       --base-url https://your-endpoint.example/v1 --api-key-env CBE_API_KEY \
       --model your-model-id --graph "$HOME/cbe-demo/graph.json" \
       --run-dir "$HOME/cbe-demo/run" --review sample
     ```

     In the evaluation, at the earlier version, this input with `zai/glm-5.3-flash` took 13 gateway requests and 0.084977 USD by the gateway's own price table, and the first pass completed. [What a run costs](running.md#what-a-run-costs-the-earlier-table) lists larger repositories.

6. Read the result. Open `$HOME/cbe-demo/run/docs/INDEX.md`, then look up a symbol:

   ```sh
   cbe find --run-dir "$HOME/cbe-demo/run" --term cJSON_Parse --limit 3
   cbe query --run-dir "$HOME/cbe-demo/run" --id 'cJSON.c::function::cJSON_Parse::33515'
   ```

   [Find and query](#find-and-query) shows the output from the evaluation's cJSON run. Inventory IDs such as `cJSON.c::function::cJSON_Parse::33515` come from the source, so the same four files give the same IDs. Summaries, explanations and `grp:` group IDs come from the model, so yours will differ.

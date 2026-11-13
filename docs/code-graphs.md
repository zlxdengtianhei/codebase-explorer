# Code graphs: what they are and what CBE uses

[简体中文](code-graphs.zh-CN.md)

**In short.**

- A code graph stores facts about code as nodes and edges. Each kind of graph answers one kind of question: which file depends on which, which function calls which, in what order statements run, where a value flows.
- CBE can build four kinds: import, call, control flow (CFG) and, only on request, data flow. All are optional; without a graph CBE still writes the map.
- Joern makes the call, CFG and data-flow edges. Grimp (Python) and dependency-cruiser (JavaScript, TypeScript) resolve imports. Tree-sitter makes no edges: it cuts files into chunks and finds the symbols.
- CBE then groups code units into modules with Louvain community detection. A model only names the modules.
- CBE does not use SCIP or language-server indexes, CodeQL, or a ranked symbol map. Section 3 gives the reasons where they were recorded.
- Call edges are the weakest part. "Resolved" means the analyzer linked the call to one target; it does not prove the link is right. Section 4 lists the errors we know of.

## 1. Graph kinds

| Kind | Question it answers | In CBE |
|---|---|---|
| Import | Which file or package depends on which? | Grimp for Python, dependency-cruiser for JavaScript and TypeScript; for other languages Joern records import declarations only, which do not resolve to a file |
| Call | Which function calls which? | Joern, when it ran |
| Control flow (CFG) | In what order can the statements of one function run? | Joern, when it ran |
| Data flow | Which definition of a variable reaches which use? | Joern, only with `cbe graph build --with-dataflow` |

CBE gives each call and import edge a status: `resolved`, `ambiguous`, `unresolved` or `external`. A CFG is not a runtime trace. See [Generate and query code graphs](reference.md#generate-and-query-code-graphs).

## 2. How others build code graphs

**Ranked symbol map (aider).** Tree-sitter finds where names are defined and where they are used. Files become graph nodes, and a ranking picks the most important definitions to fit a token budget (`--map-tokens`, 1k tokens by default) ([docs](https://aider.chat/docs/repomap.html), [design post](https://aider.chat/2023/10/22/repomap.html)). The ranking is PageRank in [aider's code](https://github.com/Aider-AI/aider/blob/main/aider/repomap.py). The aim is a small prompt, not a complete graph.

**Language servers, LSIF and SCIP.** A language server answers "go to definition" and "find references" precisely, per language. [LSIF](https://microsoft.github.io/language-server-protocol/overviews/lsif/overview/) stores those answers so that tools can use them without a running server. [SCIP](https://github.com/sourcegraph/scip) is Sourcegraph's newer index format for the same purpose ([announcement](https://sourcegraph.com/blog/announcing-scip)). An indexer runs per language, ahead of time, usually on a project that builds.

**Code property graph (Joern).** The [2014 paper](https://mlsec.tu-berlin.de/docs/2014-ieeesp.pdf) merges syntax trees, control flow graphs and program dependence graphs into one graph. [Joern](https://docs.joern.io/) builds such graphs for many languages and lets you query them; the [CPG specification](https://cpg.joern.io/) defines its layers, a call graph among them.

**Query-based analysis (CodeQL).** [CodeQL](https://codeql.github.com/docs/codeql-overview/about-codeql/) extracts a relational database from the source (for compiled languages, by watching the build), and you query it in QL.

**Community detection (Louvain, Leiden).** These methods split a graph into dense groups. [Louvain](https://networkx.org/documentation/stable/reference/algorithms/generated/networkx.algorithms.community.louvain.louvain_communities.html) is a modularity heuristic. The [Leiden paper](https://arxiv.org/abs/1810.08473) shows that Louvain can return badly connected groups, even disconnected ones, and that Leiden always returns connected groups. [GraphRAG](https://microsoft.github.io/graphrag/index/default_dataflow/) builds a hierarchy of groups with Leiden and has a model summarize each one.

## 3. What CBE uses, and what it does not

- **Tree-sitter** cuts every file at syntax boundaries and finds the symbols. Every byte lands in a chunk.
- **Joern 4.0.654** gives calls, CFG and, on request, data flow. With Java it is about 1.9 GB; `cbe graph setup` installs Joern, and a Java runtime when no Java 21 or newer is found, into your user cache ([Code graph](../README.md#code-graph)). CBE runs analyzers and does not write its own (`src/cbe/graph.py`: "It never re-implements a language analyzer").
- **Grimp** gives the Python import graph (the `graphs` extra). **dependency-cruiser** gives the JavaScript and TypeScript import graph (needs Node.js).
- **Louvain** (networkx, fixed seed) groups the units into modules. Edge weights come from calls and imports, shared files and directories, and similar wording. An edge into a unit is divided by `ln(e + in_degree)`, so a helper that everybody calls does not pull everybody into one module (`src/cbe/skeleton.py`). The grouping also uses the relations the explanation model reported; the dependency view labels a module pair found only that way model-inferred.

| Route | Used? | Why not |
|---|---|---|
| SCIP, LSIF, language servers | No | Design note (not measured by CBE): each language needs its own preconditions, such as a project that builds, `compile_commands.json` or a given Node version, so on an arbitrary repository the indexer often does not run. More precise where it runs. |
| Own name resolution on tree-sitter | No (replaced by Joern in October 2026) | Design note: one set of rules per language to maintain; the accuracy figures other tools publish are self-reported. |
| CodeQL | No | Not recorded. |
| Ranked symbol map | No | Different goal: aider cuts a map to a token budget; CBE builds a module tree that covers every unit. |
| Leiden | No | Not recorded. |

## 4. Languages

Status as `cbe languages` reports it (`call_graph`), with the conditions from the [README](../README.md#code-graph) and the errors later checks found. Parsing and chunking work for every language here, whatever its call-graph status (Ruby, Rust, PHP and C# need the `languages` extra; Kotlin and Swift need `languages-community`).

| Language | Status | Known to be wrong or weak |
|---|---|---|
| Python | works | The default `uv tool install codebase-explorer` has no Grimp, so the import graph is missing and the only hint is the last line of a long diagnostic output; install the `graphs` extra. On markupsafe (a walkthrough on 2026-11-13, not yet in the repository's evaluation), 31 `self.__class__(...)` calls were linked to an unrelated `Proxy.__class__` in a test file and marked resolved. Calls in comprehensions are a known weak spot. |
| C, C++ | works | No preprocessor: a macro can be taken for a function, and a header with many macros is cut coarsely. |
| JavaScript, TypeScript | works | Dynamic imports, CommonJS and external targets can stay partial. |
| Java | works | Project types and dependencies affect resolution. |
| Go | works | Calls across packages can stay unresolved or external. |
| Ruby | works | Dynamic dispatch can bind a call to a same-named method of another class; CBE marks many as ambiguous and some wrong bindings remain. Receiver types are weak. |
| Rust, PHP | needs_tool | Rust needs `cargo` and a Cargo layout. PHP needs `php` 7 or later. |
| C# | partial | A call to an overloaded method resolves only to the set of overloads. On GuardClauses, 993 of 2,322 calls are marked unresolved; about 955 of them are calls to methods outside the repository, `nameof` or constructor calls, and 14 are calls inside the repository that CBE cannot link. |
| Kotlin | known_failure | Joern 4.0.654 stopped on a 146-file repository; two-file examples work. |
| Swift, TSX | untested | |

`cbe graph setup` and the whole flow are tested on Linux x86_64, not yet on macOS. Read each graph's `capabilities` and `diagnostics`, not only its size ([reference](reference.md#generate-and-query-code-graphs)). Other limits: [Known limitations](../README.md#known-limitations).

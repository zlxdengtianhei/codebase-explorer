# Changelog

## 2.2.0.dev0 (unreleased)

- Accept positional search terms and query IDs alongside `--term`/`--id`, with
  conflict checks and examples for missing arguments; unknown IDs suggest `find`.
  Version and usage output identify the command as `cbe`.
- Preserve the latest physical call's result label when resumed attempts repeat,
  accumulate script wall time across active segments, and append interpreter,
  platform and declared dependency versions on every plan and resume.
- Report external graphs with only failed capabilities as failed. Joern nodes
  whose filenames are outside the source manifest keep an unknown location and
  a diagnostic instead of a false file anchor.
- Resume newly grouped units without crashing when the previous tree does not
  own them yet; retain catalog links while navigation is pending. Preserve the
  last accepted overview, dependency descriptions and key flows while the system
  task is queued again, with an INDEX note that the overview will update.
  Unhandled missing keys now print an English internal-error message.

- Add a shared Tree-sitter source context with declaration metadata, original
  byte ranges, hashes, diagnostics, and optional analyzed graph evidence.
- Integrate structured detail, unique primary ownership in a semantic module
  tree, source anchors, and catalogue queries into the existing host/script
  generation state machine.
- Add `graph build/query/capabilities`, `context build/query`, and `languages`
  commands. External graph analyzers report capabilities and unresolved scope
  independently for each language and graph kind.
- Add an OpenAI-compatible API driver with configurable endpoint, model, and
  credential environment variable, using the same tasks and recovery path.
- Report operational completion, deterministic structural checks, and semantic
  review separately. Normalize API cache usage without counting it twice.
- Preserve exact source bytes across syntax chunks, support optional additional
  grammars, and keep known-empty files in the index without model calls.
- Validate frozen context, source and recognized configuration identities when
  context and generation consume graph evidence. Expose graph expansion from
  the same frozen context, using the installed interpreter without requiring PATH.
- Preserve bounded, redacted failed API responses and available finish/usage
  metadata. Repairs rebuild ownership and may retain their own existing group IDs.
- Keep unknown model prices unknown even when token counts are exact; accept
  explicit finite, nonnegative rates without silently substituting comparison prices.
- Resolve grouped inventory IDs and synthetic `grp:` units in `find`/`query`,
  including existing semantic catalogues. Verify primary page anchors and expose
  index-only reasons. Do not label a graph with no completed backend as successfully empty.
- The script driver embeds CRLF source files byte for byte; it no longer stops
  with `SourceNotEmbedded` on them.
- Catalogue file languages are the ones frozen in the source context: `.tsx` is
  `tsx`, Ruby, PHP, C#, Kotlin and Swift files are no longer `unknown`, and a
  plan made with `--header-language cpp` lists headers as `cpp`.
- One source-discovery rule for planning, context and graphs: `cbe generate` and
  `cbe host plan` now also skip `.hg`, `.svn`, `.mypy_cache`, `.pytest_cache` and
  `.tox`. A source checkout without package metadata reports version `source`.
- A frozen graph that no longer matches the planned source stops a run with
  "frozen graph does not match the planned source: …"; `context build` and the
  run use the same check.
- Code that imports CBE modules directly needs new import paths. The package is
  organized by responsibility: `batching`, `symbols`, `checks`,
  `projection`, `prompts`, `docs`, `records`, `usage`, `model_settings`,
  `aggregation` and `principles` sit beside `host_run` (run state) and
  `generate` (script driver). The `ir`, `parser`, `inventory`, `semantic`,
  `syntax_facts`, `callable_contracts` and `adapters` modules are removed.
- `graph build --joern-heap SIZE` sets the Joern JVM maximum heap. A backend
  failure keeps its cause in the graph diagnostics and prints one line to stderr.
- `graph build --max-methods` limits only CFG export and is unlimited by
  default. Omitted methods are counted, and the CFG capability is `partial`
  when any are omitted. Truncated dataflow is `partial` with its omitted edge
  count.
- Graph output includes a `quality` audit: edge counts by status, dangling
  edges, nodes outside the manifest or with missing files, and incomplete
  capabilities. `graph capabilities --repo` recomputes it against the current
  files, and INDEX shows it under "Graph coverage".
- Import and call targets are `resolved` only with repository evidence. Joern
  include declarations resolve per language to repository files; an angle
  include that matches several files stays `unresolved` with its candidates;
  guessed Python call targets stay `unresolved`; Grimp modules map to existing
  files.
- Detail tasks receive a bounded graph excerpt for their batch (outgoing and
  incoming calls, ambiguous, external and unresolved targets, package outline,
  CFG summary) with omitted counts. Host tasks also get the batch's complete
  graph evidence as a file.
- Detail prompts size each explanation by the unit's source size (as a
  reference, not a ceiling), ask for every behavior-changing branch and failure
  path, and keep members that have their own units out of the class explanation.
- The responsibility tree is built bottom-up from accepted detail units: their
  summaries, source locations and counted unit edges. Large runs split into
  program-chosen `tree_region-*` tasks and a `tree` merge (defaults 300 units
  and 64,000 input tokens; `CBE_TREE_MAX_UNITS`, `CBE_TREE_MAX_TOKENS`). The
  tree task waits until reviews and repairs settle; detail tasks start beside
  the naming task. Model-written relations are a separate `kind=relation`,
  `provenance=model_inferred` category. Advisory P1–P7 checks appear in
  `summary.json` and INDEX.
- INDEX publishes the system overview, maintenance navigation, a dependency view
  and key flows. Dependency pairs are labelled graph-confirmed, model-inferred
  or graph-only, each with its own Mermaid line style; containment rows stay
  separate and out of Mermaid. Key flows link unit IDs; when the model gives
  none, INDEX lists five program candidates and says that the model did not
  select them.
- Program-written text in the generated documents is English: labels, the
  INDEX introduction and notes, dependency source labels and generation notes.
  Model prose keeps its own language.
- New `cbe source --run-dir RUN --id ID [--context N]` prints numbered frozen
  source after checking each file's SHA-256.
- `cbe find` prints one line per match (name, ID, kind, location, short
  summary, matched fields), exact name or ID matches first; `--json` prints the
  same rows as objects. A unit whose ID CBE corrected is marked.
- `cbe query` prints compact text by default: the explanation once, one line
  per relation or edge, ranges as `path:Lstart-Lend`. `--json` returns the full
  record, including disposition, owning unit and page anchor. Tree node IDs
  are accepted. `catalog.json` stores symbol-level call and import edges once
  and only counts CFG and dataflow edges; `query --edges all` (or a list of
  kinds) expands them from the frozen graph.
- INDEX and every node page give ready-to-run `find`, `query` and `source`
  commands.
- `summary.json` splits the published Markdown tokens into seven additive parts
  and reports model-written unit text ÷ source and published Markdown ÷ source
  (o200k). The frozen graph is reported in bytes.
- API runs with the exact model `zai/glm-5.3-flash` use tuned defaults: 1,800 s
  per call, 49,152 output tokens, low reasoning effort, JSON mode and
  8,000/10,000-token reading batches. Other models keep the previous defaults.
  `--config` overrides them, `--timeout` overrides the config, and
  `generate --help` prints the table.
- API config is validated before planning: malformed JSON, unknown keys and
  invalid values exit 2. `price_per_million` prices a run. A response that ends
  at the output limit fails with `output_limit` and is never accepted by
  normalization. The raw API record keeps the provider's `actual_model`.
- Module and repair detail tasks allow 3 answers; other tasks allow 2. After the
  last invalid detail answer, CBE tries earlier answers from newest to oldest
  and accepts the first that passes the strict checks, flagged
  `answer_fallback`; if none passes, the task fails and the run stays partial
  for resume.
- A detail unit ID that differs from a batch inventory ID only in a suffix or
  offset is corrected when the match is unique; the page, `query`, `find`,
  STATUS and `summary.json` show the correction (`id_corrected`). Unit IDs that
  match nothing are rejected. One missing or invalid disposition (two in a
  batch of 40 or more symbols) is filled as `index_only` (`index_only_filled`);
  an answer that needs more is rejected.
- Model prose shaped like a Markdown link renders as literal text; code spans
  stay verbatim.
- `cbe host verify` exits 3 when a check fails and marks the run `partial`;
  `cbe generate` exits 3 for a partial run. Status output names each failed
  task and the resume command for the driver that ran it.
- Before model work is planned, each file's chunks must cover it without gaps
  and reassemble to its SHA-256; a file that fails becomes one verified
  whole-file region (`source_reassembly_fallback`). A whole-file fallback for a
  missing grammar is reported per file as `context_fallback` with its cause, in
  diagnostics, STATUS and summaries. A non-UTF-8 file gets `decode_error` and
  no chunks while the rest of the build continues. TypeScript declarations
  inside nested wrappers no longer get overlapping chunks.
- `cbe-install --host claude-code` also installs the `cbe-writer` subagent
  (Read and Write tools only) in `.claude/agents/`; `doctor` and `uninstall`
  cover it, and it never overwrites a file it did not install.
- The skill follows how Claude Code runs subagents: example commands avoid
  quoted shell variables, so an allow-listed `cbe` runs without prompts;
  subagents only read and write files; the host submits each task on its
  `DONE` hand-back without usage, and `cbe host import-usage` adds exact usage
  later. `cbe host cost --model` prices only the rows that are still estimates.

## 2.1.1

- **2.1.0 withdrawn.** The script driver (`cbe generate`) rebuilt modules from
  run state that keeps digests, not text, so every prompt named the files but
  carried empty bodies. The model documented file names, and the run still
  reported "complete".
- 2.1.1 inlines the source: prompt building reads each file back from disk and
  accepts it only when its digest matches the plan.
- Two hard delivery checks were added so the failure is caught before money is
  spent and per call, not only at the end of a run:
  - **Pre-flight** (before each script-driver model call): every non-empty
    source file the task's prompt must embed is present in the prompt with its
    full body, or the run stops with `SourceNotEmbedded`, naming the file,
    before the model is called. progress.log and STATUS.md record it. Host-mode
    tasks (`cbe host`) list paths on purpose; their dispatch refuses any listed
    path that is missing, unreadable, or changed since the plan.
  - **Per call** (after each script-driver call): the model-reported input
    tokens (input + cache-read) must reach 50% of the source tokens embedded in
    that prompt, or the answer is rejected with `source_not_delivered` and is
    never published, even by the normalize-and-salvage path; the module ends
    failed or partial. Calls whose host reports no usage at all are recorded as
    `usage_unknown` instead of failing, and STATUS.md says the per-call check
    could not be verified.
  - The run-level backstop stays: total reported input under 50% of all source
    sent marks the run partial (`source_not_delivered`).
- Deterministic concrete-facts layer: defaults, constants, option tables,
  templates, and raise statements extracted mechanically at render time and
  attached to pages and the catalogue.
- The concrete facts moved off the module pages into the index: pages no
  longer render the "Constants and defaults (mechanical)" section (and the
  page-cap logic is gone), while `catalog.json` keeps every fact on its
  symbol and file entries and `cbe find` / `cbe query` still retrieve them.
  INDEX.md's "Maintenance navigation" says so in one line.

# Changelog

## 2.2.0.dev0 (unreleased)

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
- Remove unused legacy packet, literal, ledger and rendering helpers; retain
  source guards, current callable contracts and offline token counting. This is
  separate from the earlier 2.0 → 2.1 source reduction.
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

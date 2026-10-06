# Changelog

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

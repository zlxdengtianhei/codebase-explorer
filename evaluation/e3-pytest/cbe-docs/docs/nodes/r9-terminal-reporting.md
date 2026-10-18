# Terminal Reporting

**Capability.** All human-facing terminal output of a pytest session: header, per-test progress lines, collection reporting and end-of-session summaries, owned by the TerminalReporter plugin.

Use this subtree to see how report objects become screen output: core lifecycle, live progress rendering, summary sections and option handling are separated. It consumes reports from the runner and is written to by the live logging handler.

**Children.**

- [Reporter Lifecycle and Collection Output](r9-terminal-reporter-core.md) `r9-terminal-reporter-core` · 14 unit(s)
- [Per-Test Progress Output](r9-terminal-progress.md) `r9-terminal-progress` · 14 unit(s)
- [Summary Sections](r9-terminal-summaries.md) `r9-terminal-summaries` · 19 unit(s)
- [Terminal Options and Status Hook](r9-terminal-config.md) `r9-terminal-config` · 4 unit(s)

Parent: [pytest Core](r9-pytest-core.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

# Terminal Reporting Suite

**Capability.** Verifies TerminalReporter output across verbosity levels, progress/count/times/classic styles, collect-only rendering, summary sections, colors and code highlighting, plus unit tests of reporter internals; it is the executable spec of what pytest prints.

Choose the group by output aspect: progress styles, fine-grained verbosity, collect-only, summary sections, or reporter internals/formatting helpers. Most tests are Pytester runs with fnmatch assertions.

**Children.**

- [Progress and Output Styles](r6-terminal-progress.md) `r6-terminal-progress` · 45 unit(s)
- [Collect-Only Output](r6-terminal-collectonly.md) `r6-terminal-collectonly` · 12 unit(s)
- [Summary Sections and Reporting](r6-terminal-report-sections.md) `r6-terminal-report-sections` · 23 unit(s)
- [Terminal End-to-End Reporting](r6-terminal-functional.md) `r6-terminal-functional` · 27 unit(s)
- [Summary, Warnings and Misc Reporting](r6-terminal-summary-basics.md) `r6-terminal-summary-basics` · 18 unit(s)
- [Color and Code Highlighting](r6-terminal-color-highlight.md) `r6-terminal-color-highlight` · 9 unit(s)
- [TerminalReporter Unit Tests](r6-terminal-reporter-internals.md) `r6-terminal-reporter-internals` · 28 unit(s)
- [Formatting Helpers and Fixtures](r6-terminal-formatting-helpers.md) `r6-terminal-formatting-helpers` · 13 unit(s)

Parent: [Regression Suites](r6-test-suites.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

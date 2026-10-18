# Terminal Output & Pretty-Printing

**Capability.** Presentation-layer formatting: writing colored, separated, highlighted text to a terminal and recursively pretty-printing Python objects into readable representations.

Use this subtree when tracing how pytest renders text, source snippets, or object reprs. Consumers such as reports and --markers output depend on the terminal writer; pprint is self-contained but shares the stream-oriented design.

**Children.**

- [Safe Pretty-Printer](r3-pprint.md) `r3-pprint` · 6 unit(s)
- [Terminal Writer](r3-terminal-writer.md) `r3-terminal-writer` · 10 unit(s)

Parent: [Pytest Framework Codebase](r3-pytest.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

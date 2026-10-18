# CLI, config and package integrity tests

**Capability.** Verifies the command-line surface (help/version/ini rendering, config-file discovery) and package-level integrity (identical entry points, warning-free imports of all internal modules, assertion-diff wording, and the python -m pytest entry).

Split into cli-help-config tests, package/entry-point integrity, and assertion-diff wording; each is a small, distinct contract.

**Children.**

- [Help, version and config discovery tests](r4-cli-help-config-tests.md) `r4-cli-help-config-tests` · 4 unit(s)
- [Package and entry-point integrity tests](r4-package-entry-tests.md) `r4-package-entry-tests` · 5 unit(s)
- [Assertion diff tests](r4-assertion-diff-tests.md) `r4-assertion-diff-tests` · 2 unit(s)

Parent: [Test suites](r4-test-suites.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

# Example Scripts and Packaging Harness

**Capability.** Standalone example projects under testing/example_scripts plus the frozen-binary harness: fixture scoping/recursion demos, dataclass assertion demos, unittest interop, collection payload packages, and the tox post-build runner. They serve as inputs the suites copy or run to pin observable behavior.

Treat these as data fixtures for the test suites rather than as tests of the surrounding suite: warning-grouping and doctest suites copy them byte-for-byte, and the freeze harness drives the packaged executable.

**Children.**

- [Fixture Behavior Examples](r7-fixture-examples.md) `r7-fixture-examples` · 8 unit(s)
- [Collection and Assertion Payload Examples](r7-misc-examples.md) `r7-misc-examples` · 9 unit(s)
- [Frozen Binary Harness](r7-freeze-harness.md) `r7-freeze-harness` · 1 unit(s)

Parent: [pytest Codebase](r7-pytest-codebase.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

# Test Corpus

**Capability.** pytest's own test material: the fixture semantics suite, example scripts exercised end-to-end, output-helper tests, and frozen-executable tooling. These pin observable behavior of the framework rather than implement it.

Use these subtrees as executable specifications: fixture classes for fixture semantics, example scripts for cross-feature integration, io tests for repr contracts, and freeze scripts for packaging.

**Children.**

- [Fixture Semantics Suite](r2-fixture-tests.md) `r2-fixture-tests` · 0 unit(s)
- [Fixture Example Scripts](r2-fixture-example-scripts.md) `r2-fixture-example-scripts` · 1 unit(s)
- [Collection & Performance Examples](r2-collection-example-scripts.md) `r2-collection-example-scripts` · 0 unit(s)
- [Assertion, Warning & Unittest Examples](r2-behavior-example-scripts.md) `r2-behavior-example-scripts` · 0 unit(s)
- [Output Helper Tests](r2-io-tests.md) `r2-io-tests` · 14 unit(s)
- [Frozen Executable Tooling](r2-freeze-tooling.md) `r2-freeze-tooling` · 0 unit(s)

Parent: [Pytest Codebase](r2-pytest-root.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

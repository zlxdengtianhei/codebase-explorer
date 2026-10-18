# Assertion, Warning & Unittest Examples

**Capability.** Standalone scripts pinning cross-feature behavior: dataclass comparison output under assertion rewriting, warning-message grouping volume, and unittest asyncio integration/misuse.

Each script is a minimal reproduction; the dataclass ones exercise the _compare_eq_cls path, the unittest ones IsolatedAsyncioTestCase versus plain async methods.

**Depends on.**

- [Type-Specialized Comparisons](r2-comparison-strategies.md) · model-inferred · 0 edge(s)

Parent: [Test Corpus](r2-test-suite.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

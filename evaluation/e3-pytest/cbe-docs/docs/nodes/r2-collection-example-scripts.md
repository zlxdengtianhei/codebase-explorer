# Collection & Performance Examples

**Capability.** Example scripts probing collection rules: pytest-prefix class names in conftests, pytest_ignore_collect recursion scenarios, and a folder-tree generator for collection-performance measurement.

Use these to check name-based collection boundaries and to generate load for collect-stats benchmarks.

**Depends on.**

- [Plugin & Conftest Manager](r2-config-plugin-manager.md) · model-inferred · 0 edge(s)

Parent: [Test Corpus](r2-test-suite.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

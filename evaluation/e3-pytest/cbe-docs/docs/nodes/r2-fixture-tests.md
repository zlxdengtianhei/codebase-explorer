# Fixture Semantics Suite

**Capability.** Comprehensive tests of pytest fixture behavior: discovery and autouse ordering, parametrization/scope/lifecycle, request APIs, error surfaces, --fixtures output, and fixture-manager parsefactories, all against pytester-driven runs.

Read by topic: TestFixtureMarker for parametrize/scope, TestRequest* for request APIs, TestAutouse* for discovery and ordering, TestErrors for failure messages, TestScopeOrdering for fixturename ordering guarantees.

**Depends on.**

- [Plugin & Conftest Manager](r2-config-plugin-manager.md) · model-inferred · 0 edge(s)
- [Fixture Example Scripts](r2-fixture-example-scripts.md) · model-inferred · 0 edge(s)

Parent: [Test Corpus](r2-test-suite.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

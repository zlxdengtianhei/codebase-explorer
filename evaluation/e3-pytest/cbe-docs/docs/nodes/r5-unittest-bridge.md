# unittest integration bridge

**Capability.** Embeds unittest.TestCase suites into pytest: collecting TestCase classes as pytest collectors, running test methods on fresh instances, translating unittest result callbacks into pytest reports, wrapping setUpClass/tearDownClass and setup_method as fixtures, and special-casing Twisted trial.

Start here to understand how plain unittest code runs unchanged under pytest. Collection, per-item execution, result translation and trial workarounds are separated below.

**Children.**

- [TestCase collection](r5-unittest-collection.md) `r5-unittest-collection` · 6 unit(s)
- [TestCaseFunction item and setup fixtures](r5-unittest-case-item.md) `r5-unittest-case-item` · 16 unit(s)
- [unittest result-to-report translation](r5-unittest-result-bridge.md) `r5-unittest-result-bridge` · 7 unit(s)
- [Twisted trial workarounds](r5-unittest-twisted-workarounds.md) `r5-unittest-twisted-workarounds` · 7 unit(s)

**Depended on by.**

- [unittest integration tests](r5-unittest-integration-tests.md) · model-inferred · 0 edge(s)

Parent: [pytest codebase](r5-pytest-codebase.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

# Metafunc and parametrize tests

**Capability.** Tests of python.Metafunc and IdMaker: unit-level parametrize/idmaker behavior against mocked FunctionDefinition, functional tests through real collection and pytest_generate_tests, and mark/id-segment behaviors on parametrized sets.

Unit tests mock the Metafunc constructor (Metafunc::695); functional tests exercise full collection; the marks child covers pytest.param marks and HIDDEN_PARAM.

**Children.**

- [Metafunc unit tests](r4-metafunc-unit-tests.md) `r4-metafunc-unit-tests` · 6 unit(s)
- [Metafunc functional tests](r4-metafunc-functional-tests.md) `r4-metafunc-functional-tests` · 3 unit(s)
- [Parametrize marks and id segments](r4-metafunc-marks-ids-tests.md) `r4-metafunc-marks-ids-tests` · 2 unit(s)

Parent: [Test suites](r4-test-suites.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

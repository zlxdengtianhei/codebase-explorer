# Regression Suites

**Capability.** The three large self-test suites (assertion, collection, terminal) verifying plugin-visible behavior end to end through Pytester runs plus targeted in-process unit checks; they cohere as executable specifications of pytest's external behavior.

Use these to find the test covering a given behavior or to locate the harness idioms for new tests. All suites build on the Pytester harness and monkeypatch utilities.

**Children.**

- [Assertion Rewriting Suite](r6-test-assertion.md) `r6-test-assertion` · 2 unit(s)
- [Collection Suite](r6-test-collection.md) `r6-test-collection` · 0 unit(s)
- [Terminal Reporting Suite](r6-test-terminal.md) `r6-test-terminal` · 0 unit(s)

Parent: [pytest Framework Internals](r6-pytest-framework.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

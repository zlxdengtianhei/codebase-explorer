# Test-Suite Infrastructure

**Capability.** Shared fixtures and self-tests for pytest's own test suite: conftest fixtures that isolate colors/width/timing and provide pytester/tw mocks, plus tests of Stash, legacy path shims, and static typing contracts.

Use this subtree when writing or running pytest's own tests. The conftest fixtures guarantee deterministic environments; the stash/legacypath/typing tests verify supporting public APIs rather than runtime plugin behavior.

**Children.**

- [Testing conftest Fixtures](r3-conftest-fixtures.md) `r3-conftest-fixtures` · 9 unit(s)
- [Stash, Legacy Path & Typing Tests](r3-api-support-tests.md) `r3-api-support-tests` · 3 unit(s)

Parent: [Pytest Framework Codebase](r3-pytest.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

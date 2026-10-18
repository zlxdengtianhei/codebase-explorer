# Test suites

**Capability.** The testing/ tree verifying runtime and behavior contracts: traceback rendering, capture, monkeypatch, parametrization, report serialization, stepwise, deprecations, CLI surface, and third-party plugin integration.

Each child owns one test file's (or group's) responsibility. Fixtures/shared helpers are separated from the tests that consume them where the file structure supports it.

**Children.**

- [Excinfo and traceback tests](r4-test-excinfo.md) `r4-test-excinfo` · 0 unit(s)
- [Capture tests](r4-test-capture-suite.md) `r4-test-capture-suite` · 0 unit(s)
- [MonkeyPatch tests](r4-test-monkeypatch.md) `r4-test-monkeypatch` · 0 unit(s)
- [Metafunc and parametrize tests](r4-test-metafunc.md) `r4-test-metafunc` · 0 unit(s)
- [Report serialization tests](r4-test-reports.md) `r4-test-reports` · 0 unit(s)
- [Stepwise tests](r4-test-stepwise.md) `r4-test-stepwise` · 0 unit(s)
- [Deprecation tests](r4-deprecated-tests.md) `r4-deprecated-tests` · 0 unit(s)
- [Logging formatter tests](r4-logging-formatter-tests.md) `r4-logging-formatter-tests` · 4 unit(s)
- [CLI, config and package integrity tests](r4-cli-package-tests.md) `r4-cli-package-tests` · 0 unit(s)
- [Third-party plugin integration](r4-plugin-integration-tests.md) `r4-plugin-integration-tests` · 7 unit(s)

Parent: [Pytest codebase](r4-pytest-codebase.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

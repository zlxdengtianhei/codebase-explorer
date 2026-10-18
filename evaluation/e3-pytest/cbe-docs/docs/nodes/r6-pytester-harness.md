# Pytester Test Harness

**Capability.** Provides the plugin and fixtures for testing pytest itself: an isolated per-test directory, file factories, in-process and subprocess run entry points, hook recording, and line-based output matching; these cohere because a self-test needs reproducible runs plus assertions on output and hook calls.

Use this subtree to write or read pytest's own integration tests. Fixtures hand you a Pytester; runs return RunResult/HookRecorder objects; LineMatcher asserts on captured text.

**Children.**

- [Pytester Environment and File Setup](r6-pytester-core.md) `r6-pytester-core` · 8 unit(s)
- [Test Run Invocation](r6-pytester-run.md) `r6-pytester-run` · 8 unit(s)
- [Hook Recording](r6-pytester-recording.md) `r6-pytester-recording` · 2 unit(s)
- [Output Capture and Line Matching](r6-pytester-output-matching.md) `r6-pytester-output-matching` · 2 unit(s)

Parent: [pytest Framework Internals](r6-pytest-framework.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

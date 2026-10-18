# Fixtures, Marks and Bootstrap Primitives

**Capability.** Owns fixture declaration, registration, setup/teardown, and request semantics; the pytest.mark domain model; rootdir/ini bootstrapping; process-level diagnostics (faulthandler, time, scope); the unittest bridge; and the suites for fixtures, junitxml, cache, and unittest integration. These concerns cohere as the per-item runtime semantics layered on top of config.

Use this subtree to understand how fixtures and marks behave at runtime, how rootdir and ini parsing bootstrap a Config, and how unittest suites embed into pytest. Dedicated test suites sit beside each plugin area.

**Children.**

- [pytest codebase](r5-pytest-codebase.md) `r5-pytest-codebase` · 0 unit(s)

**Depends on.**

- [Assertion Rewriting, Session and Temp Plugins](assertion-session-tmp.md) · graph-confirmed · 6 edge(s)
- [Configuration & Plugin Core](config-plugin-core.md) · graph-confirmed · 2 edge(s)
- [Hook Contracts and Python Collection](hooks-collection-python.md) · graph-confirmed · 2 edge(s)
- [Platform, I/O and Reporting Plugins](platform-io-plugins.md) · graph-confirmed · 2 edge(s)
- [Runtime Helper Library](runtime-helper-library.md) · graph-confirmed · 4 edge(s)
- [Support Libraries and Runtime Tooling](support-and-tooling.md) · graph-confirmed · 562 edge(s) · Fixture, mark, unittest-bridge and junitxml code consume path, repr and source helper libraries.

**Depended on by.**

- [Configuration & Plugin Core](config-plugin-core.md) · graph-confirmed · 4 edge(s)
- [Framework Overview](framework-overview.md) · graph-confirmed · 1 edge(s)
- [Hook Contracts and Python Collection](hooks-collection-python.md) · graph-confirmed · 3 edge(s)
- [Logging, Runner and Terminal Loop](logging-runner-terminal.md) · graph-confirmed · 1 edge(s)
- [Platform, I/O and Reporting Plugins](platform-io-plugins.md) · graph-confirmed · 1 edge(s)
- [Support Libraries and Runtime Tooling](support-and-tooling.md) · graph-confirmed · 1 edge(s)

Parent: [Framework Core](framework-core.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

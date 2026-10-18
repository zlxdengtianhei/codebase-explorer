# Assertion Rewriting, Session and Temp Plugins

**Capability.** Owns transparent assertion introspection, the command-line entry and session lifecycle, collection-tree construction from filesystem paths, typed Stash infrastructure, stepwise resumption, temporary directory management, and legacy py.path compatibility, together with the suites and example scripts exercising them. These are the session-scoped mechanics around the run loop.

Read this subtree to understand how plain asserts yield detailed reports, how an invocation becomes a Session, and how basetemp and legacy paths are managed. Example scripts act as executable fixtures for regression scenarios.

**Children.**

- [Pytest Framework and Test Suite](r8-pytest-root.md) `r8-pytest-root` · 1 unit(s)

**Depends on.**

- [Configuration & Plugin Core](config-plugin-core.md) · graph-confirmed · 28 edge(s) · Assertion rewriting, the session plugins and stepwise read configuration and rewrite settings through the config core.
- [Hook Contracts and Python Collection](hooks-collection-python.md) · graph-confirmed · 2 edge(s)
- [Runtime Helper Library](runtime-helper-library.md) · graph-confirmed · 17 edge(s)
- [Support Libraries and Runtime Tooling](support-and-tooling.md) · graph-confirmed · 376 edge(s)

**Depended on by.**

- [Configuration & Plugin Core](config-plugin-core.md) · graph-confirmed · 2 edge(s)
- [Fixtures, Marks and Bootstrap Primitives](fixtures-marks-bootstrap.md) · graph-confirmed · 6 edge(s)
- [Support Libraries and Runtime Tooling](support-and-tooling.md) · graph-confirmed · 2 edge(s)

Parent: [Framework Core](framework-core.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

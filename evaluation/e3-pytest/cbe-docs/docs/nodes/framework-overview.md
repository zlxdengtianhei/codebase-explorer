# Framework Overview

**Capability.** Owns the whole-pytest orientation view: the public API facade, cross-cutting plugins (doctest, approx, leaked-exception reporting), compatibility layers, and the major test suites that pin framework behavior. It coheres as the top-level map between product code and testing tree.

Use this subtree to orient between product code under src/_pytest and the testing tree, and to find the public API surface and cross-cutting plugins. Cross-cutting dependencies flow downward into introspection and compatibility utilities.

**Children.**

- [pytest codebase](r1-pytest-codebase.md) `r1-pytest-codebase` · 0 unit(s)

**Depends on.**

- [Configuration & Plugin Core](config-plugin-core.md) · graph-confirmed · 35 edge(s)
- [Fixtures, Marks and Bootstrap Primitives](fixtures-marks-bootstrap.md) · graph-confirmed · 1 edge(s)
- [Hook Contracts and Python Collection](hooks-collection-python.md) · graph-confirmed · 4 edge(s)
- [Platform, I/O and Reporting Plugins](platform-io-plugins.md) · graph-confirmed · 1 edge(s)
- [Support Libraries and Runtime Tooling](support-and-tooling.md) · graph-confirmed · 505 edge(s)

**Depended on by.**

- [Configuration & Plugin Core](config-plugin-core.md) · graph-confirmed · 1 edge(s)
- [Hook Contracts and Python Collection](hooks-collection-python.md) · graph-confirmed · 1 edge(s)
- [Logging, Runner and Terminal Loop](logging-runner-terminal.md) · graph-confirmed · 7 edge(s)
- [Platform, I/O and Reporting Plugins](platform-io-plugins.md) · graph-confirmed · 1 edge(s)
- [Runtime Helper Library](runtime-helper-library.md) · graph-confirmed · 16 edge(s)
- [Support Libraries and Runtime Tooling](support-and-tooling.md) · graph-confirmed · 17 edge(s)

Parent: [pytest Codebase](pytest.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

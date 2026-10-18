# Hook Contracts and Python Collection

**Capability.** Owns the framework's extension contracts and its Python-language layer: hookspec declarations by lifecycle phase, the abstract collection tree (nodes.py), and Python test discovery, Function execution, xunit setup, parametrization, and junitxml reporting, plus the internal suites and example scripts that pin them. The hook contracts and node model are what python.py and plugins build on.

Use the hookspec subtree as the contract reference per session phase, the nodes subtree for the shared collection model, and the python subtree for how .py files become collectable items. Test and example subtrees serve as executable specifications.

**Children.**

- [pytest Codebase](r7-pytest-codebase.md) `r7-pytest-codebase` · 1 unit(s)

**Depends on.**

- [Configuration & Plugin Core](config-plugin-core.md) · graph-confirmed · 11 edge(s)
- [Fixtures, Marks and Bootstrap Primitives](fixtures-marks-bootstrap.md) · graph-confirmed · 3 edge(s)
- [Framework Overview](framework-overview.md) · graph-confirmed · 1 edge(s)
- [Logging, Runner and Terminal Loop](logging-runner-terminal.md) · graph-confirmed · 1 edge(s)
- [Platform, I/O and Reporting Plugins](platform-io-plugins.md) · graph-confirmed · 1 edge(s)
- [Runtime Helper Library](runtime-helper-library.md) · graph-confirmed · 10 edge(s)
- [Support Libraries and Runtime Tooling](support-and-tooling.md) · graph-confirmed · 469 edge(s) · Python collection, junitxml and the internal suites consume the shared path, repr and source helpers.

**Depended on by.**

- [Assertion Rewriting, Session and Temp Plugins](assertion-session-tmp.md) · graph-confirmed · 2 edge(s)
- [Configuration & Plugin Core](config-plugin-core.md) · graph-confirmed · 2 edge(s)
- [Fixtures, Marks and Bootstrap Primitives](fixtures-marks-bootstrap.md) · graph-confirmed · 2 edge(s)
- [Framework Overview](framework-overview.md) · graph-confirmed · 4 edge(s)
- [Logging, Runner and Terminal Loop](logging-runner-terminal.md) · graph-confirmed · 7 edge(s)
- [Platform, I/O and Reporting Plugins](platform-io-plugins.md) · graph-confirmed · 13 edge(s)
- [Runtime Helper Library](runtime-helper-library.md) · graph-confirmed · 34 edge(s)
- [Support Libraries and Runtime Tooling](support-and-tooling.md) · graph-confirmed · 39 edge(s)

Parent: [Framework Core](framework-core.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

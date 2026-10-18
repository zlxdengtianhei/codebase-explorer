# Configuration & Plugin Core

**Capability.** Builds a pytest invocation: CLI entry and Config creation, argument/ini parsing, plugin and conftest discovery and registration, config-time warnings, cache persistence, assertion-rewrite setup, and shared path/import utilities. Parsing, plugin registration, and ini lookup form one interleaved pipeline feeding every other subsystem.

Use this subtree to trace how command-line args, ini files, conftests, and plugins become a usable Config and hook registry. The cache provider and path utilities are shared infrastructure kept separate from their consumers.

**Children.**

- [Pytest Codebase](r2-pytest-root.md) `r2-pytest-root` · 39 unit(s)
- [Configuration & Plugin Core](config-plugin-core-unit.md) `config-plugin-core-unit` · 0 unit(s)

**Depends on.**

- [Assertion Rewriting, Session and Temp Plugins](assertion-session-tmp.md) · graph-confirmed · 2 edge(s)
- [Fixtures, Marks and Bootstrap Primitives](fixtures-marks-bootstrap.md) · graph-confirmed · 4 edge(s)
- [Framework Overview](framework-overview.md) · graph-confirmed · 1 edge(s)
- [Hook Contracts and Python Collection](hooks-collection-python.md) · graph-confirmed · 2 edge(s)
- [Logging, Runner and Terminal Loop](logging-runner-terminal.md) · graph-confirmed · 3 edge(s)
- [Platform, I/O and Reporting Plugins](platform-io-plugins.md) · graph-confirmed · 4 edge(s) · Config setup interacts with terminal, capture and warning plugins during invocation building.
- [Runtime Helper Library](runtime-helper-library.md) · graph-confirmed · 5 edge(s)
- [Support Libraries and Runtime Tooling](support-and-tooling.md) · graph-confirmed · 421 edge(s)

**Depended on by.**

- [Assertion Rewriting, Session and Temp Plugins](assertion-session-tmp.md) · graph-confirmed · 28 edge(s) · Assertion rewriting, the session plugins and stepwise read configuration and rewrite settings through the config core.
- [Fixtures, Marks and Bootstrap Primitives](fixtures-marks-bootstrap.md) · graph-confirmed · 2 edge(s)
- [Framework Overview](framework-overview.md) · graph-confirmed · 35 edge(s)
- [Hook Contracts and Python Collection](hooks-collection-python.md) · graph-confirmed · 11 edge(s)
- [Logging, Runner and Terminal Loop](logging-runner-terminal.md) · graph-confirmed · 6 edge(s)
- [Platform, I/O and Reporting Plugins](platform-io-plugins.md) · graph-confirmed · 9 edge(s)
- [Runtime Helper Library](runtime-helper-library.md) · graph-confirmed · 4 edge(s)
- [Support Libraries and Runtime Tooling](support-and-tooling.md) · graph-confirmed · 11 edge(s)

Parent: [Framework Core](framework-core.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

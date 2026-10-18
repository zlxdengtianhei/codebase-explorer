# Runtime Helper Library

**Capability.** Independently importable provider modules shipped inside pytest: outcome signals, raises and exception-group assertions, mark expression evaluation, argument parsing, interactive debugging, OS error mapping, and pytester assertion helpers, with the test suites verifying each. Each child owns one module's responsibility.

Navigate here for any standalone src/ runtime module; dependencies run from consumers to providers, and inferred (non-static) evidence is marked in depends_on basis.

**Children.**

- [Pytest codebase](r4-pytest-codebase.md) `r4-pytest-codebase` · 0 unit(s)

**Depends on.**

- [Configuration & Plugin Core](config-plugin-core.md) · graph-confirmed · 4 edge(s)
- [Framework Overview](framework-overview.md) · graph-confirmed · 16 edge(s)
- [Hook Contracts and Python Collection](hooks-collection-python.md) · graph-confirmed · 34 edge(s)
- [Platform, I/O and Reporting Plugins](platform-io-plugins.md) · graph-confirmed · 24 edge(s)
- [Support Libraries and Runtime Tooling](support-and-tooling.md) · containment · → 0 / ← 0 edge(s) (ancestor direct units and descendant subtree; → follows ` runtime-helper-library ` → ` support-and-tooling `)

**Depended on by.**

- [Assertion Rewriting, Session and Temp Plugins](assertion-session-tmp.md) · graph-confirmed · 17 edge(s)
- [Configuration & Plugin Core](config-plugin-core.md) · graph-confirmed · 5 edge(s)
- [Fixtures, Marks and Bootstrap Primitives](fixtures-marks-bootstrap.md) · graph-confirmed · 4 edge(s)
- [Hook Contracts and Python Collection](hooks-collection-python.md) · graph-confirmed · 10 edge(s)
- [Logging, Runner and Terminal Loop](logging-runner-terminal.md) · graph-confirmed · 7 edge(s)
- [Platform, I/O and Reporting Plugins](platform-io-plugins.md) · graph-confirmed · 5 edge(s)
- [Support Libraries and Runtime Tooling](support-and-tooling.md) · containment · → 0 / ← 0 edge(s) (ancestor direct units and descendant subtree; → follows ` support-and-tooling ` → ` runtime-helper-library `)

Parent: [Support Libraries and Runtime Tooling](support-and-tooling.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

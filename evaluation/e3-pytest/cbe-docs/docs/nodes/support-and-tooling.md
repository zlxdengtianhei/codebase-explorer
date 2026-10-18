# Support Libraries and Runtime Tooling

**Capability.** Owns the dependency-free foundations and independently importable helpers pytest ships: legacy path objects, safe reprs, monkeypatching, filesystem/import path utilities, the outcome/raises/mark-expression runtime library, plus the Pytester self-test harness and its suites. They cohere as infrastructure consumed by plugins and tests but owning no run-lifecycle logic themselves.

Enter here for infrastructure primitives and helper modules rather than test-run logic. Consumers live in the core and platform subtrees; the harness and suites verify behavior end to end.

**Children.**

- [pytest Framework Internals](r6-pytest-framework.md) `r6-pytest-framework` · 1 unit(s)
- [Runtime Helper Library](runtime-helper-library.md) `runtime-helper-library` · 0 unit(s)

**Depends on.**

- [Assertion Rewriting, Session and Temp Plugins](assertion-session-tmp.md) · graph-confirmed · 2 edge(s)
- [Configuration & Plugin Core](config-plugin-core.md) · graph-confirmed · 11 edge(s)
- [Fixtures, Marks and Bootstrap Primitives](fixtures-marks-bootstrap.md) · graph-confirmed · 1 edge(s)
- [Framework Overview](framework-overview.md) · graph-confirmed · 17 edge(s)
- [Hook Contracts and Python Collection](hooks-collection-python.md) · graph-confirmed · 39 edge(s)
- [Platform, I/O and Reporting Plugins](platform-io-plugins.md) · graph-confirmed · 36 edge(s)
- [Runtime Helper Library](runtime-helper-library.md) · containment · → 0 / ← 0 edge(s) (ancestor direct units and descendant subtree; → follows ` support-and-tooling ` → ` runtime-helper-library `)

**Depended on by.**

- [Assertion Rewriting, Session and Temp Plugins](assertion-session-tmp.md) · graph-confirmed · 376 edge(s)
- [Configuration & Plugin Core](config-plugin-core.md) · graph-confirmed · 421 edge(s)
- [Fixtures, Marks and Bootstrap Primitives](fixtures-marks-bootstrap.md) · graph-confirmed · 562 edge(s) · Fixture, mark, unittest-bridge and junitxml code consume path, repr and source helper libraries.
- [Framework Overview](framework-overview.md) · graph-confirmed · 505 edge(s)
- [Hook Contracts and Python Collection](hooks-collection-python.md) · graph-confirmed · 469 edge(s) · Python collection, junitxml and the internal suites consume the shared path, repr and source helpers.
- [Logging, Runner and Terminal Loop](logging-runner-terminal.md) · graph-confirmed · 394 edge(s)
- [Platform, I/O and Reporting Plugins](platform-io-plugins.md) · graph-confirmed · 334 edge(s)
- [Runtime Helper Library](runtime-helper-library.md) · containment · → 0 / ← 0 edge(s) (ancestor direct units and descendant subtree; → follows ` runtime-helper-library ` → ` support-and-tooling `)

Parent: [pytest Codebase](pytest.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

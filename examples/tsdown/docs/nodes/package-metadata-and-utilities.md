# Package metadata and utilities

**Capability.** Produces and validates package metadata—exports fields and lint checks—while providing dependency externals and shared general helpers.

Come here for post-build package correctness and shared utilities. Dependency handling and general utilities underpins the other children, which generate exports and run publint and types-wrong checks.

**Children.**

- [Dependency handling and general utilities](dependency-handling-and-general-utilities.md) `dependency-handling-and-general-utilities` · 12 unit(s)
- [Package exports generation](package-exports-generation.md) `package-exports-generation` · 10 unit(s)
- [Package lint checks](package-lint-checks.md) `package-lint-checks` · 10 unit(s)

**Depends on.**

- [Configuration loading and resolution](configuration-loading-and-resolution.md) · graph-confirmed · 2 edge(s)
- [Entry resolution and filesystem helpers](entry-resolution-and-filesystem-helpers.md) · graph-confirmed · 2 edge(s)
- [Logging and size reporting](logging-and-size-reporting.md) · graph-confirmed · 1 edge(s)

**Depended on by.**

- [Build execution pipeline](build-execution-pipeline.md) · graph-confirmed · 9 edge(s) · 1 inferred relation(s) · The build pipeline relies on package metadata and utilities for exports generation, lint checks, and shared helpers.
- [CLI entry and debug](cli-entry-and-debug.md) · graph-confirmed · 1 edge(s)
- [Configuration loading and resolution](configuration-loading-and-resolution.md) · graph-confirmed · 8 edge(s)
- [Entry resolution and filesystem helpers](entry-resolution-and-filesystem-helpers.md) · graph-confirmed · 2 edge(s)
- [Single executable builds](single-executable-builds.md) · graph-confirmed · 1 edge(s)

Parent: [tsdown bundling system](tsdown-bundling-system.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

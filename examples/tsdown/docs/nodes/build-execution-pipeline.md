# Build execution pipeline

**Capability.** Executes builds end to end: orchestrating parallel per-format builds and lifecycles while assembling Rolldown input, output, and plugin options.

Come here when a build runs or fails. Build orchestration and lifecycle manages the overall flow and side effects, while Rolldown option assembly translates resolved configs into the actual Rolldown build inputs.

**Children.**

- [Build orchestration and lifecycle](build-orchestration-and-lifecycle.md) `build-orchestration-and-lifecycle` · 18 unit(s)
- [Rolldown option assembly](rolldown-option-assembly.md) `rolldown-option-assembly` · 15 unit(s)

**Depends on.**

- [Configuration loading and resolution](configuration-loading-and-resolution.md) · graph-confirmed · 6 edge(s) · The build pipeline calls into configuration loading to obtain build-ready settings.
- [Entry resolution and filesystem helpers](entry-resolution-and-filesystem-helpers.md) · graph-confirmed · 7 edge(s) · The build pipeline uses entry resolution and filesystem helpers to normalize entries and manage files.
- [Logging and size reporting](logging-and-size-reporting.md) · graph-confirmed · 4 edge(s) · 1 inferred relation(s) · The build pipeline uses logging and size reporting to print build output and per-chunk sizes.
- [Package metadata and utilities](package-metadata-and-utilities.md) · graph-confirmed · 9 edge(s) · 1 inferred relation(s) · The build pipeline relies on package metadata and utilities for exports generation, lint checks, and shared helpers.
- [Single executable builds](single-executable-builds.md) · graph-confirmed · 1 edge(s) · The build pipeline invokes single-executable builds for the experimental exe feature.

**Depended on by.**

- [Configuration loading and resolution](configuration-loading-and-resolution.md) · graph-confirmed · 1 edge(s) · Resolved configuration is passed into the build pipeline to execute builds.

Parent: [tsdown bundling system](tsdown-bundling-system.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

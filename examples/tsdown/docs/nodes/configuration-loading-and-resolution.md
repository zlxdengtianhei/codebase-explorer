# Configuration loading and resolution

**Capability.** Discovers and imports config files, then normalizes them into per-format resolved configs with defaults and feature flags.

Come here to understand how user configuration becomes build-ready settings. Config file loading finds and parses configs including workspace expansion, and Config resolution and normalization applies defaults and per-format resolution.

**Children.**

- [Config resolution and normalization](config-resolution-and-normalization.md) `config-resolution-and-normalization` · 13 unit(s)
- [Config file loading](config-file-loading.md) `config-file-loading` · 8 unit(s)

**Depends on.**

- [Build execution pipeline](build-execution-pipeline.md) · graph-confirmed · 1 edge(s) · Resolved configuration is passed into the build pipeline to execute builds.
- [Entry resolution and filesystem helpers](entry-resolution-and-filesystem-helpers.md) · graph-confirmed · 3 edge(s)
- [Logging and size reporting](logging-and-size-reporting.md) · graph-confirmed · 3 edge(s)
- [Package metadata and utilities](package-metadata-and-utilities.md) · graph-confirmed · 8 edge(s)
- [Single executable builds](single-executable-builds.md) · graph-confirmed · 1 edge(s)

**Depended on by.**

- [Build execution pipeline](build-execution-pipeline.md) · graph-confirmed · 6 edge(s) · The build pipeline calls into configuration loading to obtain build-ready settings.
- [CLI entry and debug](cli-entry-and-debug.md) · graph-confirmed · 1 edge(s) · The CLI entry loads and resolves the user's configuration before running builds.
- [Entry resolution and filesystem helpers](entry-resolution-and-filesystem-helpers.md) · graph-confirmed · 1 edge(s)
- [Package metadata and utilities](package-metadata-and-utilities.md) · graph-confirmed · 2 edge(s)

Parent: [tsdown bundling system](tsdown-bundling-system.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

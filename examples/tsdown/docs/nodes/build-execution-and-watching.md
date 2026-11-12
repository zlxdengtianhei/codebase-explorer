# Build execution and watching

**Capability.** Coordinates build lifecycle, watch state, copy operations, target handling, and compatibility warnings.

Use for runtime build orchestration and watch behavior. Lifecycle manages configs, bundles, and hooks; target helpers handle copy, shortcuts, and targets; watch set records metadata and chunks.

**Children.**

- [Build orchestration lifecycle](build-orchestration-lifecycle.md) `build-orchestration-lifecycle` · 12 unit(s)
- [Copy shortcuts target helpers](copy-shortcuts-target-helpers.md) `copy-shortcuts-target-helpers` · 7 unit(s)
- [Watch set and chunks](watch-set-and-chunks.md) `watch-set-and-chunks` · 4 unit(s)

**Depends on.**

- [Config file loading](config-file-loading.md) · graph-confirmed · 1 edge(s)
- [Entry and path resolution](entry-and-path-resolution.md) · graph-confirmed · 5 edge(s)
- [Executable builds and sizing](executable-builds-and-sizing.md) · graph-confirmed · 1 edge(s)
- [Package output and validation](package-output-and-validation.md) · graph-confirmed · 13 edge(s) · Build execution invokes package output and validation for post-build package artifacts and checks.
- [Rolldown option assembly](rolldown-option-assembly.md) · graph-confirmed · 2 edge(s)

**Depended on by.**

- [Config resolution and logging](config-resolution-and-logging.md) · graph-confirmed · 2 edge(s) · Config resolution supplies resolved options and logging context to build execution and watching.
- [Rolldown option assembly](rolldown-option-assembly.md) · graph-confirmed · 1 edge(s)

Parent: [tsdown build tool](tsdown-build-tool.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

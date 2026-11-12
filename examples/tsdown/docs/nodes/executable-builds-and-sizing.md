# Executable builds and sizing

**Capability.** Builds Node SEA executables and reports bundle sizes with compression metrics.

Use for executable packaging and size reporting. SEA builds validate and produce executables; size reporting computes and formats bundle byte metrics.

**Children.**

- [Executable SEA builds](executable-sea-builds.md) `executable-sea-builds` · 5 unit(s)
- [Bundle size reporting](bundle-size-reporting.md) `bundle-size-reporting` · 5 unit(s)

**Depends on.**

- [Config resolution and logging](config-resolution-and-logging.md) · graph-confirmed · 1 edge(s)
- [Entry and path resolution](entry-and-path-resolution.md) · graph-confirmed · 2 edge(s)
- [Package output and validation](package-output-and-validation.md) · graph-confirmed · 1 edge(s)

**Depended on by.**

- [Build execution and watching](build-execution-and-watching.md) · graph-confirmed · 1 edge(s)
- [Config resolution and logging](config-resolution-and-logging.md) · graph-confirmed · 1 edge(s)
- [Package output and validation](package-output-and-validation.md) · graph-confirmed · 1 edge(s)
- [Rolldown option assembly](rolldown-option-assembly.md) · graph-confirmed · 1 edge(s)

Parent: [tsdown build tool](tsdown-build-tool.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

# tsdown Build Tool

**Capability.** tsdown is a library bundler CLI that turns user configuration into resolved per-format build configs and drives Rolldown to produce package-ready output artifacts.

Start here to understand the tool. Entry flows from the CLI through config resolution into build orchestration, which delegates to Rolldown option assembly, plugins, and post-build packaging features. Shared utilities are factored out and consumed by all feature areas.

**Children.**

- [Command-Line Interface](cli.md) `cli` · 3 unit(s)
- [Build Orchestration](build-orchestration.md) `build-orchestration` · 20 unit(s)
- [Configuration Resolution](config.md) `config` · 5 unit(s)
- [Rolldown Options Assembly](rolldown-assembly.md) `rolldown-assembly` · 7 unit(s)
- [Output File Naming and Formats](output-shaping.md) `output-shaping` · 13 unit(s)
- [Single-Executable Output](exe-output.md) `exe-output` · 9 unit(s)
- [Package Publishing](package-publishing.md) `package-publishing` · 17 unit(s)
- [Build Size Reporting](reporting.md) `reporting` · 7 unit(s)
- [Shared Utilities](shared-utils.md) `shared-utils` · 0 unit(s)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

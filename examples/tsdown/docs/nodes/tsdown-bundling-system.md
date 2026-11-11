# tsdown bundling system

**Capability.** A TypeScript/JavaScript bundler that turns user configs and entries into Rolldown builds with generated package exports, lint checks, and CLI tooling.

Come here for the complete system: build execution, configuration, package metadata tooling, and supporting utilities. The build orchestration group drives everything, config groups supply resolved settings, and the remaining children provide entry resolution, logging, executables, and the CLI.

**Children.**

- [Build execution pipeline](build-execution-pipeline.md) `build-execution-pipeline` · 33 unit(s)
- [Package metadata and utilities](package-metadata-and-utilities.md) `package-metadata-and-utilities` · 32 unit(s)
- [Configuration loading and resolution](configuration-loading-and-resolution.md) `configuration-loading-and-resolution` · 21 unit(s)
- [Logging and size reporting](logging-and-size-reporting.md) `logging-and-size-reporting` · 9 unit(s)
- [Entry resolution and filesystem helpers](entry-resolution-and-filesystem-helpers.md) `entry-resolution-and-filesystem-helpers` · 8 unit(s)
- [Single executable builds](single-executable-builds.md) `single-executable-builds` · 5 unit(s)
- [CLI entry and debug](cli-entry-and-debug.md) `cli-entry-and-debug` · 5 unit(s)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

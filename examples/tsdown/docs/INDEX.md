# tsdown: code map

tsdown is a build tool that spans CLI entry, config discovery and resolution, Rolldown option assembly, build execution and watching, package output validation, and executable or size reporting. Top-level modules divide the work between user-facing CLI/config handling, build lifecycle and watch orchestration, option/plugin assembly, entry/path resolution, and post-build package or executable artifacts. Package output modules handle dependency externalization, export maps, and tarball validation, while executable modules cover SEA builds and bundle-size reporting.

## Modules

- [**Package output and validation**](nodes/package-output-and-validation.md) — Handles dependency externalization, package export metadata, and tarball validation for built packages. (30 units; `exports.ts`, `deps.ts`, `pkg/index.ts`)
  - [**Dependency externalization utilities**](nodes/dependency-externalization-utilities.md) — Decides dependency externalization and provides general helpers for debouncing, promises, imports, pattern matching, resolution checks, and array normalization. (13 units; `deps.ts`, `general.ts`)
  - [**Package export map generation**](nodes/package-export-map-generation.md) — Builds package.json export maps, legacy fields, CSS and inlined-dependency metadata, and writes changed package metadata. (9 units; `exports.ts`, `general.ts`)
  - [**Package tarball validation**](nodes/package-tarball-validation.md) — Collects completed bundles, writes exports, packs packages, and runs publint/ATTW checks with formatted logging. (8 units; `pkg/index.ts`, `attw.ts`, `publint.ts`)
- [**Build execution and watching**](nodes/build-execution-and-watching.md) — Coordinates build lifecycle, watch state, copy operations, target handling, and compatibility warnings. (23 units; `build.ts`, `copy.ts`, `shortcuts.ts`)
  - [**Build orchestration lifecycle**](nodes/build-orchestration-lifecycle.md) — Orchestrates resolved configs, builds bundles, manages watch/devtools lifecycle, cleans outputs, and runs post-build hooks. (12 units; `build.ts`, `clean.ts`, `hooks.ts`)
  - [**Copy shortcuts target helpers**](nodes/copy-shortcuts-target-helpers.md) — Runs copy operations, handles keyboard shortcuts, resolves Node targets, and warns about CJS require(ESM) compatibility. (7 units; `copy.ts`, `shortcuts.ts`, `target.ts`)
  - [**Watch set and chunks**](nodes/watch-set-and-chunks.md) — Adds config and package metadata to the watch set and records output chunks with their output directory. (4 units; `watch.ts`, `chunks.ts`)
- [**Config resolution and logging**](nodes/config-resolution-and-logging.md) — Resolves user configs and options, loads package/tsconfig metadata, formats logs, and adds shebang execute permissions. (16 units; `options.ts`, `logger.ts`, `tsconfig.ts`)
- [**Rolldown option assembly**](nodes/rolldown-option-assembly.md) — Builds Rolldown input/output options and plugins, including filenames, shims, node protocol, CSS guards, and debug serialization. (16 units; `rolldown.ts`, `output.ts`, `node-protocol.ts`)
- [**Executable builds and sizing**](nodes/executable-builds-and-sizing.md) — Builds Node SEA executables and reports bundle sizes with compression metrics. (10 units; `exe.ts`, `report.ts`, `format.ts`)
  - [**Executable SEA builds**](nodes/executable-sea-builds.md) — Validates and builds Node SEA executables from output chunks, including naming, signing, and size reporting. (5 units; `exe.ts`)
  - [**Bundle size reporting**](nodes/bundle-size-reporting.md) — Computes and logs bundle sizes, including gzip and brotli, and formats byte counts for reports. (5 units; `report.ts`, `format.ts`)
- [**Entry and path resolution**](nodes/entry-and-path-resolution.md) — Resolves entry inputs into name-to-path maps and provides filesystem/path helpers for access, prefixes, and extensions. (8 units; `entry.ts`, `fs.ts`)
- [**Config file loading**](nodes/config-file-loading.md) — Loads config files through selected parsers/importers, resolves workspace layers, and returns resolved configs with discovered files. (8 units; `file.ts`, `workspace.ts`, `config/index.ts`)
- [**CLI entry and debug**](nodes/cli-entry-and-debug.md) — Registers and runs the CLI, enables debug namespaces, and provides the executable entry with Node-version warning. (5 units; `cli.ts`, `debug.ts`, `run.ts`)

## Key flows

- **Main build and copy**: The main build path resolves configs, builds each config, then post-build copy uses array normalization. — `build` → `build.ts-buildwithconfigs-orchestration` → `build.ts-buildsingle-orchestration` → `postBuild` → `copy.ts-copy-implementation` → `toArray`
- **Executable post-build**: Post-build executable handling delegates to the SEA executable builder for each output. — `build` → `build.ts-buildwithconfigs-orchestration` → `build.ts-buildsingle-orchestration` → `postBuild` → `buildExe` → `buildSingleExe`
- **Watch cleanup**: Watcher handling cleans emitted chunks through filesystem wrappers. — `build` → `build.ts-buildwithconfigs-orchestration` → `build.ts-buildsingle-orchestration` → `handleWatcher` → `cleanChunks` → `fs.ts-filesystem-wrappers`
- **Rolldown input options**: Build initialization assembles Rolldown input options through the shared option builder. — `build` → `build.ts-buildwithconfigs-orchestration` → `build.ts-buildsingle-orchestration` → `initBuildOptions` → `getBuildOptions` → `rolldown.ts-resolveinputoptions`
- **Dependency pattern matching**: The dependency plugin handler matches dependency patterns during externalization decisions. — `src/features/deps.ts:DepPlugin.handler` → `matchPattern`

## Read further

`RUN` is this run directory. Find an `ID` by name, then read it:

- `cbe find --run-dir "$RUN" --term "NAME"` — locate a unit, symbol or file by name
- `cbe query --run-dir "$RUN" --id "ID"` — the explanation, relations and evidence of one unit
- `cbe source --run-dir "$RUN" --id "ID" --context 2` — the frozen source, digest checked

More: [DEPENDENCIES.md](DEPENDENCIES.md) · [RUN.md](RUN.md)

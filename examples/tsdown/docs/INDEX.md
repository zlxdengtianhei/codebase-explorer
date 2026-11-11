# tsdown: code map

tsdown is a TypeScript/JavaScript bundler that turns user configs and entries into Rolldown builds, then finalizes packages with generated exports, lint checks, and optional single-executable output. The CLI entry parses argv and hands off to configuration loading, which discovers config files and normalizes them into per-format resolved configs. The build execution pipeline then orchestrates parallel builds and lifecycles while Rolldown option assembly constructs the actual build inputs, with entry resolution, logging/size reporting, package metadata tooling, and executable builds supporting along the way.

## Modules

- [**Build execution pipeline**](nodes/build-execution-pipeline.md) — Executes builds end to end: orchestrating parallel per-format builds and lifecycles while assembling Rolldown input, output, and plugin options. (33 units; `rolldown.ts`, `build.ts`, `copy.ts`)
  - [**Build orchestration and lifecycle**](nodes/build-orchestration-and-lifecycle.md) — Drives builds: resolving configs into parallel builds, managing watch/devtools/shortcuts lifecycles, and running post-build copy, clean, and executable side effects. (18 units; `build.ts`, `copy.ts`, `shortcuts.ts`)
  - [**Rolldown option assembly**](nodes/rolldown-option-assembly.md) — Translates resolved configs into Rolldown input/output options, plugin pipeline, and per-format build options, including debug config serialization. (15 units; `rolldown.ts`, `output.ts`, `node-protocol.ts`)
- [**Package metadata and utilities**](nodes/package-metadata-and-utilities.md) — Produces and validates package metadata—exports fields and lint checks—while providing dependency externals and shared general helpers. (32 units; `exports.ts`, `deps.ts`, `attw.ts`)
  - [**Dependency handling and general utilities**](nodes/dependency-handling-and-general-utilities.md) — Handles dependency externals and bundling policy plus shared general helpers like debounce, pattern matching, and dynamic imports. (12 units; `deps.ts`, `general.ts`)
  - [**Package exports generation**](nodes/package-exports-generation.md) — Computes and writes package.json export fields (main, module, types, exports) from build chunks, honoring dev, wildcard, and exclusion options. (10 units; `exports.ts`)
  - [**Package lint checks**](nodes/package-lint-checks.md) — Runs publint and are-the-types-wrong checks on packed tarballs, coordinating per-package post-build work across bundles. (10 units; `attw.ts`, `pkg/index.ts`, `publint.ts`)
- [**Configuration loading and resolution**](nodes/configuration-loading-and-resolution.md) — Discovers and imports config files, then normalizes them into per-format resolved configs with defaults and feature flags. (21 units; `options.ts`, `file.ts`, `workspace.ts`)
  - [**Config resolution and normalization**](nodes/config-resolution-and-normalization.md) — Resolves user configs into per-format ResolvedConfig objects, applying defaults, filters, CI-aware feature flags, and target/tsconfig resolution. (13 units; `options.ts`, `tsconfig.ts`, `target.ts`)
  - [**Config file loading**](nodes/config-file-loading.md) — Discovers, parses, and imports tsdown config files, including workspace expansion and Vite/Vitest config reuse. (8 units; `file.ts`, `workspace.ts`, `config/index.ts`)
- [**Logging and size reporting**](nodes/logging-and-size-reporting.md) — Provides the leveled logger, color helpers, and per-chunk size reporting (raw, gzip, brotli) printed after builds. (9 units; `logger.ts`, `report.ts`, `format.ts`)
- [**Entry resolution and filesystem helpers**](nodes/entry-resolution-and-filesystem-helpers.md) — Resolves user entry options (string, array, object, glob) into name-to-path maps, backed by small fs and path utilities. (8 units; `entry.ts`, `fs.ts`)
- [**Single executable builds**](nodes/single-executable-builds.md) — Builds Node single-executable applications from bundled chunks, validating environment support and computing output names. (5 units; `exe.ts`)
- [**CLI entry and debug**](nodes/cli-entry-and-debug.md) — Defines and runs the tsdown CLI, parsing argv, enabling debug namespaces, and providing the config-file identity helper. (5 units; `cli.ts`, `debug.ts`, `run.ts`)

## Key flows

- **Build to post-build package finalization**: A build run orchestrates per-config builds, then bundleDone coordinates exports writing, lint checks, and tarball packing. — `build` → `build.ts-buildwithconfigs-orchestration` → `build.ts-buildsingle` → `build.ts-buildwithconfigs-lifecycle-helpers` → `bundleDone` → `writeExports`
- **Post-build lint and tarball validation**: After bundling, bundleDone packs a tarball and runs publint and are-the-types-wrong checks per package. — `build` → `build.ts-buildwithconfigs-orchestration` → `build.ts-buildsingle` → `build.ts-buildwithconfigs-lifecycle-helpers` → `bundleDone` → `publint`
- **Single-executable build path**: The build pipeline finishes a bundle and then produces a Node single-executable application with a resolved output name. — `build` → `build.ts-buildwithconfigs-orchestration` → `build.ts-buildsingle` → `postBuild` → `buildExe` → `buildSingleExe`
- **Watch-mode entry re-resolution**: In watch mode, changed glob entries are re-resolved through object/array entry normalization before rebuilding. — `build` → `build.ts-buildwithconfigs-orchestration` → `build.ts-buildsingle` → `handleWatcher` → `toObjectEntry` → `resolveObjectEntry`
- **Post-build cleanup and copy**: After each single build, the output directory is cleaned and copy side effects run via filesystem wrappers. — `build` → `build.ts-buildwithconfigs-orchestration` → `build.ts-buildsingle` → `postBuild` → `copy.ts-copy-pipeline` → `fs.ts-fs-wrappers`
- **Success hooks after build**: Once a single build completes its post-build steps, user on-success hooks are executed. — `build` → `build.ts-buildwithconfigs-orchestration` → `build.ts-buildsingle` → `postBuild` → `executeOnSuccess`

## Read further

`RUN` is this run directory. Find an `ID` by name, then read it:

- `cbe find --run-dir "$RUN" --term "NAME"` — locate a unit, symbol or file by name
- `cbe query --run-dir "$RUN" --id "ID"` — the explanation, relations and evidence of one unit
- `cbe source --run-dir "$RUN" --id "ID" --context 2` — the frozen source, digest checked

More: [DEPENDENCIES.md](DEPENDENCIES.md) · [RUN.md](RUN.md)

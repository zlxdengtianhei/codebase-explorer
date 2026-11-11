# Single executable builds

**Capability.** Builds Node single-executable applications from bundled chunks, validating environment support and computing output names.

Come here for the experimental exe feature: SEA config generation, invoking Node's --build-sea, codesigning, and environment validation.

**Depends on.**

- [Entry resolution and filesystem helpers](entry-resolution-and-filesystem-helpers.md) · graph-confirmed · 2 edge(s) · Single-executable builds use entry and filesystem helpers to locate chunks and compute output names.
- [Logging and size reporting](logging-and-size-reporting.md) · graph-confirmed · 1 edge(s)
- [Package metadata and utilities](package-metadata-and-utilities.md) · graph-confirmed · 1 edge(s)
- [Dependency handling and general utilities](dependency-handling-and-general-utilities.md) · graph-only · 1 edge(s)

**Depended on by.**

- [Build execution pipeline](build-execution-pipeline.md) · graph-confirmed · 1 edge(s) · The build pipeline invokes single-executable builds for the experimental exe feature.
- [Configuration loading and resolution](configuration-loading-and-resolution.md) · graph-confirmed · 1 edge(s)
- [Build orchestration and lifecycle](build-orchestration-and-lifecycle.md) · graph-only · 1 edge(s)
- [Config resolution and normalization](config-resolution-and-normalization.md) · graph-only · 1 edge(s)

Parent: [tsdown bundling system](tsdown-bundling-system.md)

## Units (5)

<a id="u-44db5251620e"></a>
### `exe.ts-exe-sea-option-types`

`export interface ExeOptions extends ExeExtensionOptions` · [src/features/exe.ts:L16-L23][f1]

ExeOptions extends the @tsdown/exe extension options with `fileName` (string or chunk-derived function, without suffix/extension) and `seaConfig`, a partial Node SEA config minus main/output/mainFormat.

SeaConfig mirrors Node's SEA options with tsdown-friendly defaults noted in docstrings (warning disabled, code cache enabled) that implementations may override.

<a id="u-5ec03dd7b88c"></a>
### `buildExe`

`export async function buildExe( config: ResolvedConfig, chunks: RolldownChunk[], ): P…` · [src/features/exe.ts:L87-L143][f1]

Builds Node single-executable applications from the bundled output chunks.

Returns immediately without exe config. DTS chunks (fileName matching RE_DTS) are filtered out first; more than one remaining chunk throws listing the offenders. With exe.targets set, it warns that seaConfig.executable is ignored, dynamically imports @tsdown/exe (via importWithError, which surfaces a load error), and for each target resolves a Node binary, computes a platform suffix, derives the output file name, and builds one executable sequentially. Without targets it builds a single executable using defaults. Errors from the per-target loop propagate and abort remaining targets.

calls: [resolveOutputFileName](single-executable-builds.md#u-3028e8eea5f5), [buildSingleExe](single-executable-builds.md#u-8715ba3f798c), [function::importWithError][f2], [function::buildSingle.postBuild][f3]

<a id="u-8715ba3f798c"></a>
### `buildSingleExe`

`async function buildSingleExe( config: ResolvedConfig, bundledFile: string, outputFil…` · [src/features/exe.ts:L172-L253][f1]

Runs one SEA build: writes a temp sea-config.json and invokes the host Node binary with --build-sea, then codesigns and reports.

The config merges defaults ({disableExperimentalSEAWarning: true} plus user seaConfig) with main=bundledFile, output=outDir/outputFile, and mainFormat 'module' for es format else 'commonjs'; an explicit executable (target binary path) is added when given. It always uses process.execPath for the --build-sea child (stdio: stderr inherited, throwOnError), so child failure throws. The temp directory is removed in finally unless the debug flag is enabled, in which case it is preserved. For darwin targets (or host darwin without a target) it runs ad-hoc `codesign --sign -`; on failure it only warns, with a manual command hint on darwin hosts or a note that automatic signing is unsupported elsewhere. Finally it stats the output and logs its formatted size plus a success line with elapsed time; a missing stat silently skips the size log. codesign must exist on PATH on darwin hosts — its absence is caught, but the --build-sea child's availability is not.

**Notes.**

- side_effect: creates and (usually) removes a temp directory under os.tmpdir()
- failure: codesign failure is swallowed into a warning; --build-sea failure throws

calls: [function::fsRemove][f4], [function::fsStat][f4]

<a id="u-3028e8eea5f5"></a>
### `resolveOutputFileName`

`function resolveOutputFileName( exe: ExeOptions, chunk: RolldownChunk, bundledFile: s…` · [src/features/exe.ts:L145-L170][f1]

Computes the executable's output file name (no directory).

If exe.fileName is set, a function form receives the chunk; otherwise the base name is the bundled file's name without extension. A target suffix is appended when provided, and '.exe' is appended when the target platform is 'win' or, with no target, the host is win32.

<a id="u-788f5b9b60dc"></a>
### `validateSea`

`export function validateSea({ dts, entry, logger, nameLabel, }: Omit<ResolvedConfig, …` · [src/features/exe.ts:L50-L85][f1]

Validates that the environment supports the experimental `exe` feature before building.

Throws if running under Bun or Deno, if the Node version is below 25.7.0, or if more than one entry exists. If dts is enabled it warns that generated .d.ts files won't be embedded in the executable; it always logs an info that `exe` is experimental. Returns void; all failures are thrown Errors.

calls: [function::resolveUserConfig][f5]

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/rolldown/tsdown/blob/2b1be7e0accdb1d6e903cd42642666431fc5e93d/src/features/exe.ts
[f2]: https://github.com/rolldown/tsdown/blob/2b1be7e0accdb1d6e903cd42642666431fc5e93d/src/utils/general.ts
[f3]: https://github.com/rolldown/tsdown/blob/2b1be7e0accdb1d6e903cd42642666431fc5e93d/src/build.ts
[f4]: https://github.com/rolldown/tsdown/blob/2b1be7e0accdb1d6e903cd42642666431fc5e93d/src/utils/fs.ts
[f5]: https://github.com/rolldown/tsdown/blob/2b1be7e0accdb1d6e903cd42642666431fc5e93d/src/config/options.ts

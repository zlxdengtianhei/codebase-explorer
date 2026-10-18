# Single-Executable Output

**Capability.** Builds Node single-executable applications (SEA) from rolldown chunks when config.exe is set, including environment validation and output naming.

Use this subtree for the exe/SEA feature. Validation runs during config resolution while actual executable production happens after bundling; both share the exe option types.

**Depends on.**

- [General and Filesystem Helpers](general-and-fs.md) · graph-confirmed · 4 edge(s)
- [Logging](logging.md) · graph-only · 2 edge(s)

**Depended on by.**

- [Build Orchestration](build-orchestration.md) · graph-confirmed · 1 edge(s)
- [User Config Normalization](config-merging.md) · graph-confirmed · 1 edge(s)

Parent: [tsdown Build Tool](tsdown.md)

## Units (9)

<a id="u-5ec03dd7b88c"></a>
### `buildExe`

`export async function buildExe( config: ResolvedConfig, chunks: RolldownChunk[], ): P…` · [src/features/exe.ts:L87-L143][f1]

Builds single-executable applications from rolldown chunks when config.exe is set.

Dts chunks are filtered out via the RE_DTS filename pattern; if more than one chunk remains it throws listing the chunk names. With exe.targets configured, seaConfig.executable is ignored with a warning, @tsdown/exe is dynamically imported via importWithError, and for each target a node binary is resolved, a suffix derived, and buildSingleExe invoked. Without targets, buildSingleExe runs once with no explicit executable (the host Node binary is used).

**Notes.**

- failure: Throws when filtered non-dts chunks exceed one; importWithError surfaces module-load errors.

calls: [buildSingleExe](exe-output.md#u-8715ba3f798c), [resolveOutputFileName](exe-output.md#u-3028e8eea5f5), [importWithError](general-and-fs.md#u-6e036190d6a7)

<a id="u-8715ba3f798c"></a>
### `buildSingleExe`

`async function buildSingleExe( config: ResolvedConfig, bundledFile: string, outputFil…` · [src/features/exe.ts:L172-L253][f1]

Builds one SEA executable.

A temp directory hosts sea-config.json, assembled with defaults disableExperimentalSEAWarning: true overridden by exe.seaConfig, then main (the bundled file), output (outDir/outputFile), and mainFormat ('module' for es format, otherwise 'commonjs'); the target executable is set when supplied. The host process.execPath runs --build-sea with stdio ignoring stdout/stderr but inheriting stderr, throwing on failure. The temp dir is always removed in finally unless debug is enabled, in which case it is preserved and logged. For darwin targets (or a darwin host), ad-hoc codesign runs; a signing failure only warns with a manual-command hint on darwin hosts and a different message elsewhere. Finally the output is stat'd and, if present, its size is formatted and logged, followed by a success log with elapsed milliseconds. Returns no value; fs/process errors from --build-sea propagate after cleanup.

**Notes.**

- side_effect: Writes sea-config.json, spawns node --build-sea and possibly codesign, and deletes the temp directory unless debugging.
- condition: Temp directory is preserved when debug.enabled is true.

calls: [fsRemove](general-and-fs.md#u-55a789017e76), [fsStat](general-and-fs.md#u-73b329382a5b), [formatBytes](general-and-fs.md#u-53867d634f8b)

<a id="u-3028e8eea5f5"></a>
### `resolveOutputFileName`

`function resolveOutputFileName( exe: ExeOptions, chunk: RolldownChunk, bundledFile: s…` · [src/features/exe.ts:L145-L170][f1]

Computes the executable file name.

exe.fileName (string, or function of the chunk) overrides the base; otherwise the base is the bundled file name without its extension. The target suffix is appended when present, and '.exe' is appended when the target platform is 'win' or, absent a target, the host platform is win32.

<a id="u-788f5b9b60dc"></a>
### `validateSea`

`export function validateSea({ dts, entry, logger, nameLabel, }: Omit<ResolvedConfig, …` · [src/features/exe.ts:L50-L85][f1]

Validates that the exe option can run in the current environment.

Throws when running under Bun or Deno, when the Node version does not satisfy >=25.7.0, or when more than one entry point is configured (the error lists all entries). Warns (non-fatal) when dts generation is enabled since declarations are not embedded, then always logs that the exe feature is experimental. The destructured config omits 'format', so format is not consulted here.

**Notes.**

- failure: Three throwing conditions: Bun/Deno runtime, Node < 25.7.0, multiple entries.

calls: [createLogger](logging.md#u-44145ce36528)

<a id="u-c67aa232f8ee"></a>
### `ExeOptions`

`export interface ExeOptions extends ExeExtensionOptions` · [src/features/exe.ts:L16-L23][f1]

Exe option shape extending ExeExtensionOptions: optional seaConfig (without main/output/mainFormat) and fileName (string or chunk-to-string function) for the output base name.

<a id="u-a8dcf651b01a"></a>
### `SeaConfig`

`export interface SeaConfig` · [src/features/exe.ts:L30-L46][f1]

Node SEA configuration shape: main, executable, output, mainFormat, warning/snapshot/code-cache toggles, execArgv and its extension mode, and assets.

Defaults differ from Node's per the documented JSDoc.

<a id="u-d97f33e4a6bf"></a>
### `exe.ts module code (L1–L15)`

`module_region` · [src/features/exe.ts:L1-L15][f1]

Imports fs/promises, os, path, process, ansis, obug, dts-filename regex, semver satisfies, tinyexec, and local utils used by the exe feature.

<a id="u-1ee749b795d7"></a>
### `exe.ts module code (L46–L49)`

`module_region` · [src/features/exe.ts:L46-L49][f1]

Creates the 'tsdown:exe' debug logger used by buildExe and buildSingleExe.

<a id="u-af4b8ef25967"></a>
### `exe.ts module code (L23–L29)`

`module_region` · [src/features/exe.ts:L23-L29][f1]

Trailing region of the ExeOptions declaration block; no executable code.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/rolldown/tsdown/blob/2b1be7e0accdb1d6e903cd42642666431fc5e93d/src/features/exe.ts
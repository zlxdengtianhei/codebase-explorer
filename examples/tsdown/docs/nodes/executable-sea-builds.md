# Executable SEA builds

**Capability.** Validates and builds Node SEA executables from output chunks, including naming, signing, and size reporting.

Come here for executable-build options and post-build SEA generation. Units cover validation, temporary sea-config creation, Node build-sea invocation, and executable naming.

**Depends on.**

- [Bundle size reporting](bundle-size-reporting.md) · graph-confirmed · 1 edge(s)
- [Entry and path resolution](entry-and-path-resolution.md) · graph-only · 2 edge(s)
- [Dependency externalization utilities](dependency-externalization-utilities.md) · graph-only · 1 edge(s)

**Depended on by.**

- [Build orchestration lifecycle](build-orchestration-lifecycle.md) · graph-only · 1 edge(s)
- [Config resolution and logging](config-resolution-and-logging.md) · graph-only · 1 edge(s)

Parent: [Executable builds and sizing](executable-builds-and-sizing.md)

## Units (5)

<a id="u-ccebba450bd8"></a>
### `exe.ts-exe-option-types`

`export interface ExeOptions extends ExeExtensionOptions` · [src/features/exe.ts:L16-L23][f1]

Defines executable-build options and the Node SEA configuration passed through.

ExeOptions extends the external exe extension options, allows a partial SEA config without main/output/mainFormat, and lets fileName be a fixed string or a function of the chunk. SeaConfig documents main, executable, output, mainFormat, experimental-warning suppression default true, snapshot default false, code cache default false, execArgv, execArgvExtension default 'env', and assets. The interface comment mentions enabling code cache, but the field's documented default is false.

<a id="u-5ec03dd7b88c"></a>
### `buildExe`

`export async function buildExe( config: ResolvedConfig, chunks: RolldownChunk[], ): P…` · [src/features/exe.ts:L87-L143][f1]

Builds one or more executables from the non-declaration output chunks after a build.

It returns immediately when exe is disabled. It filters out dts chunks, throws if more than one remains, and uses the first chunk to locate the bundled file. With targets, it warns that seaConfig.executable is ignored, dynamically imports the exe helper, resolves each target's Node binary and suffix, and builds each output; without targets it builds one host output. Import, resolution, and build errors propagate.

**Uncertainties.**

- No guard is visible for zero non-dts chunks before the first chunk is read.

<a id="u-8715ba3f798c"></a>
### `buildSingleExe`

`async function buildSingleExe( config: ResolvedConfig, bundledFile: string, outputFil…` · [src/features/exe.ts:L172-L253][f1]

Builds one SEA executable, writes a temporary sea-config.json, runs Node's build-sea, optionally code-signs, and reports size.

It creates a temp directory, merges defaults with seaConfig, forces main/output/mainFormat, and adds executable when supplied. It runs the host Node with --build-sea and throwOnError; the temp directory is removed in finally unless debug is enabled. On darwin target or host it attempts ad-hoc codesign; failure is warned, with manual guidance only on a darwin host and an unsupported-automatic-signing warning otherwise. It then logs size when stat succeeds and always logs success.

**Uncertainties.**

- Whether fsRemove or fsStat failures are caught is not shown; only codesign failure is caught.

<a id="u-3028e8eea5f5"></a>
### `resolveOutputFileName`

`function resolveOutputFileName( exe: ExeOptions, chunk: RolldownChunk, bundledFile: s…` · [src/features/exe.ts:L145-L170][f1]

Computes the executable file name from an explicit name, the bundled file, target suffix, and Windows extension.

A function-valued fileName is called with the chunk; otherwise the bundled file's basename without extension is used. A provided suffix is appended. The .exe suffix is added when the target platform is win, or when no target platform is given and the host is win32. The result is a name, not joined to outDir.

<a id="u-788f5b9b60dc"></a>
### `validateSea`

`export function validateSea({ dts, entry, logger, nameLabel, }: Omit<ResolvedConfig, …` · [src/features/exe.ts:L50-L85][f1]

Validates that the current runtime and config can use the exe feature, throwing before any build work on unsupported cases.

It throws in Bun or Deno, on Node versions below 25.7.0, and when more than one entry is configured. If dts is enabled it warns that declarations will not be included; it always logs that exe is experimental. It returns no value.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/rolldown/tsdown/blob/2b1be7e0accdb1d6e903cd42642666431fc5e93d/src/features/exe.ts

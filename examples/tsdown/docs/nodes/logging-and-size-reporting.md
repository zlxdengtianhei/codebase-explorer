# Logging and size reporting

**Capability.** Provides the leveled logger, color helpers, and per-chunk size reporting (raw, gzip, brotli) printed after builds.

Come here for output formatting: byte-size computation and the report plugin that prints per-file sizes, plus the shared console logger and chunk outDir annotation.

**Depended on by.**

- [Build execution pipeline](build-execution-pipeline.md) · graph-confirmed · 4 edge(s) · 1 inferred relation(s) · The build pipeline uses logging and size reporting to print build output and per-chunk sizes.
- [Configuration loading and resolution](configuration-loading-and-resolution.md) · graph-confirmed · 3 edge(s)
- [Package metadata and utilities](package-metadata-and-utilities.md) · graph-confirmed · 1 edge(s)
- [Single executable builds](single-executable-builds.md) · graph-confirmed · 1 edge(s)
- [Config resolution and normalization](config-resolution-and-normalization.md) · graph-only · 3 edge(s)
- [Rolldown option assembly](rolldown-option-assembly.md) · graph-only · 3 edge(s)
- [Build orchestration and lifecycle](build-orchestration-and-lifecycle.md) · graph-only · 1 edge(s)
- [Package exports generation](package-exports-generation.md) · graph-only · 1 edge(s)

Parent: [tsdown bundling system](tsdown-bundling-system.md)

## Units (9)

<a id="u-437a92d5327f"></a>
### `format.ts-format-helpers`

`export function formatBytes(bytes: number): string | undefined` · [src/utils/format.ts:L1-L7][f1]

formatBytes renders a byte count as a decimal string: Infinity yields undefined, >1,000,000 yields MB with 2 decimals, otherwise kB with 2 decimals.

detectIndentation scans JSON lines for the first indented line; a tab-containing indent returns '\t', otherwise the indent's length; no indented line (or empty input) defaults to 2.

<a id="u-a9c2fa9df395"></a>
### `logger.ts-color-generation`

`export function generateColor(name: string = 'default'): Ansis` · [src/utils/logger.ts:L153-L172][f2]

generateColor returns a cached Ansis color per name: 'default' (or a missing name) is blue; other names are hashed character-by-character (hash = code + (hash<<5) - hash), the hash mod 360 becomes hue with fixed saturation 35 and lightness 55, converted to an RGB color.

hslToRgb implements standard HSL→RGB conversion (achromatic shortcut when saturation is 0, values clamped at 0 and rounded to 0-255); hue2rgb is the per-channel helper with t wrapped into [0,1] and the standard piecewise ramp.

<a id="u-c2b543d550a8"></a>
### `logger.ts-createlogger`

`export function createLogger( level: LogLevel = 'info', options: LoggerOptions = {}, …` · [src/utils/logger.ts:L49-L67][f2]

Builds a leveled console logger.

Options are merged over defaults (allowClearScreen true, failOnWarn false, globalThis.console); if customLogger is provided it is returned verbatim, bypassing all built-in behavior. The internal output() drops messages whose type exceeds the logger's level threshold (silent 0 < error 1 < warn 2 < info 3) and maps info to console.log, warn/error to their same-named methods. info prints a blue ℹ prefix; success prints a green ✔ at info level; warn prints a bgYellow WARN banner and records the formatted message in a module-level warnedMessages set; warnOnce skips messages already in that set (checked before the failOnWarn redirect, so a previously warned message is silently dropped even when failOnWarn is set). With failOnWarn, warn and warnOnce delegate to error instead. error prints a bgRed ERROR banner and sets process.exitCode = 1. clearScreen(type) clears the terminal only when the logger's level is at least the given type's level, and only if allowClearScreen, a TTY stdout, and no CI env var; otherwise clearing is a no-op. The intermediate createLogger overloads and method definitions are parts of this single factory.

<a id="u-d0df71b65f80"></a>
### `logger.ts-logger-internals`

`function format(msgs: any[])` · [src/utils/logger.ts:L35-L37][f2]

format joins message args with spaces, dropping undefined and false values.

clearScreen prints rows-2 newlines (none if non-positive) and uses readline to move the cursor to 0,0 and clear downward; it is only used when clearing is permitted.

<a id="u-8bca55f34fc8"></a>
### `logger.ts-logger-label-formatting`

`export function getNameLabel(ansis: Ansis, name?: string): string | undefined` · [src/utils/logger.ts:L130-L133][f2]

getNameLabel returns an ansis-colored '[name]' string, or undefined when no name is given.

prettyFormat maps a rolldown format to a colored bracketed label: 'es' becomes blue 'ESM', 'cjs' becomes yellow 'CJS', anything else is uppercased and passed through the noop color (uncolored).

<a id="u-162a1329d7a0"></a>
### `report.ts-reportplugin`

`export function ReportPlugin( config: ResolvedConfig, cjsDts?: boolean, isDualFormat?…` · [src/features/report.ts:L60-L67][f3]

Factory for the 'tsdown:report' plugin whose writeBundle resolves the output directory — the parent of outputOptions.file, or outputOptions.dir, both relative to config.cwd — and delegates to outputReport with the bundle contents, cjsDts and isDualFormat flags.

<a id="u-2ceaef0c3bf8"></a>
### `calcSize`

`async function calcSize( options: Required<ReportOptions>, chunk: OutputAsset | Outpu…` · [src/features/report.ts:L158-L195][f3]

Computes raw, gzip, and brotli byte sizes for one chunk (code for chunks, source for assets).

Files larger than maxCompressSize skip compression and keep Infinity sizes (formatted text may be undefined). Otherwise gzip and brotli are computed only when enabled. Also records filename, whether it is a .d.ts file, and whether it is an entry chunk.

<a id="u-abbbe59b5509"></a>
### `outputReport`

`export async function outputReport( config: ResolvedConfig, chunks: Array<OutputAsset…` · [src/features/report.ts:L83-L156][f3]

Prints a per-file size report to config.logger.

Merges config.report over defaults (gzip on, brotli off, maxCompressSize 1MB), computes SizeInfo per chunk via calcSize, pads raw/gzip/brotli text columns to the widest, and sums raw bytes. Sorting: non-dts before dts, entries first, then raw size descending. Each line shows the outDir-relative normalized filename (green for dts, bold for entries), raw size, and gzip/brotli columns only when the corresponding option is on and the text exists; a final line reports file count and total size. In dual-format builds a pretty format label (cjs when cjsDts) prefixes lines.

<a id="u-7a2fdc0e4dc6"></a>
### `addOutDirToChunks`

`export function addOutDirToChunks( chunks: Array<OutputChunk | OutputAsset>, outDir: …` · [src/utils/chunks.ts:L13-L22][f4]

Mutates each rolldown chunk/asset by assigning an `outDir` property and returns the array cast to the augmented chunk type.

Pure side-effect mapping over the input; no filtering or error handling.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/rolldown/tsdown/blob/2b1be7e0accdb1d6e903cd42642666431fc5e93d/src/utils/format.ts
[f2]: https://github.com/rolldown/tsdown/blob/2b1be7e0accdb1d6e903cd42642666431fc5e93d/src/utils/logger.ts
[f3]: https://github.com/rolldown/tsdown/blob/2b1be7e0accdb1d6e903cd42642666431fc5e93d/src/features/report.ts
[f4]: https://github.com/rolldown/tsdown/blob/2b1be7e0accdb1d6e903cd42642666431fc5e93d/src/utils/chunks.ts

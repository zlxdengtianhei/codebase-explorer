# Build Size Reporting

**Capability.** Reports the size of each emitted chunk and asset after bundling, with optional gzip and brotli compression measurements.

Use this subtree to understand the size report output. The tsdown:report plugin hooks write-end and delegates to measurement and formatting helpers.

**Depends on.**

- [General and Filesystem Helpers](general-and-fs.md) · graph-confirmed · 4 edge(s)
- [Logging](logging.md) · graph-confirmed · 1 edge(s)

**Depended on by.**

- [Build Orchestration](build-orchestration.md) · model-inferred · 0 edge(s)
- [Rolldown Options Assembly](rolldown-assembly.md) · graph-only · 1 edge(s)

Parent: [tsdown Build Tool](tsdown.md)

## Units (7)

<a id="u-f9d0cf989188"></a>
### `ReportPlugin`

`export function ReportPlugin( config: ResolvedConfig, cjsDts?: boolean, isDualFormat?…` · [src/features/report.ts:L60-L67][f1]

Creates the 'tsdown:report' plugin, which prints a size report after each bundle is written.

Its writeBundle derives the output directory: when outputOptions.file is set, it resolves config.cwd + file and takes the parent; otherwise it resolves outputOptions.dir (asserted non-null). It then delegates to outputReport with the bundle values, the derived outDir, and the cjsDts/isDualFormat flags for the format label.

calls: [outputReport](reporting.md#u-abbbe59b5509)

**Uncertainties.**

- outputOptions.dir! is assumed present when outputOptions.file is absent; no fallback exists in this code.

<a id="u-2ceaef0c3bf8"></a>
### `calcSize`

`async function calcSize( options: Required<ReportOptions>, chunk: OutputAsset | Outpu…` · [src/features/report.ts:L158-L195][f1]

Measures one output chunk or asset.

Content is chunk.code for chunks or chunk.source for assets; raw size is its UTF-8 byte length. If raw exceeds maxCompressSize, gzip and brotli stay Infinity and compression is skipped; otherwise gzip is measured when options.gzip is true and brotli when options.brotli is true. dts is detected by RE_DTS on the filename, isEntry only for chunks. Uncompressed sizes format via formatBytes (rawText non-null asserted); Infinity yields whatever formatBytes returns for it (normally undefined, so gzipText/brotliText are absent).

calls: [formatBytes](general-and-fs.md#u-53867d634f8b)

**Uncertainties.**

- formatBytes's handling of Infinity lives in src/utils/format.ts and is not visible here.

<a id="u-abbbe59b5509"></a>
### `outputReport`

`export async function outputReport( config: ResolvedConfig, chunks: Array<OutputAsset…` · [src/features/report.ts:L83-L156][f1]

Formats and logs the per-file size report.

Options are the defaults (gzip true, brotli false, maxCompressSize 1MB) merged with config.report. Each chunk is measured by calcSize; column widths are computed from the longest filename and the longest formatted raw/gzip/brotli strings, and all text cells are right-padded. Rows sort with dts files last, entry files first, then by raw size descending. A format label is shown only when isDualFormat (using prettyFormat of 'cjs' when cjsDts, else config.format). Each row logs the dimmed outDir prefix, a colored (green for dts, bold for entries) normalized filename, padded size texts, and conditional gzip/brotli columns; a final line logs the file count and total raw bytes.

calls: [calcSize](reporting.md#u-2ceaef0c3bf8), [formatBytes](general-and-fs.md#u-53867d634f8b), [prettyFormat](logging.md#u-9a73f5293780)

**Uncertainties.**

- With zero chunks, Math.max(...[]) yields -Infinity for the width computations; behavior in that degenerate case is not guarded here.

<a id="u-4dc00cd421bf"></a>
### `ReportOptions`

`export interface ReportOptions` · [src/features/report.ts:L30-L52][f1]

Report option interface (gzip default true, brotli default false, maxCompressSize default 1MB) with the caveat that compressing large files is slow.

<a id="u-2552366fe692"></a>
### `SizeInfo`

`interface SizeInfo` · [src/features/report.ts:L18-L28][f1]

Per-file measurement record: filename, dts/isEntry flags, raw/gzip/brotli byte counts, and padded display texts.

<a id="u-85f8733dbcde"></a>
### `report.ts module code (L1–L17)`

`module_region` · [src/features/report.ts:L1-L17][f1]

Module imports plus the tsdown:report debug logger and promisified zlib gzip/brotli compress helpers.

<a id="u-7491c3f2012d"></a>
### `report.ts module code (L52–L59)`

`module_region` · [src/features/report.ts:L52-L59][f1]

defaultOptions constant for report: gzip true, brotli false, maxCompressSize 1_000_000.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/rolldown/tsdown/blob/2b1be7e0accdb1d6e903cd42642666431fc5e93d/src/features/report.ts
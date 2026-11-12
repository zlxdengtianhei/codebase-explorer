# Bundle size reporting

**Capability.** Computes and logs bundle sizes, including gzip and brotli, and formats byte counts for reports.

Use this module for post-output size reports and byte formatting. Units cover report plugin creation, per-file size calculation, output directory selection, and logging.

**Depends on.**

- [Config resolution and logging](config-resolution-and-logging.md) · graph-only · 1 edge(s)

**Depended on by.**

- [Executable SEA builds](executable-sea-builds.md) · graph-confirmed · 1 edge(s)
- [Package export map generation](package-export-map-generation.md) · graph-only · 1 edge(s)
- [Rolldown option assembly](rolldown-option-assembly.md) · graph-only · 1 edge(s)

Parent: [Executable builds and sizing](executable-builds-and-sizing.md)

## Units (5)

<a id="u-437a92d5327f"></a>
### `format.ts-format-helpers`

`export function formatBytes(bytes: number): string | undefined` · [src/utils/format.ts:L1-L7][f1]

Formats byte counts: Infinity returns undefined; values greater than 1,000,000 use MB with two decimals; all other values, including exactly 1,000,000, use kB with two decimals.

Infers indentation from the first line with leading whitespace followed by a non-whitespace character: a tab in that whitespace returns a tab character, otherwise the whitespace length is returned; no matching line returns 2.

<a id="u-5407fbea872b"></a>
### `report.ts-reportplugin-factory`

`export function ReportPlugin( config: ResolvedConfig, cjsDts?: boolean, isDualFormat?…` · [src/features/report.ts:L60-L67][f2]

Creates the report plugin that writes a size report after bundle output.

It returns a plugin whose writeBundle computes the output directory from the file or dir option and calls the report writer with the bundle values, cjsDts, and dual-format flag. It does not format or log sizes itself.

<a id="u-2ceaef0c3bf8"></a>
### `calcSize`

`async function calcSize( options: Required<ReportOptions>, chunk: OutputAsset | Outpu…` · [src/features/report.ts:L158-L195][f2]

Computes raw, gzip, and brotli sizes for one output chunk or asset.

Content is chunk code for chunks and source for assets; raw size is UTF-8 byte length. If raw exceeds maxCompressSize, compression is skipped and compressed sizes stay Infinity. Otherwise gzip and brotli are computed only when enabled. The result records filename, dts detection, entry status, raw size, and formatted size text.

<a id="u-abbbe59b5509"></a>
### `outputReport`

`export async function outputReport( config: ResolvedConfig, chunks: Array<OutputAsset…` · [src/features/report.ts:L83-L156][f2]

Formats and logs per-file and total bundle sizes, optionally with gzip and brotli.

It makes the output directory relative to cwd, merges report defaults, calculates every chunk size, and pads size text columns. Files sort with dts last, entries first, then raw size descending. Each line logs the relative directory, colored filename, raw size, and enabled compressed sizes. A final line logs file count and total raw size. A dual-format label is added only when requested.

<a id="u-595b690939bb"></a>
### `ReportPlugin.writeBundle`

`async writeBundle(outputOptions, bundle)` · [src/features/report.ts:L67-L79][f2]

Computes the report output directory and invokes the report writer after bundle output.

If a file option exists, its parent directory is used; otherwise the dir option is resolved against the config cwd. Missing both makes path resolution fail. The bundle values and format flags are passed through.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/rolldown/tsdown/blob/2b1be7e0accdb1d6e903cd42642666431fc5e93d/src/utils/format.ts
[f2]: https://github.com/rolldown/tsdown/blob/2b1be7e0accdb1d6e903cd42642666431fc5e93d/src/features/report.ts

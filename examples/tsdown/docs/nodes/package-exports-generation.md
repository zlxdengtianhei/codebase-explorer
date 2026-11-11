# Package exports generation

**Capability.** Computes and writes package.json export fields (main, module, types, exports) from build chunks, honoring dev, wildcard, and exclusion options.

Come here for how output chunks are turned into package.json exports entries and written back to disk. Includes export-name derivation, path joining, types detection, and CSS asset exports.

**Depends on.**

- [Dependency handling and general utilities](dependency-handling-and-general-utilities.md) · graph-confirmed · 7 edge(s) · Exports generation uses shared dependency and general utilities for path and pattern handling.
- [Entry resolution and filesystem helpers](entry-resolution-and-filesystem-helpers.md) · graph-only · 1 edge(s)
- [Logging and size reporting](logging-and-size-reporting.md) · graph-only · 1 edge(s)

**Depended on by.**

- [Package lint checks](package-lint-checks.md) · graph-confirmed · 1 edge(s) · Package lint checks use exports generation while coordinating per-package post-build work.
- [Config resolution and normalization](config-resolution-and-normalization.md) · graph-only · 1 edge(s)

Parent: [Package metadata and utilities](package-metadata-and-utilities.md)

## Units (10)

<a id="u-04a90067f931"></a>
### `exportCss`

`function exportCss( exports: Record<string, any>, chunks: ChunksByFormat, css: { spli…` · [src/features/pkg/exports.ts:L353-L370][f1]

Adds a single CSS asset export unless css.splitting is enabled.

Scans all chunks in every format for the first asset whose file name matches the CSS pattern, then maps './<file>' to its outDir-relative path; returns after the first match.

calls: [slash](../../catalog.json)

<a id="u-22adfbe936a8"></a>
### `exportMeta`

`function exportMeta( exports: Record<string, any>, all?: boolean, packageJson?: boole…` · [src/features/pkg/exports.ts:L341-L351][f1]

Adds a wildcard export './*' → './*' when all is set, otherwise './package.json' → './package.json' when packageJson is set; does nothing otherwise.

<a id="u-dd2b18ee85fd"></a>
### `genSubExport`

`function genSubExport( devExports: string | boolean | undefined, { src, es, cjs }: Su…` · [src/features/pkg/exports.ts:L317-L339][f1]

Renders one sub-export value.

With devExports === true it returns the raw src path. Otherwise, a single-format export without a dev condition collapses to its cjs or es path; dual-format or dev-condition exports become an object with the custom condition pointing at src (when devExports is a string) and import/require keys for dual format, or a single default key otherwise.

<a id="u-65ca0aa4a406"></a>
### `generateExports`

`export async function generateExports( pkg: PackageJson, chunks: ChunksByFormat, opti…` · [src/features/pkg/exports.ts:L143-L315][f1]

Computes the package.json export fields (main, module, types, exports, inlinedDependencies, publishExports) from build chunks.

Warns if chunks contain neither cjs nor es formats. legacy defaults to false only when the build is pure ESM. For each es/cjs format it filters chunks to code entries (non-entries kept only when all is on and their facade module is neither virtual (\0-prefixed) nor from node_modules), dropping names matching exclude. A single non-dts entry (or one named index) becomes the root export '.', setting main (cjs) or module (es) and the corresponding types slot; 'x/index' names become './x'; others './name'. Each export accumulates per-format dist paths and a src path from the facade module. Exports are sorted with 'index' first, then alphabetically, and rendered via genSubExport; exportMeta adds './*' or './package.json'; exportCss adds a CSS asset export unless css.splitting is on. customExports is merged in (object) or awaited with the exports and context (function, isPublish false). When devExports is truthy, a parallel publishExports map is built the same way but with genSubExport(false, ...) and isPublish true. Returns main/module/types only when legacy (falling back to existing pkg fields), types otherwise preserving pkg.types, exports, inlinedDependencies only when emission is enabled, and publishExports.

calls: [genSubExport](../../catalog.json), [exportMeta](../../catalog.json), [exportCss](../../catalog.json), [getExportName](../../catalog.json), [shouldExclude](../../catalog.json)

**Uncertainties.**

- Behavior of matchPattern (glob vs regex semantics) is defined outside this file.

<a id="u-55d786ea558e"></a>
### `getExportName`

`function getExportName( chunk: RolldownCodeChunk, ): [name: string, normalizedName: s…` · [src/features/pkg/exports.ts:L402-L414][f1]

Derives an export name from a chunk: slash-normalizes the file name, strips the extension, and detects .d files by the remaining '.d' suffix, trimming it; returns [name, originalFileName, isDts].

calls: [stripExtname](../../catalog.json)

<a id="u-44615f0e8dc9"></a>
### `hasExportsTypes`

`export function hasExportsTypes(pkg?: PackageJson): boolean` · [src/features/pkg/exports.ts:L372-L400][f1]

Reports whether a package.json exports field advertises types: false when exports is missing, an array, or non-object; true when a top-level 'types' key exists or when the '.' entry is an object containing 'types'.

<a id="u-70c06da6dd04"></a>
### `join`

`function join(pkgRoot: string, outDir: string, fileName: string)` · [src/features/pkg/exports.ts:L416-L419][f1]

Joins a chunk's output path into a package-relative export path: computes the slash-normalized outDir relative to pkgRoot, prefixing './' when non-empty or '.' otherwise, then appends the file name.

<a id="u-a5ef8a9e5562"></a>
### `shouldExclude`

`function shouldExclude( fileName: string, exclude?: (RegExp | string)[], ): boolean` · [src/features/pkg/exports.ts:L135-L141][f1]

Returns whether a chunk export name matches any of the exclude patterns; false when the exclude list is absent or empty.

calls: [matchPattern](../../catalog.json)

<a id="u-6b2cf5a6af2b"></a>
### `writeExports`

`export async function writeExports( options: ResolvedConfig, chunks: ChunksByFormat, …` · [src/features/pkg/exports.ts:L99-L131][f1]

Writes generated export fields back into package.json on disk.

Asserts options.pkg exists, calls generateExports to get main/module/types/exports/inlinedDependencies plus optional publishExports, and merges them into the package object (clearing packageJsonPath so it is not serialized). If publishExports is present, stores it under publishConfig.exports, creating publishConfig if needed. Reads the original file, re-serializes with the detected indentation, preserves a trailing newline, and writes only when the content actually changed.

calls: [generateExports](../../catalog.json), [detectIndentation](../../catalog.json)

<a id="u-910af185da4f"></a>
### `ExportsOptions`

`export interface ExportsOptions` · [src/features/pkg/exports.ts:L16-L97][f1]

Options interface controlling package.json exports generation: devExports (boolean or custom condition string) to point exports at source in dev, packageJson (default true) to expose ./package.json, all to export every chunk, exclude patterns (glob or RegExp, no extensions, relative to dist), legacy main/module generation (default false for pure ESM, true otherwise), customExports as a static record or an async-capable function receiving exports plus pkg/chunks/isPublish context, and inlinedDependencies (default true) to emit the inlined-dependency list.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/rolldown/tsdown/blob/2b1be7e0accdb1d6e903cd42642666431fc5e93d/src/features/pkg/exports.ts

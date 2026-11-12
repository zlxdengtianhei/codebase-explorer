# Package export map generation

**Capability.** Builds package.json export maps, legacy fields, CSS and inlined-dependency metadata, and writes changed package metadata.

Use this module when package exports, types entries, exclusions, or package.json metadata must be derived from built chunks. It also includes a comma-splitting utility used by export processing.

**Depends on.**

- [Dependency externalization utilities](dependency-externalization-utilities.md) · graph-confirmed · 3 edge(s)
- [Bundle size reporting](bundle-size-reporting.md) · graph-only · 1 edge(s)
- [Entry and path resolution](entry-and-path-resolution.md) · graph-only · 1 edge(s)

**Depended on by.**

- [Dependency externalization utilities](dependency-externalization-utilities.md) · graph-confirmed · 3 edge(s)
- [Package tarball validation](package-tarball-validation.md) · graph-confirmed · 2 edge(s)
- [Config resolution and logging](config-resolution-and-logging.md) · graph-only · 3 edge(s)
- [Config file loading](config-file-loading.md) · graph-only · 2 edge(s)
- [Entry and path resolution](entry-and-path-resolution.md) · graph-only · 2 edge(s)
- [Build orchestration lifecycle](build-orchestration-lifecycle.md) · graph-only · 1 edge(s)
- [CLI entry and debug](cli-entry-and-debug.md) · graph-only · 1 edge(s)
- [Copy shortcuts target helpers](copy-shortcuts-target-helpers.md) · graph-only · 1 edge(s)
- [Watch set and chunks](watch-set-and-chunks.md) · graph-only · 1 edge(s)

Parent: [Package output and validation](package-output-and-validation.md)

## Units (9)

<a id="u-a7cb65e5ed45"></a>
### `exports.ts-export-path-helpers`

`function getExportName( chunk: RolldownCodeChunk, ): [name: string, normalizedName: s…` · [src/features/pkg/exports.ts:L402-L414][f1]

Derives export names from chunk file names and builds package-root-relative export paths.

- The name helper slash-normalizes the file name, strips the extension, marks names ending in '.d' as declaration files, and removes that suffix from the returned name. Its second return value is the slash-normalized file name, not the original file name.
- The path helper computes the out directory relative to the package root, slash-normalizes it, prefixes './' when nonempty or '.' when empty, and appends the file name. The result is relative to the package root.

<a id="u-777d632bd290"></a>
### `general.ts-general-value-helpers`

`export function resolveComma<T extends string>(arr: T[]): T[]` · [src/utils/general.ts:L18-L20][f2]

Splits every string element on commas and flattens the results, preserving empty segments.

Converts a string to a regular expression only when it is longer than two characters and starts and ends with a slash; the inner text is passed to the RegExp constructor without flags, and all other values are returned unchanged. Replaces every backslash with a forward slash. The identity callback returns its argument unchanged.

<a id="u-04a90067f931"></a>
### `exportCss`

`function exportCss( exports: Record<string, any>, chunks: ChunksByFormat, css: { spli…` · [src/features/pkg/exports.ts:L353-L370][f1]

Adds the first CSS asset to the export map unless CSS splitting is enabled.

- If splitting is true, no change.
- Otherwise scans chunks in order and exports the first asset whose file name matches the CSS pattern under './<slash-normalized filename>'.
- The export value is built from the package root, out directory, and filename, so it is package-root-relative rather than outDir-relative.
- Only the first matching CSS asset is added.

<a id="u-22adfbe936a8"></a>
### `exportMeta`

`function exportMeta( exports: Record<string, any>, all?: boolean, packageJson?: boole…` · [src/features/pkg/exports.ts:L341-L351][f1]

Adds wildcard or package.json metadata entries to an export map.

When all is true it sets './*' to './*'; otherwise when packageJson is true it sets './package.json' to './package.json'. The all branch wins when both are true.

<a id="u-dd2b18ee85fd"></a>
### `genSubExport`

`function genSubExport( devExports: string | boolean | undefined, { src, es, cjs }: Su…` · [src/features/pkg/exports.ts:L317-L339][f1]

Shapes one export entry according to devExports and available CJS/ESM targets.

- devExports true returns the source target directly, even if it is undefined.
- With no dual format and no devExports, returns the CJS or ESM string.
- Otherwise returns an object: a string devExports adds a custom condition pointing at the source target; ESM adds import when dual-format else default; CJS adds require when dual-format else default.

<a id="u-65ca0aa4a406"></a>
### `generateExports`

`export async function generateExports( pkg: PackageJson, chunks: ChunksByFormat, opti…` · [src/features/pkg/exports.ts:L143-L315][f1]

Builds package.json export maps, legacy fields, CSS and inlined-dependency metadata from built chunks.

- Warns when chunks contain neither CJS nor ESM formats.
- Legacy output defaults to true unless the only format is ESM.
- Only CJS and ESM chunks are processed. Non-entry chunks are included only when all is true; then chunks whose facade module id starts with NUL or matches node_modules are skipped. Excluded names are filtered out.
- If exactly one non-declaration chunk remains for a format, every chunk in that format is treated as an index entry. Otherwise a name of index becomes '.', a name ending in /index becomes its parent path, and other names get a './' prefix.
- For index entries, CJS declarations set CJS types, CJS code sets main, ESM declarations set ESM types, and ESM code sets module.
- Non-declaration chunks set the format target and, when a facade module id exists and no source target is set, add a package-root-relative source path.
- Export keys are '.' or './...'; the comparator's index special case never matches, so all keys are ordered by localeCompare.
- Metadata adds './*' when all is true, otherwise './package.json' when packageJson is true.
- Object custom exports are spread after generated exports; function custom exports are awaited and may replace the map, with isPublish false for the main map and true for publish exports.
- Publish exports are built only when devExports is truthy, using the same metadata, CSS, and custom-export steps with dev exports disabled.
- Legacy fields are returned only when legacy is true, with fallbacks to the other format and then the original package fields; when legacy is false main/module are undefined and types is the original package types. Inlined dependencies are included only when enabled.

<a id="u-44615f0e8dc9"></a>
### `hasExportsTypes`

`export function hasExportsTypes(pkg?: PackageJson): boolean` · [src/features/pkg/exports.ts:L372-L400][f1]

Checks whether package exports declare a types entry at the root or under the main export.

- No exports: false.
- A non-array object with a types key: true.
- A non-array object with a '.' key whose value is a non-null object containing types: true.
- Arrays, strings, and other shapes: false.

<a id="u-a5ef8a9e5562"></a>
### `shouldExclude`

`function shouldExclude( fileName: string, exclude?: (RegExp | string)[], ): boolean` · [src/features/pkg/exports.ts:L135-L141][f1]

Decides whether a file name matches any configured exclusion pattern.

With no patterns it returns false; otherwise it delegates to pattern matching.

<a id="u-6b2cf5a6af2b"></a>
### `writeExports`

`export async function writeExports( options: ResolvedConfig, chunks: ChunksByFormat, …` · [src/features/pkg/exports.ts:L99-L131][f1]

Generates package export fields, merges them into package.json, and writes the file only when content changes.

- The package metadata is asserted present, then generated fields and optional publish exports are merged over the original package object with the package-json path removed.
- When publish exports exist, publishConfig is created if needed and its exports field is replaced.
- The original file is read, indentation is detected, and a trailing newline is preserved when the original had one.
- The file is written only if the serialized content differs from the original.

Look up code: the commands are under "Read further" in [INDEX.md](../INDEX.md); `cbe query` and `cbe source` take a unit title or anchor from this page.

[f1]: https://github.com/rolldown/tsdown/blob/2b1be7e0accdb1d6e903cd42642666431fc5e93d/src/features/pkg/exports.ts
[f2]: https://github.com/rolldown/tsdown/blob/2b1be7e0accdb1d6e903cd42642666431fc5e93d/src/utils/general.ts

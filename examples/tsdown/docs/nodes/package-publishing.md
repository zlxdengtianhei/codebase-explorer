# Package Publishing

**Capability.** Coordinates per-package completion: generates and writes package.json exports fields, and runs publish checks (publint, are-the-types-wrong) against the packed tarball.

Use this subtree to understand what tsdown writes into package.json and how publish-readiness checks are executed. It buffers bundles until all configs for a package finish, then runs exports, publint, and attw once per package.

**Depends on.**

- [General and Filesystem Helpers](general-and-fs.md) · graph-confirmed · 15 edge(s) · Publishing uses fs removal, indentation detection, and path helpers when writing exports and packing tarballs.
- [Logging](logging.md) · graph-confirmed · 2 edge(s)

**Depended on by.**

- [Build Orchestration](build-orchestration.md) · graph-confirmed · 4 edge(s) · After all configs for a package finish, orchestration triggers package publishing (exports, publint, attw).
- [Entry Resolution](entry-resolution.md) · model-inferred · 0 edge(s)
- [Dependency Externalization](externalization.md) · graph-confirmed · 2 edge(s)
- [User Config Normalization](config-merging.md) · graph-only · 1 edge(s)
- [General and Filesystem Helpers](general-and-fs.md) · graph-only · 1 edge(s)

Parent: [tsdown Build Tool](tsdown.md)

## Units (17)

<a id="u-a3955ba81d03"></a>
### `bundleDone`

`export async function bundleDone( bundleByPkg: BundleByPkg, bundle: TsdownBundle, ): …` · [src/features/pkg/index.ts:L49-L112][f1]

Coordinates per-package completion: buffers bundles until all expected bundles for the package arrived, then emits exports, publint, and attw once.

**Notes.**

- condition: Bundles before the last one return the shared pending promise; the final bundle triggers all work then resolves it.
- failure: More than one distinct exports config throws a descriptive Error listing formatted options; publint/attw work still run in that case? No — the throw aborts before them.
- failure: Pack/publint/attw errors are caught and logged via configs[0].logger.error; ctx.resolve() still runs afterward.
- condition: Multiple distinct publint or attw configs only warn (via publintConfigs[1].logger) but all are still executed against one tarball.

calls: [writeExports](package-publishing.md#u-6b2cf5a6af2b), [publint](package-publishing.md#u-f3ab9c1c8af3), [attw](package-publishing.md#u-17466036fb34), [packTarball](package-publishing.md#u-ecb7dfeaef07), [dedupeConfigs](package-publishing.md#u-bad4077ee69a), [mergeInlinedDeps](package-publishing.md#u-544ed4bb2928)

**Uncertainties.**

- If only publintConfigs (not attwConfigs) is non-empty and length > 1, the warning still references publintConfigs[1]; if publintConfigs is empty but attwConfigs has >1, publintConfigs[1] is undefined and would throw — the condition `publintConfigs.length > 1 || attwConfigs.length > 1` does not guard which array is indexed.

<a id="u-bad4077ee69a"></a>
### `dedupeConfigs`

`function dedupeConfigs<K extends 'publint' | 'attw' | 'exports'>( configs: Array<Reso…` · [src/features/pkg/index.ts:L139-L162][f1]

Filters configs that enabled a given feature (exports/publint/attw), dropping configs whose option object is empty or reference-equal to an already-seen one; if everything was dropped it still returns the first enabling config.

**Notes.**

- condition: Dedup relies on object identity (Set.has(config[key])), not deep equality; distinct-but-equal option objects both survive.

<a id="u-37c1dfe4abb3"></a>
### `initBundleByPkg`

`export function initBundleByPkg(configs: ResolvedConfig[]): BundleByPkg` · [src/features/pkg/index.ts:L24-L47][f1]

Groups resolved configs by their package.json path, creating per-package bookkeeping (pending promise, bundle count, format set) for later coordination in bundleDone.

Configs without a package.json are skipped entirely.

calls: [promiseWithResolvers](general-and-fs.md#u-19569223bc83)

<a id="u-544ed4bb2928"></a>
### `mergeInlinedDeps`

`function mergeInlinedDeps( bundles: TsdownBundle[], ): Record<string, string | string…` · [src/features/pkg/index.ts:L164-L186][f1]

Merges inlined dependency versions across bundles into {name: version|sortedVersions}, returning undefined when nothing was inlined.

Single versions collapse to a string; multiple become a sorted array.

<a id="u-ecb7dfeaef07"></a>
### `packTarball`

`async function packTarball( packageJsonPath: string, ): Promise<Buffer<ArrayBuffer>>` · [src/features/pkg/index.ts:L114-L137][f1]

Packs the package directory into an npm-style tarball in a fresh temp dir, returning its bytes, always removing the temp dir afterward.

**Notes.**

- failure: Deno projects (detect().name === 'deno') raise an Error; detect failures pass packageManager: undefined.
- side_effect: Dynamically imports package-manager-detector/detect and @publint/pack concurrently; temp dir cleanup runs even on failure.

calls: [fsRemove](general-and-fs.md#u-55a789017e76)

<a id="u-65ca0aa4a406"></a>
### `generateExports`

`export async function generateExports( pkg: PackageJson, chunks: ChunksByFormat, opti…` · [src/features/pkg/exports.ts:L143-L315][f2]

Builds the package exports map, legacy main/module/types fields, and optional publish-time exports from bundled chunks.

**Notes.**

- condition: Chunks of formats other than es/cjs are skipped; entry-only chunks unless `all`, and even with `all`, virtual (\0) and node_modules facade modules are dropped; `exclude` filters by export name.
- condition: A chunk becomes the '.' export when it is the single non-dts entry or named 'index'; then main/module/cjsTypes/esmTypes are assigned by format; names ending in '/index' lose that suffix.
- condition: legacy defaults to true unless the build is pure ESM; returned main falls back module→pkg.main and types falls back cjsTypes→esmTypes→pkg.types.
- condition: devExports=true routes every export to source and puts dist exports in publishExports; a string devExports adds that custom condition in genSubExport.
- side_effect: customExports object merges over generated exports; a function form is awaited with isPublish=false for the dev map and true for publishExports.

calls: [getExportName](package-publishing.md#u-55d786ea558e), [genSubExport](package-publishing.md#u-dd2b18ee85fd), [exportMeta](package-publishing.md#u-22adfbe936a8), [exportCss](package-publishing.md#u-04a90067f931)

**Uncertainties.**

- Sorting places a literal 'index' key first via `a === 'index'`, but keys are prefixed ('./index' etc.) elsewhere; whether an unprefixed 'index' key can occur is not provable here.
- inlinedDependencies output reflects the passed map verbatim when enabled; its shape is set by mergeInlinedDeps.

<a id="u-6b2cf5a6af2b"></a>
### `writeExports`

`export async function writeExports( options: ResolvedConfig, chunks: ChunksByFormat, …` · [src/features/pkg/exports.ts:L99-L131][f2]

Writes generated package.json exports back to disk, preserving indentation and publishing-only exports.

**Notes.**

- side_effect: Reads the original package.json, rewrites it synchronously only when serialized content differs; a trailing newline is preserved.
- contract: publishExports from generateExports is moved into updatedPkg.publishConfig.exports; packageJsonPath is stripped from the written object.

calls: [generateExports](package-publishing.md#u-65ca0aa4a406), [detectIndentation](general-and-fs.md#u-0851d0845062)

**Uncertainties.**

- typeAssert(options.pkg) throwing behavior depends on src/utils/general.ts, not shown here.

<a id="u-dd2b18ee85fd"></a>
### `genSubExport`

`function genSubExport( devExports: string | boolean | undefined, { src, es, cjs }: Su…` · [src/features/pkg/exports.ts:L317-L339][f2]

Converts one {src, es, cjs} record into an exports value: devExports===true yields the src path; a single-format non-dev build yields the bare path; otherwise a conditions object where dual formats use import/require and single-format es or cjs uses default, optionally adding a string-named dev condition first.

**Notes.**

- condition: When devExports===true the code returns src! without a null check; a missing src would produce undefined.

<a id="u-04a90067f931"></a>
### `exportCss`

`function exportCss( exports: Record<string, any>, chunks: ChunksByFormat, css: { spli…` · [src/features/pkg/exports.ts:L353-L370][f2]

Adds the first CSS asset chunk as an exports entry unless CSS splitting is enabled, mapping './<file>' to its dist path and stopping after the first match.

**Notes.**

- side_effect: Mutates the passed exports object; only the first CSS asset found across all formats is exported.

calls: [slash](general-and-fs.md#u-9bf13c522663)

<a id="u-22adfbe936a8"></a>
### `exportMeta`

`function exportMeta( exports: Record<string, any>, all?: boolean, packageJson?: boole…` · [src/features/pkg/exports.ts:L341-L351][f2]

Adds wildcard or package.json meta entries to an exports map: './*': './*' when `all` is set, else './package.json' when packageJson is enabled; both false leaves the map unchanged.

<a id="u-55d786ea558e"></a>
### `getExportName`

`function getExportName( chunk: RolldownCodeChunk, ): [name: string, normalizedName: s…` · [src/features/pkg/exports.ts:L402-L414][f2]

Derives an export name from a chunk file name by stripping the extension and detecting a trailing '.d' (declaration) marker.

calls: [stripExtname](general-and-fs.md#u-fc10eca7c52b)

<a id="u-44615f0e8dc9"></a>
### `hasExportsTypes`

`export function hasExportsTypes(pkg?: PackageJson): boolean` · [src/features/pkg/exports.ts:L372-L400][f2]

Reports whether a package.json exports field declares a types condition, checking exports.types and the '.' subpath's types.

Non-object exports, arrays, or a missing exports field return false; string values of exports['.'] do not count.

**Uncertainties.**

- String shorthand exports (e.g. exports: './index.js') can never have a types key, hence false — intentional per code but worth noting as a limit.

<a id="u-70c06da6dd04"></a>
### `join`

`function join(pkgRoot: string, outDir: string, fileName: string)` · [src/features/pkg/exports.ts:L416-L419][f2]

Joins a package root, out directory, and file name into a './'-prefixed exports path; an outDir equal to the package root yields './<fileName>'.

calls: [slash](general-and-fs.md#u-9bf13c522663)

<a id="u-a5ef8a9e5562"></a>
### `shouldExclude`

`function shouldExclude( fileName: string, exclude?: (RegExp | string)[], ): boolean` · [src/features/pkg/exports.ts:L135-L141][f2]

Returns true when the file name matches any exclude pattern; an empty or missing pattern list means nothing is excluded.

calls: [matchPattern](general-and-fs.md#u-f95494f1507b)

<a id="u-17466036fb34"></a>
### `attw`

`export async function attw( options: ResolvedConfig, tarball: Buffer<ArrayBuffer>, ):…` · [src/features/pkg/attw.ts:L95-L166][f3]

Runs are-you-typed checks on the built tarball when attw is configured, logging problems per profile/ignore rules.

**Notes.**

- side_effect: Logs via options.logger; reports elapsed time on success via performance.now().
- failure: importWithError failures propagate; unknown ignoreRules only warn, they do not abort.

calls: [importWithError](general-and-fs.md#u-6e036190d6a7), [formatProblem](package-publishing.md#u-50180c862a03)

**Uncertainties.**

- Whether checkPackage can reject for malformed tarballs is not shown; such errors would propagate to the caller.

<a id="u-50180c862a03"></a>
### `formatProblem`

`function formatProblem(packageName: string, problem: Problem): string` · [src/features/pkg/attw.ts:L171-L227][f3]

Renders one ATTW problem as an indented, emoji-prefixed human-readable string; each ProblemKind gets its own template and the default case JSON-stringifies unknown kinds.

Entry-point and resolution-kind suffixes are only appended when those fields exist on the problem; entrypoint paths are joined with the package name and slashed.

**Uncertainties.**

- The 'UnexpectedModuleSyntax' branch maps syntax === 99 to 'ESM' and anything else to 'CJS'; other numeric codes are unverified against @arethetypeswrong/core enums.

<a id="u-f3ab9c1c8af3"></a>
### `publint`

`export async function publint( options: ResolvedConfig, tarball: Buffer<ArrayBuffer>,…` · [src/features/pkg/publint.ts:L16-L63][f4]

Lints the packed tarball with publint when enabled, logging each issue at a level mapped from its type.

**Notes.**

- condition: Message types map error→error, warning→warn, suggestion→info on options.logger.
- side_effect: Success path logs elapsed time; errors from dynamic imports or publint propagate to the caller (bundleDone catches pack-stage errors).

calls: [importWithError](general-and-fs.md#u-6e036190d6a7)

**Uncertainties.**

- formatMessage is called with options.pkg as the second argument; whether that overload produces package-relative messages depends on publint's API, not shown here.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/rolldown/tsdown/blob/2b1be7e0accdb1d6e903cd42642666431fc5e93d/src/features/pkg/index.ts
[f2]: https://github.com/rolldown/tsdown/blob/2b1be7e0accdb1d6e903cd42642666431fc5e93d/src/features/pkg/exports.ts
[f3]: https://github.com/rolldown/tsdown/blob/2b1be7e0accdb1d6e903cd42642666431fc5e93d/src/features/pkg/attw.ts
[f4]: https://github.com/rolldown/tsdown/blob/2b1be7e0accdb1d6e903cd42642666431fc5e93d/src/features/pkg/publint.ts
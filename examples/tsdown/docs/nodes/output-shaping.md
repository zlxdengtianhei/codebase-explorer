# Output File Naming and Formats

**Capability.** Resolves chunk filename templates, JS extensions from package type and format, and banner/footer addons, and warns about legacy CJS targets.

Use this subtree to understand how emitted files are named and which extensions they get. Format and CJS-compatibility concerns that affect emitted artifacts are grouped here.

**Depends on.**

- [Package Metadata Helpers](package-metadata.md) · graph-confirmed · 1 edge(s) · Chunk filename resolution reads the package module type to pick JS extensions.

**Depended on by.**

- [Build Orchestration](build-orchestration.md) · graph-confirmed · 1 edge(s)
- [Rolldown Options Assembly](rolldown-assembly.md) · graph-confirmed · 3 edge(s) · resolveOutputOptions uses output shaping for chunk filename templates and banner/footer addons.

Parent: [tsdown Build Tool](tsdown.md)

## Units (13)

<a id="u-b521ce5719c7"></a>
### `resolveChunkAddon`

`export function resolveChunkAddon( chunkAddon: ChunkAddon | undefined, format: Normal…` · [src/features/output.ts:L101-L130][f1]

Wraps the banner/footer addon option into a Rolldown AddonFunction; undefined input returns undefined.

At render time a function addon is invoked once with { format, fileName } and its result (object, string, or undefined) replaces the addon for the rest of the call. A string result is returned verbatim. Otherwise the file name decides the key: RE_JS files use .js, RE_CSS files use .css, RE_DTS files use .dts, each defaulting to '' when absent; unmatched files get ''.

**Uncertainties.**

- A function addon is re-invoked for every chunk since the memoized result only lives within one invocation.

<a id="u-fa191ddae689"></a>
### `resolveChunkFilename`

`export function resolveChunkFilename( { outExtensions, fixedExtension, pkg, hash }: R…` · [src/features/output.ts:L44-L76][f1]

Produces entry and chunk filename templates for a format.

It reads the package type via getPackageType, then lets a configured outExtensions factory override the js and dts extensions (a falsy factory result is ignored). The js extension defaults to '.' plus resolveJsOutputExtension(packageType, format, fixedExtension). An iife/umd format adds '.<format>' to basenames, and a hash adds '-[hash]' to the chunk template only. It returns [entry, chunk] via createChunkFilename, which returns a plain string when no dts extension is set, or a per-chunk function that swaps in the dts extension for files whose name ends with '.d'.

calls: [getPackageType](package-metadata.md#u-f900f56cf2b7), [resolveChunkFilename](output-shaping.md#u-fa191ddae689)

<a id="u-61ab17605f5c"></a>
### `resolveJsOutputExtension`

`function resolveJsOutputExtension( packageType: PackageType, format: NormalizedFormat…` · [src/features/output.ts:L29-L42][f1]

Chooses the JS file extension from package type and format.

For 'es': 'js' when fixedExtension is off and the package is type module, otherwise 'mjs'. For 'cjs': 'cjs' when fixedExtension is on or the package is type module, otherwise 'js'. Any other format yields 'js'.

<a id="u-baea103aecc3"></a>
### `ChunkAddonObject`

`export interface ChunkAddonObject` · [src/features/output.ts:L90-L94][f1]

Per-file-type addon strings keyed by js, css, dts.

<a id="u-8e6d8b5d8b36"></a>
### `OutExtensionContext`

`export interface OutExtensionContext` · [src/features/output.ts:L15-L20][f1]

Context passed to outExtensions factories: input options, format, and optional package.json type.

<a id="u-ffe4895c5c63"></a>
### `OutExtensionObject`

`export interface OutExtensionObject` · [src/features/output.ts:L21-L24][f1]

Factory result with optional js and dts extension overrides.

<a id="u-42a9168f04fe"></a>
### `output.ts module code (L1–L14)`

`module_region` · [src/features/output.ts:L1-L14][f1]

Module imports.

<a id="u-3ed0d2402006"></a>
### `ChunkAddon`

`export type ChunkAddon = ChunkAddonObject | ChunkAddonFunction | string` · [src/features/output.ts:L99-L99][f1]

Union of addon object, addon function, or plain string.

<a id="u-13b36a33fd72"></a>
### `ChunkAddonFunction`

`export type ChunkAddonFunction = (ctx: { format: Format fileName: string }) => ChunkA…` · [src/features/output.ts:L95-L98][f1]

Addon function type receiving format and fileName, returning an object, string, or undefined.

<a id="u-18067fc4e3b9"></a>
### `ChunkFileName`

`type ChunkFileName = string | ((chunk: PreRenderedChunk) => string)` · [src/features/output.ts:L78-L78][f1]

File name template type: static string or per-chunk function.

<a id="u-919324b20151"></a>
### `OutExtensionFactory`

`export type OutExtensionFactory = ( context: OutExtensionContext, ) => OutExtensionOb…` · [src/features/output.ts:L25-L27][f1]

Function type for the outExtensions option.

<a id="u-e69cdaffd8fa"></a>
### `warnLegacyCJS`

`export function warnLegacyCJS(config: ResolvedConfig): void` · [src/features/cjs.ts:L5-L28][f2]

Warns once via the config logger when CJS output targets Node versions supporting require(esm).

Returns early when exe is set, target is missing, the legacyCjs check is disabled (default enabled), or format does not include 'cjs'. Otherwise it coerces the substring after 'node' in each target token and checks it against '^20.19.0 || >=22.12.0'; if any target satisfies, it logs a one-time ESM recommendation. Tokens whose version cannot be coerced are silently skipped.

calls: [method::createLogger.warnOnce::2163][f3]

**Uncertainties.**

- Tokens are split on the literal 'node'; comma-joined tokens would fail coercion unless config.target already holds individual targets.

<a id="u-6e01ed89948f"></a>
### `cjs.ts module code (L1–L4)`

`module_region` · [src/features/cjs.ts:L1-L4][f2]

Imports semver coerce/satisfies helpers and the ResolvedConfig type used by warnLegacyCJS.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/rolldown/tsdown/blob/2b1be7e0accdb1d6e903cd42642666431fc5e93d/src/features/output.ts
[f2]: https://github.com/rolldown/tsdown/blob/2b1be7e0accdb1d6e903cd42642666431fc5e93d/src/features/cjs.ts
[f3]: https://github.com/rolldown/tsdown/blob/2b1be7e0accdb1d6e903cd42642666431fc5e93d/src/utils/logger.ts
# Asset Copying

**Capability.** Copies files or glob matches declared in config.copy into the output directory, applying flatten, default destination, and rename rules per entry.

Use this subtree when static assets are missing or misnamed in the output. It isolates the copy option semantics (CopyEntry/CopyOptions) from the build pipeline that invokes copy after bundling.

**Depends on.**

- [General and Filesystem Helpers](general-and-fs.md) · graph-confirmed · 3 edge(s) · Asset copying uses fs copy and array normalization helpers to perform the copies.

**Depended on by.**

- [Build Orchestration](build-orchestration.md) · containment · → 1 / ← 0 edge(s) (ancestor direct units and descendant subtree; → follows ` build-orchestration ` → ` asset-copying `) · Build orchestration invokes asset copying after bundling to place static assets in the output.

Parent: [Build Orchestration](build-orchestration.md)

## Units (8)

<a id="u-31dcb3fabb8a"></a>
### `copy`

`export async function copy(options: ResolvedConfig): Promise<void>` · [src/features/copy.ts:L39-L93][f1]

Copies files or glob matches declared in config.copy into the output directory.

Returns early when copy is unset or resolves to an empty list; an options.copy function is awaited with the config. String entries become {from:[entry]}. If any from pattern is dynamic, all patterns are globbed under cwd with onlyFiles and no directory expansion. Each concrete file is resolved by resolveCopyEntry into absolute from/to paths; an empty result logs 'No files matched for copying.' and returns. Matching pairs are copied concurrently via fsCopy; entries with verbose log the cwd-relative source and destination first. resolveCopyEntry (folded here) defaults the destination to outDir; when flatten is false and the file has a relative parent directory, the first relative segment is replaced with the destination, preserving deeper structure; rename applies to the basename.

**Notes.**

- side_effect: Performs filesystem copies and logs warnings/info through the config logger.

calls: [fsCopy](general-and-fs.md#u-7c31711dacd3), [toArray](general-and-fs.md#u-1e9a5d8a9f7d)

**Uncertainties.**

- The flatten=false branch replaces only the first path segment of the relative dir with the destination (dir.replace(dir.split(path.sep)[0], to)); behavior for multi-segment dirs rests on that replace semantics.

<a id="u-cffdf070534f"></a>
### `src/features/copy.ts:copy`

`export async function copy(options: ResolvedConfig): Promise<void>` · [src/features/copy.ts:L111-L112][f1]

Two-line closing fragment of the copy function; no behavior beyond the copy unit.

<a id="u-ea985547c0c4"></a>
### `resolveCopyEntry`

`function resolveCopyEntry( entry: CopyEntry & { from: string }, ): CopyEntry & { from…` · [src/features/copy.ts:L93-L111][f1]

Explained within the copy unit; resolves one concrete file entry to absolute from/to paths applying flatten, outDir default, and rename.

<a id="u-8c81f59037f5"></a>
### `renameTarget`

`function renameTarget( target: string, rename: NonNullable<CopyEntry['rename']>, src:…` · [src/features/copy.ts:L114-L124][f1]

Applies a rename spec to a target basename: a string rename replaces it outright; a function rename receives the parsed name, the extension with the leading dot removed, and the original source path, and its return value is used.

<a id="u-d026685c0754"></a>
### `CopyEntry`

`export interface CopyEntry` · [src/features/copy.ts:L8-L35][f1]

Declares the CopyEntry shape: from (string or string list), optional to (defaults to outDir), flatten (default true), verbose (default false), and rename (string or function of name, extension without dot, and full path).

<a id="u-1796d4597a10"></a>
### `CopyOptions`

`export type CopyOptions = Arrayable<string | CopyEntry>` · [src/features/copy.ts:L36-L36][f1]

Alias for a string, CopyEntry, or array of either.

<a id="u-68d20a883685"></a>
### `CopyOptionsFn`

`export type CopyOptionsFn = (options: ResolvedConfig) => Awaitable<CopyOptions>` · [src/features/copy.ts:L37-L37][f1]

Alias for a function receiving ResolvedConfig and returning CopyOptions synchronously or as a promise.

<a id="u-3ba4a4bb96d3"></a>
### `copy.ts module code (L1–L7)`

`module_region` · [src/features/copy.ts:L1-L7][f1]

Imports path, tinyglobby, fsCopy, toArray, and config/type types used by the copy feature.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/rolldown/tsdown/blob/2b1be7e0accdb1d6e903cd42642666431fc5e93d/src/features/copy.ts
# Entry resolution and filesystem helpers

**Capability.** Resolves user entry options (string, array, object, glob) into name-to-path maps, backed by small fs and path utilities.

Come here for how entries are normalized and resolved, including glob detection and wildcard object keys. Shared fs wrappers, common-directory, and extension-stripping helpers support it.

**Depends on.**

- [Configuration loading and resolution](configuration-loading-and-resolution.md) · graph-confirmed · 1 edge(s)
- [Package metadata and utilities](package-metadata-and-utilities.md) · graph-confirmed · 2 edge(s)
- [Dependency handling and general utilities](dependency-handling-and-general-utilities.md) · graph-only · 2 edge(s)
- [Config resolution and normalization](config-resolution-and-normalization.md) · graph-only · 1 edge(s)

**Depended on by.**

- [Build execution pipeline](build-execution-pipeline.md) · graph-confirmed · 7 edge(s) · The build pipeline uses entry resolution and filesystem helpers to normalize entries and manage files.
- [Configuration loading and resolution](configuration-loading-and-resolution.md) · graph-confirmed · 3 edge(s)
- [Package metadata and utilities](package-metadata-and-utilities.md) · graph-confirmed · 2 edge(s)
- [Single executable builds](single-executable-builds.md) · graph-confirmed · 2 edge(s) · Single-executable builds use entry and filesystem helpers to locate chunks and compute output names.
- [Build orchestration and lifecycle](build-orchestration-and-lifecycle.md) · graph-only · 5 edge(s)
- [Config resolution and normalization](config-resolution-and-normalization.md) · graph-only · 2 edge(s)
- [Rolldown option assembly](rolldown-option-assembly.md) · graph-only · 2 edge(s)
- [Config file loading](config-file-loading.md) · graph-only · 1 edge(s)
- [Package exports generation](package-exports-generation.md) · graph-only · 1 edge(s)
- [Package lint checks](package-lint-checks.md) · graph-only · 1 edge(s)

Parent: [tsdown bundling system](tsdown-bundling-system.md)

## Units (8)

<a id="u-2c6c1da2f06c"></a>
### `fs.ts-fs-wrappers`

`export function fsExists(path: string): Promise<boolean>` · [src/utils/fs.ts:L5-L10][f1]

Thin promise wrappers over node:fs/promises.

fsExists resolves true/false via access, never rejects. fsStat returns Stats or null on error. fsRemove deletes recursively with force:true and swallows all errors. fsCopy copies recursively with force:true and does not swallow errors, so it can reject.

<a id="u-2a2d2117cfa5"></a>
### `isGlobEntry`

`export function isGlobEntry(entry: TsdownInputOption | undefined): boolean` · [src/features/entry.ts:L56-L65][f2]

Reports whether an entry option contains glob syntax: false for undefined; a string is checked with isDynamicPattern; an array is checked recursively per element (strings via isDynamicPattern, nested objects recursively); an object is a glob if any key contains '*'.

calls: [function::buildSingle.handleWatcher][f3]

<a id="u-047b87245e30"></a>
### `resolveArrayEntry`

`async function resolveArrayEntry( entries: (string | Record<string, Arrayable<string>…` · [src/features/entry.ts:L131-L174][f2]

Resolves array-form entries by splitting strings from nested objects.

String entries are globbed (cwd-relative, absolute results) if any is a dynamic pattern, otherwise used verbatim; each resulting file is keyed by its extension-stripped path relative to the lowest common ancestor of all resolved string entries, slash-normalized. Nested object entries are resolved with resolveObjectEntry and merged after the string-derived map (object keys win on collision via Object.assign).

calls: [resolveObjectEntry](entry-resolution-and-filesystem-helpers.md#u-83692ca4a865), [function::lowestCommonAncestor][f1]

<a id="u-29c7af1463ba"></a>
### `resolveEntry`

`export async function resolveEntry( logger: Logger, entry: UserConfig['entry'], cwd: …` · [src/features/entry.ts:L11-L40][f2]

Resolves the user entry option into a name→absolute-path map, defaulting and erroring clearly.

With no entry, it tries cwd/src/index.ts as {index}; if that doesn't exist it throws 'No input files, try "tsdown <your-file>" or create src/index.ts'. The entry is converted via toObjectEntry; if the result is empty it throws 'Cannot find entry: <json>'. On success it logs the relative entry paths and returns the map.

calls: [toObjectEntry](entry-resolution-and-filesystem-helpers.md#u-13f5fd0aa8fa), [function::fsExists][f1], [function::resolveUserConfig][f4]

<a id="u-83692ca4a865"></a>
### `resolveObjectEntry`

`async function resolveObjectEntry( entries: Record<string, string | string[]>, cwd: s…` · [src/features/entry.ts:L67-L129][f2]

Resolves object-form entries where keys may contain '*'.

For a plain (non-glob) key, an array value throws a TypeError; otherwise the pair is kept as-is (value not resolved to absolute here). For a glob key, values are normalized to patterns and globbed relative to cwd (no directory expansion); zero matches throws 'Cannot find files for entry key ...'. All non-negated patterns must share the same picomatch base directory — a differing base throws, and if every pattern is negated (base undefined) it throws 'Cannot determine base directory...'. Each matched file becomes an entry whose name is the key with '*' replaced by the extension-stripped path of the file relative to that base, slash-normalized; the value is the cwd-absolute file path. All keys resolve concurrently; errors propagate.

<a id="u-13f5fd0aa8fa"></a>
### `toObjectEntry`

`export function toObjectEntry( entry: TsdownInputOption, cwd: string, ): Promise<Reco…` · [src/features/entry.ts:L42-L54][f2]

Normalizes a string entry to a one-element array, then dispatches: object entries go to resolveObjectEntry, arrays to resolveArrayEntry.

Returns the resulting promise of a name→path record.

<a id="u-7dd4d279c25f"></a>
### `lowestCommonAncestor`

`export function lowestCommonAncestor(...filepaths: string[]): string` · [src/utils/fs.ts:L24-L47][f1]

Computes the deepest shared directory prefix of one or more file paths.

Empty input returns '', a single path returns its dirname. Paths are normalized, then each subsequent path is compared segment-by-segment against the current ancestor, truncating the ancestor at the first mismatch; the split limit means a path that fully matches a longer ancestor still truncates correctly. If the result is a lone root segment (empty string), returns path.sep + that segment (POSIX '/', Windows drive like 'C:'), otherwise joins segments with path.sep.

<a id="u-fc10eca7c52b"></a>
### `stripExtname`

`export function stripExtname(filePath: string): string` · [src/utils/fs.ts:L49-L53][f1]

Removes the file extension from a path using path.extname; if there is no extension the path is returned unchanged.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/rolldown/tsdown/blob/2b1be7e0accdb1d6e903cd42642666431fc5e93d/src/utils/fs.ts
[f2]: https://github.com/rolldown/tsdown/blob/2b1be7e0accdb1d6e903cd42642666431fc5e93d/src/features/entry.ts
[f3]: https://github.com/rolldown/tsdown/blob/2b1be7e0accdb1d6e903cd42642666431fc5e93d/src/build.ts
[f4]: https://github.com/rolldown/tsdown/blob/2b1be7e0accdb1d6e903cd42642666431fc5e93d/src/config/options.ts

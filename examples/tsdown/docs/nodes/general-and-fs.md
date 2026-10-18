# General and Filesystem Helpers

**Capability.** General-purpose helpers (array/pattern/comma/regex normalization, dynamic import with error capture, promise resolvers, debounce, type assertions) plus tolerant fs primitives and chunk annotation.

Use this subtree for path slasherization, existence checks that never reject, and option-value normalization primitives reused everywhere. Chunk annotation (addOutDirToChunks) is included as it is a shared rolldown-output helper.

**Depends on.**

- [Package Publishing](package-publishing.md) · graph-only · 1 edge(s)

**Depended on by.**

- [Asset Copying](asset-copying.md) · graph-confirmed · 3 edge(s) · Asset copying uses fs copy and array normalization helpers to perform the copies.
- [Build Orchestration](build-orchestration.md) · graph-confirmed · 10 edge(s)
- [Config File Discovery and Loading](config-file-loading.md) · graph-confirmed · 2 edge(s)
- [User Config Normalization](config-merging.md) · graph-confirmed · 7 edge(s)
- [Entry Resolution](entry-resolution.md) · graph-confirmed · 7 edge(s) · Entry resolution uses slash, existence checks, extension stripping, and array/pattern helpers.
- [Single-Executable Output](exe-output.md) · graph-confirmed · 4 edge(s)
- [Dependency Externalization](externalization.md) · graph-confirmed · 9 edge(s)
- [Package Publishing](package-publishing.md) · graph-confirmed · 15 edge(s) · Publishing uses fs removal, indentation detection, and path helpers when writing exports and packing tarballs.
- [Bundled Rolldown Plugins](plugin-pipeline.md) · graph-confirmed · 5 edge(s)
- [Build Size Reporting](reporting.md) · graph-confirmed · 4 edge(s)
- [Rolldown Options Assembly](rolldown-assembly.md) · graph-confirmed · 17 edge(s)
- [Target and Tsconfig Resolution](target-and-tsconfig.md) · graph-confirmed · 3 edge(s)
- [Command-Line Interface](cli.md) · graph-only · 2 edge(s)
- [Workspace Expansion](workspace-resolution.md) · graph-only · 2 edge(s)

Parent: [Shared Utilities](shared-utils.md)

## Units (20)

<a id="u-1e9a5d8a9f7d"></a>
### `toArray`

`export function toArray<T>( val: T | T[] | null | undefined, defaultValue?: T, ): T[]` · [src/utils/general.ts:L4-L16][f1]

Normalizes a value into an array.

Arrays pass through by reference; null/undefined yields [defaultValue] when a truthy defaultValue is given, otherwise an empty array; any other value is wrapped in a single-element array.

**Notes.**

- condition: A defaultValue of null/undefined (or generally falsy) is ignored, returning [].

<a id="u-adfdd23335a0"></a>
### `resolveComma`

`export function resolveComma<T extends string>(arr: T[]): T[]` · [src/utils/general.ts:L18-L20][f1]

Splits every string in an array on commas and flattens the results into one array, expanding comma-separated option values.

<a id="u-85b32d43a2f4"></a>
### `resolveRegex`

`export function resolveRegex<T>(str: T): T | RegExp` · [src/utils/general.ts:L22-L32][f1]

Converts slash-delimited string literals into RegExp objects.

Only strings longer than two characters that both start and end with '/' become new RegExp(body); everything else, including non-strings, is returned unchanged.

**Notes.**

- failure: An invalid pattern body propagates a RegExp SyntaxError from the constructor.

<a id="u-9bf13c522663"></a>
### `slash`

`export function slash(string: string): string` · [src/utils/general.ts:L34-L36][f1]

Replaces every backslash in a string with a forward slash, normalizing Windows-style paths.

<a id="u-f95494f1507b"></a>
### `matchPattern`

`export function matchPattern( id: string, patterns: (string | RegExp)[], ): boolean` · [src/utils/general.ts:L40-L51][f1]

Tests an id against a list of string or RegExp patterns, returning true when any matches.

RegExp patterns are tested with lastIndex reset to 0 first so stateful regexes behave predictably. String patterns match on exact equality or via picomatch glob matching.

uses: [slash](general-and-fs.md#u-9bf13c522663)

**Uncertainties.**

- Whether picomatch matching is case-sensitive depends on picomatch defaults not visible here.

<a id="u-2cf9b0e46dec"></a>
### `pkgExists`

`export function pkgExists(moduleName: string): boolean` · [src/utils/general.ts:L53-L59][f1]

Reports whether a module name resolves from the current package.

Uses import.meta.resolve, returning true on success and false when it throws; the thrown error is discarded.

<a id="u-6e036190d6a7"></a>
### `importWithError`

`export async function importWithError<T>( moduleName: string, resolvePaths?: string[]…` · [src/utils/general.ts:L61-L81][f1]

Dynamically imports a module, optionally resolving it against explicit search paths.

When resolvePaths is given, require.resolve finds the module among those paths and it is converted to a file URL for import; otherwise the module name is imported directly. An import failure is rethrown as a new Error telling the user to ensure the module is installed, with the original error attached as cause; resolution via require.resolve itself can still throw before that wrapping.

**Uncertainties.**

- Path resolution uses require.resolve, which is CJS-oriented; its behavior under ESM bundling is not established here.

<a id="u-19569223bc83"></a>
### `promiseWithResolvers`

`export function promiseWithResolvers<T>(): { promise: Promise<T> resolve: (value: T) …` · [src/utils/general.ts:L84-L94][f1]

Creates a promise together with its resolve function (a Promise.withResolvers polyfill).

Returns an object exposing the promise and the resolve callback; reject is not exposed, so consumers cannot reject this promise.

<a id="u-976b6a668555"></a>
### `debounce`

`export function debounce<T extends (...args: any[]) => any>( fn: T, delay: number, ):…` · [src/utils/general.ts:L100-L105][f1]

Returns a debounced wrapper around fn: each call clears the pending timer and schedules fn with the latest arguments after delay milliseconds, so only the last call in a burst runs.

The returned function carries cancel(), which clears the pending timer so the scheduled invocation never fires. Timers are per-debounced-function state.

<a id="u-2d6f421314ba"></a>
### `typeAssert`

`export function typeAssert<T>( value: T, ): asserts value is Exclude<T, false | null …` · [src/utils/general.ts:L96-L98][f1]

TypeScript assertion helper with an empty body: at runtime it does nothing, but statically narrows a value to exclude false, null, and undefined.

<a id="u-c52d58ffbbd4"></a>
### `noop`

`export const noop = <T>(v: T): T =>` · [src/utils/general.ts:L38-L38][f1]

Identity helper returning its argument unchanged; used as a default no-op colorizer.

<a id="u-0f222011da8d"></a>
### `fsExists`

`export function fsExists(path: string): Promise<boolean>` · [src/utils/fs.ts:L5-L10][f2]

Checks path existence via access, resolving true on success and false on any error, so permission-denied and nonexistent paths are indistinguishable.

<a id="u-73b329382a5b"></a>
### `fsStat`

`export function fsStat(path: string): Promise<Stats | null>` · [src/utils/fs.ts:L12-L14][f2]

Stats a path, resolving to its Stats object or to null on any stat failure instead of rejecting.

<a id="u-55a789017e76"></a>
### `fsRemove`

`export function fsRemove(path: string): Promise<void>` · [src/utils/fs.ts:L16-L18][f2]

Recursively removes a path with force:true, tolerating missing paths; all rm errors are swallowed and the promise resolves to undefined.

<a id="u-7c31711dacd3"></a>
### `fsCopy`

`export function fsCopy(from: string, to: string): Promise<void>` · [src/utils/fs.ts:L20-L22][f2]

Copies a file or directory recursively with force:true so existing destinations are overwritten; errors from cp propagate to the caller.

<a id="u-7dd4d279c25f"></a>
### `lowestCommonAncestor`

`export function lowestCommonAncestor(...filepaths: string[]): string` · [src/utils/fs.ts:L24-L47][f2]

Computes the deepest common directory of the given file paths.

Empty input returns ''; a single path returns its dirname. Each path is normalized then split on the path separator; for each remaining path the shared segment prefix is truncated at the first mismatching segment. When the ancestor reduces to the root segment (empty string, length 1) the result is the path separator, otherwise the segments are rejoined.

uses: [fsStat](general-and-fs.md#u-73b329382a5b)

**Uncertainties.**

- Comparison is purely lexical on segment strings; symlinks, case differences, and relative vs absolute mixing are not resolved beyond path.normalize.

<a id="u-fc10eca7c52b"></a>
### `stripExtname`

`export function stripExtname(filePath: string): string` · [src/utils/fs.ts:L49-L53][f2]

Removes a single trailing extension from a file path.

If path.extname yields no extension the input is returned unchanged; otherwise the string is sliced by the extension's length.

<a id="u-7a2fdc0e4dc6"></a>
### `addOutDirToChunks`

`export function addOutDirToChunks( chunks: Array<OutputChunk | OutputAsset>, outDir: …` · [src/utils/chunks.ts:L13-L22][f3]

Annotates rolldown output chunks and assets with the build output directory.

Maps the input array, assigns outDir on each object (with a ts-expect-error because base rolldown types lack the property), and returns the same objects cast to RolldownChunk[]. The returned array is new but its elements are the same references as the input, so input objects are mutated in place.

**Notes.**

- side_effect: Each input chunk object gains an outDir property; callers receive the same object references.

<a id="u-53867d634f8b"></a>
### `formatBytes`

`export function formatBytes(bytes: number): string | undefined` · [src/utils/format.ts:L1-L7][f4]

Renders a byte count as a human-readable string.

Infinity returns undefined. Values above 1,000,000 become megabytes with two decimals; everything else becomes kilobytes with two decimals, using the same 1000-based divisor for the 1000..1000000 range.

<a id="u-0851d0845062"></a>
### `detectIndentation`

`export function detectIndentation(jsonText: string): string | number` · [src/utils/format.ts:L9-L23][f4]

Detects the indentation used in a JSON text by finding the first line whose leading whitespace precedes non-space content.

Tabs anywhere in that leading run return '\t'; otherwise the run's character count is returned. Lines with no indentation are skipped, and if no indented line exists the fallback is 2.

**Uncertainties.**

- The first indented line decides the result; mixed indentation later in the file is ignored.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/rolldown/tsdown/blob/2b1be7e0accdb1d6e903cd42642666431fc5e93d/src/utils/general.ts
[f2]: https://github.com/rolldown/tsdown/blob/2b1be7e0accdb1d6e903cd42642666431fc5e93d/src/utils/fs.ts
[f3]: https://github.com/rolldown/tsdown/blob/2b1be7e0accdb1d6e903cd42642666431fc5e93d/src/utils/chunks.ts
[f4]: https://github.com/rolldown/tsdown/blob/2b1be7e0accdb1d6e903cd42642666431fc5e93d/src/utils/format.ts
# Entry Resolution

**Capability.** Resolves the configured entry option (string, array, object, or glob patterns) into a map of entry names to absolute file paths.

Use this subtree when entries resolve to unexpected names or paths. It owns all entry-shape normalization and glob expansion, shared by config resolution and buildSingle's glob-entry checks.

**Depends on.**

- [General and Filesystem Helpers](general-and-fs.md) · graph-confirmed · 7 edge(s) · Entry resolution uses slash, existence checks, extension stripping, and array/pattern helpers.
- [Package Publishing](package-publishing.md) · model-inferred · 0 edge(s)

**Depended on by.**

- [Configuration Resolution](config.md) · containment · → 0 / ← 0 edge(s) (ancestor direct units and descendant subtree; → follows ` config ` → ` entry-resolution `)
- [User Config Normalization](config-merging.md) · graph-confirmed · 1 edge(s) · User config normalization invokes entry resolution to turn the entry option into resolved paths.
- [Build Orchestration](build-orchestration.md) · graph-only · 2 edge(s)

Parent: [Configuration Resolution](config.md)

## Units (6)

<a id="u-29c7af1463ba"></a>
### `resolveEntry`

`export async function resolveEntry( logger: Logger, entry: UserConfig['entry'], cwd: …` · [src/features/entry.ts:L11-L40][f1]

Resolves the configured entry into a map of entry names to absolute file paths.

When entry is empty or missing, it defaults to src/index.ts under cwd: if that exists it becomes {index: <path>}, otherwise it throws telling the user to pass input files or create src/index.ts. After normalizing via toObjectEntry, an empty result throws 'Cannot find entry'. On success it logs the cwd-relative entry paths through the logger, colored with the supplied Ansis instance.

**Notes.**

- failure: Throws when no entry is configured and src/index.ts does not exist, or when resolution yields no entries.

calls: [toObjectEntry](entry-resolution.md#u-13f5fd0aa8fa), [fsExists](general-and-fs.md#u-0f222011da8d)

<a id="u-13f5fd0aa8fa"></a>
### `toObjectEntry`

`export function toObjectEntry( entry: TsdownInputOption, cwd: string, ): Promise<Reco…` · [src/features/entry.ts:L42-L54][f1]

Normalizes an entry option into a name-to-path map: a string is wrapped in an array; arrays go to resolveArrayEntry, objects go to resolveObjectEntry.

Its return value is the promise produced by those resolvers.

calls: [resolveObjectEntry](entry-resolution.md#u-83692ca4a865), [resolveArrayEntry](entry-resolution.md#u-047b87245e30)

<a id="u-047b87245e30"></a>
### `resolveArrayEntry`

`async function resolveArrayEntry( entries: (string | Record<string, Arrayable<string>…` · [src/features/entry.ts:L131-L174][f1]

Resolves an array entry mixing strings and objects.

Strings are separated from object entries; if any string is a dynamic pattern, all string patterns are globbed under cwd (absolute, no expansion) and each match is path.resolve'd, otherwise the strings pass through. Entry names are derived from the lowest common ancestor: the extension-stripped, slashed path relative to that base maps to the file. Object entries are resolved via resolveObjectEntry and merged after the string-derived map, so object keys win on collisions.

calls: [lowestCommonAncestor](general-and-fs.md#u-7dd4d279c25f), [resolveObjectEntry](entry-resolution.md#u-83692ca4a865), [stripExtname](general-and-fs.md#u-fc10eca7c52b), [slash](general-and-fs.md#u-9bf13c522663)

<a id="u-83692ca4a865"></a>
### `resolveObjectEntry`

`async function resolveObjectEntry( entries: Record<string, string | string[]>, cwd: s…` · [src/features/entry.ts:L67-L129][f1]

Resolves an object entry ({name: path|patterns}) into name-to-absolute-path pairs.

Keys without '*': array values throw a TypeError; the pair passes through unchanged. Glob keys: values are normalized to patterns and globbed under cwd (no directory expansion); zero matches throw. All non-negated patterns must share the same picomatch base directory or an error is thrown; only negated patterns (no positive base) also throw. Each matched file yields a key where every '*' in the key is replaced with the extension-stripped path relative to the base (slashed), mapping to the absolute file path. Results across keys are flattened into one object.

**Notes.**

- failure: Throws on array values under non-glob keys, on zero glob matches, on mismatched pattern bases, and when no positive pattern base exists.

calls: [stripExtname](general-and-fs.md#u-fc10eca7c52b), [slash](general-and-fs.md#u-9bf13c522663), [toArray](general-and-fs.md#u-1e9a5d8a9f7d)

<a id="u-2a2d2117cfa5"></a>
### `isGlobEntry`

`export function isGlobEntry(entry: TsdownInputOption | undefined): boolean` · [src/features/entry.ts:L56-L65][f1]

Reports whether an entry option contains glob patterns.

Undefined returns false; a string is tested with isDynamicPattern; arrays return true if any element is a glob string or recursively a glob entry; objects return true when any key contains '*'. Used by the watcher to detect glob-based inputs.

**Uncertainties.**

- Object values are not inspected for globs; only keys are tested.

<a id="u-f16d28abc183"></a>
### `entry.ts module code (L1–L10)`

`module_region` · [src/features/entry.ts:L1-L10][f1]

Imports path, picomatch, tinyglobby, fs/generic helpers, and types used by entry resolution.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/rolldown/tsdown/blob/2b1be7e0accdb1d6e903cd42642666431fc5e93d/src/features/entry.ts
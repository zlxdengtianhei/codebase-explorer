# Entry and path resolution

**Capability.** Resolves entry inputs into name-to-path maps and provides filesystem/path helpers for access, prefixes, and extensions.

Come here for entry normalization, glob detection, and small filesystem/path utilities. Units cover string, array, and object entry forms plus common path operations.

**Depends on.**

- [Package output and validation](package-output-and-validation.md) · graph-confirmed · 3 edge(s)
- [Package export map generation](package-export-map-generation.md) · graph-only · 2 edge(s)
- [Dependency externalization utilities](dependency-externalization-utilities.md) · graph-only · 1 edge(s)

**Depended on by.**

- [Build execution and watching](build-execution-and-watching.md) · graph-confirmed · 5 edge(s)
- [Config file loading](config-file-loading.md) · graph-confirmed · 1 edge(s)
- [Config resolution and logging](config-resolution-and-logging.md) · graph-confirmed · 3 edge(s)
- [Executable builds and sizing](executable-builds-and-sizing.md) · graph-confirmed · 2 edge(s)
- [Package output and validation](package-output-and-validation.md) · graph-confirmed · 2 edge(s)
- [Rolldown option assembly](rolldown-option-assembly.md) · graph-confirmed · 1 edge(s)
- [Build orchestration lifecycle](build-orchestration-lifecycle.md) · graph-only · 4 edge(s)
- [Executable SEA builds](executable-sea-builds.md) · graph-only · 2 edge(s)
- [Copy shortcuts target helpers](copy-shortcuts-target-helpers.md) · graph-only · 1 edge(s)
- [Package export map generation](package-export-map-generation.md) · graph-only · 1 edge(s)
- [Package tarball validation](package-tarball-validation.md) · graph-only · 1 edge(s)

Parent: [tsdown build tool](tsdown-build-tool.md)

## Units (8)

<a id="u-44fab1ea1c14"></a>
### `fs.ts-filesystem-wrappers`

`export function fsExists(path: string): Promise<boolean>` · [src/utils/fs.ts:L5-L10][f1]

Access checks resolve true on success and false on any failure, never rejecting.

Stat returns stats or null on failure. Remove recursively with force enabled and swallows removal errors, always resolving void. Copy recursively with force enabled and propagates copy failures.

<a id="u-2a2d2117cfa5"></a>
### `isGlobEntry`

`export function isGlobEntry(entry: TsdownInputOption | undefined): boolean` · [src/features/entry.ts:L56-L65][f2]

Detects whether entry input contains a glob pattern without expanding it.

Undefined is false; a string uses dynamic-pattern detection; an array is true if any element is a glob; an object is true if any key contains '*'. Nested arrays are checked recursively.

<a id="u-047b87245e30"></a>
### `resolveArrayEntry`

`async function resolveArrayEntry( entries: (string | Record<string, Arrayable<string>…` · [src/features/entry.ts:L131-L174][f2]

Resolves array-form entries by separating string paths from object entries.

If any string entry is a dynamic pattern, all string entries are globbed with cwd, no directory expansion, and absolute results; otherwise strings are used as given. The common ancestor of resolved strings becomes the base for keys made from slashed, extensionless relative paths. Object entries are resolved and merged afterward, so later object keys can override string-derived keys. Glob and object-resolution errors propagate.

**Uncertainties.**

- Behavior when the array contains only object entries depends on lowestCommonAncestor with no paths, which is not shown.

<a id="u-29c7af1463ba"></a>
### `resolveEntry`

`export async function resolveEntry( logger: Logger, entry: UserConfig['entry'], cwd: …` · [src/features/entry.ts:L11-L40][f2]

Resolves user entry input into a name-to-path map, supplying a default or throwing when none can be found.

When entry is missing or an empty object, it checks cwd/src/index.ts and uses index if present; otherwise it throws with the optional label. It then converts the entry, throws if the resulting map has no values, logs the relative paths, and returns the map. Conversion and filesystem errors propagate.

<a id="u-83692ca4a865"></a>
### `resolveObjectEntry`

`async function resolveObjectEntry( entries: Record<string, string | string[]>, cwd: s…` · [src/features/entry.ts:L67-L129][f2]

Resolves object-form entries, expanding glob keys and rejecting invalid shapes.

For a key without '*', an array value throws TypeError; otherwise the key/value pair is kept. For a glob key, values are globbed with cwd and no directory expansion; no matches throw. Non-negated value patterns must all share the same picomatch base, otherwise it throws; if no base is found it throws. Matched files become keys with '*' replaced by the extensionless relative path from that base, slashed, and values resolved against cwd. Results are flattened into one object.

**Uncertainties.**

- picomatch.scan base semantics for complex patterns are delegated and not shown.

<a id="u-13f5fd0aa8fa"></a>
### `toObjectEntry`

`export function toObjectEntry( entry: TsdownInputOption, cwd: string, ): Promise<Reco…` · [src/features/entry.ts:L42-L54][f2]

Normalizes string, array, or object entry input into a promise of a name-to-path record.

A string is wrapped in an array; non-array input goes to object resolution; array input goes to array resolution. It does not itself validate or log.

<a id="u-7dd4d279c25f"></a>
### `lowestCommonAncestor`

`export function lowestCommonAncestor(...filepaths: string[]): string` · [src/utils/fs.ts:L24-L47][f1]

Computes a common directory prefix for multiple paths.

With no paths it returns an empty string; with one path it returns that path's dirname. For multiple paths it normalizes each, splits the first by the platform separator, and progressively truncates that segment list at the first mismatch with each remaining path. The result is joined with the platform separator, except when the final segment list is a single empty segment, which returns the platform separator. A drive segment such as 'C:' is not special and is returned by the join unchanged.

<a id="u-fc10eca7c52b"></a>
### `stripExtname`

`export function stripExtname(filePath: string): string` · [src/utils/fs.ts:L49-L53][f1]

Removes the final extension reported by the platform path extname; if there is no extension, returns the input unchanged.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/rolldown/tsdown/blob/2b1be7e0accdb1d6e903cd42642666431fc5e93d/src/utils/fs.ts
[f2]: https://github.com/rolldown/tsdown/blob/2b1be7e0accdb1d6e903cd42642666431fc5e93d/src/features/entry.ts

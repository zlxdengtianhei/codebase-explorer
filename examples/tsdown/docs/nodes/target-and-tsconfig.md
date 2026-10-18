# Target and Tsconfig Resolution

**Capability.** Normalizes the build target (including pkg.engines.node derivation) and resolves the tsconfig option to an explicit path or upward search result.

Use this subtree to see how syntax-downlevel targets and tsconfig discovery are decided. Both are option-level resolvers invoked during user config resolution.

**Depends on.**

- [General and Filesystem Helpers](general-and-fs.md) · graph-confirmed · 3 edge(s)

**Depended on by.**

- [User Config Normalization](config-merging.md) · graph-confirmed · 2 edge(s)

Parent: [Configuration Resolution](config.md)

## Units (6)

<a id="u-20e81acaf8a7"></a>
### `resolveTarget`

`export function resolveTarget( logger: Logger, target: string | string[] | false | un…` · [src/features/target.ts:L7-L35][f1]

Normalizes the build target into a list of target strings.

target === false returns undefined (feature disabled); when target is null/undefined, the package.json engines.node is consulted via resolvePackageTarget and used as the target, otherwise undefined is returned. A numeric target throws a TypeError. Comma-separated tokens are expanded with resolveComma after toArray; a non-empty result is logged ('target' or plural 'targets') with colorized values and returned.

**Notes.**

- failure: Throws TypeError for a numeric target; logger.info is only called when at least one target resolves.

calls: [resolvePackageTarget](target-and-tsconfig.md#u-1db4e976c1c8), [resolveComma](general-and-fs.md#u-adfdd23335a0), [toArray](general-and-fs.md#u-1e9a5d8a9f7d)

<a id="u-1db4e976c1c8"></a>
### `resolvePackageTarget`

`export function resolvePackageTarget(pkg?: PackageJson): string | undefined` · [src/features/target.ts:L37-L44][f1]

Derives a 'node<version>' target from pkg.engines.node.

Returns undefined when engines.node is absent, when semver's minVersion cannot parse the range, or when the minimum version resolves to '0.0.0' (indicating any version); otherwise returns 'node' plus the minimum version string.

<a id="u-bd5513a084a8"></a>
### `target.ts module code (L1–L6)`

`module_region` · [src/features/target.ts:L1-L6][f1]

Imports semver minVersion, resolveComma/toArray helpers, and Logger/Ansis/PackageJson types used by target resolution.

<a id="u-0f59a9aa4cf1"></a>
### `resolveTsconfig`

`export async function resolveTsconfig( logger: Logger, tsconfig: UserConfig['tsconfig…` · [src/features/tsconfig.ts:L15-L54][f2]

Resolves the tsconfig option to a path or false.

tsconfig === false short-circuits to false with no logging. true or null/undefined searches upward from cwd for tsconfig.json; when an explicit truthy original value yielded no find, a warning names the cwd. Otherwise a string option is resolved against cwd and stat'd: a file path is used directly; a directory is searched from that directory (warning when nothing is found); any other case treats the string as a file name to find upward from cwd, warning that it doesn't exist when the search fails. A resolved path is logged cwd-relative and returned; all find/search outcomes come from findTsconfig.

**Notes.**

- failure: Missing tsconfigs produce warnings, not errors; the function still returns the falsy search result.

calls: [findTsconfig](target-and-tsconfig.md#u-5d3c9649f814), [fsStat](general-and-fs.md#u-73b329382a5b)

<a id="u-5d3c9649f814"></a>
### `findTsconfig`

`function findTsconfig( cwd?: string, name: string = 'tsconfig.json', ): string | false` · [src/features/tsconfig.ts:L8-L13][f2]

Explained within resolveTsconfig: searches upward for the given file name (default 'tsconfig.json') from cwd and returns the found path or false.

<a id="u-a94e056a5a90"></a>
### `tsconfig.ts module code (L1–L7)`

`module_region` · [src/features/tsconfig.ts:L1-L7][f2]

Imports path, ansis, empathic find-up, fsStat, and config/logger types used by tsconfig resolution.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/rolldown/tsdown/blob/2b1be7e0accdb1d6e903cd42642666431fc5e93d/src/features/target.ts
[f2]: https://github.com/rolldown/tsdown/blob/2b1be7e0accdb1d6e903cd42642666431fc5e93d/src/features/tsconfig.ts
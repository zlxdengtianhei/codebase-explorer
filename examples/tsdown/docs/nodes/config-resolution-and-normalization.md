# Config resolution and normalization

**Capability.** Resolves user configs into per-format ResolvedConfig objects, applying defaults, filters, CI-aware feature flags, and target/tsconfig resolution.

Come here for how a user config becomes validated ResolvedConfig instances, including deep-merge of overrides, env filtering, and engines.node target derivation. Also normalizes formats, arrays, and package.json types.

**Depends on.**

- [Config file loading](config-file-loading.md) · graph-confirmed · 1 edge(s) · 1 inferred relation(s)
- [Dependency handling and general utilities](dependency-handling-and-general-utilities.md) · graph-only · 5 edge(s)
- [Logging and size reporting](logging-and-size-reporting.md) · graph-only · 3 edge(s)
- [Entry resolution and filesystem helpers](entry-resolution-and-filesystem-helpers.md) · graph-only · 2 edge(s)
- [Build orchestration and lifecycle](build-orchestration-and-lifecycle.md) · graph-only · 1 edge(s)
- [Package exports generation](package-exports-generation.md) · graph-only · 1 edge(s)
- [Single executable builds](single-executable-builds.md) · graph-only · 1 edge(s)

**Depended on by.**

- [Config file loading](config-file-loading.md) · graph-confirmed · 2 edge(s) · Config file loading hands parsed configs to resolution and normalization for defaults and per-format resolution.
- [Rolldown option assembly](rolldown-option-assembly.md) · graph-only · 3 edge(s)
- [Build orchestration and lifecycle](build-orchestration-and-lifecycle.md) · graph-only · 2 edge(s)
- [Dependency handling and general utilities](dependency-handling-and-general-utilities.md) · graph-only · 2 edge(s)
- [CLI entry and debug](cli-entry-and-debug.md) · graph-only · 1 edge(s)
- [Entry resolution and filesystem helpers](entry-resolution-and-filesystem-helpers.md) · graph-only · 1 edge(s)

Parent: [Configuration loading and resolution](configuration-loading-and-resolution.md)

## Units (13)

<a id="u-6a53186827b6"></a>
### `options.ts-mergeconfig-overloads`

`export function mergeConfig( defaults: UserConfig, overrides: UserConfig, ): UserConfig` · [src/config/options.ts:L353-L356][f1]

Two overload signatures (UserConfig and InlineConfig pairs) plus one implementation that deep-merges overrides onto defaults using a defu instance customized so that when both sides hold arrays, the override array replaces the default array instead of concatenating.

<a id="u-eb3b113d206d"></a>
### `tsconfig.ts-tsconfig-resolution`

`function findTsconfig( cwd?: string, name: string = 'tsconfig.json', ): string | false` · [src/features/tsconfig.ts:L8-L13][f2]

Resolves the user tsconfig option to a path, false, or a directory-derived lookup, with warnings for misses.

findTsconfig does an empathic find-up for a name (default tsconfig.json) from a cwd, returning false when absent. resolveTsconfig: false passes through as false. true or null/undefined triggers a find-up from cwd; when the user explicitly passed true and nothing is found it warns 'No tsconfig found in <cwd>'. A string is resolved against cwd: an existing file is used directly; an existing directory triggers a find-up of the default name inside it (warning if none found); a nonexistent path falls back to find-up using the string as the config name from cwd, warning '<original> doesn't exist' if that also fails. Any resolved path is logged relative to cwd. The result is the absolute path or false; fsStat errors propagate.

calls: [function::resolveUserConfig][f1]

<a id="u-214398a0ba44"></a>
### `filterConfig`

`function filterConfig( filter: InlineConfig['filter'], configCwd: string, name?: stri…` · [src/config/options.ts:L399-L416][f1]

Decides whether a config should run given an optional filter.

No filter means pass. The config cwd is made relative to process.cwd() ('.' if same). A RegExp filter matches the config name or the relative cwd; a string/array filter matches by exact name equality or exact relative-cwd equality.

<a id="u-bab6e24b1339"></a>
### `filterEnv`

`function filterEnv( envDict: Record<string, string | undefined>, envPrefixes: string[…` · [src/config/options.ts:L333-L344][f1]

Filters an env record to keys with non-null values that start with any of the given prefixes, returning a new record.

<a id="u-5c9b32bbb6d0"></a>
### `resolveCIOption`

`function resolveCIOption(value: boolean | CIOption): boolean` · [src/config/options.ts:L393-L397][f1]

Resolves a boolean or CIOption to a boolean: 'ci-only' is true only in CI, 'local-only' is true only outside CI, booleans pass through.

<a id="u-af8d01c05608"></a>
### `resolveFeatureOption`

`export function resolveFeatureOption<T>( value: Exclude<WithEnabled<T>, undefined>, d…` · [src/config/options.ts:L383-L391][f1]

Resolves a WithEnabled feature option against defaults: an object value is returned as-is if its enabled field (default true) passes CI resolution, otherwise false; a non-object value returns defaults when it passes CI resolution, otherwise false.

<a id="u-9f27c28524ef"></a>
### `resolveUserConfig`

`export async function resolveUserConfig( userConfig: UserConfig, inlineConfig: Inline…` · [src/config/options.ts:L43-L330][f1]

Resolves one user config into an array of ResolvedConfig (one per output format), applying defaults, deprecations, validation, and feature resolution.

Destructures ~50 options with defaults (entry, plugins, clean:true, logLevel:'info', treeshake:true, platform:'node', outDir:'dist', envPrefix:'TSDOWN_', hash:true, cjsDefault:true, globImport:true, fixedExtension: platform==='node', write:true, etc.; unbundle defaults to !bundle when bundle is boolean). Reads package.json from cwd; in workspace mode the name defaults to the package name. If the inline filter excludes this config (by cwd or name), returns []. Creates a logger with failOnWarn resolved via feature-option semantics. Deprecation handling: boolean bundle warns; removeNodeProtocol warns and maps to nodeProtocol 'strip' (throws TypeError if nodeProtocol is also set); injectStyle merges into css.inject (throws if css.inject already set); publicDir warns and is merged into copy (throws if copy also set). Resolves entry, target, tsconfig, clean, and deps via feature modules; feature options (publint, attw, exports, unused, report, exe, dts, devtools) are resolved so they become either their options object or false, honoring enabled and CI-only/local-only flags. dts defaults to false when exe is enabled, otherwise auto-detected from pkg types/typings or a types entry in exports. Throws if exports is enabled without a package.json; warns for publint/attw enabled without one. envPrefix is arrayified; an empty prefix disables filtering with a leakage warning. Env merging precedence: env file < process.env < explicit env option; envFile requires util.parseEnv (throws on runtimes without it). fromVite loads a Vite config: array-form resolve.alias throws TypeError, otherwise alias and plugins are merged in. ignoreWatch entries are regex-resolved and string paths resolved against cwd. Devtools in watch mode disables its UI with a warning; otherwise the UI defaults to presence of @vitejs/devtools/cli. Builds the base config object; if exe is enabled it is validated via validateSea. Format handling: an object format maps to one ResolvedConfig per key with that key's overrides spread last; otherwise formats come from comma-split array (default 'esm'). Per-format, copy and onSuccess are kept only on the first config to avoid duplicate execution.

**Notes.**

- contract: Returns [] when filtered out, otherwise one ResolvedConfig per format.

calls: [filterConfig](config-resolution-and-normalization.md#u-214398a0ba44), [filterEnv](config-resolution-and-normalization.md#u-bab6e24b1339), [resolveFeatureOption](config-resolution-and-normalization.md#u-af8d01c05608), [loadViteConfig](config-file-loading.md#u-0db73e2398fc), [resolveEntry](../../catalog.json.gz), [resolveTarget](../../catalog.json.gz), [resolveTsconfig](../../catalog.json.gz), [resolveDepsConfig](../../catalog.json.gz), [validateSea](../../catalog.json.gz)

**Uncertainties.**

- Behavior of resolveEntry, resolveTarget, resolveTsconfig, resolveClean, resolveDepsConfig, validateSea, and hasExportsTypes is not visible in this excerpt; only their call sites and effects on the config fields are established.

<a id="u-1db4e976c1c8"></a>
### `resolvePackageTarget`

`export function resolvePackageTarget(pkg?: PackageJson): string | undefined` · [src/features/target.ts:L37-L44][f3]

Derives a target string from package.json engines.node: returns undefined when absent, when semver can't compute a minimum, or when the minimum is '0.0.0'; otherwise returns `node<minVersion>`.

Note the signature declares string|string[]|false|undefined input but only string|false|undefined handling is observable here.

<a id="u-20e81acaf8a7"></a>
### `resolveTarget`

`export function resolveTarget( logger: Logger, target: string | string[] | false | un…` · [src/features/target.ts:L7-L35][f3]

Resolves the target option into a string array, falling back to the package's engines.node minimum.

target===false returns undefined. A null/undefined target uses resolvePackageTarget's result, or returns undefined if that's absent. A numeric target throws a TypeError. Otherwise the value is array-normalized, comma-split, the resolved list is logged (singular/plural 'target(s)'), and returned; an empty list is returned as-is (empty array).

calls: [resolvePackageTarget](config-resolution-and-normalization.md#u-1db4e976c1c8), [function::resolveUserConfig][f1]

<a id="u-1e9a5d8a9f7d"></a>
### `toArray`

`export function toArray<T>( val: T | T[] | null | undefined, defaultValue?: T, ): T[]` · [src/utils/general.ts:L4-L16][f4]

Normalizes a value into an array: arrays pass through as-is, null/undefined yields the default value wrapped in an array (or an empty array when no default), and any other value is wrapped in a single-element array.

<a id="u-f900f56cf2b7"></a>
### `getPackageType`

`export function getPackageType(pkg: PackageJson | undefined): PackageType` · [src/utils/package.ts:L27-L34][f5]

Returns a package.json's `type` field, restricted to 'module' or 'commonjs'; any other non-empty value throws an Error naming the invalid type, and a missing package or missing type field yields undefined.

<a id="u-4374d0c5e362"></a>
### `normalizeFormat`

`export function normalizeFormat(format: Format): NormalizedFormat` · [src/utils/package.ts:L36-L48][f5]

Normalizes format aliases: 'es', 'esm', and 'module' map to 'es'; 'cjs' and 'commonjs' map to 'cjs'; any other format string is returned unchanged.

<a id="u-75e57eaf2966"></a>
### `readPackageJson`

`export async function readPackageJson( dir: string, ): Promise<PackageJsonWithPath | …` · [src/utils/package.ts:L13-L24][f5]

Finds the nearest package.json at or above the given directory via empathic, reads and JSON-parses it, and returns its contents merged with the resolved packageJsonPath.

Returns undefined when no package.json is found; a parse failure would reject. Logs the path through a debug logger.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/rolldown/tsdown/blob/2b1be7e0accdb1d6e903cd42642666431fc5e93d/src/config/options.ts
[f2]: https://github.com/rolldown/tsdown/blob/2b1be7e0accdb1d6e903cd42642666431fc5e93d/src/features/tsconfig.ts
[f3]: https://github.com/rolldown/tsdown/blob/2b1be7e0accdb1d6e903cd42642666431fc5e93d/src/features/target.ts
[f4]: https://github.com/rolldown/tsdown/blob/2b1be7e0accdb1d6e903cd42642666431fc5e93d/src/utils/general.ts
[f5]: https://github.com/rolldown/tsdown/blob/2b1be7e0accdb1d6e903cd42642666431fc5e93d/src/utils/package.ts

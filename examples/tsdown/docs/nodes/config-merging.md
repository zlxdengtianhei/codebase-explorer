# User Config Normalization

**Capability.** Resolves one user config into per-format resolved configs by merging defaults, normalizing flags and env filtering, and invoking feature-specific resolvers.

Use this subtree to see every option normalization step applied to a single UserConfig. It is the hub where feature resolvers (entry, clean, deps, target, tsconfig, exe validation) get called.

**Depends on.**

- [Build Orchestration](build-orchestration.md) · graph-confirmed · 1 edge(s)
- [Entry Resolution](entry-resolution.md) · graph-confirmed · 1 edge(s) · User config normalization invokes entry resolution to turn the entry option into resolved paths.
- [Single-Executable Output](exe-output.md) · graph-confirmed · 1 edge(s)
- [Dependency Externalization](externalization.md) · graph-confirmed · 1 edge(s)
- [General and Filesystem Helpers](general-and-fs.md) · graph-confirmed · 7 edge(s)
- [Logging](logging.md) · graph-confirmed · 3 edge(s)
- [Package Metadata Helpers](package-metadata.md) · graph-confirmed · 2 edge(s)
- [Target and Tsconfig Resolution](target-and-tsconfig.md) · graph-confirmed · 2 edge(s)
- [Config File Discovery and Loading](config-file-loading.md) · graph-only · 1 edge(s)
- [Package Publishing](package-publishing.md) · graph-only · 1 edge(s)

**Depended on by.**

- [Configuration Resolution](config.md) · containment · → 1 / ← 0 edge(s) (ancestor direct units and descendant subtree; → follows ` config ` → ` config-merging `)
- [Rolldown Options Assembly](rolldown-assembly.md) · graph-only · 2 edge(s)

Parent: [Configuration Resolution](config.md)

## Units (3)

<a id="u-9f27c28524ef"></a>
### `resolveUserConfig`

`export async function resolveUserConfig( userConfig: UserConfig, inlineConfig: Inline…` · [src/config/options.ts:L43-L330][f1]

Resolves one user config into one or more fully resolved per-format configs.

It applies defaults from destructuring (e.g. entry, format, clean true, outDir 'dist', sourcemap false, treeshake true, envPrefix 'TSDOWN_'), reads package.json from cwd, and returns [] early when filterConfig rejects this cwd/name. It creates a logger honoring logLevel, customLogger, and failOnWarn (via resolveFeatureOption), warns on the deprecated `bundle` boolean, and throws TypeError when `removeNodeProtocol` is combined with `nodeProtocol`; otherwise removeNodeProtocol:true maps to nodeProtocol 'strip' and false to false. It resolves outDir against cwd, clean, entry, target, tsconfig, and converts feature flags (publint, attw, exports, unused, report, exe, dts, devtools) via resolveFeatureOption. When package.json is missing, exports enabled throws; publint/attw warn. Deprecated `injectStyle` merges into css.inject (throws if both set); `publicDir` is deprecated and throws if combined with `copy`. Env assembly: process.env filtered by prefixes, optionally an envFile parsed with util.parseEnv (throws if the runtime lacks it) with precedence env file < process.env < tsdown option; an empty prefix disables filtering with a leak warning. fromVite pulls alias/plugins from loadViteConfig, throwing on array-form Vite alias. ignoreWatch entries become regexes or cwd-resolved paths. devtools disables its UI in watch mode; otherwise ui defaults to whether @vitejs/devtools/cli exists. If exe is enabled, validateSea validates the config. Finally the config object is replicated per format: object-form format yields one config per key with per-format overrides spread on top; array/comma-form uses resolveComma; copy and onSuccess are kept only on the first (idx 0) replica and format is normalized.

**Notes.**

- side_effect: Emits logger warnings/info messages for deprecated options, missing package.json, env file usage, and empty envPrefix.

calls: [options.ts-merge-and-flag-helpers](config-merging.md#u-8ed4832a9578), [filterEnv](config-merging.md#u-bab6e24b1339), [loadViteConfig](config-file-loading.md#u-0db73e2398fc), [readPackageJson](package-metadata.md#u-75e57eaf2966), [normalizeFormat](package-metadata.md#u-4374d0c5e362), [createLogger](logging.md#u-44145ce36528), [toArray](general-and-fs.md#u-1e9a5d8a9f7d), [resolveComma](general-and-fs.md#u-adfdd23335a0), [resolveRegex](general-and-fs.md#u-85b32d43a2f4), [pkgExists](general-and-fs.md#u-2cf9b0e46dec), [validateSea](exe-output.md#u-788f5b9b60dc)

**Uncertainties.**

- Exact behavior of resolveEntry, resolveTarget, resolveTsconfig, resolveClean, and resolveDepsConfig is defined in their own modules.

<a id="u-bab6e24b1339"></a>
### `filterEnv`

`function filterEnv( envDict: Record<string, string | undefined>, envPrefixes: string[…` · [src/config/options.ts:L333-L344][f1]

Filters an environment dictionary to entries whose key starts with one of the given prefixes and whose value is not null/undefined; returns a new plain record without mutating the input.

<a id="u-8ed4832a9578"></a>
### `options.ts-merge-and-flag-helpers`

`export function mergeConfig( defaults: UserConfig, overrides: UserConfig, ): UserConfig` · [src/config/options.ts:L353-L356][f1]

Merging and flag-resolution helpers.

The module defu instance treats arrays as replace rather than concat: when both existing and incoming values are arrays the incoming array wins. mergeConfig (three overloads, one implementation) deep-merges overrides over defaults using that defu, so arrays in overrides replace arrays in defaults. mergeUserOptions accepts a static object or an async function receiving the defaults plus extra args; a function returning void/null (or a falsy static value) yields the defaults unchanged, otherwise the user object is defu-merged over the defaults. resolveFeatureOption normalizes a WithEnabled feature flag to a concrete options object or false: an object value keeps the whole object when resolveCIOption(enabled ?? true) passes and is false otherwise; a boolean/string value yields the supplied defaults when enabled and false otherwise. resolveCIOption maps 'ci-only' to true only inside CI (isInCi), 'local-only' to true only outside CI, and passes plain booleans through. filterConfig gates a config by name or cwd: no filter always passes; a RegExp filter passes if it matches the name or the process.cwd()-relative config cwd (rendered as '.' when identical); an array/string filter passes when any value equals the name or the relative cwd.

calls: [toArray](general-and-fs.md#u-1e9a5d8a9f7d)

**Uncertainties.**

- Non-array conflict resolution follows the defu library's merge semantics, which are external.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/rolldown/tsdown/blob/2b1be7e0accdb1d6e903cd42642666431fc5e93d/src/config/options.ts
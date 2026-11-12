# Dependency externalization utilities

**Capability.** Decides dependency externalization and provides general helpers for debouncing, promises, imports, pattern matching, resolution checks, and array normalization.

Come here for production dependency externalization, package-name parsing, bundling audits, and shared utility helpers. The units combine dependency policy with small general-purpose functions used across the build.

**Depends on.**

- [Package export map generation](package-export-map-generation.md) · graph-confirmed · 3 edge(s)

**Depended on by.**

- [Package export map generation](package-export-map-generation.md) · graph-confirmed · 3 edge(s)
- [Package tarball validation](package-tarball-validation.md) · graph-confirmed · 4 edge(s) · Tarball validation uses dependency externalization utilities when packing and checking packages.
- [Config resolution and logging](config-resolution-and-logging.md) · graph-only · 6 edge(s)
- [Build orchestration lifecycle](build-orchestration-lifecycle.md) · graph-only · 3 edge(s)
- [Copy shortcuts target helpers](copy-shortcuts-target-helpers.md) · graph-only · 3 edge(s)
- [Rolldown option assembly](rolldown-option-assembly.md) · graph-only · 3 edge(s)
- [Watch set and chunks](watch-set-and-chunks.md) · graph-only · 2 edge(s)
- [CLI entry and debug](cli-entry-and-debug.md) · graph-only · 1 edge(s)
- [Config file loading](config-file-loading.md) · graph-only · 1 edge(s)
- [Entry and path resolution](entry-and-path-resolution.md) · graph-only · 1 edge(s)
- [Executable SEA builds](executable-sea-builds.md) · graph-only · 1 edge(s)

Parent: [Package output and validation](package-output-and-validation.md)

## Units (13)

<a id="u-11b7d7f0f9bf"></a>
### `deps.ts-depplugin-factory`

`export function DepPlugin( { pkg, deps: { alwaysBundle, onlyAllowBundle, skipNodeModu…` · [src/features/deps.ts:L182-L197][f1]

Creates the externalization plugin that marks production dependencies external and audits bundled node_modules dependencies.

It captures production dependency names when a package is present and returns a plugin with resolveId and post-generateBundle handlers. The resolveId handler delegates externalization decisions to the strategy function; the generateBundle handler delegates dependency parsing and onlyAllowBundle enforcement. It also records inlined package versions and importers into the shared bundle record.

<a id="u-7e883bfc5141"></a>
### `general.ts-debounce`

`export function debounce<T extends (...args: any[]) => any>( fn: T, delay: number, ):…` · [src/utils/general.ts:L100-L105][f2]

Returns a debounced wrapper around a function.

Each wrapper call clears any pending timer and schedules the function with the latest arguments after the delay; the wrapper itself returns void. The wrapper exposes cancel, which clears the pending timer. There is no immediate invocation and no promise result.

<a id="u-afbc02c36336"></a>
### `general.ts-promise-resolver-and-assertion-helper`

`export function promiseWithResolvers<T>(): { promise: Promise<T> resolve: (value: T) …` · [src/utils/general.ts:L84-L94][f2]

Creates a promise and exposes its resolve function.

The resolve binding is passed through an assertion helper that has an empty body and performs no runtime check, only narrowing types for the compiler; no reject function is exposed.

<a id="u-f2a4005226e8"></a>
### `externalStrategy`

`async function externalStrategy( context: PluginContext, id: string, importer: string…` · [src/features/deps.ts:L305-L341][f1]

Decides externalization for an import using shim, alwaysBundle, skipNodeModulesBundle, production deps, and dts type packages.

The shim file returns false. A truthy alwaysBundle result returns 'no-external'. With skipNodeModulesBundle, a resolved id that is external or under node_modules returns true. Production deps match exact names or subpaths; dts importers also match a generated @types name unless the id already starts with @types/. Otherwise it returns false. The doc comment lists 'absolute', but the implementation never returns it.

<a id="u-bd95157b459a"></a>
### `getProductionDeps`

`function getProductionDeps(pkg: PackageJson): Set<string>` · [src/features/deps.ts:L347-L352][f1]

Collects dependency and peerDependency names from package.json.

It returns a Set of keys from both maps, treating missing maps as empty. No filtering or version handling is performed.

<a id="u-cdada5ac8cd6"></a>
### `parseBundledDep`

`async function parseBundledDep( moduleId: string, ): Promise<{ name: string; pkgName:…` · [src/features/deps.ts:L152-L180][f1]

Parses a module id inside node_modules to identify package name, package.json name, and version.

It normalizes slashes, finds the last `/node_modules/`, and returns undefined if absent. Scoped packages use two path segments; others use one. It reads and parses the package.json at the package root. Read or parse failures are swallowed and return undefined.

<a id="u-d376915de2cd"></a>
### `resolveDepsConfig`

`export function resolveDepsConfig( config: UserConfig, logger?: Logger, ): ResolvedDe…` · [src/features/deps.ts:L72-L150][f1]

Resolves dependency bundling options, translating deprecated aliases and validating mutually exclusive settings.

Deprecated `external`, `noExternal`, `inlineOnly`, and top-level `skipNodeModulesBundle` are applied only when non-null; each conflicts with its corresponding deps field only when that field is non-null, so null or undefined is accepted. Conflicts throw TypeError; otherwise a warning is logged and the alias value is used. String neverBundle/alwaysBundle values become regexes. Non-function alwaysBundle values become matcher functions. skipNodeModulesBundle with any alwaysBundle throws TypeError. onlyAllowBundle is array-normalized unless false. Returns the resolved object.

<a id="u-8a2c1f74a314"></a>
### `DepPlugin.handler`

`async handler(id, importer, extraOptions)` · [src/features/deps.ts:L197-L218][f1]

Resolves non-relative imports by deciding whether to externalize them.

The filter only admits ids not starting with a dot and with a non-empty importer. Entry imports return undefined. After asserting the importer, it asks the strategy function and checks whether the id is a Node builtin. A true strategy result returns an external resolution; builtins get moduleSideEffects false, others leave it undefined. Other strategy results return undefined. The strategy never returns the documented 'absolute' value in this implementation.

<a id="u-e38afaf1c0f3"></a>
### `src/features/deps.ts:DepPlugin.handler`

`async handler(options, bundle)` · [src/features/deps.ts:L223-L295][f1]

Audits bundled node_modules dependencies and enforces onlyAllowBundle after generation.

It skips assets, parses each chunk module id, and records dependency names, package versions, and importers. When onlyAllowBundle is truthy, dependencies not matching its patterns are reported through this.error with importer details; unused patterns are logged. When onlyAllowBundle is null and dependencies were found, it logs a hint. When onlyAllowBundle is false, neither error nor hint is emitted. It mutates the shared inlinedDeps map.

<a id="u-6e036190d6a7"></a>
### `importWithError`

`export async function importWithError<T>( moduleName: string, resolvePaths?: string[]…` · [src/utils/general.ts:L61-L81][f2]

Imports a module, optionally resolving it first through require.resolve with supplied paths and converting that path to a file URL.

The require.resolve step runs before the try block, so its failures propagate unwrapped. The dynamic import is wrapped: any import failure throws a new Error naming the module and preserving the original error as cause.

<a id="u-f95494f1507b"></a>
### `matchPattern`

`export function matchPattern( id: string, patterns: (string | RegExp)[], ): boolean` · [src/utils/general.ts:L40-L51][f2]

Tests an id against a list of patterns and returns true if any matches.

A RegExp pattern has lastIndex reset to 0 before test. A string pattern matches by exact equality or by glob matching; exact equality short-circuits the glob call.

<a id="u-2cf9b0e46dec"></a>
### `pkgExists`

`export function pkgExists(moduleName: string): boolean` · [src/utils/general.ts:L53-L59][f2]

Reports whether a module name can be resolved by import.meta.resolve.

Resolution success returns true; any thrown resolution error is caught and returns false. It does not import the module.

<a id="u-1e9a5d8a9f7d"></a>
### `toArray`

`export function toArray<T>( val: T | T[] | null | undefined, defaultValue?: T, ): T[]` · [src/utils/general.ts:L4-L16][f2]

Normalizes a value to an array.

Arrays are returned as-is; null or undefined returns a one-element array only when the optional default is truthy, otherwise an empty array; any other value is wrapped in a one-element array. Falsy defaults such as 0, empty string, or false therefore produce an empty array.

Look up code: the commands are under "Read further" in [INDEX.md](../INDEX.md); `cbe query` and `cbe source` take a unit title or anchor from this page.

[f1]: https://github.com/rolldown/tsdown/blob/2b1be7e0accdb1d6e903cd42642666431fc5e93d/src/features/deps.ts
[f2]: https://github.com/rolldown/tsdown/blob/2b1be7e0accdb1d6e903cd42642666431fc5e93d/src/utils/general.ts

# Dependency handling and general utilities

**Capability.** Handles dependency externals and bundling policy plus shared general helpers like debounce, pattern matching, and dynamic imports.

Come here for dependency externalization, onlyAllowBundle enforcement, package.json dependency parsing, and deprecated option migration. The general.ts helpers (debounce, promiseWithResolvers, import resolution) are shared across the codebase.

**Depends on.**

- [Config resolution and normalization](config-resolution-and-normalization.md) · graph-only · 2 edge(s)

**Depended on by.**

- [Package exports generation](package-exports-generation.md) · graph-confirmed · 7 edge(s) · Exports generation uses shared dependency and general utilities for path and pattern handling.
- [Package lint checks](package-lint-checks.md) · graph-confirmed · 5 edge(s)
- [Config resolution and normalization](config-resolution-and-normalization.md) · graph-only · 5 edge(s)
- [Build orchestration and lifecycle](build-orchestration-and-lifecycle.md) · graph-only · 4 edge(s)
- [Rolldown option assembly](rolldown-option-assembly.md) · graph-only · 4 edge(s)
- [Config file loading](config-file-loading.md) · graph-only · 2 edge(s)
- [Entry resolution and filesystem helpers](entry-resolution-and-filesystem-helpers.md) · graph-only · 2 edge(s)
- [CLI entry and debug](cli-entry-and-debug.md) · graph-only · 1 edge(s)
- [Single executable builds](single-executable-builds.md) · graph-only · 1 edge(s)

Parent: [Package metadata and utilities](package-metadata-and-utilities.md)

## Units (12)

<a id="u-b9da2c60c1f3"></a>
### `deps.ts-depplugin-generatebundle`

`export function DepPlugin( { pkg, deps: { alwaysBundle, onlyAllowBundle, skipNodeModu…` · [src/features/deps.ts:L218-L223][f1]

Post-ordered generateBundle that scans bundled chunks for node_modules dependencies and enforces onlyAllowBundle.

For each chunk module id, parseBundledDep extracts the package; found packages are recorded in tsdownBundle.inlinedDeps (pkgName -> set of versions) and their importers collected via getModuleInfo. If onlyAllowBundle is truthy, any bundled dep not matching the patterns triggers this.error with a per-dep message listing importers; patterns matching no bundled dep produce an info log suggesting removal. If onlyAllowBundle is null and deps were bundled, it logs a hint listing detected deps and pointing to the onlyAllowBundle option; onlyAllowBundle === false suppresses everything. Assets are skipped.

calls: [parseBundledDep](dependency-handling-and-general-utilities.md#u-cdada5ac8cd6)

<a id="u-43c34d98d8b2"></a>
### `deps.ts-depplugin-resolveid`

`export function DepPlugin( { pkg, deps: { alwaysBundle, onlyAllowBundle, skipNodeModu…` · [src/features/deps.ts:L182-L197][f1]

Factory returning the 'tsdown:external' plugin whose resolveId handler externalizes production/peer dependencies for non-entry relative-importer matches.

The filter only fires for ids not starting with '.' with a non-empty importer; entries are skipped. It delegates to externalStrategy: on true or 'absolute' it returns {id, external, moduleSideEffects: false for Node builtins, else undefined}; 'no-external' and false fall through so other resolvers handle the id.

calls: [deps.ts-externalstrategy](dependency-handling-and-general-utilities.md#u-3e33a98fd547)

<a id="u-3e33a98fd547"></a>
### `deps.ts-externalstrategy`

`export function DepPlugin( { pkg, deps: { alwaysBundle, onlyAllowBundle, skipNodeModu…` · [src/features/deps.ts:L295-L305][f1]

Decides externality for a module id: true = always external, false = defer to other plugins, 'absolute' = external as absolute path, 'no-external' = defer but mark non-external.

Order: the shim file is never external; alwaysBundle match returns 'no-external'; with skipNodeModulesBundle, a resolve() that is external or under node_modules returns true; if the package's production deps exist, an exact or `${dep}/`-prefixed id returns true, and a .d.ts importer of a non-@types id maps to `@types/<mangled>` and returns true if that types package is a production dep; otherwise false.

calls: [getProductionDeps](dependency-handling-and-general-utilities.md#u-bd95157b459a)

<a id="u-7e883bfc5141"></a>
### `general.ts-debounce`

`export function debounce<T extends (...args: any[]) => any>( fn: T, delay: number, ):…` · [src/utils/general.ts:L100-L105][f2]

Returns a wrapper that resets a timer on each call and invokes the original function with the latest arguments only after `delay` ms of quiet; the wrapper carries a cancel() that clears the pending timer.

The inner debounced function and its cancel attachment are the implementation, not separate API.

<a id="u-c9c621cbb4b4"></a>
### `general.ts-general-string-regex-helpers`

`export function resolveComma<T extends string>(arr: T[]): T[]` · [src/utils/general.ts:L18-L20][f2]

resolveComma splits each string in an array on commas and flattens the results.

resolveRegex converts a string longer than 2 chars that both starts and ends with '/' into a RegExp of the inner content; anything else is returned unchanged. slash replaces all backslashes with forward slashes. noop is the identity function.

<a id="u-2605d6af7f4c"></a>
### `general.ts-promise-type-assertion-helpers`

`export function promiseWithResolvers<T>(): { promise: Promise<T> resolve: (value: T) …` · [src/utils/general.ts:L84-L94][f2]

promiseWithResolvers hand-rolls Promise.withResolvers: it captures the resolve callback from the Promise executor (typeAssert asserts it was assigned) and returns { promise, resolve }.

typeAssert is a no-op assertion signature narrowing out false/null/undefined.

<a id="u-bd95157b459a"></a>
### `getProductionDeps`

`function getProductionDeps(pkg: PackageJson): Set<string>` · [src/features/deps.ts:L347-L352][f1]

Returns the set of dependency and peerDependency names from a package.json, used to decide what stays external.

<a id="u-cdada5ac8cd6"></a>
### `parseBundledDep`

`async function parseBundledDep( moduleId: string, ): Promise<{ name: string; pkgName:…` · [src/features/deps.ts:L152-L180][f1]

Parses a module id under node_modules into {name, pkgName, version} by reading its package.json; returns undefined otherwise.

Finds the last '/node_modules/' segment; scoped packages take two path parts. Reads and JSON-parses package.json from the package root; any read/parse failure is swallowed and yields undefined.

**Uncertainties.**

- The empty catch means all package.json read/parse errors are indistinguishable from non-node_modules ids.

<a id="u-d376915de2cd"></a>
### `resolveDepsConfig`

`export function resolveDepsConfig( config: UserConfig, logger?: Logger, ): ResolvedDe…` · [src/features/deps.ts:L72-L150][f1]

Resolves dependency-bundling options, migrating four deprecated top-level options into the deps namespace with type errors on conflicts.

If `external`/`noExternal`/`inlineOnly`/`skipNodeModulesBundle` is set, the corresponding deps.* value must be null or a TypeError is thrown; otherwise the deprecated value is adopted and a warning logged. String neverBundle/alwaysBundle become regexes via resolveRegex. Non-function alwaysBundle becomes a matcher (id) => matchPattern(id, patterns). skipNodeModulesBundle together with a non-null alwaysBundle throws a TypeError (mutual exclusivity). onlyAllowBundle is array-normalized unless false. Returns the resolved config with skipNodeModulesBundle defaulting to false.

**Notes.**

- failure: Four distinct TypeErrors: each deprecated option paired with its deps.* replacement, plus skipNodeModulesBundle+alwaysBundle conflict.

calls: [matchPattern](../../catalog.json)

<a id="u-6e036190d6a7"></a>
### `importWithError`

`export async function importWithError<T>( moduleName: string, resolvePaths?: string[]…` · [src/utils/general.ts:L61-L81][f2]

Dynamically imports a module, optionally resolving it first through require.resolve with the given paths and converting to a file URL.

Any import failure is rethrown wrapped in a new Error naming the module and suggesting installation, with the original error as `cause`. Note: the require.resolve call itself is outside the try block, so its failures propagate unwrapped.

<a id="u-f95494f1507b"></a>
### `matchPattern`

`export function matchPattern( id: string, patterns: (string | RegExp)[], ): boolean` · [src/utils/general.ts:L40-L51][f2]

Tests an id against a list of string or RegExp patterns, returning true on the first match.

RegExp patterns have lastIndex reset before test (safe for global regexes); strings match by exact equality or via picomatch glob matching.

<a id="u-2cf9b0e46dec"></a>
### `pkgExists`

`export function pkgExists(moduleName: string): boolean` · [src/utils/general.ts:L53-L59][f2]

Checks whether a module can be resolved from the current context via import.meta.resolve, returning true on success and false on any resolution error (caught and ignored).

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/rolldown/tsdown/blob/2b1be7e0accdb1d6e903cd42642666431fc5e93d/src/features/deps.ts
[f2]: https://github.com/rolldown/tsdown/blob/2b1be7e0accdb1d6e903cd42642666431fc5e93d/src/utils/general.ts

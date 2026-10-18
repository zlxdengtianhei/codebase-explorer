# Dependency Externalization

**Capability.** Decides which dependencies stay external versus inlined, validates and normalizes the deps options, and audits bundled node_modules dependencies.

Use this subtree when troubleshooting what ends up inside the bundle versus left external. It owns the tsdown:external plugin plus the config normalization and package metadata parsing behind it.

**Depends on.**

- [General and Filesystem Helpers](general-and-fs.md) · graph-confirmed · 9 edge(s)
- [Package Metadata Helpers](package-metadata.md) · model-inferred · 0 edge(s)
- [Package Publishing](package-publishing.md) · graph-confirmed · 2 edge(s)

**Depended on by.**

- [User Config Normalization](config-merging.md) · graph-confirmed · 1 edge(s)
- [Rolldown Options Assembly](rolldown-assembly.md) · containment · → 1 / ← 0 edge(s) (ancestor direct units and descendant subtree; → follows ` rolldown-assembly ` → ` externalization `) · Input options assembly wires the dependency externalization plugin into the plugin pipeline.

Parent: [Rolldown Options Assembly](rolldown-assembly.md)

## Units (9)

<a id="u-bb7e95b646eb"></a>
### `deps-ts-dep-plugin`

`export function DepPlugin( { pkg, deps: { alwaysBundle, onlyAllowBundle, skipNodeModu…` · [src/features/deps.ts:L182-L197][f1]

Builds the 'tsdown:external' Rolldown plugin that decides which dependencies stay external and audits inlined ones.

resolveId (filtered to non-relative ids imported from a real importer) skips entry modules, asserts the importer exists via typeAssert, delegates to externalStrategy, and when the strategy returns true or 'absolute' returns the id as external, marking builtins as having no side effects; false or 'no-external' leaves resolution to other plugins. externalStrategy returns false for the shims file; 'no-external' when alwaysBundle matches; true under skipNodeModulesBundle when resolution lands on an external or node_modules path; true when the id matches production deps (including @types packages referenced from dts importers, ignoring @types/* ids); otherwise false. generateBundle (post) scans every non-asset chunk's moduleIds via parseBundledDep, recording dep names and versions into tsdownBundle.inlinedDeps and importer sets. With onlyAllowBundle set, it calls this.error listing unlisted deps and their importers (aborting the bundle) and logs unused allow-list patterns; when onlyAllowBundle is merely unset and bundled deps exist, it logs an informational hint suggesting the option.

calls: [typeAssert](general-and-fs.md#u-2d6f421314ba), [matchPattern](general-and-fs.md#u-f95494f1507b), [parseBundledDep](externalization.md#u-cdada5ac8cd6), [getProductionDeps](externalization.md#u-bd95157b459a); uses: [join](package-publishing.md#u-70c06da6dd04)

**Uncertainties.**

- The plugin is only constructed when config.pkg or deps.skipNodeModulesBundle is set, per resolveInputOptions; behavior without a package.json for the externalStrategy deps branch is therefore config-dependent.

<a id="u-bd95157b459a"></a>
### `getProductionDeps`

`function getProductionDeps(pkg: PackageJson): Set<string>` · [src/features/deps.ts:L347-L352][f1]

Returns the set of dependency names from the package's `dependencies` and `peerDependencies` fields, defaulting each missing field to an empty object.

<a id="u-cdada5ac8cd6"></a>
### `parseBundledDep`

`async function parseBundledDep( moduleId: string, ): Promise<{ name: string; pkgName:…` · [src/features/deps.ts:L152-L180][f1]

Extracts package metadata for a bundled module id found under node_modules.

It slash-normalizes the id, and returns undefined if '/node_modules/' never appears. The package name after the last node_modules segment handles scoped names ('@scope/pkg'); the package root is the id prefix up to that name. It then reads and parses the root's package.json and returns { name, pkgName, version }. Any read/parse error is swallowed, returning undefined.

**Notes.**

- failure: Missing or invalid package.json is silently ignored (empty catch), so the module is treated as not a bundled dependency.

calls: [slash](general-and-fs.md#u-9bf13c522663)

<a id="u-d376915de2cd"></a>
### `resolveDepsConfig`

`export function resolveDepsConfig( config: UserConfig, logger?: Logger, ): ResolvedDe…` · [src/features/deps.ts:L72-L150][f1]

Validates and normalizes the deps configuration, migrating deprecated top-level options.

Each deprecated option (`external`, `noExternal`, `inlineOnly`, top-level `skipNodeModulesBundle`) throws a TypeError if its new `deps.*` counterpart is also set, otherwise logs a deprecation warning through the optional logger and adopts the value. String `neverBundle` and `alwaysBundle` values are converted via resolveRegex; a non-function `alwaysBundle` is wrapped into a predicate using matchPattern. `skipNodeModulesBundle` together with `alwaysBundle` throws a TypeError as mutually exclusive. `onlyAllowBundle` (unless false/null) is normalized to an array. Returns the resolved config with skipNodeModulesBundle defaulting to false.

**Notes.**

- failure: Four distinct TypeError cases: deprecated option paired with its replacement, and skipNodeModulesBundle+alwaysBundle.

calls: [resolveRegex](general-and-fs.md#u-85b32d43a2f4), [matchPattern](general-and-fs.md#u-f95494f1507b), [toArray](general-and-fs.md#u-1e9a5d8a9f7d)

<a id="u-9cf86604171b"></a>
### `DepsConfig`

`export interface DepsConfig` · [src/features/deps.ts:L35-L63][f1]

Public deps option interface: neverBundle, alwaysBundle, onlyAllowBundle (false suppresses warnings), skipNodeModulesBundle, documented with their semantics.

<a id="u-a23279477926"></a>
### `ResolvedDepsConfig`

`export interface ResolvedDepsConfig` · [src/features/deps.ts:L65-L70][f1]

Normalized output shape of resolveDepsConfig: alwaysBundle as NoExternalFn, onlyAllowBundle as array-or-false, skipNodeModulesBundle required boolean.

<a id="u-d454df704ad8"></a>
### `NoExternalFn`

`export type NoExternalFn = ( id: string, importer: string | undefined, ) => boolean |…` · [src/features/deps.ts:L30-L33][f1]

Type alias for the alwaysBundle predicate signature: (id, importer) => boolean | null | undefined | void.

<a id="u-e7e7cb630b65"></a>
### `deps.ts module code (L1–L29)`

`module_region` · [src/features/deps.ts:L1-L29][f1]

Module imports and the tsdown:dep debug logger instance.

<a id="u-6acc74635584"></a>
### `deps.ts module code (L342–L346)`

`module_region` · [src/features/deps.ts:L342-L346][f1]

Trailing comment noting production deps are excluded from the bundle.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/rolldown/tsdown/blob/2b1be7e0accdb1d6e903cd42642666431fc5e93d/src/features/deps.ts
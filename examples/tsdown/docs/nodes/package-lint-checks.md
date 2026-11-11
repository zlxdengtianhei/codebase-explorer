# Package lint checks

**Capability.** Runs publint and are-the-types-wrong checks on packed tarballs, coordinating per-package post-build work across bundles.

Come here for post-build package validation: packing tarballs, running ATTW and publint, and merging results per package. Also coordinates bundle-by-package grouping and inlined dependency version merging.

**Depends on.**

- [Dependency handling and general utilities](dependency-handling-and-general-utilities.md) · graph-confirmed · 5 edge(s)
- [Package exports generation](package-exports-generation.md) · graph-confirmed · 1 edge(s) · Package lint checks use exports generation while coordinating per-package post-build work.
- [Entry resolution and filesystem helpers](entry-resolution-and-filesystem-helpers.md) · graph-only · 1 edge(s)

**Depended on by.**

- [Build orchestration and lifecycle](build-orchestration-and-lifecycle.md) · graph-only · 1 edge(s)

Parent: [Package metadata and utilities](package-metadata-and-utilities.md)

## Units (10)

<a id="u-0e392c6d6980"></a>
### `index.ts-per-package-bundle-registry`

`export interface BundleByPkg` · [src/features/pkg/index.ts:L14-L22][f1]

initBundleByPkg groups configs by their package.json path, returning a map (BundleByPkg) holding a promise/resolve pair, a count of configs, a set of their formats, and an empty bundles array per package.

Configs without a package.json are skipped; the first config for a package creates the entry via promiseWithResolvers, and every config increments count and adds its format.

<a id="u-17466036fb34"></a>
### `attw`

`export async function attw( options: ResolvedConfig, tarball: Buffer<ArrayBuffer>, ):…` · [src/features/pkg/attw.ts:L95-L166][f2]

Runs the are-the-types-wrong check on a packed tarball and reports problems through the config logger.

Returns immediately if attw is disabled or no package.json was found (warn in the latter case). Destructures profile (default 'strict'), level (default 'warn'), and ignoreRules (default []) from options.attw, passing the rest to the core check. Warns if any ignoreRules value is not a known problem flag. Loads @arethetypeswrong/core via importWithError with resolvePaths, creates a package from the tarball buffer, and checks it. If the result has types, filters problems: ignored kinds are dropped; problems with a resolutionKind are kept only when their kind is not in the profile's ignore list (strict ignores none, node16 ignores node10, esm-only ignores node10 and node16-cjs); other problems always pass. Remaining problems are formatted (one line each) into an error message; a package without types yields 'Package has no types'. On error message it logs via logger[level] (so 'error' can fail the build); otherwise logs success with elapsed ms.

calls: [formatProblem](../../catalog.json), [importWithError](../../catalog.json)

**Uncertainties.**

- Whether logger.error actually fails the build depends on the logger implementation, not visible here.

<a id="u-50180c862a03"></a>
### `formatProblem`

`function formatProblem(packageName: string, problem: Problem): string` · [src/features/pkg/attw.ts:L171-L227][f2]

Renders a single ATTW problem as a human-readable line, prefixing resolution kind and entrypoint (path joined with the package name, slash-normalized) when present.

Each ProblemKind gets a distinct message: NoResolution (❌), UntypedResolution (⚠️), FalseESM/FalseCJS (module-kind mismatch with types and implementation file names), CJSResolvesToESM (⚡), NamedExports (with optional missing-export list and all-missing marker), FallbackCondition, FalseExportDefault, MissingExportEquals, InternalResolutionError (file, option, specifier, mode), UnexpectedModuleSyntax (syntax 99 shown as ESM, else CJS), and CJSOnlyExportsDefault. Unknown kinds fall back to JSON.stringify of the problem.

calls: [slash](../../catalog.json)

<a id="u-43e206dc438b"></a>
### `AttwOptions`

`export interface AttwOptions extends CheckPackageOptions` · [src/features/pkg/attw.ts:L31-L81][f2]

Options interface for the are-the-types-wrong check, extending CheckPackageOptions with a profile selector (strict/node16/esm-only, default strict), a level (error/warn, default warn), an ignoreRules list of problem-kind flag names, and an internal resolvePaths for module resolution.

<a id="u-a3955ba81d03"></a>
### `bundleDone`

`export async function bundleDone( bundleByPkg: BundleByPkg, bundle: TsdownBundle, ): …` · [src/features/pkg/index.ts:L49-L112][f1]

Coordinates per-package post-build work once all of a package's bundles have finished.

Ignores bundles without a package; otherwise pushes the bundle into the package's registry and, if not all expected bundles have arrived yet, awaits the registry promise. Once complete, it collects the configs and dedupes those with exports options: more than one distinct exports config throws an Error listing the conflicting options (formatted with colors) and asking to merge them; a single config triggers writeExports with chunks merged per format (skipping bundles without exports options) and inlined deps merged across bundles. It then dedupes publint and attw configs; if either has multiple entries it warns (via the second publint config's logger) that configurations should be merged. If any publint or attw config exists, it packs a tarball once and runs all checks concurrently via Promise.all; any error there is caught and logged as 'Pack failed:' by the first config's logger rather than propagated. Finally resolves the registry promise so other waiters proceed.

calls: [writeExports](../../catalog.json), [packTarball](../../catalog.json), [publint](../../catalog.json), [attw](../../catalog.json), [dedupeConfigs](../../catalog.json), [mergeInlinedDeps](../../catalog.json)

**Uncertainties.**

- The warn for multiple publint/attw configs indexes publintConfigs[1] without checking it exists; if only attw has multiple entries this could be undefined and throw, depending on config shapes.

<a id="u-bad4077ee69a"></a>
### `dedupeConfigs`

`function dedupeConfigs<K extends 'publint' | 'attw' | 'exports'>( configs: Array<Reso…` · [src/features/pkg/index.ts:L139-L162][f1]

Filters configs to those with a truthy value for the given key (publint, attw, or exports) and removes duplicates by reference identity, also dropping configs whose option object has no keys.

Returns an empty array when no config has the option; if all candidates were filtered out as empty or duplicate, returns the first candidate so at least one config is kept.

<a id="u-544ed4bb2928"></a>
### `mergeInlinedDeps`

`function mergeInlinedDeps( bundles: TsdownBundle[], ): Record<string, string | string…` · [src/features/pkg/index.ts:L164-L186][f1]

Merges inlined dependency version sets across all bundles of a package into a single record.

Returns undefined when nothing was inlined; a package with one version maps to that version string, and multiple versions map to a sorted array of the distinct versions.

<a id="u-ecb7dfeaef07"></a>
### `packTarball`

`async function packTarball( packageJsonPath: string, ): Promise<Buffer<ArrayBuffer>>` · [src/features/pkg/index.ts:L114-L137][f1]

Packs a package directory into a tarball buffer for lint checks.

Creates a temp directory under the OS tmpdir, dynamically imports the package-manager detector and @publint/pack in parallel, detects the package manager from the package directory, and refuses Deno projects with an explicit error. Packs with the detected package manager name and ignoreScripts true, reads the tarball file into a Buffer, and always removes the temp directory in a finally block; detection or pack failures propagate after cleanup.

<a id="u-f3ab9c1c8af3"></a>
### `publint`

`export async function publint( options: ResolvedConfig, tarball: Buffer<ArrayBuffer>,…` · [src/features/pkg/publint.ts:L16-L63][f3]

Runs the publint check on a packed tarball and logs each message.

Returns immediately if publint is disabled or no package.json was found (warn in the latter case). Loads publint and publint/utils via importWithError using the configured resolvePaths, then runs publint with pack set to the tarball buffer. With no messages it logs success with elapsed ms; otherwise each message is formatted with formatMessage and logged at error/warn/info corresponding to its error/warning/suggestion type.

calls: [importWithError](../../catalog.json)

**Uncertainties.**

- The source file's parse tree contains a syntax-error node near line 1 per diagnostics; the visible implementation is coherent but the excerpt may not be the exact on-disk source.

<a id="u-7c72f46fda2a"></a>
### `PublintOptions`

`export interface PublintOptions extends Omit<Options, 'pack' | 'pkgDir'>` · [src/features/pkg/publint.ts:L11-L14][f3]

Options interface for the publint check, extending publint's Options minus its pack and pkgDir fields (both supplied by the runner) and adding an internal resolvePaths for module resolution.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/rolldown/tsdown/blob/2b1be7e0accdb1d6e903cd42642666431fc5e93d/src/features/pkg/index.ts
[f2]: https://github.com/rolldown/tsdown/blob/2b1be7e0accdb1d6e903cd42642666431fc5e93d/src/features/pkg/attw.ts
[f3]: https://github.com/rolldown/tsdown/blob/2b1be7e0accdb1d6e903cd42642666431fc5e93d/src/features/pkg/publint.ts

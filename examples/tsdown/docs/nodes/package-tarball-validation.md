# Package tarball validation

**Capability.** Collects completed bundles, writes exports, packs packages, and runs publint/ATTW checks with formatted logging.

Come here for post-bundle package validation and tarball checks. Units cover completion coordination, temporary packing, publint/ATTW execution, and problem formatting.

**Depends on.**

- [Dependency externalization utilities](dependency-externalization-utilities.md) · graph-confirmed · 4 edge(s) · Tarball validation uses dependency externalization utilities when packing and checking packages.
- [Package export map generation](package-export-map-generation.md) · graph-confirmed · 2 edge(s)
- [Entry and path resolution](entry-and-path-resolution.md) · graph-only · 1 edge(s)

**Depended on by.**

- [Build orchestration lifecycle](build-orchestration-lifecycle.md) · graph-only · 2 edge(s)

Parent: [Package output and validation](package-output-and-validation.md)

## Units (8)

<a id="u-17466036fb34"></a>
### `attw`

`export async function attw( options: ResolvedConfig, tarball: Buffer<ArrayBuffer>, ):…` · [src/features/pkg/attw.ts:L95-L166][f1]

Runs an ATTW package check on a tarball and reports filtered problems through the configured logger.

- If the attw option is absent: return silently.
- If package metadata is absent: warn and return.
- Defaults are profile strict, level warn, and no ignored rules; invalid ignored-rule names warn but do not stop the check.
- The core module is imported dynamically, a package is created from the tarball, and the package is checked.
- If the result has no types: report 'Package has no types'.
- Otherwise drop problems whose kind flag is ignored, and for problems carrying a resolution kind drop those whose resolution kind is listed in the selected profile's ignore list; keep all other problems.
- Remaining problems are formatted individually and joined with newlines; those formatted entries may themselves be multi-line.
- Any resulting message is logged at the configured level; otherwise a success message includes elapsed milliseconds.
Import and check errors are not caught here.

<a id="u-50180c862a03"></a>
### `formatProblem`

`function formatProblem(packageName: string, problem: Problem): string` · [src/features/pkg/attw.ts:L171-L227][f1]

Formats one ATTW problem into a human-readable string, using multi-line output for several problem kinds.

- Resolution-kind and entrypoint suffixes are appended only when the problem carries those fields; the entrypoint is joined with the package name and slash-normalized.
- No-resolution, untyped-resolution, CJS-resolves-to-ESM, and fallback-condition cases are single-line entries with those suffixes.
- False-ESM and false-CJS cases are two-line entries showing module kinds and types/implementation file names.
- Named-exports cases are two-line entries; they add an all-missing marker when applicable and a missing-name list when nonempty.
- False-export-default and missing-export-equals cases are two-line entries with types/implementation file names.
- Internal-resolution-error and unexpected-module-syntax cases are two-line entries; syntax value 99 is rendered as ESM, otherwise CJS.
- CJS-only-exports-default is a single-line entry with the file name.
- Unknown kinds fall back to a JSON dump of the problem.

<a id="u-a3955ba81d03"></a>
### `bundleDone`

`export async function bundleDone( bundleByPkg: BundleByPkg, bundle: TsdownBundle, ): …` · [src/features/pkg/index.ts:L49-L112][f2]

Collects completed bundles per package, writes exports once all expected bundles arrive, then runs publint/ATTW checks.

- A bundle without package metadata returns immediately.
- The bundle is pushed into its package context; if fewer bundles than expected have arrived, the shared promise is returned so the caller waits.
- When complete, exports configs are deduplicated. More than one throws a conflicting-exports error before the shared promise is resolved; exactly one triggers export writing with chunks grouped by format from bundles that have exports and merged inlined dependencies.
- Publint and ATTW configs are deduplicated. If either has more than one, a warning is emitted through the second publint config; that access is unguarded when publint has fewer than two entries.
- If any publint or ATTW configs exist, one tarball is packed and all checks run in parallel. Packing or check errors are caught, logged as 'Pack failed' through the first config logger, and not rethrown.
- The shared promise is resolved at the end. Export writing and the conflicting-exports throw occur before the try block, so their errors prevent resolution.

<a id="u-bad4077ee69a"></a>
### `dedupeConfigs`

`function dedupeConfigs<K extends 'publint' | 'attw' | 'exports'>( configs: Array<Reso…` · [src/features/pkg/index.ts:L139-L162][f2]

Filters configs by a key, removes empty option objects and duplicate object identities, with a fallback.

- No truthy key: empty result.
- Empty option object: dropped.
- Duplicate object reference: dropped, keeping the first occurrence.
- If every filtered candidate was empty, returns the first filtered candidate; duplicate filtering alone cannot empty the list because the first duplicate is kept.

<a id="u-37c1dfe4abb3"></a>
### `initBundleByPkg`

`export function initBundleByPkg(configs: ResolvedConfig[]): BundleByPkg` · [src/features/pkg/index.ts:L24-L47][f2]

Groups resolved configs by package.json path and creates a shared completion promise per package.

- Configs without a package-json path are skipped.
- The first config for a path creates a promise/resolver pair, zero count, an empty format set, and an empty bundle list.
- Every config for that path increments the count and adds its format.
- Returns the map of package paths to their shared state.

<a id="u-544ed4bb2928"></a>
### `mergeInlinedDeps`

`function mergeInlinedDeps( bundles: TsdownBundle[], ): Record<string, string | string…` · [src/features/pkg/index.ts:L164-L186][f2]

Merges inlined dependency versions across bundles into a single map.

- Versions are collected per package in sets, deduplicating across bundles.
- No packages: undefined.
- One version: stored as a string.
- Multiple versions: stored as a sorted array.

<a id="u-ecb7dfeaef07"></a>
### `packTarball`

`async function packTarball( packageJsonPath: string, ): Promise<Buffer<ArrayBuffer>>` · [src/features/pkg/index.ts:L114-L137][f2]

Creates a temporary directory, packs the package into a tarball, and returns its bytes.

- The temp directory is created under the system temp directory with a fixed prefix.
- The detector and packer modules are imported before the try block; if either import fails, the temp directory is not removed.
- Inside the try, the package manager is detected; Deno projects throw an explicit error.
- Packing uses the temp destination, detected package manager, and ignoreScripts true; the resulting tarball path is read and returned.
- The finally block removes the temp directory after imports succeed, including on detect, pack, or read errors. Errors propagate.

<a id="u-f3ab9c1c8af3"></a>
### `publint`

`export async function publint( options: ResolvedConfig, tarball: Buffer<ArrayBuffer>,…` · [src/features/pkg/publint.ts:L16-L63][f3]

Runs publint on a tarball and logs each message at a severity-derived level.

- If the publint option is absent: return silently.
- If package metadata is absent: warn and return.
- Publint and its utilities are imported dynamically with configured resolve paths; publint is called with the tarball buffer.
- No messages: success log with elapsed milliseconds and return.
- Each message is formatted with package metadata; error maps to error, warning to warn, and suggestion to info, then logs with the name label and publint label.
Import and check errors are not caught here.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/rolldown/tsdown/blob/2b1be7e0accdb1d6e903cd42642666431fc5e93d/src/features/pkg/attw.ts
[f2]: https://github.com/rolldown/tsdown/blob/2b1be7e0accdb1d6e903cd42642666431fc5e93d/src/features/pkg/index.ts
[f3]: https://github.com/rolldown/tsdown/blob/2b1be7e0accdb1d6e903cd42642666431fc5e93d/src/features/pkg/publint.ts

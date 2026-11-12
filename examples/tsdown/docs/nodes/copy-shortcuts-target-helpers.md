# Copy shortcuts target helpers

**Capability.** Runs copy operations, handles keyboard shortcuts, resolves Node targets, and warns about CJS require(ESM) compatibility.

Come here for ancillary build features: file copying, interactive shortcuts, target normalization, and a CJS compatibility warning. Units define option shapes and runtime helpers for those features.

**Depends on.**

- [Dependency externalization utilities](dependency-externalization-utilities.md) · graph-only · 3 edge(s)
- [Entry and path resolution](entry-and-path-resolution.md) · graph-only · 1 edge(s)
- [Package export map generation](package-export-map-generation.md) · graph-only · 1 edge(s)

**Depended on by.**

- [Build orchestration lifecycle](build-orchestration-lifecycle.md) · graph-confirmed · 3 edge(s) · Build lifecycle calls copy, shortcut, and target helpers during orchestration.
- [Config resolution and logging](config-resolution-and-logging.md) · graph-only · 1 edge(s)

Parent: [Build execution and watching](build-execution-and-watching.md)

## Units (7)

<a id="u-0a4e73393eea"></a>
### `copy.ts-copy-implementation`

`export async function copy(options: ResolvedConfig): Promise<void>` · [src/features/copy.ts:L39-L93][f1]

Runs configured copy operations, resolving globs and destinations, then copying files.

If copy is absent, resolves to an empty list, or matches no files, it returns; the no-match case warns. A function-valued copy is awaited. String entries become single-source entries; any dynamic source pattern triggers globbing with cwd, files only, and no directory expansion. Each resolved entry defaults flatten to true, resolves source against cwd, uses explicit destination or outDir, preserves relative directories when flatten is false and a directory exists, and applies rename as a fixed name or callback. Verbose entries log relative source/destination before fsCopy; copy errors propagate through Promise.all.

**Uncertainties.**

- Exact glob matching and negation semantics are delegated to tinyglobby and not shown.

<a id="u-0d81475842f5"></a>
### `copy.ts-copy-option-types`

`export interface CopyEntry` · [src/features/copy.ts:L8-L35][f1]

Defines the copy configuration shape: a source path or glob, optional destination, flattening, verbosity, and rename behavior.

CopyOptions is a single string/entry or a flat array of those, not nested arrays; CopyOptionsFn returns an awaitable CopyOptions. CopyEntry defaults flatten to true and verbose to false; omitted destination falls back to outDir. rename may be a fixed string or a function receiving name, extension without dot, and full source path.

<a id="u-990fb81dcc75"></a>
### `shortcuts.ts-shortcut-input-handling`

`async function onInput(input: string)` · [src/features/shortcuts.ts:L16-L19][f2]

Handles shortcut input, displays help, and runs the selected action with a running guard.

While an action is running, input is ignored. Input is trimmed and lowercased. `h` logs the shortcut list, deduplicating keys and skipping null actions. A matching key sets the guard, awaits the action, then clears it. If the action throws or rejects, the guard is never cleared, so later input remains ignored. Actions restart, clear the console, or exit the process.

<a id="u-cd50e60eb855"></a>
### `shortcuts.ts-shortcuts-factory`

`export function shortcuts(restart: () => void): () => void` · [src/features/shortcuts.ts:L14-L16][f2]

Creates a readline-based keyboard shortcut handler and returns a close function.

It keeps a running guard, defines the input handler and shortcut table, attaches a line listener to stdin, and returns a function that closes the readline interface.

<a id="u-e69cdaffd8fa"></a>
### `warnLegacyCJS`

`export function warnLegacyCJS(config: ResolvedConfig): void` · [src/features/cjs.ts:L5-L28][f3]

Warns once when a CJS build targets Node versions that support require(ESM), unless disabled or exe.

Returns immediately when exe is set, no target is configured, legacy-CJS checks are disabled, or the format list lacks cjs. Otherwise it scans targets for a Node version satisfying ^20.19.0 || >=22.12.0 after coercing the substring after 'node'; if any target matches, it emits one warning recommending ESM. Non-Node or uncoercible targets do not match. The warning is side-effect only; no value is returned.

<a id="u-1db4e976c1c8"></a>
### `resolvePackageTarget`

`export function resolvePackageTarget(pkg?: PackageJson): string | undefined` · [src/features/target.ts:L37-L44][f4]

Derives a Node target string from a package's engines.node range.

It returns undefined when the package, engine range, or minimum version is absent, and also when the minimum version is 0.0.0. Otherwise it returns node plus the minimum version. It does not validate the range beyond the min-version helper.

<a id="u-20e81acaf8a7"></a>
### `resolveTarget`

`export function resolveTarget( logger: Logger, target: string | string[] | false | un…` · [src/features/target.ts:L7-L35][f4]

Resolves target input into a normalized list, optionally falling back to the package engine.

false returns undefined; null/undefined tries the package target and returns undefined if none. A numeric target throws TypeError. Otherwise comma-separated values are flattened, logged when non-empty with singular/plural label, and returned. Package fallback and logging are side effects; no other validation is shown.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/rolldown/tsdown/blob/2b1be7e0accdb1d6e903cd42642666431fc5e93d/src/features/copy.ts
[f2]: https://github.com/rolldown/tsdown/blob/2b1be7e0accdb1d6e903cd42642666431fc5e93d/src/features/shortcuts.ts
[f3]: https://github.com/rolldown/tsdown/blob/2b1be7e0accdb1d6e903cd42642666431fc5e93d/src/features/cjs.ts
[f4]: https://github.com/rolldown/tsdown/blob/2b1be7e0accdb1d6e903cd42642666431fc5e93d/src/features/target.ts

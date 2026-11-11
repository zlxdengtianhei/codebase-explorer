# Build orchestration and lifecycle

**Capability.** Drives builds: resolving configs into parallel builds, managing watch/devtools/shortcuts lifecycles, and running post-build copy, clean, and executable side effects.

Come here for the top-level build pipeline: single-config builds, parallel multi-config orchestration, watch and devtools lifecycle, and post-build tasks. Feature files for CJS warnings, clean, copy, hooks, and shortcuts live alongside it.

**Depends on.**

- [Rolldown option assembly](rolldown-option-assembly.md) · graph-confirmed · 4 edge(s) · Build orchestration uses Rolldown option assembly to turn resolved configs into Rolldown build options.
- [Entry resolution and filesystem helpers](entry-resolution-and-filesystem-helpers.md) · graph-only · 5 edge(s)
- [Dependency handling and general utilities](dependency-handling-and-general-utilities.md) · graph-only · 4 edge(s)
- [Config resolution and normalization](config-resolution-and-normalization.md) · graph-only · 2 edge(s)
- [Config file loading](config-file-loading.md) · graph-only · 1 edge(s)
- [Logging and size reporting](logging-and-size-reporting.md) · graph-only · 1 edge(s)
- [Package lint checks](package-lint-checks.md) · graph-only · 1 edge(s)
- [Single executable builds](single-executable-builds.md) · graph-only · 1 edge(s)

**Depended on by.**

- [Config resolution and normalization](config-resolution-and-normalization.md) · graph-only · 1 edge(s)

Parent: [Build execution pipeline](build-execution-pipeline.md)

## Units (18)

<a id="u-43aaa1c449bd"></a>
### `build.ts-buildsingle`

`async function buildSingle( config: ResolvedConfig, configFiles: string[], isDualForm…` · [src/build.ts:L127-L156][f1]

Builds one resolved config without watch/shortcut orchestration.

It creates hooks and context, warns on legacy CJS usage, times the build, fires the 'build:prepare' hook, runs the shared clean, and resolves a debug rolldown config directory. It constructs a TsdownBundle holding the chunk array, config, an inlinedDeps map, and an asyncDispose method. A debounced (100ms) postBuild is set up so watch rebuilds coalesce; errors from it are logged, not thrown. It calls initBuildOptions to get rolldown BuildOptions: in watch mode it starts rolldownWatch and attaches handleWatcher; otherwise it runs rolldownBuild once and extends the chunk array with addOutDirToChunks over each output using the config's outDir. In non-watch mode it logs a success line with elapsed time and awaits postBuild directly; in watch mode postBuild is driven by watcher events. Returns the bundle.

<a id="u-5c7a2c2e3c96"></a>
### `build.ts-buildwithconfigs-lifecycle-helpers`

`const clean = () =>` · [src/build.ts:L64-L67][f1]

Three closures shared across configs.

clean memoizes a single cleanOutDir(configs) promise; concurrent callers get the same in-flight or settled promise. restart is guarded by a restarting flag so re-entrant calls are no-ops; it awaits all registered dispose callbacks, clears the require cache via clearRequireCache, then calls the caller-provided _restart (which re-runs the whole build). done wraps bundleDone with the per-package chunk map so each bundle's completion is recorded against its package.

<a id="u-45e0b3981b7c"></a>
### `build.ts-buildwithconfigs-orchestration`

`export async function buildWithConfigs( configs: ResolvedConfig[], configFiles: strin…` · [src/build.ts:L58-L64][f1]

Internal API that builds all resolved configs in parallel and manages watch/devtools lifecycle.

It lazily memoizes output-dir cleaning via a shared clean promise so the first buildSingle call to invoke it performs the clean and later calls reuse it. It groups configs by package via initBundleByPkg, computes per-config isDualFormat (true when the config has no pkg, otherwise whether that package builds more than one format), logs 'Build start', and awaits Promise.all of buildSingle for every config, passing the shared clean, restart, and done callbacks. After building: if any config has watch enabled, it registers keyboard shortcuts (wired to restart) and each bundle's asyncDispose as dispose callbacks; otherwise, if a config enables devtools with a UI, it starts the devtools UI for the first such config (typeAssert narrows devtools to non-optional). Returns the array of bundles. The disposeCbs/restarting state exist so restart can run all disposers, clear the require cache, and re-invoke the caller's restart function exactly once per trigger.

<a id="u-cc3aa48ef2b1"></a>
### `build.ts-bundle-asyncdispose`

`const asyncDispose: typeof Symbol.asyncDispose = Symbol.asyncDispose || Symbol.for('S…` · [src/build.ts:L37-L38][f1]

The bundle exposes an asyncDispose method (keyed by a Symbol.asyncDispose fallback that uses Symbol.for when the runtime lacks the well-known symbol) that cancels the pending debounced postBuild, aborts the current onSuccess AbortController if any, and closes the watcher if one exists.

It is registered by buildWithConfigs in watch mode so restart disposes watchers and pending side effects.

<a id="u-0d81475842f5"></a>
### `copy.ts-copy-option-types`

`export interface CopyEntry` · [src/features/copy.ts:L8-L35][f2]

CopyEntry describes one copy job: source path(s) or glob(s) in `from`, optional destination `to` (defaults to outDir), `flatten` (default true, dropping directory structure), `verbose` logging flag, and `rename` as a fixed string or a (name, extension, fullPath) callback.

CopyOptions is a string-or-entry, possibly nested array; CopyOptionsFn is a config-driven async factory for those options.

<a id="u-b20ef0862c31"></a>
### `copy.ts-copy-pipeline`

`export async function copy(options: ResolvedConfig): Promise<void>` · [src/features/copy.ts:L39-L93][f2]

Copies configured files/globs into the output tree, resolving destinations and optionally renaming.

Returns early when no copy option exists or resolves to an empty list; a function option is awaited with the config first. String entries become {from:[entry]}. If any source is a dynamic glob pattern, all sources are expanded via tinyglobby glob (cwd-relative, files only, no directory expansion); otherwise sources are used as-is. Each source is resolved per entry: `from` and `to` are made absolute against cwd (to defaults to outDir); with flatten (default) the file lands directly in `to`, otherwise the source's directory structure below cwd's first segment is preserved by replacing that segment with `to`. `rename` overrides the final base name — a string is used verbatim, a function receives (name, extension-without-dot, full source path). If nothing resolves after globbing, it warns 'No files matched for copying.' and returns; otherwise all copies run concurrently via fsCopy, with verbose entries logging relative from/to paths first. Any fsCopy rejection propagates (Promise.all).

**Notes.**

- condition: flatten=false with an empty dir (file directly under cwd) still writes to `to` itself
- side_effect: writes files/directories into the destination

calls: [function::fsCopy][f3], [function::buildSingle.postBuild][f1]

<a id="u-e34fcff7ec63"></a>
### `shortcuts.ts-shortcuts`

`export function shortcuts(restart: () => void): () => void` · [src/features/shortcuts.ts:L14-L16][f4]

Installs a stdin readline listener implementing interactive build shortcuts and returns a close function.

Recognized line inputs (trimmed, lowercased): 'r' restarts via the supplied callback, 'c' clears the console, 'q' exits the process with code 0, 'h' prints the shortcut help (deduplicating keys). Unknown input is ignored. While an action is running, further input is ignored until it finishes; the actionRunning flag is reset after the awaited action completes. The listener is attached via readline.createInterface on process.stdin and closed by the returned function.

<a id="u-20b3d0e57fe7"></a>
### `build`

`export async function build( inlineConfig: InlineConfig = {}, ): Promise<TsdownBundle[]>` · [src/build.ts:L43-L50][f1]

Public entry point that builds with tsdown from an inline config.

Sets the global logger level to the config's logLevel or 'info', resolves the inline config into per-build configs plus config file paths, then delegates to buildWithConfigs with a restart closure that re-runs build with the same inline config. Any error from resolution or building propagates to the caller.

<a id="u-06edfedfe9df"></a>
### `handleWatcher`

`function handleWatcher(watcher: RolldownWatcher)` · [src/build.ts:L188-L267][f1]

Attaches rolldown watcher event handlers for one config.

On 'change': an 'update' event records the changed file and immediately cancels the debounced postBuild and aborts the in-flight onSuccess, preventing duplicate onSuccess runs across rapid saves; if the changed file is a known config file or matches the config filename pattern, it logs and calls restart; if a create/delete occurs while the raw entry is a glob, it recomputes the object entry and compares sorted key sets, restarting when entry files changed. On 'event': START cancels the pending postBuild, cleans chunks from the outDir if config.clean is non-empty, clears the chunk array and error flag; BUNDLE_START clears the screen and logs the accumulated changed files; BUNDLE_END closes the result and logs rebuild duration; ERROR closes the result, logs the error, and sets hasError; END schedules the debounced postBuild only if no error occurred. All handlers are async; rejections inside them are not caught here.

<a id="u-1fa8abb83b64"></a>
### `initBuildOptions`

`async function initBuildOptions()` · [src/build.ts:L269-L306][f1]

Builds the rolldown BuildOptions array for one config.

It calls getBuildOptions for the main build, fires the 'build:before' hook with the merged context and build options, and, if a debug rolldown config directory was resolved, writes debug output via debugBuildOptions. When the format is 'cjs' and dts is enabled, it appends a second getBuildOptions call flagged as the dts variant. Returns the array of one or two BuildOptions.

<a id="u-898e85c48bd7"></a>
### `postBuild`

`async function postBuild()` · [src/build.ts:L308-L320][f1]

Runs post-build side effects for one config: copies files, builds an executable from the chunks, and on the first successful build only calls the done callback (recording the bundle against its package).

It then fires the 'build:done' hook with the context and chunks, marks hasBuilt so done never repeats, aborts any previous onSuccess process, and starts a new one via executeOnSuccess, keeping its AbortController in ab for later cancellation. In watch mode this runs debounced; its errors are caught and logged by the debounce wrapper.

<a id="u-e69cdaffd8fa"></a>
### `warnLegacyCJS`

`export function warnLegacyCJS(config: ResolvedConfig): void` · [src/features/cjs.ts:L5-L28][f5]

Warns once that ESM is preferred when a CJS build targets Node versions supporting require(esm).

Returns immediately if exe is enabled, target is falsy, the legacyCjs check is disabled (default enabled), or format lacks 'cjs'. Otherwise it coerces each target's version after a literal 'node' prefix and warns via logger.warnOnce only if any target satisfies ^20.19.0 || >=22.12.0.

calls: [function::buildSingle][f1]

<a id="u-1475c9e19d41"></a>
### `cleanChunks`

`export async function cleanChunks( outDir: string, chunks: Array<OutputAsset | Output…` · [src/features/clean.ts:L70-L81][f6]

Deletes the given output chunks/asset files by resolving each chunk's fileName against outDir and removing it, all concurrently.

calls: [fsRemove](../../catalog.json.gz)

<a id="u-31a32a6d82f5"></a>
### `cleanOutDir`

`export async function cleanOutDir(configs: ResolvedConfig[]): Promise<void>` · [src/features/clean.ts:L14-L48][f6]

Collects and deletes files matched by each config's clean globs, skipping the outDir itself.

When devtools is enabled with clean not explicitly false, 'node_modules/.rolldown' is appended to that config's clean list. Globs run with cwd=config.cwd, dotfiles included, matching files and directories; entries whose trailing-slash-normalized path equals the normalized outDir are excluded. All removals are deduplicated in a Set, logged as a count, then removed concurrently via fsRemove; if nothing matched, it returns without logging.

calls: [fsRemove](../../catalog.json.gz)

<a id="u-1fe6db3c3cb7"></a>
### `resolveClean`

`export function resolveClean( clean: UserConfig['clean'], outDir: string, cwd: string…` · [src/features/clean.ts:L50-L68][f6]

Normalizes the user clean option into a glob-pattern array and refuses to clean the cwd.

`true` becomes [slash(outDir)]; falsy becomes []. If any pattern resolves to the cwd, it throws an Error telling the user to pick a different path; otherwise the array is returned unchanged.

calls: [slash](../../catalog.json.gz)

<a id="u-de7f8d83c517"></a>
### `startDevtoolsUI`

`export async function startDevtoolsUI(config: DevtoolsOptions): Promise<void>` · [src/features/devtools.ts:L21-L30][f7]

Starts the @vitejs/devtools UI by dynamically importing '@vitejs/devtools/cli-commands' (via importWithError, which surfaces an install hint on failure) and calling start with host 127.0.0.1, open: true, overridden by config.ui when it is an object.

<a id="u-015bcdef331a"></a>
### `createHooks`

`export async function createHooks(options: ResolvedConfig): Promise<{ hooks: Hookable…` · [src/features/hooks.ts:L41-L56][f8]

Creates the hookable instance and build context from resolved config.

If config.hooks is an object its hooks are added directly; if a function it is awaited with the Hookable instance so it can register hooks itself. Returns {hooks, context} where context bundles the config and hooks.

<a id="u-5b8b50c3a50c"></a>
### `executeOnSuccess`

`export function executeOnSuccess( config: ResolvedConfig, ): AbortController | undefined` · [src/features/hooks.ts:L58-L87][f8]

Runs the onSuccess hook, returning an AbortController or undefined when onSuccess is unset.

A string command is executed with tinyexec (shell, inherited stdio, cwd=config.cwd); a non-zero exit code sets process.exitCode, and aborting the controller tree-kills the process if it has a pid. A function onSuccess receives (config, ab.signal) and manages its own abort handling.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/rolldown/tsdown/blob/2b1be7e0accdb1d6e903cd42642666431fc5e93d/src/build.ts
[f2]: https://github.com/rolldown/tsdown/blob/2b1be7e0accdb1d6e903cd42642666431fc5e93d/src/features/copy.ts
[f3]: https://github.com/rolldown/tsdown/blob/2b1be7e0accdb1d6e903cd42642666431fc5e93d/src/utils/fs.ts
[f4]: https://github.com/rolldown/tsdown/blob/2b1be7e0accdb1d6e903cd42642666431fc5e93d/src/features/shortcuts.ts
[f5]: https://github.com/rolldown/tsdown/blob/2b1be7e0accdb1d6e903cd42642666431fc5e93d/src/features/cjs.ts
[f6]: https://github.com/rolldown/tsdown/blob/2b1be7e0accdb1d6e903cd42642666431fc5e93d/src/features/clean.ts
[f7]: https://github.com/rolldown/tsdown/blob/2b1be7e0accdb1d6e903cd42642666431fc5e93d/src/features/devtools.ts
[f8]: https://github.com/rolldown/tsdown/blob/2b1be7e0accdb1d6e903cd42642666431fc5e93d/src/features/hooks.ts

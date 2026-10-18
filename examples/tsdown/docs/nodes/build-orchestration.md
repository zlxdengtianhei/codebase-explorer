# Build Orchestration

**Capability.** Coordinates a full multi-config build run: cleans output, groups configs per package, runs one bundle per config in parallel, and wires lifecycle hooks, keyboard shortcuts, devtools UI, and watch disposal.

Use this subtree to trace the top-level build flow from the public build() entry through per-config bundle execution. Hooks, shortcuts, cleaning, and devtools belong here because each is invoked inside the build pipeline. Failure of one config affects the whole run, so parallel coordination is the shared concern.

**Children.**

- [Asset Copying](asset-copying.md) `asset-copying` · 8 unit(s)

**Depends on.**

- [Asset Copying](asset-copying.md) · containment · → 1 / ← 0 edge(s) (ancestor direct units and descendant subtree; → follows ` build-orchestration ` → ` asset-copying `) · Build orchestration invokes asset copying after bundling to place static assets in the output.
- [Configuration Resolution](config.md) · graph-confirmed · 3 edge(s) · Build orchestration calls resolveConfig to obtain the fully resolved per-format configs before bundling.
- [Single-Executable Output](exe-output.md) · graph-confirmed · 1 edge(s)
- [General and Filesystem Helpers](general-and-fs.md) · graph-confirmed · 10 edge(s)
- [Logging](logging.md) · model-inferred · 0 edge(s)
- [Output File Naming and Formats](output-shaping.md) · graph-confirmed · 1 edge(s)
- [Package Publishing](package-publishing.md) · graph-confirmed · 4 edge(s) · After all configs for a package finish, orchestration triggers package publishing (exports, publint, attw).
- [Build Size Reporting](reporting.md) · model-inferred · 0 edge(s)
- [Rolldown Options Assembly](rolldown-assembly.md) · graph-confirmed · 4 edge(s) · Per-config bundling uses rolldown option assembly to build input/output options and debug dumps.
- [Entry Resolution](entry-resolution.md) · graph-only · 2 edge(s)

**Depended on by.**

- [Command-Line Interface](cli.md) · model-inferred · 0 edge(s) · The CLI dispatches the parsed command into the build entry point.
- [User Config Normalization](config-merging.md) · graph-confirmed · 1 edge(s)

Parent: [tsdown Build Tool](tsdown.md)

## Units (20)

<a id="u-20b3d0e57fe7"></a>
### `build`

`export async function build( inlineConfig: InlineConfig = {}, ): Promise<TsdownBundle[]>` · [src/build.ts:L43-L50][f1]

Public entry point that builds from user-supplied inline config.

It sets the global logger level from inlineConfig.logLevel (defaulting to 'info'), awaits resolveConfig to turn the inline config into resolved configs plus the config file paths involved, then delegates the whole run to buildWithConfigs, passing a restart closure that re-invokes build(inlineConfig) so a watch-mode restart re-resolves and rebuilds from the same user input.

calls: [resolveConfig](config.md#u-3ddd9346e44f), [build-ts-buildwithconfigs](build-orchestration.md#u-50217960b27f)

**Uncertainties.**

- resolveConfig's resolution and error behavior is external to this file.

<a id="u-50217960b27f"></a>
### `build-ts-buildwithconfigs`

`export async function buildWithConfigs( configs: ResolvedConfig[], configFiles: strin…` · [src/build.ts:L58-L64][f1]

Coordinates a full multi-config build: cleans the output once, groups configs per package, runs buildSingle for each config in parallel, and wires watch/devtools disposal.

clean() memoizes a single cleanOutDir(configs) promise so the output directory is cleaned at most once per run. restart() guards re-entry with a restarting flag, awaits all registered dispose callbacks, clears the require cache so later builds re-read changed modules, then invokes the injected _restart callback. done() forwards each finished bundle to bundleDone keyed by the per-package chunk grouping. Bundles come from Promise.all over configs, computing isDualFormat as the package's format-set size > 1 (true when the config has no package). After building: if any config has watch enabled, shortcuts(restart) and each bundle's asyncDispose are pushed into disposeCbs for later restart; otherwise, if the first config with devtools.ui exists, startDevtoolsUI is started (after a typeAssert narrowing). Returns all bundles.

**Notes.**

- side_effect: restart() calls clearRequireCache() before _restart so the rebuilt run picks up changed modules.
- condition: Watch mode and devtools UI are mutually exclusive here: devtools only starts when no config has watch.

calls: [cleanOutDir](build-orchestration.md#u-31a32a6d82f5), [initBundleByPkg](package-publishing.md#u-37c1dfe4abb3), [bundleDone](package-publishing.md#u-a3955ba81d03), [shortcuts-ts-keyboard-shortcuts](build-orchestration.md#u-397c312a5a0e), [startDevtoolsUI](build-orchestration.md#u-de7f8d83c517), [typeAssert](general-and-fs.md#u-2d6f421314ba), [build-ts-buildsingle](build-orchestration.md#u-3373284022b2)

**Uncertainties.**

- Behavior of _restart depends on the caller-supplied callback; only that build() passes () => build(inlineConfig) is evident.

<a id="u-3373284022b2"></a>
### `build-ts-buildsingle`

`async function buildSingle( config: ResolvedConfig, configFiles: string[], isDualForm…` · [src/build.ts:L127-L156][f1]

Builds one resolved configuration (or sets up watch for it) and returns a TsdownBundle whose chunks array and asyncDispose are live state.

It creates build hooks, warns on legacy CJS usage, fires the build:prepare hook, awaits the shared clean, resolves the rolldown debug-config directory, then either starts rolldownWatch with handleWatcher attached, or runs rolldownBuild once and pushes outputs (tagged with outDir) into chunks. Non-watch runs log success with elapsed milliseconds and await postBuild directly. postBuild runs copy, buildExe, first-time done(bundle) bookkeeping, the build:done hook, then aborts any prior success command and launches a new one via executeOnSuccess; errors from the debounced postBuild path are caught and logged via logger.error. initBuildOptions resolves the primary rolldown options, fires build:before, optionally dumps debug config files, and appends a second options pass (generate-dts variant) when format is 'cjs' and dts is enabled. The asyncDispose member cancels the pending debounced postBuild, aborts the success-command controller, and closes the watcher. handleWatcher handles watcher events: on 'change', update events record the file and immediately cancel pending postBuild and abort the success controller to avoid duplicate onSuccess runs; if the changed id is a known config file or matches the endsWithConfig pattern, the whole run restarts; create/delete events on a glob entry recompute the entry mapping via toObjectEntry and restart when its sorted keys differ. Watcher lifecycle events: START cancels postBuild, cleans emitted chunks when config.clean is non-empty, clears chunks and resets hasError; END schedules the debounced postBuild only when no error occurred; BUNDLE_START logs changed files when present and clears the list; BUNDLE_END closes the result and logs rebuild duration; ERROR closes the result, logs the error and sets hasError, suppressing the next END's postBuild until the next START.

**Notes.**

- failure: Watcher ERROR events set hasError so the following END skips postBuild; the direct (non-debounced) postBuild in non-watch mode is not caught here and propagates.
- condition: The 100ms debounce coalesces postBuild across rapid watch rebuilds; 'update' changes also cancel it preemptively.

calls: [createHooks](build-orchestration.md#u-015bcdef331a), [warnLegacyCJS](output-shaping.md#u-e69cdaffd8fa), [getDebugRolldownDir](rolldown-assembly.md#u-ebb3a577fb25), [debounce](general-and-fs.md#u-976b6a668555), [getBuildOptions](rolldown-assembly.md#u-c7b946124458), [debugBuildOptions](rolldown-assembly.md#u-4ce786ef6bf6), [addOutDirToChunks](general-and-fs.md#u-7a2fdc0e4dc6), [copy](asset-copying.md#u-31dcb3fabb8a), [buildExe](exe-output.md#u-5ec03dd7b88c), [executeOnSuccess](build-orchestration.md#u-5b8b50c3a50c), [cleanChunks](build-orchestration.md#u-1475c9e19d41), [isGlobEntry](entry-resolution.md#u-2a2d2117cfa5), [toObjectEntry](entry-resolution.md#u-13f5fd0aa8fa); uses: [src/features/watch.ts][f2]

**Uncertainties.**

- Rolldown watcher event payload shapes come from rolldown and are not verified here.
- Whether executeOnSuccess always returns an abortable handle is inferred from ab?.abort() usage.
- The exact contract of getBuildOptions's boolean fifth argument (a dts variant flag) is not visible in this file.

<a id="u-015bcdef331a"></a>
### `createHooks`

`export async function createHooks(options: ResolvedConfig): Promise<{ hooks: Hookable…` · [src/features/hooks.ts:L41-L56][f3]

Creates the hookable instance and shared build context used for tsdown lifecycle hooks.

When options.hooks is an object its hooks are registered via addHooks; when it is a function the function receives the Hookable instance to register hooks itself. Returns { hooks, context } where context carries the resolved options and the hooks instance.

<a id="u-5b8b50c3a50c"></a>
### `executeOnSuccess`

`export function executeOnSuccess( config: ResolvedConfig, ): AbortController | undefined` · [src/features/hooks.ts:L58-L87][f3]

Runs the onSuccess hook after a build and returns an AbortController for cancellation.

Returns undefined when no onSuccess is configured. A string onSuccess is executed through a shell in config.cwd with inherited stdio; a non-zero exit code sets process.exitCode, and aborting the returned controller kills the child via treeKill when a pid exists. A function onSuccess is invoked directly with the config and the abort signal; the controller is returned but the function does not abort it.

**Notes.**

- side_effect: Spawns a shell process and may set process.exitCode.

**Uncertainties.**

- Whether the returned AbortController is aborted by the caller (watch mode) is not visible here.

<a id="u-f68ae6ce9f4b"></a>
### `BuildContext`

`export interface BuildContext` · [src/features/hooks.ts:L8-L11][f3]

Hook context carrying the resolved options and the hooks instance.

<a id="u-dd141c30f28b"></a>
### `RolldownContext`

`export interface RolldownContext` · [src/features/hooks.ts:L13-L15][f3]

Hook context extension carrying the Rolldown BuildOptions.

<a id="u-861f7cd23197"></a>
### `TsdownHooks`

`export interface TsdownHooks` · [src/features/hooks.ts:L20-L39][f3]

Declares the build:prepare, build:before (with RolldownContext), and build:done (with chunks) hook signatures and their documented timing.

<a id="u-6a02ff4929ae"></a>
### `hooks.ts module code (L1–L7)`

`module_region` · [src/features/hooks.ts:L1-L7][f3]

Module imports.

<a id="u-a83aef2fea4c"></a>
### `hooks.ts module code (L15–L19)`

`module_region` · [src/features/hooks.ts:L15-L19][f3]

Doc comment introducing the TsdownHooks interface.

<a id="u-397c312a5a0e"></a>
### `shortcuts-ts-keyboard-shortcuts`

`export function shortcuts(restart: () => void): () => void` · [src/features/shortcuts.ts:L14-L16][f4]

Installs interactive stdin keyboard shortcuts for watch mode and returns a teardown function that closes the readline interface.

Each 'line' event is handled by onInput, which ignores input while an action is running and trims/lowercases first. Recognized keys: 'r' invokes the restart callback, 'c' clears the console, 'q' exits the process with code 0. 'h' prints the shortcut list via globalLogger, de-duplicating keys and skipping entries with no action (none exist here). Unknown input is ignored. Running an action sets actionRunning before awaiting and clears it after, so concurrent lines are dropped during execution; note an action that throws leaves actionRunning true, permanently disabling further shortcuts.

uses: [src/utils/logger.ts][f5]

**Uncertainties.**

- Error propagation from shortcut actions is unguarded in this source, so the stuck actionRunning flag is inferred from the missing try/finally.

<a id="u-84409c095a0e"></a>
### `Shortcut`

`export interface Shortcut` · [src/features/shortcuts.ts:L8-L12][f4]

Shortcut descriptor: key, description, and action thunk.

<a id="u-eda6cb2c4e16"></a>
### `shortcuts.ts module code (L1–L7)`

`module_region` · [src/features/shortcuts.ts:L1-L7][f4]

Module imports and a comment crediting the Vite-derived origin of this code.

<a id="u-1475c9e19d41"></a>
### `cleanChunks`

`export async function cleanChunks( outDir: string, chunks: Array<OutputAsset | Output…` · [src/features/clean.ts:L70-L81][f6]

Deletes the emitted chunk/asset files from disk, resolving each chunk's fileName against outDir and removing it concurrently via fsRemove.

No existence check is made; errors from fsRemove propagate to the caller.

calls: [fsRemove](general-and-fs.md#u-55a789017e76)

<a id="u-31a32a6d82f5"></a>
### `cleanOutDir`

`export async function cleanOutDir(configs: ResolvedConfig[]): Promise<void>` · [src/features/clean.ts:L14-L48][f6]

Removes stale files listed by each config's clean globs before a build.

For each config it appends 'node_modules/.rolldown' to the clean list when devtools is enabled and devtools.clean is not explicitly false, then globs the list (absolute, dot-inclusive, files and dirs) from config.cwd. Files whose path, with a trailing slash stripped, equals the normalized outDir are skipped so the output directory itself is never removed. All unique survivors are removed concurrently via fsRemove after logging 'Cleaning N files'; if nothing matched, the function returns silently.

**Notes.**

- side_effect: Deletes files and directories on disk and logs the count via globalLogger.
- condition: The devtools auto-clean push mutates each passed config's clean array in place.

calls: [fsRemove](general-and-fs.md#u-55a789017e76); uses: [src/utils/logger.ts][f5]

<a id="u-1fe6db3c3cb7"></a>
### `resolveClean`

`export function resolveClean( clean: UserConfig['clean'], outDir: string, cwd: string…` · [src/features/clean.ts:L50-L68][f6]

Normalizes the user `clean` option into an array of glob paths.

`true` becomes [slash(outDir)], and any falsy value becomes []. It then resolves each entry against the process cwd and throws an Error if any entry equals the current working directory, refusing to clean it. Otherwise returns the normalized array unchanged otherwise.

calls: [slash](general-and-fs.md#u-9bf13c522663)

<a id="u-c26a5e7d44e0"></a>
### `clean.ts module code (L1–L13)`

`module_region` · [src/features/clean.ts:L1-L13][f6]

Module imports and the RE_LAST_SLASH trailing-slash regex constant.

<a id="u-de7f8d83c517"></a>
### `startDevtoolsUI`

`export async function startDevtoolsUI(config: DevtoolsOptions): Promise<void>` · [src/features/devtools.ts:L21-L30][f7]

Starts the experimental devtools UI by dynamically importing @vitejs/devtools/cli-commands via importWithError and calling its start with a fixed host of 127.0.0.1, open: true, overridden by the object form of config.ui when provided; a boolean ui contributes no overrides.

calls: [importWithError](general-and-fs.md#u-6e036190d6a7)

**Uncertainties.**

- Failure behavior depends on importWithError, which is outside this file.

<a id="u-5b936c0619f4"></a>
### `DevtoolsOptions`

`export interface DevtoolsOptions extends NonNullable<InputOptions['devtools']>` · [src/features/devtools.ts:L5-L19][f7]

Devtools option interface extending Rolldown's devtools input option with experimental `ui` (boolean or partial StartOptions) and `clean` (default true) flags.

<a id="u-af4c2727bae0"></a>
### `devtools.ts module code (L1–L4)`

`module_region` · [src/features/devtools.ts:L1-L4][f7]

Module imports.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/rolldown/tsdown/blob/2b1be7e0accdb1d6e903cd42642666431fc5e93d/src/build.ts
[f2]: https://github.com/rolldown/tsdown/blob/2b1be7e0accdb1d6e903cd42642666431fc5e93d/src/features/watch.ts
[f3]: https://github.com/rolldown/tsdown/blob/2b1be7e0accdb1d6e903cd42642666431fc5e93d/src/features/hooks.ts
[f4]: https://github.com/rolldown/tsdown/blob/2b1be7e0accdb1d6e903cd42642666431fc5e93d/src/features/shortcuts.ts
[f5]: https://github.com/rolldown/tsdown/blob/2b1be7e0accdb1d6e903cd42642666431fc5e93d/src/utils/logger.ts
[f6]: https://github.com/rolldown/tsdown/blob/2b1be7e0accdb1d6e903cd42642666431fc5e93d/src/features/clean.ts
[f7]: https://github.com/rolldown/tsdown/blob/2b1be7e0accdb1d6e903cd42642666431fc5e93d/src/features/devtools.ts
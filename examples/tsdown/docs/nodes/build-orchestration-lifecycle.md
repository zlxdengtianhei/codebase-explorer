# Build orchestration lifecycle

**Capability.** Orchestrates resolved configs, builds bundles, manages watch/devtools lifecycle, cleans outputs, and runs post-build hooks.

Use this module for the public build entry and multi-config build lifecycle. It covers cleaning, watcher registration, devtools startup, hooks, and post-build side effects.

**Depends on.**

- [Copy shortcuts target helpers](copy-shortcuts-target-helpers.md) · graph-confirmed · 3 edge(s) · Build lifecycle calls copy, shortcut, and target helpers during orchestration.
- [Watch set and chunks](watch-set-and-chunks.md) · graph-confirmed · 1 edge(s)
- [Entry and path resolution](entry-and-path-resolution.md) · graph-only · 4 edge(s)
- [Dependency externalization utilities](dependency-externalization-utilities.md) · graph-only · 3 edge(s)
- [Package tarball validation](package-tarball-validation.md) · graph-only · 2 edge(s)
- [Rolldown option assembly](rolldown-option-assembly.md) · graph-only · 2 edge(s)
- [Config file loading](config-file-loading.md) · graph-only · 1 edge(s)
- [Executable SEA builds](executable-sea-builds.md) · graph-only · 1 edge(s)
- [Package export map generation](package-export-map-generation.md) · graph-only · 1 edge(s)

**Depended on by.**

- [Config resolution and logging](config-resolution-and-logging.md) · graph-only · 1 edge(s)

Parent: [Build execution and watching](build-execution-and-watching.md)

## Units (12)

<a id="u-5cb90f2fbb18"></a>
### `build.ts-buildsingle-orchestration`

`async function buildSingle( config: ResolvedConfig, configFiles: string[], isDualForm…` · [src/build.ts:L127-L156][f1]

Builds one resolved config and returns a bundle handle, without owning watch shortcuts.

It creates hooks/context, warns legacy CJS, records start time, runs build:prepare, cleans output, resolves the debug rolldown directory, and initializes chunks, watcher/abort state, a 100 ms debounced post-build that logs errors, and a bundle object whose async dispose cancels debounce, aborts, and closes the watcher. It obtains build options; in watch mode it starts rolldown watch and installs the watcher handler, otherwise it runs rolldown build and appends output chunks with out-dir metadata. In non-watch mode it logs completion and awaits post-build before returning. The bundle starts with hasBuilt false.

<a id="u-45e0b3981b7c"></a>
### `build.ts-buildwithconfigs-orchestration`

`export async function buildWithConfigs( configs: ResolvedConfig[], configFiles: strin…` · [src/build.ts:L58-L64][f1]

Orchestrates resolved configs: memoizes output cleaning, builds each config in parallel, and wires watch/devtools lifecycle.

Cleaning returns the same promise after the first call. Restart returns immediately if already restarting; otherwise it sets a one-way flag, awaits all dispose callbacks, clears the require cache, and invokes the supplied restart callback. Because the flag is never reset, only the first restart trigger proceeds; later triggers are no-ops. Done delegates to package bundle completion. It logs build start, computes dual-format per package (true when no package, otherwise package format count >1), and calls the single-config builder with shared clean/restart/done. After all builds, it finds the first devtools UI config and whether any config watches. If watching, it registers shortcuts and each bundle's async dispose; otherwise, if a devtools UI config exists, it starts devtools. Returns all bundles.

<a id="u-20b3d0e57fe7"></a>
### `build`

`export async function build( inlineConfig: InlineConfig = {}, ): Promise<TsdownBundle[]>` · [src/build.ts:L43-L50][f1]

Public build entry: sets the global logger level from the inline log level or info, resolves configs and config files, then delegates to the multi-config builder with a restart callback that recursively calls this entry with the same inline config.

Returns the resulting bundles; resolution errors propagate.

<a id="u-06edfedfe9df"></a>
### `handleWatcher`

`function handleWatcher(watcher: RolldownWatcher)` · [src/build.ts:L188-L267][f1]

Registers change and lifecycle handlers on a rolldown watcher.

On update events it records the changed id, cancels pending debounced post-build, and aborts the current controller. If the changed id is a config file or matches the config suffix, it logs and calls restart. On create/delete for a glob raw entry, it recomputes the entry object and calls restart only when sorted entry keys differ. Lifecycle: START cancels debounce, cleans chunks only when config.clean is non-empty, clears chunks, and resets error state; END schedules debounced post-build only if no error; BUNDLE_START clears the screen and logs accumulated changed files only when the list is non-empty, then empties it; BUNDLE_END closes the result and logs rebuild duration; ERROR closes the result, logs the error, and marks error state. Restart calls may be no-ops after the first because the shared restart guard is one-way.

<a id="u-898e85c48bd7"></a>
### `postBuild`

`async function postBuild()` · [src/build.ts:L308-L320][f1]

Runs post-build side effects in order: copy, executable build, first-time package completion, build:done hook, then marks built, aborts the current controller, and starts on-success execution.

Package completion runs only while hasBuilt is false. hasBuilt is set only after the build:done hook, so if copy, executable build, package completion, or the hook throws, hasBuilt stays false and package completion can run again on a later post-build. If on-success setup throws after hasBuilt is set, the built flag remains true.

<a id="u-e24ddcc54e85"></a>
### `buildSingle.[asyncDispose]`

`const bundle: TsdownBundle = { chunks, config, inlinedDeps: new Map(), async [asyncDi…` · [src/build.ts:L156-L164][f1]

Bundle disposal cancels the pending debounced post-build, aborts the current abort controller if present, and awaits watcher close if present.

It does not reset state or catch errors.

<a id="u-1475c9e19d41"></a>
### `cleanChunks`

`export async function cleanChunks( outDir: string, chunks: Array<OutputAsset | Output…` · [src/features/clean.ts:L70-L81][f2]

Deletes each emitted chunk file under the output directory in parallel.

Each chunk filename is resolved against the output directory, debug-logged, and removed. The returned promise rejects if any removal fails; there is no filtering or fallback.

<a id="u-31a32a6d82f5"></a>
### `cleanOutDir`

`export async function cleanOutDir(configs: ResolvedConfig[]): Promise<void>` · [src/features/clean.ts:L14-L48][f2]

Removes configured clean targets for each resolved config while protecting the output directory.

For each config, devtools enabled with clean not false adds `node_modules/.rolldown` to the clean list. Empty clean lists are skipped. Patterns are globbed relative to the config cwd with absolute, dot, and non-file-only matching. A matched path is queued only when its trailing-slash-normalized form differs from the normalized outDir. If nothing is queued it returns; otherwise it logs the count, removes all queued paths in parallel, and debug-logs completion. Removal failures reject the returned promise. It mutates the config clean list and deletes files.

<a id="u-1fe6db3c3cb7"></a>
### `resolveClean`

`export function resolveClean( clean: UserConfig['clean'], outDir: string, cwd: string…` · [src/features/clean.ts:L50-L68][f2]

Normalizes the clean option into an array and rejects cleaning the current working directory.

`true` becomes the slashed output directory; any falsy value becomes an empty array; an array is kept. If any item resolves to the provided cwd, it throws an Error. Returns the resulting array.

<a id="u-de7f8d83c517"></a>
### `startDevtoolsUI`

`export async function startDevtoolsUI(config: DevtoolsOptions): Promise<void>` · [src/features/devtools.ts:L21-L30][f3]

Starts the Vite devtools UI with local defaults and optional user overrides.

It dynamically imports the devtools CLI commands, then calls start with host 127.0.0.1 and open true. If the ui option is an object, its fields are spread over those defaults. Import or start failures propagate.

<a id="u-015bcdef331a"></a>
### `createHooks`

`export async function createHooks(options: ResolvedConfig): Promise<{ hooks: Hookable…` · [src/features/hooks.ts:L41-L56][f4]

Creates a hookable instance and build context from user hook configuration.

An object hook configuration is added directly; a function hook configuration is awaited with the hookable instance. The returned context contains the resolved config and the hookable. Errors from the function hook propagate.

<a id="u-5b8b50c3a50c"></a>
### `executeOnSuccess`

`export function executeOnSuccess( config: ResolvedConfig, ): AbortController | undefined` · [src/features/hooks.ts:L58-L87][f4]

Runs the configured onSuccess command or callback and returns an abort controller for cancellation.

Without onSuccess it returns undefined. A string command runs through a shell with inherited stdio and the config cwd; its nonzero exit code is copied to process.exitCode, and abort kills the child process when a pid exists. A callback receives the config and abort signal; its returned promise is not awaited or caught. Synchronous callback errors propagate.

Look up code: the commands are under "Read further" in [INDEX.md](../INDEX.md); `cbe query` and `cbe source` take a unit title or anchor from this page.

[f1]: https://github.com/rolldown/tsdown/blob/2b1be7e0accdb1d6e903cd42642666431fc5e93d/src/build.ts
[f2]: https://github.com/rolldown/tsdown/blob/2b1be7e0accdb1d6e903cd42642666431fc5e93d/src/features/clean.ts
[f3]: https://github.com/rolldown/tsdown/blob/2b1be7e0accdb1d6e903cd42642666431fc5e93d/src/features/devtools.ts
[f4]: https://github.com/rolldown/tsdown/blob/2b1be7e0accdb1d6e903cd42642666431fc5e93d/src/features/hooks.ts

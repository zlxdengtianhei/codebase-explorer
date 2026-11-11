# Rolldown option assembly

**Capability.** Translates resolved configs into Rolldown input/output options, plugin pipeline, and per-format build options, including debug config serialization.

Come here to understand how tsdown constructs Rolldown BuildOptions, merges user input/output options, and wires plugins like css-guard, shebang, shims, and watch. Also covers banner/footer addons and file-extension choice per format.

**Depends on.**

- [Dependency handling and general utilities](dependency-handling-and-general-utilities.md) · graph-only · 4 edge(s)
- [Config resolution and normalization](config-resolution-and-normalization.md) · graph-only · 3 edge(s)
- [Logging and size reporting](logging-and-size-reporting.md) · graph-only · 3 edge(s)
- [Entry resolution and filesystem helpers](entry-resolution-and-filesystem-helpers.md) · graph-only · 2 edge(s)

**Depended on by.**

- [Build orchestration and lifecycle](build-orchestration-and-lifecycle.md) · graph-confirmed · 4 edge(s) · Build orchestration uses Rolldown option assembly to turn resolved configs into Rolldown build options.

Parent: [Build execution pipeline](build-execution-pipeline.md)

## Units (15)

<a id="u-ec779dcd5bd8"></a>
### `output.ts-resolvechunkfilename`

`export function resolveChunkFilename( { outExtensions, fixedExtension, pkg, hash }: R…` · [src/features/output.ts:L44-L76][f1]

Computes [entryFileNames, chunkFileNames] patterns for a format.

Calls the user outExtensions factory with {options, format, pkgType} to override js/dts extensions; the js extension defaults to '.' + resolveJsOutputExtension. iife/umd formats get a `.<format>` suffix, and chunks additionally get '-[hash]' when hash is enabled. createChunkFilename returns a plain string when no dts extension is set, otherwise a function choosing the dts extension for chunk names ending in '.d' and the js extension otherwise.

calls: [resolveJsOutputExtension](rolldown-option-assembly.md#u-61ab17605f5c)

<a id="u-15c90c7f25b1"></a>
### `rolldown.ts-cssguardplugin`

`export function CssGuardPlugin(): Plugin` · [src/features/rolldown.ts:L344-L350][f2]

Factory for the 'tsdown:css-guard' plugin that fails the build when CSS is present without @tsdown/css installed.

Its post-ordered transform matches ids ending in .css/.less/.sass/.scss/.styl/.stylus and throws an Error naming the file and instructing `npm install @tsdown/css`.

<a id="u-affd06d98a1c"></a>
### `rolldown.ts-resolveinputoptions`

`async function resolveInputOptions( config: ResolvedConfig, format: NormalizedFormat,…` · [src/features/rolldown.ts:L74-L188][f2]

Builds Rolldown InputOptions with an ordered plugin pipeline, then merges user inputOptions via mergeUserOptions keyed by [format, {cjsDts}].

Plugins: NodeProtocolPlugin when nodeProtocol is set; DepPlugin when a package.json exists or skipNodeModulesBundle; when dts is set, the dts plugin for es format, or with emitDtsOnly+cjsDefault when cjsDts. For non-cjsDts builds only: unplugin-unused (when unused), the @tsdown/css plugin if installed else CssGuardPlugin, ShebangPlugin, importGlobPlugin when globImport, and user plugins. ReportPlugin is added when report is on and logger level >= info; WatchPlugin when watch is on. define merges config.define with `process.env.<k>` and `import.meta.env.<k>` per env entry; inject comes from getShimsInject only when shims is on and not cjsDts. platform is forced to 'node' for cjsDts or cjs format. moduleTypes defaults '.node' to 'copy' plus user loader. logLevel is 'silent' when the logger level is 'error'. The onLog handler suppresses MIXED_EXPORT warnings when cjsDefault is on, escalates warn-level logs (except PLUGIN_TIMINGS) to error when logger.options.failOnWarn, then defers to the default handler.

**Notes.**

- condition: The unplugin-unused, CSS, Shebang, importGlob and user plugins are gated on !cjsDts, i.e. they are absent only for cjs-dts builds, regardless of the dts option.

calls: [NodeProtocolPlugin](rolldown-option-assembly.md#u-0ba0d4cbad8c), [deps.ts-depplugin-resolveid](dependency-handling-and-general-utilities.md#u-43c34d98d8b2), [report.ts-reportplugin](logging-and-size-reporting.md#u-162a1329d7a0), [watch.ts-watchplugin](rolldown-option-assembly.md#u-6f34a8506ce9)

<a id="u-5f383a2c9119"></a>
### `shebang.ts-shebangplugin`

`export function ShebangPlugin( logger: Logger, cwd: string, nameLabel?: string, isDua…` · [src/features/shebang.ts:L10-L18][f3]

Factory for the 'tsdown:shebang' plugin that makes shebang-carrying entry chunks executable.

In writeBundle it iterates only entry chunks whose code starts with `#!`; resolves the output path from options.file or dir+fileName; if the file exists it logs (with a format label in dual-format builds) that execute permission is granted and chmods it to 0o755. Non-entry chunks and files without a shebang are skipped, as are missing files.

<a id="u-9a508d8546b9"></a>
### `shims.ts-esm-shims-injection`

`export const shimFile: string = path.resolve( import.meta.dirname, import.meta.TSDOWN…` · [src/features/shims.ts:L4-L8][f4]

Locates the bundled esm-shims.js next to the package root (production) or repo root (development) via import.meta.dirname, and exposes an inject map for rolldown: only for 'es' format on the 'node' platform it returns {__dirname, __filename} each mapped to [shimFile, exportName]; otherwise undefined.

calls: [function::resolveInputOptions][f2]

<a id="u-6f34a8506ce9"></a>
### `watch.ts-watchplugin`

`export function WatchPlugin( configFiles: string[], { config, chunks }: TsdownBundle,…` · [src/features/watch.ts:L9-L22][f5]

Factory for the 'tsdown:watch' plugin that extends Rolldown's watch set and records output chunks.

When config.ignoreWatch is non-empty, an options hook pushes those patterns into inputOptions.watch.exclude (initializing the array if needed). buildStart registers config.tsconfig, each config file, any files from a non-boolean config.watch (comma-split), and the package.json path when config.pkg exists as watch files. A post-ordered generateBundle pushes addOutDirToChunks of the bundle values into the shared bundle's chunks list.

<a id="u-52460b98c903"></a>
### `mergeUserOptions`

`export async function mergeUserOptions<T extends object, A extends unknown[]>( defaul…` · [src/config/options.ts:L368-L381][f6]

Merges user-provided options onto defaults: the user value may be a function receiving (defaults, ...args) whose awaited result is merged; a null/undefined/void result returns defaults unchanged.

Merging uses the same array-replacing defu.

<a id="u-0ba0d4cbad8c"></a>
### `NodeProtocolPlugin`

`export function NodeProtocolPlugin(nodeProtocolOption: 'strip' | true): Plugin` · [src/features/node-protocol.ts:L8-L50][f7]

Rolldown plugin that rewrites Node builtin module ids according to the option.

With 'strip', ids like `node:fs` matching builtins are re-resolved without the prefix; if another resolver handles the stripped id non-externally that result is used, otherwise the stripped id is returned as external with no side effects. With true, bare builtin ids are rewritten to `node:<id>` and marked external with no side effects. The resolveId filter and handler are chosen by the option; order is 'pre'.

<a id="u-b521ce5719c7"></a>
### `resolveChunkAddon`

`export function resolveChunkAddon( chunkAddon: ChunkAddon | undefined, format: Normal…` · [src/features/output.ts:L101-L130][f1]

Turns a banner/footer addon into a Rolldown AddonFunction, or undefined for a falsy addon.

The returned function: if the addon is a function it is called with {format, fileName} and the result replaces it; a string result is returned verbatim; an object result picks .js/.css/.dts by testing the chunk fileName against JS/CSS/DTS filename regexes, defaulting to '' for unmatched files or missing fields.

<a id="u-61ab17605f5c"></a>
### `resolveJsOutputExtension`

`function resolveJsOutputExtension( packageType: PackageType, format: NormalizedFormat…` · [src/features/output.ts:L29-L42][f1]

Chooses the JS file extension for a format given the package type and fixedExtension.

es: 'js' only when packageType is 'module' and fixedExtension is unset, else 'mjs'. cjs: 'cjs' when fixedExtension is set or packageType is 'module', else 'js'. Any other format yields 'js'.

<a id="u-4ce786ef6bf6"></a>
### `debugBuildOptions`

`export async function debugBuildOptions( dir: string, name: string | undefined, forma…` · [src/features/rolldown.ts:L283-L315][f2]

Serializes build options into a runnable rolldown config file at `<dir>/rolldown.config.<format>.js`.

It first installs custom inspect handlers on plugins via handlePluginInspect, then writes a header comment (tsdown and rolldown versions, timestamp, package name or 'not specified') followed by `export default <serialized>` using util.formatWithOptions with unlimited depth/array/string length, and debug-logs the output path.

<a id="u-c7b946124458"></a>
### `getBuildOptions`

`export async function getBuildOptions( config: ResolvedConfig, format: NormalizedForm…` · [src/features/rolldown.ts:L36-L72][f2]

Assembles a complete Rolldown BuildOptions for one format by resolving input options (passing format, configFiles, bundle, cjsDts, isDualFormat) and output options, then spreading inputs, attaching output, and setting write from config.

Debug-logs the config labeled 'cjs dts' when cjsDts is true.

<a id="u-ebb3a577fb25"></a>
### `getDebugRolldownDir`

`export async function getDebugRolldownDir(): Promise<string | undefined>` · [src/features/rolldown.ts:L278-L281][f2]

Returns a fresh temp directory (mkdtemp under os.tmpdir with prefix 'tsdown-config-') for debug config dumps, or undefined when the 'tsdown:rolldown' debug namespace is not enabled.

<a id="u-d525eb96a2a5"></a>
### `handlePluginInspect`

`function handlePluginInspect(plugins: RolldownPluginOption)` · [src/features/rolldown.ts:L317-L342][f2]

Recursively attaches a util.inspect.custom function to plugin objects so serialization stays compact: plugins with an `_options` property inspect as {name, options}, others as a quoted `"rolldown plugin: <name>"` string.

Arrays are traversed element-wise; non-plugin objects are left alone.

<a id="u-9b5ea05ef4d5"></a>
### `resolveOutputOptions`

`async function resolveOutputOptions( inputOptions: InputOptions, config: ResolvedConf…` · [src/features/rolldown.ts:L231-L276][f2]

Builds Rolldown OutputOptions and merges user outputOptions via mergeUserOptions keyed by [format, {cjsDts}].

Format is forced to 'es' for cjsDts builds; exports is 'auto' when cjsDefault else 'named'; entry/chunk filename patterns come from resolveChunkFilename. minify is applied only when minify is set and the build is not cjsDts (i.e. minification is disabled for cjs-dts builds). unbundle enables preserveModules with preserveModulesRoot set to the lowest common ancestor of the entry paths. Banner/footer become postBanner/postFooter addons via resolveChunkAddon; codeSplitting is disabled when config.exe is set.

**Notes.**

- condition: minify: !cjsDts && minify — cjsDts builds are never minified even if minify is configured.

calls: [output.ts-resolvechunkfilename](rolldown-option-assembly.md#u-ec779dcd5bd8), [resolveChunkAddon](rolldown-option-assembly.md#u-b521ce5719c7)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/rolldown/tsdown/blob/2b1be7e0accdb1d6e903cd42642666431fc5e93d/src/features/output.ts
[f2]: https://github.com/rolldown/tsdown/blob/2b1be7e0accdb1d6e903cd42642666431fc5e93d/src/features/rolldown.ts
[f3]: https://github.com/rolldown/tsdown/blob/2b1be7e0accdb1d6e903cd42642666431fc5e93d/src/features/shebang.ts
[f4]: https://github.com/rolldown/tsdown/blob/2b1be7e0accdb1d6e903cd42642666431fc5e93d/src/features/shims.ts
[f5]: https://github.com/rolldown/tsdown/blob/2b1be7e0accdb1d6e903cd42642666431fc5e93d/src/features/watch.ts
[f6]: https://github.com/rolldown/tsdown/blob/2b1be7e0accdb1d6e903cd42642666431fc5e93d/src/config/options.ts
[f7]: https://github.com/rolldown/tsdown/blob/2b1be7e0accdb1d6e903cd42642666431fc5e93d/src/features/node-protocol.ts

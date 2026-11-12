# Rolldown option assembly

**Capability.** Builds Rolldown input/output options and plugins, including filenames, shims, node protocol, CSS guards, and debug serialization.

Use this module to assemble Rolldown build options for a format. It covers plugin lists, output naming, shims, warning suppression, and debug config writing.

**Depends on.**

- [Build execution and watching](build-execution-and-watching.md) · graph-confirmed · 1 edge(s)
- [Config resolution and logging](config-resolution-and-logging.md) · graph-confirmed · 4 edge(s) · Rolldown option assembly uses config resolution and logging for resolved build options.
- [Entry and path resolution](entry-and-path-resolution.md) · graph-confirmed · 1 edge(s)
- [Executable builds and sizing](executable-builds-and-sizing.md) · graph-confirmed · 1 edge(s)
- [Package output and validation](package-output-and-validation.md) · graph-confirmed · 3 edge(s)
- [Dependency externalization utilities](dependency-externalization-utilities.md) · graph-only · 3 edge(s)
- [Bundle size reporting](bundle-size-reporting.md) · graph-only · 1 edge(s)
- [Watch set and chunks](watch-set-and-chunks.md) · graph-only · 1 edge(s)

**Depended on by.**

- [Build execution and watching](build-execution-and-watching.md) · graph-confirmed · 2 edge(s)
- [Build orchestration lifecycle](build-orchestration-lifecycle.md) · graph-only · 2 edge(s)

Parent: [tsdown build tool](tsdown-build-tool.md)

## Units (16)

<a id="u-fc5677117af6"></a>
### `rolldown.ts-cssguardplugin-factory`

`export function CssGuardPlugin(): Plugin` · [src/features/rolldown.ts:L344-L350][f1]

Creates a plugin that throws when CSS-like files are transformed without the CSS package.

It returns a post-order transform plugin filtered to css, less, sass, scss, styl, and stylus extensions. The handler always throws an installation error naming the file.

<a id="u-affd06d98a1c"></a>
### `rolldown.ts-resolveinputoptions`

`async function resolveInputOptions( config: ResolvedConfig, format: NormalizedFormat,…` · [src/features/rolldown.ts:L74-L188][f1]

Builds Rolldown input options and the plugin list for a format, with cjsDts-specific omissions.

Node protocol, dependency, dts, report, and watch plugins are added conditionally. The dts plugin is added for ES format, or in emitDtsOnly mode for cjsDts. When cjsDts is false, it also adds unused, CSS, shebang, glob-import, and user plugins; CSS falls back to a guard plugin when @tsdown/css is absent. Environment values are merged into define for process.env and import.meta.env. Shims are injected only when enabled and cjsDts is false. Platform becomes node for cjsDts or cjs format. Log level maps error to silent. User input options are merged last with format context.

<a id="u-1fa8abb83b64"></a>
### `initBuildOptions`

`async function initBuildOptions()` · [src/build.ts:L269-L306][f2]

Builds rolldown options for the config.

It gets base options, runs build:before with context plus options, and writes debug options only when a debug directory exists. It returns one options object, plus a second options object only when format is cjs and dts is enabled; the second call passes the dts flag true. No catch.

<a id="u-0ba0d4cbad8c"></a>
### `NodeProtocolPlugin`

`export function NodeProtocolPlugin(nodeProtocolOption: 'strip' | true): Plugin` · [src/features/node-protocol.ts:L8-L50][f3]

Creates a plugin that adds or strips the node: protocol for builtin modules.

It builds the list of builtins without the protocol. In strip mode, matching node:-prefixed ids are stripped; if another resolver resolves the stripped id to a non-external module, that resolution is returned, otherwise the stripped id is marked external with no side effects. In add mode, bare builtin ids are rewritten to node:-prefixed external modules with no side effects.

<a id="u-6bcfef951475"></a>
### `createChunkFilename`

`function createChunkFilename( basename: string, jsExtension: string, dtsExtension?: s…` · [src/features/output.ts:L79-L88][f4]

Creates a static or chunk-aware filename template depending on the dts extension.

Without a dts extension it returns a plain basename plus JS extension string. With one it returns a function that uses the dts extension when the chunk name ends with `.d`, otherwise the JS extension.

<a id="u-b521ce5719c7"></a>
### `resolveChunkAddon`

`export function resolveChunkAddon( chunkAddon: ChunkAddon | undefined, format: Normal…` · [src/features/output.ts:L101-L130][f4]

Normalizes a chunk addon option into a Rolldown addon function.

Falsy input returns undefined. The returned function calls a function addon once with format and filename, then reuses that result for later chunks. A string result is returned directly. Otherwise the filename is tested against JS, CSS, and DTS patterns in that order, returning the matching addon field or an empty string.

<a id="u-fa191ddae689"></a>
### `resolveChunkFilename`

`export function resolveChunkFilename( { outExtensions, fixedExtension, pkg, hash }: R…` · [src/features/output.ts:L44-L76][f4]

Builds entry and chunk filename templates from output extension settings and format.

It reads the package type, optionally calls the outExtensions factory, and falls back to the computed JS extension. IIFE and UMD formats add a format suffix. The entry template uses the name and suffix; the chunk template also includes a hash placeholder when hashing is enabled. A dts extension, when supplied, makes the templates chunk-aware.

<a id="u-61ab17605f5c"></a>
### `resolveJsOutputExtension`

`function resolveJsOutputExtension( packageType: PackageType, format: NormalizedFormat…` · [src/features/output.ts:L29-L42][f4]

Chooses a js, mjs, or cjs extension from package type, format, and fixedExtension.

ES format yields js only when fixedExtension is false and package type is module; otherwise mjs. CJS format yields cjs when fixedExtension is true or package type is module; otherwise js. Other formats yield js.

<a id="u-4ce786ef6bf6"></a>
### `debugBuildOptions`

`export async function debugBuildOptions( dir: string, name: string | undefined, forma…` · [src/features/rolldown.ts:L283-L315][f1]

Writes a serialized Rolldown config file for debugging.

It installs custom plugin inspection, serializes the build options with unlimited depth and collection lengths, and writes a JS file named by format. The file header includes tsdown and Rolldown versions, generation time, and package name or a fallback. Write failures propagate.

<a id="u-c7b946124458"></a>
### `getBuildOptions`

`export async function getBuildOptions( config: ResolvedConfig, format: NormalizedForm…` · [src/features/rolldown.ts:L36-L72][f1]

Assembles Rolldown build options by resolving input and output options for a format.

It calls the input resolver with the config, format, config files, bundle, cjsDts, and dual-format flag, then the output resolver with those input options. The result spreads input options and adds output and the config write flag. It debug-logs the assembled config.

<a id="u-ebb3a577fb25"></a>
### `getDebugRolldownDir`

`export async function getDebugRolldownDir(): Promise<string | undefined>` · [src/features/rolldown.ts:L278-L281][f1]

Creates a temporary directory for debug config output only when debug is enabled.

It returns undefined when debug is disabled; otherwise it makes a directory under the system temp directory with a tsdown-config prefix.

<a id="u-d525eb96a2a5"></a>
### `handlePluginInspect`

`function handlePluginInspect(plugins: RolldownPluginOption)` · [src/features/rolldown.ts:L317-L342][f1]

Recursively installs a custom inspect hook on plugin objects for debug serialization.

Arrays are traversed. Objects with a name get an inspect.custom function that either shows name and _options or returns a plugin-name string. It mutates the plugin objects.

<a id="u-9b5ea05ef4d5"></a>
### `resolveOutputOptions`

`async function resolveOutputOptions( inputOptions: InputOptions, config: ResolvedConf…` · [src/features/rolldown.ts:L231-L276][f1]

Builds Rolldown output options, including filenames, addons, minification, and preserveModules.

It resolves entry and chunk filename templates, then merges defaults with user output options. Format becomes ES for cjsDts. Exports are auto when cjsDefault is set, otherwise named. Minification is disabled only when cjsDts is true. PreserveModules follows unbundle, with its root set to the common ancestor of entries only when unbundle is enabled. Banner and footer become chunk addons. Code splitting is disabled for executables.

<a id="u-10ea568fec30"></a>
### `CssGuardPlugin.handler`

`handler(_code, id)` · [src/features/rolldown.ts:L350-L355][f1]

Throws an installation error for any CSS-like module that reaches it.

The error names the file and instructs installing @tsdown/css. It has no fallback or conditional behavior beyond the plugin filter.

<a id="u-dd1271810548"></a>
### `resolveInputOptions.onLog`

`const inputOptions = await mergeUserOptions( { input: entry, cwd, external: neverBund…` · [src/features/rolldown.ts:L188-L220][f1]

Suppresses mixed-export warnings and optionally escalates warnings to errors.

A MIXED_EXPORT log is dropped when cjsDefault is enabled. A warning is escalated through the default handler when failOnWarn is set and the code is not PLUGIN_TIMINGS. The original level is then passed to the default handler as well, so an escalated warning can be handled twice.

<a id="u-0acb9a1b84d0"></a>
### `getShimsInject`

`export function getShimsInject( format: NormalizedFormat, platform: ResolvedConfig['p…` · [src/features/shims.ts:L10-L20][f5]

Returns ESM shim injections only for ES format on the Node platform.

In that case it maps __dirname and __filename to the shared esm-shims.js file and the corresponding export name; otherwise it returns undefined. The shim file path is resolved relative to the module directory, using the production flag to choose parent or grandparent.

Look up code: the commands are under "Read further" in [INDEX.md](../INDEX.md); `cbe query` and `cbe source` take a unit title or anchor from this page.

[f1]: https://github.com/rolldown/tsdown/blob/2b1be7e0accdb1d6e903cd42642666431fc5e93d/src/features/rolldown.ts
[f2]: https://github.com/rolldown/tsdown/blob/2b1be7e0accdb1d6e903cd42642666431fc5e93d/src/build.ts
[f3]: https://github.com/rolldown/tsdown/blob/2b1be7e0accdb1d6e903cd42642666431fc5e93d/src/features/node-protocol.ts
[f4]: https://github.com/rolldown/tsdown/blob/2b1be7e0accdb1d6e903cd42642666431fc5e93d/src/features/output.ts
[f5]: https://github.com/rolldown/tsdown/blob/2b1be7e0accdb1d6e903cd42642666431fc5e93d/src/features/shims.ts

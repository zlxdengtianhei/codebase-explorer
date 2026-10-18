# Rolldown Options Assembly

**Capability.** Assembles complete Rolldown InputOptions and OutputOptions per format, wiring the internal plugin pipeline and supporting debug config dumps.

Use this subtree to see how tsdown builds the actual rolldown build options, including plugin ordering and mergeUserOptions integration. Debug dumping of generated rolldown configs is colocated here because it serializes these same options.

**Children.**

- [Bundled Rolldown Plugins](plugin-pipeline.md) `plugin-pipeline` · 7 unit(s)
- [Dependency Externalization](externalization.md) `externalization` · 9 unit(s)

**Depends on.**

- [Dependency Externalization](externalization.md) · containment · → 1 / ← 0 edge(s) (ancestor direct units and descendant subtree; → follows ` rolldown-assembly ` → ` externalization `) · Input options assembly wires the dependency externalization plugin into the plugin pipeline.
- [General and Filesystem Helpers](general-and-fs.md) · graph-confirmed · 17 edge(s)
- [Output File Naming and Formats](output-shaping.md) · graph-confirmed · 3 edge(s) · resolveOutputOptions uses output shaping for chunk filename templates and banner/footer addons.
- [Bundled Rolldown Plugins](plugin-pipeline.md) · containment · → 4 / ← 0 edge(s) (ancestor direct units and descendant subtree; → follows ` rolldown-assembly ` → ` plugin-pipeline `) · resolveInputOptions injects the bundled rolldown plugins into the input options.
- [User Config Normalization](config-merging.md) · graph-only · 2 edge(s)
- [Build Size Reporting](reporting.md) · graph-only · 1 edge(s)

**Depended on by.**

- [Build Orchestration](build-orchestration.md) · graph-confirmed · 4 edge(s) · Per-config bundling uses rolldown option assembly to build input/output options and debug dumps.

Parent: [tsdown Build Tool](tsdown.md)

## Units (7)

<a id="u-c7b946124458"></a>
### `getBuildOptions`

`export async function getBuildOptions( config: ResolvedConfig, format: NormalizedForm…` · [src/features/rolldown.ts:L36-L72][f1]

Assembles the full Rolldown BuildOptions for one format by combining resolveInputOptions and resolveOutputOptions.

The result spreads the input options, sets output and write from config.write, and debug-logs the config tagged with the format ('cjs dts' when cjsDts).

calls: [resolveInputOptions](rolldown-assembly.md#u-7fc5b178e947), [resolveOutputOptions](rolldown-assembly.md#u-9b5ea05ef4d5)

**Uncertainties.**

- The file's parse tree contains an ERROR node, so token-level coverage of this file is preserved but incomplete.

<a id="u-7fc5b178e947"></a>
### `resolveInputOptions`

`async function resolveInputOptions( config: ResolvedConfig, format: NormalizedFormat,…` · [src/features/rolldown.ts:L74-L188][f1]

Builds the Rolldown InputOptions for one format, including the tsdown plugin pipeline and defaults later merged with user inputOptions via mergeUserOptions.

Plugins are pushed in order: NodeProtocolPlugin when nodeProtocol is set; DepPlugin when a package or skipNodeModulesBundle is present; the dts plugin (dynamic import of rolldown-plugin-dts) for es format, or with emitDtsOnly and cjsDefault for the cjsDts pass; when not cjsDts: unplugin-unused's Unused when configured, CssPlugin (dynamic import) if @tsdown/css exists else CssGuardPlugin, ShebangPlugin, and importGlobPlugin when globImport is on; ReportPlugin when report is on and the logger level is at least info; WatchPlugin when watching; user plugins only on non-cjsDts passes. define merges config.define with env values injected as both process.env.KEY and import.meta.env.KEY (JSON-stringified); inject comes from getShimsInject only when shims and not cjsDts. Base options set platform to 'node' for cjs/CJS-dts builds, moduleTypes defaulting '.node' to 'copy', silent logLevel when the logger level is 'error', and devtools passthrough. The onLog hook suppresses MIXED_EXPORT warnings when cjsDefault is enabled, and escalates warnings to 'error' when logger.options.failOnWarn is set (except PLUGIN_TIMINGS) before always delegating to defaultHandler.

calls: [options.ts-merge-and-flag-helpers](config-merging.md#u-8ed4832a9578), [deps-ts-dep-plugin](externalization.md#u-bb7e95b646eb), [NodeProtocolPlugin](plugin-pipeline.md#u-0ba0d4cbad8c), [getShimsInject](plugin-pipeline.md#u-0acb9a1b84d0), [ReportPlugin](reporting.md#u-f9d0cf989188), [CssGuardPlugin](rolldown-assembly.md#u-4254ca9071c7), [ShebangPlugin](plugin-pipeline.md#u-bb3837c30551), [WatchPlugin](plugin-pipeline.md#u-cf0a21dabc14), [importWithError](general-and-fs.md#u-6e036190d6a7), [pkgExists](general-and-fs.md#u-2cf9b0e46dec)

**Uncertainties.**

- The dts plugin and CssPlugin are dynamically imported, so their runtime behavior is outside this file.
- The meaning of the LogLevels threshold (>=3 as info) depends on src/utils/logger.ts.

<a id="u-9b5ea05ef4d5"></a>
### `resolveOutputOptions`

`async function resolveOutputOptions( inputOptions: InputOptions, config: ResolvedConf…` · [src/features/rolldown.ts:L231-L276][f1]

Builds the Rolldown OutputOptions for one format, merged with user outputOptions via mergeUserOptions.

For the cjsDts pass the format is forced to 'es'. Entry/chunk file names come from resolveChunkFilename (honoring fixedExtension, outExtensions, and hash). exports is 'auto' when cjsDefault is set, else 'named'; minify applies only when not cjsDts; preserveModules follows the unbundle option with preserveModulesRoot computed as the lowest common ancestor of entry values; postBanner/postFooter come from resolveChunkAddon over the banner/footer options; codeSplitting is disabled for exe builds (otherwise undefined).

calls: [resolveChunkFilename](output-shaping.md#u-fa191ddae689), [resolveChunkAddon](output-shaping.md#u-b521ce5719c7), [options.ts-merge-and-flag-helpers](config-merging.md#u-8ed4832a9578), [lowestCommonAncestor](general-and-fs.md#u-7dd4d279c25f)

<a id="u-4ce786ef6bf6"></a>
### `debugBuildOptions`

`export async function debugBuildOptions( dir: string, name: string | undefined, forma…` · [src/features/rolldown.ts:L283-L315][f1]

Writes a self-describing debug rolldown config file to dir as rolldown.config.<format>.js.

It first decorates all plugins for readable inspection via handlePluginInspect, serializes the build options with formatWithOptions at unlimited depth/array/string lengths, and embeds the tsdown version, rolldown version, generation timestamp, and package name ('not specified' when absent) in a comment header. The file content is `export default <serialized>`.

calls: [debugBuildOptions](rolldown-assembly.md#u-4ce786ef6bf6)

<a id="u-ebb3a577fb25"></a>
### `getDebugRolldownDir`

`export async function getDebugRolldownDir(): Promise<string | undefined>` · [src/features/rolldown.ts:L278-L281][f1]

Returns a fresh temporary directory (tmpdir()/tsdown-config-*) for dumping debug configs, but only when the 'tsdown:rolldown' debug namespace is enabled; otherwise returns undefined.

<a id="u-4254ca9071c7"></a>
### `CssGuardPlugin`

`export function CssGuardPlugin(): Plugin` · [src/features/rolldown.ts:L344-L350][f1]

Creates the 'tsdown:css-guard' fallback plugin used when @tsdown/css is not installed.

Its post-order transform hook, filtered to CSS-family stylesheet ids (css, less, sass, scss, styl, stylus), unconditionally throws an Error telling the user to install @tsdown/css, so any stylesheet in the build aborts with that message.

group: [CssGuardPlugin](rolldown-assembly.md#u-4254ca9071c7)

<a id="u-bc94212cdea0"></a>
### `rolldown.ts module code (L1–L35)`

`module_region` · [src/features/rolldown.ts:L1-L35][f1]

Module imports, tsdown:rolldown debug logger, and package.json metadata import.

**Uncertainties.**

- This file's parse tree contains an ERROR node, so residual content coverage may be imprecise.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/rolldown/tsdown/blob/2b1be7e0accdb1d6e903cd42642666431fc5e93d/src/features/rolldown.ts
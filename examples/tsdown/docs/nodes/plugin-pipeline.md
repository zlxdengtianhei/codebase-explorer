# Bundled Rolldown Plugins

**Capability.** Small self-contained rolldown plugins handling node: protocol normalization, shebang executable bits, ESM shims, and watch-mode input tracking.

Use this subtree to inspect individual plugin behaviors injected by resolveInputOptions. Each plugin owns one narrow bundling concern and can be understood in isolation.

**Depends on.**

- [General and Filesystem Helpers](general-and-fs.md) · graph-confirmed · 5 edge(s)
- [Logging](logging.md) · graph-confirmed · 1 edge(s)

**Depended on by.**

- [Rolldown Options Assembly](rolldown-assembly.md) · containment · → 4 / ← 0 edge(s) (ancestor direct units and descendant subtree; → follows ` rolldown-assembly ` → ` plugin-pipeline `) · resolveInputOptions injects the bundled rolldown plugins into the input options.

Parent: [Rolldown Options Assembly](rolldown-assembly.md)

## Units (7)

<a id="u-0ba0d4cbad8c"></a>
### `NodeProtocolPlugin`

`export function NodeProtocolPlugin(nodeProtocolOption: 'strip' | true): Plugin` · [src/features/node-protocol.ts:L8-L50][f1]

Normalizes Node builtin import specifiers per the nodeProtocol option via a pre-order resolveId plugin.

It first lists builtin modules that lack the 'node:' prefix. With 'strip', the filter matches 'node:<builtin>' ids; the handler strips the 5-char prefix, first tries this.resolve so aliases or tsconfig paths can still win, and otherwise returns the stripped id as external with moduleSideEffects false. With true, the filter matches bare builtin ids and the handler rewrites them to 'node:<id>' as external with moduleSideEffects false. The docstring notes the protocol requires Node v14.18+.

**Uncertainties.**

- Whether this.resolve can resolve to a non-builtin file for a name that is a builtin name depends on user alias plugins; the code prefers such a resolution over externalizing.

<a id="u-bb3837c30551"></a>
### `ShebangPlugin`

`export function ShebangPlugin( logger: Logger, cwd: string, nameLabel?: string, isDua…` · [src/features/shebang.ts:L10-L18][f2]

Creates the 'tsdown:shebang' plugin, which restores the executable bit on entry outputs that start with a shebang.

In writeBundle it iterates bundle artifacts, skipping non-chunks and non-entry chunks and anything whose code fails /^#!.*/. The target path resolves the explicit options.file when set, otherwise joins options.dir with chunk.fileName (dir asserted non-null). Only when fsExists confirms the file was written does it log the chmod (with the format label when isDualFormat) and apply chmod 0o755; missing files are silently skipped.

calls: [fsExists](general-and-fs.md#u-0f222011da8d), [prettyFormat](logging.md#u-9a73f5293780)

**Uncertainties.**

- When options.file is set, every matching entry chunk chmods that same file path; whether multi-entry output with a single file option occurs in practice is not visible here.

<a id="u-ee2d8d331801"></a>
### `shebang.ts module code (L1–L9)`

`module_region` · [src/features/shebang.ts:L1-L9][f2]

Module imports and the RE_SHEBANG /^#!.*/ constant.

<a id="u-0acb9a1b84d0"></a>
### `getShimsInject`

`export function getShimsInject( format: NormalizedFormat, platform: ResolvedConfig['p…` · [src/features/shims.ts:L10-L20][f3]

Returns esm-shim injections only for the combination of es format and node platform: __dirname and __filename are mapped to the corresponding exports of the shimFile constant.

Any other format/platform combination returns undefined, meaning no injections.

<a id="u-7db915e1f2c6"></a>
### `shims.ts module code (L1–L9)`

`module_region` · [src/features/shims.ts:L1-L9][f3]

Resolves the shimFile constant to esm-shims.js relative to this module, one or two directories up depending on the TSDOWN_PRODUCTION build flag.

<a id="u-cf0a21dabc14"></a>
### `WatchPlugin`

`export function WatchPlugin( configFiles: string[], { config, chunks }: TsdownBundle,…` · [src/features/watch.ts:L9-L22][f4]

Creates the 'tsdown:watch' plugin wiring extra watch inputs and chunk tracking.

Its options hook exists only when config.ignoreWatch is non-empty: it lazily creates inputOptions.watch and appends all ignoreWatch entries to watch.exclude (toArray-normalized). buildStart adds watch files: config.tsconfig when set, every config file passed to the plugin, each comma-resolved entry of config.watch when it is not a boolean, and the package's packageJsonPath when config.pkg exists. Its post-order generateBundle handler appends the bundle outputs, mapped by addOutDirToChunks with config.outDir, to the shared tsdownBundle.chunks list.

calls: [resolveComma](general-and-fs.md#u-adfdd23335a0), [toArray](general-and-fs.md#u-1e9a5d8a9f7d), [addOutDirToChunks](general-and-fs.md#u-7a2fdc0e4dc6)

<a id="u-e14fea0ca222"></a>
### `watch.ts module code (L1–L8)`

`module_region` · [src/features/watch.ts:L1-L8][f4]

Module imports.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/rolldown/tsdown/blob/2b1be7e0accdb1d6e903cd42642666431fc5e93d/src/features/node-protocol.ts
[f2]: https://github.com/rolldown/tsdown/blob/2b1be7e0accdb1d6e903cd42642666431fc5e93d/src/features/shebang.ts
[f3]: https://github.com/rolldown/tsdown/blob/2b1be7e0accdb1d6e903cd42642666431fc5e93d/src/features/shims.ts
[f4]: https://github.com/rolldown/tsdown/blob/2b1be7e0accdb1d6e903cd42642666431fc5e93d/src/features/watch.ts
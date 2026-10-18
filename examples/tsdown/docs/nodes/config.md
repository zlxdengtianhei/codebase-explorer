# Configuration Resolution

**Capability.** Transforms user-supplied inline options or config files into a flat list of fully resolved build configs, including the public defineConfig helper and the type-level contract.

Use this subtree to understand how tsdown turns loose user input into ResolvedConfig objects. It owns the defineConfig typing surface, the shared type definitions, and the pipeline that multiplies configs across formats, workspaces, and config files.

**Children.**

- [Config File Discovery and Loading](config-file-loading.md) `config-file-loading` · 4 unit(s)
- [User Config Normalization](config-merging.md) `config-merging` · 3 unit(s)
- [Workspace Expansion](workspace-resolution.md) `workspace-resolution` · 1 unit(s)
- [Entry Resolution](entry-resolution.md) `entry-resolution` · 6 unit(s)
- [Target and Tsconfig Resolution](target-and-tsconfig.md) `target-and-tsconfig` · 6 unit(s)

**Depends on.**

- [Config File Discovery and Loading](config-file-loading.md) · containment · → 1 / ← 0 edge(s) (ancestor direct units and descendant subtree; → follows ` config ` → ` config-file-loading `) · resolveConfig loads user config files via the config file loader.
- [User Config Normalization](config-merging.md) · containment · → 1 / ← 0 edge(s) (ancestor direct units and descendant subtree; → follows ` config ` → ` config-merging `)
- [Entry Resolution](entry-resolution.md) · containment · → 0 / ← 0 edge(s) (ancestor direct units and descendant subtree; → follows ` config ` → ` entry-resolution `)
- [Workspace Expansion](workspace-resolution.md) · containment · → 1 / ← 0 edge(s) (ancestor direct units and descendant subtree; → follows ` config ` → ` workspace-resolution `)

**Depended on by.**

- [Build Orchestration](build-orchestration.md) · graph-confirmed · 3 edge(s) · Build orchestration calls resolveConfig to obtain the fully resolved per-format configs before bundling.

Parent: [tsdown Build Tool](tsdown.md)

## Units (5)

<a id="u-36e982819374"></a>
### `config-ts-defineconfig`

`export function defineConfig(options: UserConfig): UserConfig` · [src/config.ts:L9-L9][f1]

Public config helper: defineConfig is an identity function accepting a single UserConfig object, an array of configs, or a config function, and returning it unchanged; its value is purely the typed overloads that narrow the input to UserConfig, UserConfig[], UserConfigFn, or UserConfigExport.

The module also re-exports the UserConfig-related types and mergeConfig from the internal config implementation; these re-exports carry no behavior.

<a id="u-62365116d429"></a>
### `types.ts-config-type-definitions`

`export type Sourcemap = boolean | 'inline' | 'hidden'` · [src/config/types.ts:L50-L50][f2]

Type-only definitions for tsdown configuration.

Sourcemap is boolean | 'inline' | 'hidden'; Format is rolldown's ModuleFormat and NormalizedFormat its internal subset. TsdownInputOption extends input to strings or records mapping output names to glob string arrays including `!`-negation patterns. Workspace describes workspace mode: include ('auto' by default, glob-supported), exclude (defaulting to node_modules/dist/test/tests/temp/tmp patterns), and an optional workspace config file toggle/path. CIOption is 'ci-only' | 'local-only'; WithEnabled<T> lets any feature option be a boolean, a CI mode, or an options object with an `enabled` field defaulting to true. UserConfig declares all build options with documented defaults (entry defaults to src/index.ts, outDir 'dist', format defaults to ESM, clean true, hash true, write true, fixedExtension true for node platform, cjsDefault true, globImport true, report true, platform 'node'), deprecations (external/noExternal/inlineOnly/skipNodeModulesBundle to deps options; bundle to unbundle; injectStyle to css.inject; publicDir to copy; removeNodeProtocol to nodeProtocol), and experimental features (devtools, exe/SEA, workspace). InlineConfig adds CLI/API-only `config`, `configLoader` ('auto' | 'native' | 'unrun'), and `filter`. UserConfigFn receives inline config plus { ci }; UserConfigExport is an awaitable arrayable config or such a function. ResolvedConfig omits workspace/fromVite and deprecated or merged keys, makes most options optional, and adds resolved fields: expanded entry, rawEntry for watch re-globbing, nameLabel, single NormalizedFormat, string[] target and clean, pkg, nodeProtocol, logger, string|RegExp[] ignoreWatch, resolved deps, and each feature as `false | Options`.

**Uncertainties.**

- ResolvedConfig is computed via Overwrite/MarkPartial utility types; the exact resulting optionality of each field depends on those external utilities.

<a id="u-ac0742734544"></a>
### `shims-d-ts-importmeta`

`declare global { interface ImportMeta` · [src/shims.d.ts:L1-L4][f3]

Ambient type declaration only: augments the global ImportMeta interface with an optional TSDOWN_PRODUCTION boolean and exports nothing at runtime.

No behavior.

<a id="u-3ddd9346e44f"></a>
### `resolveConfig`

`export async function resolveConfig(inlineConfig: InlineConfig): Promise<{ configs: R…` · [src/config/index.ts:L20-L68][f4]

Resolves an inline CLI config into a flat list of fully resolved build configs plus the config files consulted.

It first normalizes inlineConfig.cwd via path.resolve, then loadConfigFile yields root UserConfig entries and an optional config file path; the file path, when present, is collected into the returned files list. Each root config goes through resolveWorkspace, producing workspace configs and additional workspace files that are appended to files. Workspace configs are filtered: entries are kept only when they are not workspaces themselves or they declare an entry. Surviving configs pass through resolveUserConfig (run concurrently via Promise.all), results are flattened and falsy entries removed. If the final config list is empty the function throws Error('No valid configuration found.'); otherwise it returns { configs, files }. The resolved count is the product of root, workspace, and sub config counts per the file's comment. Logging goes through an obug 'tsdown:config' debug instance and only emits when debug is enabled.

calls: [loadConfigFile](config-file-loading.md#u-60d630078245), [resolveWorkspace](workspace-resolution.md#u-58cffcc57f13), [resolveUserConfig](config-merging.md#u-9f27c28524ef)

**Uncertainties.**

- Whether loadConfigFile or resolveWorkspace can throw and how such errors propagate is not visible in this file
- resolveUserConfig may return falsy values (the code filters !!config), but the conditions producing them are not shown here

<a id="u-fc3cdca9a97e"></a>
### `index.ts module code (L1–L19)`

`module_region` · [src/config/index.ts:L1-L19][f4]

Module preamble: imports node:path, obug's createDebug, and sibling config modules; re-exports everything from ./types.ts; creates the module-level debug logger 'tsdown:config' and records a comment describing the resolution pipeline and config-count multiplication.

No executable behavior beyond the debug instance and re-export.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/rolldown/tsdown/blob/2b1be7e0accdb1d6e903cd42642666431fc5e93d/src/config.ts
[f2]: https://github.com/rolldown/tsdown/blob/2b1be7e0accdb1d6e903cd42642666431fc5e93d/src/config/types.ts
[f3]: https://github.com/rolldown/tsdown/blob/2b1be7e0accdb1d6e903cd42642666431fc5e93d/src/shims.d.ts
[f4]: https://github.com/rolldown/tsdown/blob/2b1be7e0accdb1d6e903cd42642666431fc5e93d/src/config/index.ts
# Config file loading

**Capability.** Discovers, parses, and imports tsdown config files, including workspace expansion and Vite/Vitest config reuse.

Come here for how config files are found and loaded: parser selection (native, jiti, unrun), file imports via URL, and workspace-mode per-package expansion. Ends with fully resolved build configs.

**Depends on.**

- [Config resolution and normalization](config-resolution-and-normalization.md) · graph-confirmed · 2 edge(s) · Config file loading hands parsed configs to resolution and normalization for defaults and per-format resolution.
- [Dependency handling and general utilities](dependency-handling-and-general-utilities.md) · graph-only · 2 edge(s)
- [Entry resolution and filesystem helpers](entry-resolution-and-filesystem-helpers.md) · graph-only · 1 edge(s)

**Depended on by.**

- [Config resolution and normalization](config-resolution-and-normalization.md) · graph-confirmed · 1 edge(s) · 1 inferred relation(s)
- [Build orchestration and lifecycle](build-orchestration-and-lifecycle.md) · graph-only · 1 edge(s)

Parent: [Configuration loading and resolution](configuration-loading-and-resolution.md)

## Units (8)

<a id="u-ae849af2d3c6"></a>
### `createParser`

`function createParser(loader: Parser)` · [src/config/file.ts:L162-L183][f1]

Builds the file parser used by the config loader.

For package.json it reads, JSON.parses, and returns the parsed tsdown field; for tsdown.config or any .json file it returns the parsed JSON. Other files are imported via nativeImport or unrunImport depending on the chosen loader.

calls: [nativeImport](config-file-loading.md#u-a83fa7a051dd), [unrunImport](config-file-loading.md#u-c209b695626f)

<a id="u-60d630078245"></a>
### `loadConfigFile`

`export async function loadConfigFile( inlineConfig: InlineConfig, workspace?: string,…` · [src/config/file.ts:L57-L144][f1]

Discovers and loads tsdown config files for a directory, returning an array of user configs plus the config file path.

If inline config is false, returns a single empty config. If config is a string path: a file path overrides discovery (cwd becomes its directory); a directory path becomes the search cwd. Otherwise it searches for tsdown.config.{ts,mts,cts,js,mjs,cjs,json} and package.json (tsdown field), stopping upward traversal at the workspace directory when given. The loaded export is awaited; a top-level function is called with (inlineConfig, {ci: isInCi}). The result is normalized to an array (empty array becomes one empty config); nested functions throw an error telling users the function must be top-level. Each config's cwd is resolved against the search cwd (config-provided cwd is resolved relative to it).

**Notes.**

- failure: Throws when a function is nested inside multiple configurations.

calls: [resolveConfigLoader](config-file-loading.md#u-b213cb28603d), [createParser](config-file-loading.md#u-ae849af2d3c6), [nativeImport](config-file-loading.md#u-a83fa7a051dd), [unrunImport](config-file-loading.md#u-c209b695626f)

<a id="u-0db73e2398fc"></a>
### `loadViteConfig`

`export async function loadViteConfig( prefix: string, cwd: string, configLoader: Inli…` · [src/config/file.ts:L22-L53][f1]

Loads a Vite/Vitest config file (e.g. vite.config) from a directory using the resolved loader and parser, returning the user config or undefined if none found.

The loaded export is awaited; if it is a function it is invoked with {command:'build', mode:'production'} and its return value is used. Logs the config source path via the global logger.

calls: [resolveConfigLoader](config-file-loading.md#u-b213cb28603d), [createParser](config-file-loading.md#u-ae849af2d3c6)

<a id="u-a83fa7a051dd"></a>
### `nativeImport`

`async function nativeImport(id: string)` · [src/config/file.ts:L185-L222][f1]

Imports a config file natively via a file URL, bypassing module caches when possible.

If import-without-cache is supported it initializes it with skipNodeModules and passes cache:'no' import attributes; otherwise under non-Bun runtimes it appends a random no-cache query parameter. Import failures are caught: 'Cannot find module' errors are rethrown as a friendlier error suggesting the unrun loader (with the original as cause); errors whose stack references node:internal/modules/esm/translators are rethrown as a known-Node-bug error suggesting unrun or Node >= 24.11.1; all other errors propagate unchanged. Returns mod.default or the module itself if no default export.

<a id="u-b213cb28603d"></a>
### `resolveConfigLoader`

`function resolveConfigLoader( configLoader: InlineConfig['configLoader'] = 'auto', ):…` · [src/config/file.ts:L152-L160][f1]

Maps a configLoader setting to the actual parser: 'auto' resolves to a module-level choice computed once — 'native' under Bun, or when the runtime has native TypeScript support and import-without-cache reports support, otherwise 'unrun'.

Any other value becomes 'unrun' except an explicit 'native'.

<a id="u-c209b695626f"></a>
### `unrunImport`

`async function unrunImport(id: string)` · [src/config/file.ts:L224-L230][f1]

Loads a config file by delegating to the unrun package, returning its module object; unrun is imported dynamically on first use.

<a id="u-3ddd9346e44f"></a>
### `resolveConfig`

`export async function resolveConfig(inlineConfig: InlineConfig): Promise<{ configs: R…` · [src/config/index.ts:L20-L68][f2]

Resolves an inline CLI config into a flat list of fully resolved build configs plus the config file paths used.

It first resolves `cwd` to an absolute path, then loads the root config file(s), then for each root config resolves workspaces, filters workspace configs to those that are non-workspace or have an `entry`, and resolves each through user-config resolution, flattening and dropping falsy results. It collects root and workspace file paths into `files`. If no resolved configs remain, it throws `Error('No valid configuration found.')`. Debug logging traces inline, root, workspace, and resolved configs.

calls: [function::loadConfigFile][f1], [function::resolveWorkspace][f3], [function::resolveUserConfig][f4]

**Uncertainties.**

- Semantics of `config.workspace` and the exact meaning of the `!config.workspace || config.entry` filter depend on types and resolveWorkspace, not visible here.
- Whether resolveUserConfig can return falsy values (filtered later) is not established by this source.

<a id="u-58cffcc57f13"></a>
### `resolveWorkspace`

`export async function resolveWorkspace( config: UserConfig, inlineConfig: InlineConfi…` · [src/config/workspace.ts:L18-L92][f3]

Expands workspace mode into per-package user configs.

It merges config and inlineConfig (inline wins) to get the root cwd and workspace setting; without a workspace setting it returns the single merged config. A true workspace becomes {}, and a string/array workspace becomes {include: ...}. Package discovery: include 'auto' globs **/package.json under rootCwd (minus the root package.json) and maps to parent directories; an explicit include globs directories directly. Both honor a default exclude set (node_modules, dist, test/tests, temp/tmp patterns). Zero packages found throws. For each package directory it calls loadConfigFile with the package cwd and the workspace config setting, collecting configs and found config file paths; each loaded config is merged over the root normalized config (root values as defaults). All packages load in parallel via Promise.all.

**Notes.**

- failure: Throws 'No workspace packages found...' when discovery yields no packages.

calls: [loadConfigFile](config-file-loading.md#u-60d630078245)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/rolldown/tsdown/blob/2b1be7e0accdb1d6e903cd42642666431fc5e93d/src/config/file.ts
[f2]: https://github.com/rolldown/tsdown/blob/2b1be7e0accdb1d6e903cd42642666431fc5e93d/src/config/index.ts
[f3]: https://github.com/rolldown/tsdown/blob/2b1be7e0accdb1d6e903cd42642666431fc5e93d/src/config/workspace.ts
[f4]: https://github.com/rolldown/tsdown/blob/2b1be7e0accdb1d6e903cd42642666431fc5e93d/src/config/options.ts

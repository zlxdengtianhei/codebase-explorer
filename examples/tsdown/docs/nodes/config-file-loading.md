# Config file loading

**Capability.** Loads config files through selected parsers/importers, resolves workspace layers, and returns resolved configs with discovered files.

Use this module for config discovery and loading from files or workspaces. Units cover parser selection, JSON/JS/TS imports, Vite config loading, and workspace flattening.

**Depends on.**

- [Config resolution and logging](config-resolution-and-logging.md) · graph-confirmed · 1 edge(s)
- [Entry and path resolution](entry-and-path-resolution.md) · graph-confirmed · 1 edge(s)
- [Package output and validation](package-output-and-validation.md) · graph-confirmed · 3 edge(s)
- [Package export map generation](package-export-map-generation.md) · graph-only · 2 edge(s)
- [Dependency externalization utilities](dependency-externalization-utilities.md) · graph-only · 1 edge(s)

**Depended on by.**

- [Build execution and watching](build-execution-and-watching.md) · graph-confirmed · 1 edge(s)
- [Config resolution and logging](config-resolution-and-logging.md) · graph-confirmed · 1 edge(s)
- [Build orchestration lifecycle](build-orchestration-lifecycle.md) · graph-only · 1 edge(s)

Parent: [tsdown build tool](tsdown-build-tool.md)

## Units (8)

<a id="u-b1ff4d6c25ca"></a>
### `file.ts-config-loader-selection`

`const isBun = !!process.versions.bun const nativeTS = process.features.typescript || …` · [src/config/file.ts:L148-L150][f1]

Selects the config parser implementation from the requested loader and runtime capabilities.

The auto choice is native when running under Bun, or when native TypeScript/Deno support is present and the import-without-cache feature is supported; otherwise it is unrun. An explicit native request stays native; any other explicit value resolves to unrun. The module-level auto choice is computed once from process/runtime flags.

<a id="u-ae849af2d3c6"></a>
### `createParser`

`function createParser(loader: Parser)` · [src/config/file.ts:L162-L183][f1]

Creates an async file parser that reads JSON-like config files directly and delegates JavaScript/TypeScript files to the selected importer.

A basename of package.json is parsed as JSON and returns its `tsdown` field; a basename equal to the config prefix or ending in `.json` is parsed as JSON and returned whole. Other files go to the native importer when the loader is native, otherwise to the unrun importer. File-read and JSON-parse errors propagate.

<a id="u-60d630078245"></a>
### `loadConfigFile`

`export async function loadConfigFile( inlineConfig: InlineConfig, workspace?: string,…` · [src/config/file.ts:L57-L144][f1]

Loads tsdown config exports from a file or discovery sources and normalizes them into per-config cwd values.

If the config option is false it returns one empty config. A string path is inspected only when fsStat returns a stat: a file becomes an explicit override and sets cwd to its directory; a directory sets cwd to that directory; a missing path is ignored and discovery continues. Discovery searches `tsdown.config` with ts/mts/cts/js/mjs/cjs/json plus package.json, using the selected loader; explicit override searches only the given file. The loader stops at the parent of the workspace directory when a workspace is supplied. If a result is found it logs the source, awaits the export, and calls a top-level function with the inline config and `{ ci: isInCi }`. The export is array-normalized; an empty result becomes `[{}]`; any function nested after normalization throws. Each returned config gets cwd resolved from its own cwd relative to the loader cwd, or the loader cwd when absent. The source file is returned when found. Read, parse, and import errors propagate.

<a id="u-0db73e2398fc"></a>
### `loadViteConfig`

`export async function loadViteConfig( prefix: string, cwd: string, configLoader: Inli…` · [src/config/file.ts:L22-L53][f1]

Loads a Vite config through the selected config loader and returns its resolved export.

It builds a parser for the chosen loader, searches for `<prefix>.config` with js/mjs/ts/cjs/mts/cts extensions under the given cwd, and returns undefined when no result is found. On a hit it logs the source, awaits the exported config, and if the export is a function calls it with `{ command: 'build', mode: 'production' }`; otherwise returns the value. Loader, parser, and import errors propagate.

<a id="u-a83fa7a051dd"></a>
### `nativeImport`

`async function nativeImport(id: string)` · [src/config/file.ts:L185-L222][f1]

Imports a config file through native dynamic import with cache-busting behavior and translates two known failure modes.

When import-without-cache is supported it initializes that support with skipNodeModules and sets a no-cache import attribute; otherwise, outside Bun, it appends a random no-cache query parameter. The module default export is returned when present, otherwise the module namespace. A 'Cannot find module' error is rethrown as a new error suggesting the unrun loader; a stack containing the Node ESM translator internal path is rethrown as a known-Node-bug error suggesting unrun or a newer Node; all other errors propagate unchanged.

<a id="u-c209b695626f"></a>
### `unrunImport`

`async function unrunImport(id: string)` · [src/config/file.ts:L224-L230][f1]

Imports a config file through the unrun loader and returns its module export.

It dynamically imports unrun, calls it with a file URL for the path, and returns the resulting module. Import and loader errors propagate.

<a id="u-3ddd9346e44f"></a>
### `resolveConfig`

`export async function resolveConfig(inlineConfig: InlineConfig): Promise<{ configs: R…` · [src/config/index.ts:L20-L68][f2]

resolveConfig normalizes an optional inline working directory, loads root and workspace configuration layers, resolves each applicable config, and returns resolved configs plus discovered files.

It mutates the supplied inline config only when its cwd is truthy, replacing it with an absolute path. It then loads the root config; if a root file is returned, that file is added to the result files and logged, otherwise it logs that none was found. For every root config it resolves workspaces, appends any returned workspace files, filters workspace configs to those that are not workspace-scoped or that have an entry, resolves the survivors, flattens the per-root results, and drops falsy resolved configs. If no resolved configs remain, it throws Error('No valid configuration found.'); otherwise it returns the configs and accumulated files. There is no catch, so failures from loading, workspace resolution, or user-config resolution propagate. Debug logging occurs throughout.

calls: [loadConfigFile](../../catalog.json.gz), [resolveWorkspace](../../catalog.json.gz), [resolveUserConfig](../../catalog.json.gz), [path.resolve](../../catalog.json.gz)

**Uncertainties.**

- The exact return shape and failure behavior of loadConfigFile, resolveWorkspace, and resolveUserConfig are not visible; the truthiness filter implies resolveUserConfig may return a falsy value.
- Whether workspaceFiles can be an empty array versus undefined is not visible; the code appends it only when truthy.

<a id="u-58cffcc57f13"></a>
### `resolveWorkspace`

`export async function resolveWorkspace( config: UserConfig, inlineConfig: InlineConfi…` · [src/config/workspace.ts:L18-L92][f3]

Resolves workspace mode into a flat list of configs and discovered config files.

With no workspace option it returns the merged config as a single config and an empty file list. `true` means auto-discovery; a string or array becomes the include list; an object supplies include/exclude/config. Auto-discovery globs package.json files under the root cwd, excludes the default node_modules/dist/test/temp patterns, drops the root package.json, and maps each file to its directory. Explicit includes glob directories only, absolutely, with the same excludes. No packages throws. Each package directory loads a config file with the workspace config override and that directory as cwd; found files are collected as concurrent loads finish, and each loaded config is merged over the normalized root/inline config. Loader errors propagate.

Look up code: the commands are under "Read further" in [INDEX.md](../INDEX.md); `cbe query` and `cbe source` take a unit title or anchor from this page.

[f1]: https://github.com/rolldown/tsdown/blob/2b1be7e0accdb1d6e903cd42642666431fc5e93d/src/config/file.ts
[f2]: https://github.com/rolldown/tsdown/blob/2b1be7e0accdb1d6e903cd42642666431fc5e93d/src/config/index.ts
[f3]: https://github.com/rolldown/tsdown/blob/2b1be7e0accdb1d6e903cd42642666431fc5e93d/src/config/workspace.ts

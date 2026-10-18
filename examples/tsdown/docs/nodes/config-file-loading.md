# Config File Discovery and Loading

**Capability.** Locates, imports, and parses tsdown and Vite/Vitest config files, including cache-defeating native ESM import and loader selection.

Use this subtree when config files are not being picked up or parsed as expected. It isolates all filesystem/module-loading mechanics so resolution logic above stays declarative.

**Depends on.**

- [General and Filesystem Helpers](general-and-fs.md) · graph-confirmed · 2 edge(s)

**Depended on by.**

- [Configuration Resolution](config.md) · containment · → 1 / ← 0 edge(s) (ancestor direct units and descendant subtree; → follows ` config ` → ` config-file-loading `) · resolveConfig loads user config files via the config file loader.
- [Workspace Expansion](workspace-resolution.md) · graph-confirmed · 1 edge(s) · Workspace expansion reuses the config file loader to load per-package configs.
- [User Config Normalization](config-merging.md) · graph-only · 1 edge(s)

Parent: [Configuration Resolution](config.md)

## Units (4)

<a id="u-60d630078245"></a>
### `loadConfigFile`

`export async function loadConfigFile( inlineConfig: InlineConfig, workspace?: string,…` · [src/config/file.ts:L57-L144][f1]

Discovers and loads the tsdown config file and normalizes the export into an array of UserConfig objects.

Branches: inlineConfig.config === false returns a single empty config with no file. A string config path is stat'd: if it is a file, override mode is set (cwd becomes the file's directory and only that exact file is parsed with no extensions); if a directory, it becomes the cwd; if the stat misses, default discovery proceeds (tsdown.config.{ts,mts,cts,js,mjs,cjs,json} plus package.json). When a workspace root is passed, stopAt is its parent directory. If a result is found, its source is logged (with the loader name unless native), the export is awaited, and a top-level function export is invoked as exported(inlineConfig, { ci: isInCi }). The export is flattened with toArray; an empty array gains one empty object; a function nested among multiple configs throws an Error instructing the function to be top-level. Each returned config gets cwd resolved against the discovered cwd.

calls: [file.ts-loader-and-parser-helpers](config-file-loading.md#u-8fa12d2713e9); uses: [fsStat](general-and-fs.md#u-73b329382a5b)

**Uncertainties.**

- A stat result that is neither file nor directory falls through to default discovery; no explicit handling exists.

<a id="u-0db73e2398fc"></a>
### `loadViteConfig`

`export async function loadViteConfig( prefix: string, cwd: string, configLoader: Inli…` · [src/config/file.ts:L22-L53][f1]

Loads a Vite or Vitest config file and returns its user config for reuse by tsdown.

It resolves the loader via resolveConfigLoader, builds a parser via createParser, and uses createConfigCoreLoader to locate `${prefix}.config` with extensions js, mjs, ts, cjs, mts, cts under the given cwd. If no file is found it returns undefined. On success it logs the source path via globalLogger, awaits the export, and if the export is a function invokes it with a fixed { command: 'build', mode: 'production' } ConfigEnv and returns the result; otherwise it returns the object. Errors from loading or parsing propagate.

calls: [file.ts-loader-and-parser-helpers](config-file-loading.md#u-8fa12d2713e9)

**Uncertainties.**

- createConfigCoreLoader error semantics are external and unverified here.

<a id="u-a83fa7a051dd"></a>
### `nativeImport`

`async function nativeImport(id: string)` · [src/config/file.ts:L185-L222][f1]

Imports a config module via the runtime's native ESM import while defeating the module cache.

The path is converted to a file URL; if import-without-cache supports this runtime, a cache:'no' import attribute is set and init({ skipNodeModules: true }) is called; otherwise, when not on Bun, a randomUUID 'no-cache' query parameter is appended to the URL. The module's default export is returned when present, otherwise the namespace object. Import failures are classified in the catch handler: a message containing 'Cannot find module' is rethrown as an Error advising the --config-loader unrun flag with the original error as cause; a stack referencing node:internal/modules/esm/translators is rethrown as an Error naming a known Node.js bug and suggesting unrun or Node v24.11.1+; any other error propagates unchanged.

**Uncertainties.**

- Which runtime versions satisfy import-without-cache's isSupported is external behavior.

<a id="u-8fa12d2713e9"></a>
### `file.ts-loader-and-parser-helpers`

`type Parser = 'native' | 'unrun'` · [src/config/file.ts:L146-L146][f1]

Loader selection and config-file parsing helpers.

resolveConfigLoader maps InlineConfig.configLoader (default 'auto') to a Parser: 'auto' resolves to the module constant autoLoader — 'native' when running under Bun (process.versions.bun) or when the runtime natively supports TypeScript (process.features.typescript or process.versions.deno) and import-without-cache's isSupported is true — otherwise 'unrun'; an explicit 'native' stays 'native', and any other value becomes 'unrun'. createParser returns an async parser keyed on basename: 'package.json', 'tsdown.config', or any '*.json' name is read as UTF-8 and JSON.parse'd, returning parsed?.tsdown for package.json (undefined when the key is absent) and the parsed JSON otherwise; non-JSON files go through nativeImport for the 'native' loader or unrunImport otherwise. unrunImport dynamically imports 'unrun' and returns its evaluated module for the file URL.

**Notes.**

- contract: package.json is a config source whose config lives under the `tsdown` key.

calls: [nativeImport](config-file-loading.md#u-a83fa7a051dd)

**Uncertainties.**

- Whether unrun evaluates TypeScript/ESM identically to native import cannot be verified from this file.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/rolldown/tsdown/blob/2b1be7e0accdb1d6e903cd42642666431fc5e93d/src/config/file.ts
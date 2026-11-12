# Config resolution and logging

**Capability.** Resolves user configs and options, loads package/tsconfig metadata, formats logs, and adds shebang execute permissions.

Come here for config merging, feature-option resolution, package and tsconfig discovery, logging helpers, and shebang handling. Units describe defaults, filters, environment selection, and permission grants.

**Depends on.**

- [Build execution and watching](build-execution-and-watching.md) · graph-confirmed · 2 edge(s) · Config resolution supplies resolved options and logging context to build execution and watching.
- [Config file loading](config-file-loading.md) · graph-confirmed · 1 edge(s)
- [Entry and path resolution](entry-and-path-resolution.md) · graph-confirmed · 3 edge(s)
- [Executable builds and sizing](executable-builds-and-sizing.md) · graph-confirmed · 1 edge(s)
- [Package output and validation](package-output-and-validation.md) · graph-confirmed · 9 edge(s)
- [Dependency externalization utilities](dependency-externalization-utilities.md) · graph-only · 6 edge(s)
- [Package export map generation](package-export-map-generation.md) · graph-only · 3 edge(s)
- [Build orchestration lifecycle](build-orchestration-lifecycle.md) · graph-only · 1 edge(s)
- [Copy shortcuts target helpers](copy-shortcuts-target-helpers.md) · graph-only · 1 edge(s)
- [Executable SEA builds](executable-sea-builds.md) · graph-only · 1 edge(s)

**Depended on by.**

- [Config file loading](config-file-loading.md) · graph-confirmed · 1 edge(s)
- [Executable builds and sizing](executable-builds-and-sizing.md) · graph-confirmed · 1 edge(s)
- [Rolldown option assembly](rolldown-option-assembly.md) · graph-confirmed · 4 edge(s) · Rolldown option assembly uses config resolution and logging for resolved build options.
- [Bundle size reporting](bundle-size-reporting.md) · graph-only · 1 edge(s)

Parent: [tsdown build tool](tsdown-build-tool.md)

## Units (16)

<a id="u-a9c2fa9df395"></a>
### `logger.ts-color-generation`

`export function generateColor(name: string = 'default'): Ansis` · [src/utils/logger.ts:L153-L172][f1]

Returns a cached color function for a name.

The default name maps to blue; other names are hashed from character codes, converted to a hue modulo 360 with fixed saturation 35 and lightness 55, then converted to RGB. The HSL conversion reduces hue modulo 360 and normalizes components; zero saturation yields equal channels, otherwise it computes q and p and uses a hue helper that wraps offsets and interpolates piecewise. Each channel is multiplied by 255 first, then rounded, then clamped below at 0; there is no upper clamp. The chosen color is cached by name.

<a id="u-24677c5d90a2"></a>
### `logger.ts-label-formatting`

`export function getNameLabel(ansis: Ansis, name?: string): string | undefined` · [src/utils/logger.ts:L130-L133][f1]

Builds bracketed labels.

The name-label helper returns undefined when no name is supplied; otherwise it wraps the name in square brackets and applies the supplied color function. The format-label helper maps 'es' to blue ESM, 'cjs' to yellow CJS, and any other format to its uppercase text through an identity color function; all results are bracketed.

<a id="u-7ed82a0ef7a1"></a>
### `logger.ts-logger-factory-and-methods`

`export function createLogger( level: LogLevel = 'info', options: LoggerOptions = {}, …` · [src/utils/logger.ts:L49-L67][f1]

Builds a logger with level and options, returning a supplied custom logger immediately if present.

Defaults are info level, allowClearScreen true, failOnWarn false, and global console. Output is gated by numeric level: a message is emitted only when the logger level is at least the message type's level; info uses console.log, other types use the matching console method. Screen clearing is enabled only when allowClearScreen, stdout is a TTY, and CI is unset; otherwise it is a no-op. info prefixes a blue info mark; success prefixes a green check and logs at info level; error prefixes a red ERROR block, logs at error level, and sets process.exitCode to 1. warn adds the formatted message to a shared set and logs a yellow WARN block, but under failOnWarn it delegates to error and returns before adding. warnOnce first returns if the formatted message is already in the shared set; under failOnWarn it delegates to error and returns before adding, so repeated new warnOnce calls are not deduplicated in that mode; otherwise it adds the message and logs the warn block. The clearScreen method calls the selected clear function only when the logger level is at least the requested type's level.

<a id="u-80e9616b17a0"></a>
### `logger.ts-logger-formatting-and-screen-clearing`

`function format(msgs: any[])` · [src/utils/logger.ts:L35-L37][f1]

Formats log arguments by dropping undefined and false values and joining the rest with spaces.

Screen clearing computes rows minus two; if positive it builds that many newline characters, otherwise an empty string, then always calls console.info with that string, so even the empty case emits one newline, and finally moves the cursor to the top-left and clears downward.

<a id="u-687380b52b23"></a>
### `options.ts-config-merging`

`const defu = createDefu((obj, key, value) => { if (Array.isArray(obj[key]) && Array.i…` · [src/config/options.ts:L346-L351][f2]

Merges defaults with overrides using a defu instance whose custom merger replaces arrays instead of concatenating them.

The public overloads all delegate to that merger with overrides first and defaults second, so override values win and array-valued fields are taken wholesale from the override side. The custom merger only acts when both sides are arrays; otherwise defu's normal behavior applies.

<a id="u-aa0afee147b9"></a>
### `package.ts-package-metadata-and-format-helpers`

`export async function readPackageJson( dir: string, ): Promise<PackageJsonWithPath | …` · [src/utils/package.ts:L13-L24][f3]

Finds the nearest package.json from a directory, returning undefined if none is found; otherwise reads and parses it and returns the parsed object plus the discovered path, with read or parse failures propagating.

Extracts package type, throwing on invalid non-module/commonjs values and returning undefined when absent. Normalizes format aliases: es/esm/module to es, cjs/commonjs to cjs, and any other format unchanged.

<a id="u-a49d13ba7277"></a>
### `shebang.ts-shebangplugin-factory`

`export function ShebangPlugin( logger: Logger, cwd: string, nameLabel?: string, isDua…` · [src/features/shebang.ts:L10-L18][f4]

Creates a plugin that grants execute permission to entry chunks containing a shebang.

It returns a plugin whose writeBundle scans output chunks. Only entry chunks whose code starts with a shebang are considered. Existing files are logged and chmodded to 0755; missing files are skipped.

<a id="u-214398a0ba44"></a>
### `filterConfig`

`function filterConfig( filter: InlineConfig['filter'], configCwd: string, name?: stri…` · [src/config/options.ts:L399-L416][f2]

Decides whether a config should be kept by matching an optional filter against the config name and its cwd relative to process.cwd().

No filter keeps everything. A RegExp matches when the name matches or the relative cwd matches; a string/array matches when the name equals a value or the relative cwd equals a value. An empty relative cwd is normalized to `.`.

<a id="u-bab6e24b1339"></a>
### `filterEnv`

`function filterEnv( envDict: Record<string, string | undefined>, envPrefixes: string[…` · [src/config/options.ts:L333-L344][f2]

Filters an environment dictionary to entries whose value is non-null and whose key starts with any supplied prefix.

It returns a new plain object and does not mutate the input. An empty prefix matches every key.

<a id="u-52460b98c903"></a>
### `mergeUserOptions`

`export async function mergeUserOptions<T extends object, A extends unknown[]>( defaul…` · [src/config/options.ts:L368-L381][f2]

Merges user-provided options over defaults, optionally awaiting a function form.

If the user value is a function it is called with the defaults and extra args and awaited; a falsy result returns the defaults unchanged. Otherwise the user object is merged over defaults with the same array-replacing defu behavior.

<a id="u-5c9b32bbb6d0"></a>
### `resolveCIOption`

`function resolveCIOption(value: boolean | CIOption): boolean` · [src/config/options.ts:L393-L397][f2]

Maps CI selector values to booleans: `ci-only` is true only in CI, `local-only` is true only outside CI, and any other value is returned unchanged.

<a id="u-af8d01c05608"></a>
### `resolveFeatureOption`

`export function resolveFeatureOption<T>( value: Exclude<WithEnabled<T>, undefined>, d…` · [src/config/options.ts:L383-L391][f2]

Resolves a feature option that may be a boolean, CI selector, or object with an enabled flag.

For a non-null object it returns the object when its enabled value (default true) resolves true, otherwise false. For a scalar it returns the supplied defaults when the scalar resolves true, otherwise false.

<a id="u-9f27c28524ef"></a>
### `resolveUserConfig`

`export async function resolveUserConfig( userConfig: UserConfig, inlineConfig: Inline…` · [src/config/options.ts:L43-L330][f2]

Resolves one user config plus inline overrides into one resolved config per output format, applying defaults, deprecations, feature gates, and environment loading.

Package.json is read and, when workspace mode is set, the name is taken from it before the filter check; a rejected filter returns an empty array. The logger is created with failOnWarn feature resolution. Deprecated `bundle` warns; `removeNodeProtocol` throws if `nodeProtocol` is also set, otherwise warns and maps to `nodeProtocol: 'strip'` when true. Entry, target, tsconfig, clean, and feature options are resolved through their collaborators. `dts` defaults to false for exe, otherwise true when package types/typings or exports types exist, then is feature-resolved. Missing package.json makes `exports` throw and warns for publint/attw. `injectStyle` warns and fills `css.inject` when absent, but throws if `css.inject` is already set; `publicDir` throws with `copy`, otherwise warns. An empty env prefix warns that filtering is disabled. Env precedence is env file < process.env < explicit env; envFile requires util.parseEnv and reads the resolved file. fromVite loads a Vite config, rejects array aliases, merges alias objects, and prepends Vite plugins. ignoreWatch entries are regex-resolved and string entries are cwd-resolved. Devtools is feature-resolved; in watch mode its UI is disabled and a warning is emitted only when `devtools.ui` was truthy; otherwise UI defaults from package existence. The assembled config is validated for SEA when exe is enabled. Format is either object keys or comma/array-normalized with esm default; each format gets a resolved config, with copy and onSuccess only on the first, and object-format overrides spread last. Collaborator errors propagate.

<a id="u-e9dc039acd5f"></a>
### `ShebangPlugin.writeBundle`

`async writeBundle(options, bundle)` · [src/features/shebang.ts:L18-L36][f4]

Grants execute permission to emitted entry chunks that contain a shebang.

It skips non-chunk and non-entry outputs and code without a leading shebang. The file path comes from the file option or the output directory plus chunk filename. If the file exists, it logs the relative path and chmods it to 0755; otherwise it does nothing.

<a id="u-5d3c9649f814"></a>
### `findTsconfig`

`function findTsconfig( cwd?: string, name: string = 'tsconfig.json', ): string | false` · [src/features/tsconfig.ts:L8-L13][f5]

Finds a tsconfig file by searching upward from cwd, defaulting the file name to tsconfig.json.

It returns the found path or false when none is found. Search semantics are delegated to the upward-find helper.

<a id="u-0f59a9aa4cf1"></a>
### `resolveTsconfig`

`export async function resolveTsconfig( logger: Logger, tsconfig: UserConfig['tsconfig…` · [src/features/tsconfig.ts:L15-L54][f5]

Resolves the tsconfig option to a path or false, warning when an explicitly requested config cannot be found.

false is returned unchanged. true or null searches from cwd; a truthy original that finds nothing warns. A string is resolved against cwd: a file is used directly; a directory triggers an upward search from that directory and warns if none; any other stat result triggers a search by name from cwd and warns if none. A found path is logged relative to cwd.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/rolldown/tsdown/blob/2b1be7e0accdb1d6e903cd42642666431fc5e93d/src/utils/logger.ts
[f2]: https://github.com/rolldown/tsdown/blob/2b1be7e0accdb1d6e903cd42642666431fc5e93d/src/config/options.ts
[f3]: https://github.com/rolldown/tsdown/blob/2b1be7e0accdb1d6e903cd42642666431fc5e93d/src/utils/package.ts
[f4]: https://github.com/rolldown/tsdown/blob/2b1be7e0accdb1d6e903cd42642666431fc5e93d/src/features/shebang.ts
[f5]: https://github.com/rolldown/tsdown/blob/2b1be7e0accdb1d6e903cd42642666431fc5e93d/src/features/tsconfig.ts

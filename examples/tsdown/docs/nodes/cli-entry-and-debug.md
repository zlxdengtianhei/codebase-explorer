# CLI entry and debug

**Capability.** Defines and runs the tsdown CLI, parsing argv, enabling debug namespaces, and providing the config-file identity helper.

Come here for the command-line surface: cac command and option definitions, argv parsing and dispatch, debug flag handling, and the defineConfig type helper.

**Depends on.**

- [Configuration loading and resolution](configuration-loading-and-resolution.md) · graph-confirmed · 1 edge(s) · The CLI entry loads and resolves the user's configuration before running builds.
- [Package metadata and utilities](package-metadata-and-utilities.md) · graph-confirmed · 1 edge(s)
- [Config resolution and normalization](config-resolution-and-normalization.md) · graph-only · 1 edge(s)
- [Dependency handling and general utilities](dependency-handling-and-general-utilities.md) · graph-only · 1 edge(s)

Parent: [tsdown bundling system](tsdown-bundling-system.md)

## Units (5)

<a id="u-22ad08b2a740"></a>
### `config.ts-defineconfig`

`export function defineConfig(options: UserConfig): UserConfig` · [src/config.ts:L9-L9][f1]

Identity function with overloads for a single UserConfig, an array of them, or a config function; it returns the argument unchanged, serving purely as type inference help for user config files.

The module also re-exports mergeConfig and the config types.

<a id="u-1d7e70333814"></a>
### `runCLI`

`export async function runCLI(): Promise<void>` · [src/cli.ts:L129-L140][f2]

Runs the CLI: parses process.argv without executing, enables debug features based on the parsed --debug option, then runs the matched command.

Any thrown error is caught, logged as its stack or message via the global logger, and the process exits with code 1.

<a id="u-38d8559cae82"></a>
### `cli.ts module code (L11–L128)`

`module_region` · [src/cli.ts:L11-L128][f2]

Defines the tsdown CLI with cac: a default '[...files]' bundle command with many options (config file and loader, format, clean, externals, minify, devtools, debug, target, log level, fail-on-warn, no-write, out-dir, treeshake, sourcemap, shims, platform, dts, publint, attw, unused, watch, ignore-watch, from-vite, report, env/env-file/env-prefix, on-success, copy, tsconfig, unbundle, exe, workspace, filter, exports) plus help and version.

The default action sets the global log level, prints a version banner, dynamically imports build, maps positional file arguments to flags.entry, and awaits build(flags). Two deprecated subcommands, 'create' and 'migrate', warn and shell out via tinyexec to npx create-tsdown@latest / tsdown-migrate@latest forwarding process.argv.slice(3) with inherited stdio, then assign the child exit code to process.exitCode.

<a id="u-a79fdc63cd15"></a>
### `enableDebug`

`export function enableDebug(debug?: boolean | Arrayable<string>): void` · [src/features/debug.ts:L7-L25][f3]

Enables obug debug namespaces derived from the debug flag.

Falsy input returns immediately. `true` enables 'tsdown:*'; otherwise the value is comma-split, array-normalized, each entry prefixed with 'tsdown:', and joined with commas. Existing enabled namespaces (from namespaces()) are appended so they stay active, then enable() is called.

calls: [resolveComma](../../catalog.json.gz)

<a id="u-ae3c2ff582c3"></a>
### `run.ts module code (L1–L17)`

`module_region` · [src/run.ts:L1-L17][f4]

Executable entry point for the CLI.

It warns (yellow, via console.warn) when the running Node version is below 22.18.0 that support will be removed, best-effort enables the module compile cache inside a try/catch that swallows failures (including a missing enableCompileCache on older runtimes), and invokes runCLI.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/rolldown/tsdown/blob/2b1be7e0accdb1d6e903cd42642666431fc5e93d/src/config.ts
[f2]: https://github.com/rolldown/tsdown/blob/2b1be7e0accdb1d6e903cd42642666431fc5e93d/src/cli.ts
[f3]: https://github.com/rolldown/tsdown/blob/2b1be7e0accdb1d6e903cd42642666431fc5e93d/src/features/debug.ts
[f4]: https://github.com/rolldown/tsdown/blob/2b1be7e0accdb1d6e903cd42642666431fc5e93d/src/run.ts

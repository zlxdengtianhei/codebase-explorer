# CLI entry and debug

**Capability.** Registers and runs the CLI, enables debug namespaces, and provides the executable entry with Node-version warning.

Come here for CLI command registration, argv parsing, debug enabling, and the executable runner. Units also include a configuration identity helper.

**Depends on.**

- [Package output and validation](package-output-and-validation.md) · graph-confirmed · 2 edge(s)
- [Dependency externalization utilities](dependency-externalization-utilities.md) · graph-only · 1 edge(s)
- [Package export map generation](package-export-map-generation.md) · graph-only · 1 edge(s)

Parent: [tsdown build tool](tsdown-build-tool.md)

## Units (5)

<a id="u-520d8d6225f7"></a>
### `config.ts-defineconfig-identity`

`export function defineConfig(options: UserConfig): UserConfig` · [src/config.ts:L9-L9][f1]

Identity helper for configuration exports.

All overloads return the same value/reference unchanged; no validation, normalization, or cloning occurs.

<a id="u-1d7e70333814"></a>
### `runCLI`

`export async function runCLI(): Promise<void>` · [src/cli.ts:L129-L140][f2]

Parses argv without running, enables debug from parsed options, then runs the matched command inside a try.

Only runMatchedCommand is guarded: parse and debug-enable errors are not caught. A caught error logs stack or message and exits with code 1.

<a id="u-38d8559cae82"></a>
### `cli.ts module code (L11–L128)`

`module_region` · [src/cli.ts:L11-L128][f2]

Registers the CLI surface and command actions.

The main file command accepts unknown options and ignores option defaults, exposes many build flags, and on action sets logger level, logs a version banner, dynamically imports the build module, uses positional files as entry when present, and awaits build. The deprecated create and migrate commands warn, spawn npx with the latest package and inherited stdio, and copy the child exit code to process.exitCode. Help/version are enabled.

<a id="u-a79fdc63cd15"></a>
### `enableDebug`

`export function enableDebug(debug?: boolean | Arrayable<string>): void` · [src/features/debug.ts:L7-L25][f3]

Enables debug namespaces from a boolean or string list, preserving existing namespaces.

Falsy input returns immediately. `true` selects `tsdown:*`; otherwise comma-separated values are normalized, prefixed with `tsdown:`, and joined. Existing namespaces, when present, are appended. It calls the global enable function and logs the final namespace.

<a id="u-ae3c2ff582c3"></a>
### `run.ts module code (L1–L17)`

`module_region` · [src/run.ts:L1-L17][f4]

Executable entry: warns when Node version is below 22.18.0, attempts optional module compile-cache enablement while swallowing any error, then invokes the CLI runner without awaiting it.

The version warning is only a console warning; compile-cache failure is ignored.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/rolldown/tsdown/blob/2b1be7e0accdb1d6e903cd42642666431fc5e93d/src/config.ts
[f2]: https://github.com/rolldown/tsdown/blob/2b1be7e0accdb1d6e903cd42642666431fc5e93d/src/cli.ts
[f3]: https://github.com/rolldown/tsdown/blob/2b1be7e0accdb1d6e903cd42642666431fc5e93d/src/features/debug.ts
[f4]: https://github.com/rolldown/tsdown/blob/2b1be7e0accdb1d6e903cd42642666431fc5e93d/src/run.ts

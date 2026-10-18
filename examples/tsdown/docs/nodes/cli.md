# Command-Line Interface

**Capability.** Parses command-line arguments with cac and serves as the executable entry that enables debug namespaces and invokes the build.

Use this subtree to see how the tsdown command is defined and dispatched. Debug flag handling lives here because it is driven by CLI options before any build starts.

**Depends on.**

- [Build Orchestration](build-orchestration.md) · model-inferred · 0 edge(s) · The CLI dispatches the parsed command into the build entry point.
- [Logging](logging.md) · model-inferred · 0 edge(s)
- [General and Filesystem Helpers](general-and-fs.md) · graph-only · 2 edge(s)

Parent: [tsdown Build Tool](tsdown.md)

## Units (3)

<a id="u-7b169eb0ae3e"></a>
### `cli-ts-runcli`

`export async function runCLI(): Promise<void>` · [src/cli.ts:L129-L140][f1]

Defines the tsdown command-line interface with cac and the entry that runs it.

The 'tsdown' CLI registers help/version and a default '[...files]' bundling command exposing all CLI options (config, format, watch, minify, env, dts, workspace filters, etc.); its action sets the log level, prints a version banner, dynamically imports ./build.ts, maps positional file arguments to flags.entry, and awaits build(flags). Two deprecated commands, 'create' and 'migrate', warn and shell out via tinyexec to 'npx create-tsdown' or 'npx tsdown-migrate' (forwarding extra argv), propagating the child exit code into process.exitCode. runCLI parses argv without running, enables debug logging from --debug, then runs the matched command; a thrown error is logged (stack or message) and the process exits with code 1.

**Notes.**

- failure: Command-action errors are caught in runCLI and terminate the process with exit code 1 after logging; errors inside the default action's build() therefore abort the process, not just the command.

calls: [enableDebug](cli.md#u-a79fdc63cd15), [build](build-orchestration.md#u-20b3d0e57fe7)

**Uncertainties.**

- Whether cac itself prints option errors or throws into runCLI's catch is determined by the cac library, not this source.
- The exact UserConfig mapping of CLI flags happens in config resolution, external to this file.

<a id="u-a79fdc63cd15"></a>
### `enableDebug`

`export function enableDebug(debug?: boolean | Arrayable<string>): void` · [src/features/debug.ts:L7-L25][f2]

Turns on obug debug namespaces for tsdown.

A falsy argument returns immediately. `true` enables 'tsdown:*'; otherwise the value is converted to an array, comma-split, and each flag prefixed with 'tsdown:' and joined by commas. Any pre-existing obug namespaces are preserved by appending them. Finally calls enable(namespace).

calls: [resolveComma](general-and-fs.md#u-adfdd23335a0), [toArray](general-and-fs.md#u-1e9a5d8a9f7d)

<a id="u-930575d79f89"></a>
### `debug.ts module code (L1–L6)`

`module_region` · [src/features/debug.ts:L1-L6][f2]

Module imports and the tsdown:debug logger instance.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/rolldown/tsdown/blob/2b1be7e0accdb1d6e903cd42642666431fc5e93d/src/cli.ts
[f2]: https://github.com/rolldown/tsdown/blob/2b1be7e0accdb1d6e903cd42642666431fc5e93d/src/features/debug.ts
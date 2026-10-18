# Logging

**Capability.** Leveled, color-prefixed loggers with stable per-name colors, format labels, and terminal screen clearing.

Use this subtree to understand how tsdown output is rendered and colored. Logger creation, color generation (HSL to RGB), and format labels are colocated because they share the colorizer machinery.

**Depended on by.**

- [Build Orchestration](build-orchestration.md) · model-inferred · 0 edge(s)
- [Command-Line Interface](cli.md) · model-inferred · 0 edge(s)
- [User Config Normalization](config-merging.md) · graph-confirmed · 3 edge(s)
- [Package Publishing](package-publishing.md) · graph-confirmed · 2 edge(s)
- [Bundled Rolldown Plugins](plugin-pipeline.md) · graph-confirmed · 1 edge(s)
- [Build Size Reporting](reporting.md) · graph-confirmed · 1 edge(s)
- [Single-Executable Output](exe-output.md) · graph-only · 2 edge(s)

Parent: [Shared Utilities](shared-utils.md)

## Units (7)

<a id="u-44145ce36528"></a>
### `createLogger`

`export function createLogger( level: LogLevel = 'info', options: LoggerOptions = {}, …` · [src/utils/logger.ts:L49-L67][f1]

Builds a leveled, color-prefixed logger routed through a configurable console.

Options default to allowClearScreen=true, failOnWarn=false, and globalThis.console, then merge with the caller's options; a provided customLogger is returned as-is with no wrapper created. output() drops messages whose type level exceeds the logger's current threshold (info logs via console.log, warn/error via same-named methods), and level checks read the live logger object so later level changes take effect. Screen clearing is enabled only when allowClearScreen is on, stdout is a TTY, and CI is unset. warn and warnOnce delegate to error when failOnWarn is true, and warnOnce suppresses repeats by tracking formatted messages in a module-level Set shared by all loggers from this module.

**Notes.**

- side_effect: error sets process.exitCode = 1; warnedMessages is module-global across logger instances.
- condition: clearScreen method clears only when the current level threshold is at least the requested LogType's level.

contract: [Logger][f1]

<a id="u-2d5b7213befb"></a>
### `format`

`function format(msgs: any[])` · [src/utils/logger.ts:L35-L37][f1]

Joins variadic log arguments into a single space-separated string, filtering out undefined and false values before joining.

<a id="u-89c4828a655a"></a>
### `generateColor`

`export function generateColor(name: string = 'default'): Ansis` · [src/utils/logger.ts:L153-L172][f1]

Returns a stable ansis color per name, cached in a module-level Map.

'default' maps to blue; other names hash character codes into a hue rendered as HSL(35% saturation, 55% lightness) converted to RGB. Repeat calls return the cached color.

<a id="u-8d993ffa19ed"></a>
### `hslToRgb`

`function hslToRgb( h: number, s: number, l: number, ): [r: number, g: number, b: number]` · [src/utils/logger.ts:L174-L200][f1]

Converts HSL (degrees and percent scales) to rounded 0-255 RGB.

When saturation is 0 all channels equal lightness; otherwise the standard q/p hue2rgb interpolation is applied per channel. Results use Math.max(0, ...) but no upper clamp, relying on hue2rgb's bounded output.

**Uncertainties.**

- hslToRgb and hue2rgb are explained here rather than as separate units; they are internal helpers with no other callers in this file.

<a id="u-99ef914b4578"></a>
### `getNameLabel`

`export function getNameLabel(ansis: Ansis, name?: string): string | undefined` · [src/utils/logger.ts:L130-L133][f1]

Wraps a name as '[name]' using the supplied ansis colorizer; returns undefined when the name is falsy.

<a id="u-9a73f5293780"></a>
### `prettyFormat`

`export function prettyFormat(format: InternalModuleFormat): string` · [src/utils/logger.ts:L135-L149][f1]

Formats an internal module format as a bracketed colored label: 'es' becomes blue 'ESM', 'cjs' becomes yellow uppercase, and any other format becomes its uppercase name uncolored via the noop identity.

<a id="u-12a437657e54"></a>
### `clearScreen`

`function clearScreen()` · [src/utils/logger.ts:L39-L45][f1]

Clears the terminal by writing rows-2 newlines (empty when rows is not positive), then moving the cursor to 0,0 and clearing downward via readline on stdout.

Assumes a TTY-sized stdout; process.stdout.rows being undefined would make repeatCount NaN and thus an empty blank string.

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

[f1]: https://github.com/rolldown/tsdown/blob/2b1be7e0accdb1d6e903cd42642666431fc5e93d/src/utils/logger.ts
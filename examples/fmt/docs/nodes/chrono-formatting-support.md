# Chrono Formatting Support

**Capability.** Formats and parses chrono durations, time points, calendar fallback types, and chrono format handlers.

Use this group for chrono duration, time-point, and calendar formatting. Duration and time formatting is largest; fallback calendar types and format handlers support validation and rendering.

**Children.**

- [Chrono Duration and Time Formatting](chrono-duration-and-time-formatting.md) `chrono-duration-and-time-formatting` · 27 unit(s)
- [Chrono Calendar Fallback Types](chrono-calendar-fallback-types.md) `chrono-calendar-fallback-types` · 10 unit(s)
- [Chrono Format Handlers](chrono-format-handlers.md) `chrono-format-handlers` · 10 unit(s)

**Depends on.**

- [Core Formatting Internals](core-formatting-internals.md) · graph-confirmed · 10 edge(s)

Parent: [fmt Formatting Library](fmt-formatting-library.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

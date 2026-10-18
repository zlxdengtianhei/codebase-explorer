# Chrono Formatting

**Capability.** Formats std::chrono durations, time points, calendar types and std::tm via strftime-like specs, with overflow-checked duration arithmetic and locale-aware tm writing.

Enter at the formatter nodes; parsing validates specs through checker handlers, and the duration/tm writers do the output. Calendar and time-point formatters build on formatter<std::tm>.

**Children.**

- [Chrono Spec Parsing](chrono-parse.md) `chrono-parse` · 5 unit(s)
- [Duration Formatting](chrono-duration.md) `chrono-duration` · 12 unit(s)
- [std::tm Formatting](chrono-tm.md) `chrono-tm` · 12 unit(s)
- [Calendar & Time-Point Formatters](chrono-calendar.md) `chrono-calendar` · 3 unit(s)

Parent: [fmt Formatting Library](fmt-lib.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

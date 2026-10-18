# Transfer progress

**Capability.** Tracks transfer timing, byte counters, and speeds; enforces low-speed abort and max-filesize policies; and delivers the progress callback or the built-in textual meter at the cadence progress_calc decides.

Use the timing child for timer labels, tick entry points, and speed/abort policy; use the meter child for rendering the human-readable output. Both rest on curlx timestamps and timediff arithmetic.

**Children.**

- [Progress timing, counters and policy](r9-progress-timing-and-policy.md) `r9-progress-timing-and-policy` · 15 unit(s)
- [Progress meter rendering and delivery](r9-progress-meter.md) `r9-progress-meter` · 9 unit(s)

**Depends on.**

- [printf engine \(mprintf\)](r9-mprintf.md) · graph-confirmed · 2 edge(s)
- [Time utilities](r9-time-utils.md) · graph-confirmed · 11 edge(s)

**Depended on by.**

- [Connection pool \(cpool\)](r9-conn-pool.md) · graph-confirmed · 1 edge(s)
- [Telnet transfer loop and data path](r9-telnet-transfer-fsm.md) · graph-confirmed · 3 edge(s)

Parent: [curl codebase](r9-curl-source.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

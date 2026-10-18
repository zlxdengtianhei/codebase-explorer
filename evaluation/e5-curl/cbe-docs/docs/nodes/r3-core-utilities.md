# Shared Core Utilities

**Capability.** Cross-cutting primitives used throughout libcurl and the tool: growable dynbuf strings, integer-keyed pointer/bit containers, ASCII string helpers and error-message mapping, and internal support headers (date parsing, header store, wakeup socketpair, threaded queue, internal URL API, Windows build config).

Use this branch for infrastructure consumed by many modules. These utilities own no protocol logic; consumers should depend on them rather than reimplement allocation, container, or formatting behavior.

**Children.**

- [Dynamic Buffer \(dynbuf\)](r3-dynbuf.md) `r3-dynbuf` · 10 unit(s)
- [Integer-Keyed Containers](r3-int-containers.md) `r3-int-containers` · 27 unit(s)
- [String Helpers & Error Messages](r3-string-error-utils.md) `r3-string-error-utils` · 10 unit(s)
- [Internal Support Headers](r3-internal-headers.md) `r3-internal-headers` · 10 unit(s)

Parent: [curl Codebase](r3-curl-codebase.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

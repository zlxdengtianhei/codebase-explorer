# Command-line tool

**Capability.** The curl executable: translating configuration into easy handles, driving transfers serially or in parallel, retry and post-transfer decisions, and platform-specific CA/path support.

Entry point is operate(); transfers are prepared per config, then run by the serial, threaded-parallel, or libuv event drivers, with post-transfer handling and retry logic per transfer.

**Children.**

- [Transfer preparation](r7-tool-transfer-prep.md) `r7-tool-transfer-prep` · 22 unit(s)
- [Transfer execution and retry](r7-tool-execution.md) `r7-tool-execution` · 19 unit(s)
- [libuv event-loop driver](r7-tool-libuv-driver.md) `r7-tool-libuv-driver` · 10 unit(s)
- [Tool platform support](r7-tool-platform-support.md) `r7-tool-platform-support` · 6 unit(s)
- [Tool environment and libcurl info](r7-tool-support.md) `r7-tool-support` · 4 unit(s)

Parent: [curl codebase](r7-curl-codebase.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

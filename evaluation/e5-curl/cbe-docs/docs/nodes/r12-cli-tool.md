# Command-line tool

**Capability.** The curl executable: process startup, multi-transfer progress metering, --write-out variable and JSON output, and generated help text.

Use this subtree for user-facing tool behavior; all library interaction happens through the easy/multi APIs from here.

**Children.**

- [Tool startup](r12-tool-startup.md) `r12-tool-startup` · 3 unit(s)
- [Progress meter](r12-progress-meter.md) `r12-progress-meter` · 7 unit(s)
- [Write-out output](r12-writeout-output.md) `r12-writeout-output` · 10 unit(s)
- [Help text](r12-help-text.md) `r12-help-text` · 2 unit(s)

Parent: [curl codebase](r12-curl-codebase.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

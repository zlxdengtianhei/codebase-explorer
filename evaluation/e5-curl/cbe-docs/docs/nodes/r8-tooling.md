# Command-Line Tool Output

**Capability.** Owns the curl tool's user-visible handling of responses: the header callback driving filename selection (Content-Disposition/Location) and ETag saving, --write-out variable expansion, and small platform utilities for time, truncation, sorting and resource lookup.

Use this subtree when the question is about what the user sees or where files land, not about transfer internals. The header callback and write-out engine are the two main entry points.

**Children.**

- [Tool Header Callback](r8-tool-header-callback.md) `r8-tool-header-callback` · 9 unit(s)
- [--write-out Expansion](r8-tool-writeout.md) `r8-tool-writeout` · 15 unit(s)
- [Tool Platform Utilities](r8-tool-platform-util.md) `r8-tool-platform-util` · 7 unit(s)

Parent: [curl Codebase](r8-curl-codebase.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

# curl Command-Line Tool

**Capability.** The user-facing executable: option/parameter helpers and terminal messaging, transfer callbacks (progress, headers, debug, help scanning), and output-side helpers (directory creation, SSL session import/export).

Enter by concern: messaging covers user-visible output; callbacks cover libcurl-to-tool glue; output covers filesystem and session-file side effects. These subtrees consume the library API, not vice versa.

**Children.**

- [Tool Messaging and Parameter Helpers](r5-tool-messaging.md) `r5-tool-messaging` · 9 unit(s)
- [Tool Transfer Callbacks](r5-tool-callbacks.md) `r5-tool-callbacks` · 8 unit(s)
- [Tool Output Directories and SSL Sessions](r5-tool-output.md) `r5-tool-output` · 13 unit(s)

Parent: [curl Library and Tool](r5-curl-codebase.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

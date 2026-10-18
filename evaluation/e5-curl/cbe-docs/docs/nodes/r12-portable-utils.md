# Portable utilities

**Capability.** Cross-platform helper library (lib/curlx): safe string/time formatting, error messages, socket modes and dynamic buffers, warning-suppressing integer conversions, and Windows-specific file and header adaptations.

Borrow these utilities instead of reimplementing platform quirks. Windows-only file IO and headers are isolated so non-Windows builds are unaffected.

**Children.**

- [String and time utilities](r12-string-time-utils.md) `r12-string-time-utils` · 6 unit(s)
- [Windows file IO wrappers](r12-win32-file-io.md) `r12-win32-file-io` · 11 unit(s)
- [Windows portability headers](r12-windows-portability-headers.md) `r12-windows-portability-headers` · 2 unit(s)
- [Socket, buffer, and integer utilities](r12-socket-and-buffer-utils.md) `r12-socket-and-buffer-utils` · 3 unit(s)

Parent: [curl codebase](r12-curl-codebase.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

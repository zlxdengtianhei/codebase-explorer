# OS & File I/O

**Capability.** Owning wrappers for file descriptors, buffered FILE streams, pipes, and output streams, plus platform error reporting with UTF-8 system messages.

Use os.h types in code; their methods are implemented in src/os.cc. Error reporting paths are Windows-specialized behind the utf-8 error category.

**Children.**

- [OS Header Interface](os-interface.md) `os-interface` · 7 unit(s)
- [File I/O Implementation](os-impl-file.md) `os-impl-file` · 23 unit(s)
- [OS Error Reporting](os-impl-error.md) `os-impl-error` · 6 unit(s)

Parent: [fmt Formatting Library](fmt-lib.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

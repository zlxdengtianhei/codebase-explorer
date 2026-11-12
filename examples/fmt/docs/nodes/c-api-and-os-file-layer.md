# C API and OS File Layer

**Capability.** Implements C formatting APIs, OS file operations, ownership wrappers, and low-level OS type wrappers.

Consult this group for C-facing formatting and file/OS abstractions. C API and file operations are the largest child; ownership and type wrappers provide supporting handle and stream types.

**Children.**

- [C API and OS File Operations](c-api-and-os-file-operations.md) `c-api-and-os-file-operations` · 22 unit(s)
- [File Ownership Wrappers](file-ownership-wrappers.md) `file-ownership-wrappers` · 10 unit(s)
- [OS Type Wrappers](os-type-wrappers.md) `os-type-wrappers` · 8 unit(s)

Parent: [OS and Stream Integration](os-and-stream-integration.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

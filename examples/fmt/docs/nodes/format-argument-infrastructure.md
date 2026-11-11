# Format argument infrastructure

**Capability.** Defines formatting arguments, their storage and compile-time checking, spec parsing, buffer adapters, and compile-time format string compilation.

Come here for how format strings and arguments are represented and validated. G7 covers core parsing and buffers, G8 compile-time compilation, and the argument storage child type-erased argument handling.

**Children.**

- [Parsing and buffer foundations](parsing-and-buffer-foundations.md) `parsing-and-buffer-foundations` · 68 unit(s)
- [fmt: Compile Format](fmt-compile-format.md) `fmt-compile-format` · 31 unit(s)
- [Argument storage and checking](argument-storage-and-checking.md) `argument-storage-and-checking` · 15 unit(s)

**Depends on.**

- [Core formatting implementation](core-formatting-implementation.md) · graph-confirmed · 10 edge(s)
- [Printf implementation](printf-implementation.md) · graph-confirmed · 19 edge(s) · The argument infrastructure supplies the argument model and error reporting that the printf engine consumes.

**Depended on by.**

- [Core formatting implementation](core-formatting-implementation.md) · graph-confirmed · 7 edge(s) · The core formatting layer uses the argument infrastructure's parsing and buffer abstractions to drive value output.
- [OS file and C API](os-file-and-c-api.md) · graph-confirmed · 1 edge(s) · The OS/C API layer uses the argument infrastructure to pack arguments for its formatting entry points.
- [Wide text and styling](wide-text-and-styling.md) · graph-confirmed · 1 edge(s)

Parent: [fmt formatting library](fmt-formatting-library.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

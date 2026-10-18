# std Type Formatters

**Capability.** Formatter specializations for a broad set of C++ standard library types: vocabulary types, error/exception types, filesystem paths, complex, bitset, smart pointers, and type names.

Include std.h to format these standard types with normal format specs; subtrees group them by the machinery they share.

**Children.**

- [Vocabulary Alternative Formatters](std-vocab-alt.md) `std-vocab-alt` · 6 unit(s)
- [Type Name Formatting](std-type-name.md) `std-type-name` · 4 unit(s)
- [Error & Exception Formatters](std-error-exception.md) `std-error-exception` · 4 unit(s)
- [Value & Utility Formatters](std-values.md) `std-values` · 8 unit(s)

Parent: [fmt Formatting Library](fmt-lib.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

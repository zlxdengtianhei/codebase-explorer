# C API

**Capability.** A stable C ABI for formatting: tagged-union fmt_arg values, negative error codes, macro-based variadic wrappers, and an implementation converting C args to fmt's type-erased arguments.

C consumers include fmt-c.h and call the macros; the implementation translates the C arg arrays and forwards to the C++ engine.

**Children.**

- [C ABI Surface](fmt-c-interface.md) `fmt-c-interface` · 3 unit(s)
- [C ABI Implementation](fmt-c-impl.md) `fmt-c-impl` · 3 unit(s)

Parent: [fmt Formatting Library](fmt-lib.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

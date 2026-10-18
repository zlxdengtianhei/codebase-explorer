# fmt Formatting Library

**Capability.** Umbrella for a C++ formatting library: a compiled core engine plus header-based extensions (compiled-time formats, chrono, color, ranges, std types, printf compatibility, wide/exotic chars, OS I/O, C ABI).

Start here to navigate. The compiled runtime lives under core-runtime; each feature header is its own subtree; shared infrastructure is kept separate from its consumers.

**Children.**

- [Core Runtime & Engine](core-runtime.md) `core-runtime` · 2 unit(s)
- [Dynamic Argument Stores](args-h.md) `args-h` · 12 unit(s)
- [Compile-Time Format Strings](compile-h.md) `compile-h` · 0 unit(s)
- [Chrono Formatting](chrono-h.md) `chrono-h` · 0 unit(s)
- [Terminal Color & Styling](color-h.md) `color-h` · 0 unit(s)
- [Enum Formatting](enum-h.md) `enum-h` · 0 unit(s)
- [C API](fmt-c.md) `fmt-c` · 0 unit(s)
- [OS & File I/O](os.md) `os` · 0 unit(s)
- [std::ostream Support](ostream-h.md) `ostream-h` · 6 unit(s)
- [printf Compatibility](printf-h.md) `printf-h` · 0 unit(s)
- [Range Formatting](ranges-h.md) `ranges-h` · 0 unit(s)
- [std Type Formatters](std-h.md) `std-h` · 0 unit(s)
- [Wide & Exotic Char Support](xchar-h.md) `xchar-h` · 0 unit(s)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

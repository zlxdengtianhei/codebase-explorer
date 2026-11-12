# Low-Level Formatting Primitives

**Capability.** Provides shared low-level formatting utilities, spec parsing, numeric and string writers, floating-point cores, and UTF conversion used by higher formatting layers.

Consult this group for the primitive operations beneath format-string handling. Utilities and spec parsing feed integer, floating-point, buffer, UTF, and locale/string writers; cross-child edges show writers depending on buffer/core utilities.

**Children.**

- [Format Core Utilities](format-core-utilities.md) `format-core-utilities` · 26 unit(s)
- [Format Spec Parsing and Writing](format-spec-parsing-and-writing.md) `format-spec-parsing-and-writing` · 24 unit(s)
- [Integer and Pointer Formatting](integer-and-pointer-formatting.md) `integer-and-pointer-formatting` · 13 unit(s)
- [Buffer and Core Integer Writer](buffer-and-core-integer-writer.md) `buffer-and-core-integer-writer` · 9 unit(s)
- [Floating-Point Formatting Core](floating-point-formatting-core.md) `floating-point-formatting-core` · 7 unit(s)
- [UTF Encoding and Decoding](utf-encoding-and-decoding.md) `utf-encoding-and-decoding` · 5 unit(s)
- [String and Locale Formatting](string-and-locale-formatting.md) `string-and-locale-formatting` · 3 unit(s)

**Depends on.**

- [Platform and Dragonbox Support](platform-and-dragonbox-support.md) · graph-confirmed · 13 edge(s)

**Depended on by.**

- [Big Integer Float Formatting](big-integer-float-formatting.md) · graph-confirmed · 3 edge(s)
- [Platform and Dragonbox Support](platform-and-dragonbox-support.md) · graph-confirmed · 1 edge(s)

Parent: [Core Formatting Internals](core-formatting-internals.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

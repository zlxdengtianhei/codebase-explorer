# Core Formatting Internals

**Capability.** Houses low-level formatting primitives, platform and Dragonbox support, and arbitrary-precision integer floating-point formatting.

Use this group for the internal machinery beneath higher-level formatting. G3 provides primitives, G4 supplies platform and Dragonbox support, and big-integer float formatting handles Steele-White fixed precision.

**Children.**

- [Low-Level Formatting Primitives](low-level-formatting-primitives.md) `low-level-formatting-primitives` · 87 unit(s)
- [Platform and Dragonbox Support](platform-and-dragonbox-support.md) `platform-and-dragonbox-support` · 33 unit(s)
- [Big Integer Float Formatting](big-integer-float-formatting.md) `big-integer-float-formatting` · 5 unit(s)

**Depends on.**

- [Compiled Formatting Engine](compiled-formatting-engine.md) · graph-confirmed · 12 edge(s)

**Depended on by.**

- [Character and Style Formatting](character-and-style-formatting.md) · graph-confirmed · 3 edge(s)
- [Chrono Formatting Support](chrono-formatting-support.md) · graph-confirmed · 10 edge(s)
- [Compiled Formatting Engine](compiled-formatting-engine.md) · graph-confirmed · 11 edge(s) · compiled-formatting-engine depends on core-formatting-internals for shared formatting primitives and internals.
- [Dynamic Arguments, Enums, and C API](dynamic-arguments-enums-and-c-api.md) · graph-confirmed · 1 edge(s)

Parent: [fmt Formatting Library](fmt-formatting-library.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

# Shared Utilities

**Capability.** Cross-cutting helpers with no build-specific knowledge: filesystem primitives, general-purpose functions, logging, and package.json access, consumed by all feature areas.

Use this subtree when tracing low-level behavior such as path normalization, fs tolerances, or logger formatting. Keeping these separate prevents build logic from entangling generic helpers.

**Children.**

- [General and Filesystem Helpers](general-and-fs.md) `general-and-fs` · 20 unit(s)
- [Logging](logging.md) `logging` · 7 unit(s)
- [Package Metadata Helpers](package-metadata.md) `package-metadata` · 3 unit(s)

Parent: [tsdown Build Tool](tsdown.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

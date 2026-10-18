# cJSON Library

**Capability.** Two-part C library for JSON: the core cJSON engine that parses, prints, stores, and manipulates JSON trees, and a utilities layer implementing RFC 6901/6902/7396 on top of that engine.

Start here to navigate the codebase. Everything under core-json is the self-contained cJSON engine whose public surface is declared in cJSON.h; everything under json-utils is an optional layer consuming only the core's public API.

**Children.**

- [Core cJSON Engine](core-json.md) `core-json` · 0 unit(s)
- [cJSON Utilities \(RFC Layer\)](json-utils.md) `json-utils` · 3 unit(s)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

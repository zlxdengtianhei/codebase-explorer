# Streaming JsonReader

**Capability.** Implements JsonReader: documented token-consumption API, value decoding, low-level lexing with buffer lookahead, and structural navigation with nesting limits.

Readers debugging parse behavior or extending the reader should start at the public API child. The remaining children layer lexing, decoding, and container navigation beneath it.

**Children.**

- [JsonReader public API and docs](jsonreader-public-api-and-docs.md) `jsonreader-public-api-and-docs` · 29 unit(s)
- [Token consumption and value decoding](token-consumption-and-value-decoding.md) `token-consumption-and-value-decoding` · 14 unit(s)
- [Lexing and buffer lookahead](lexing-and-buffer-lookahead.md) `lexing-and-buffer-lookahead` · 9 unit(s)
- [Structural navigation and skipping](structural-navigation-and-skipping.md) `structural-navigation-and-skipping` · 4 unit(s)

**Depends on.**

- [In-memory tree reader](in-memory-tree-reader.md) · graph-confirmed · 1 edge(s)

**Depended on by.**

- [In-memory tree reader](in-memory-tree-reader.md) · graph-confirmed · 1 edge(s)

Parent: [JSON Reading Infrastructure](json-reading-infrastructure.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

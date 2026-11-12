# Streaming JSON reader internals

**Capability.** Implements low-level streaming JSON reading, token scanning, scalar consumption, and structure navigation.

Relevant for parser internals and diagnostics. Core manages reader state and paths; scanning finds tokens and literals; value consumption parses scalars and strings; structure navigation handles arrays, objects, and skipping.

**Children.**

- [Streaming JSON reader core](streaming-json-reader-core.md) `streaming-json-reader-core` · 14 unit(s)
- [JSON token scanning](json-token-scanning.md) `json-token-scanning` · 12 unit(s)
- [JSON value consumption](json-value-consumption.md) `json-value-consumption` · 12 unit(s)
- [JSON structure navigation](json-structure-navigation.md) `json-structure-navigation` · 6 unit(s)

**Depends on.**

- [JsonElement tree reader](jsonelement-tree-reader.md) · graph-confirmed · 1 edge(s)

**Depended on by.**

- [JsonElement tree reader](jsonelement-tree-reader.md) · graph-confirmed · 1 edge(s)

Parent: [Streaming and tree reading](streaming-and-tree-reading.md)

Look up code: the commands are under "Read further" in [INDEX.md](../INDEX.md); `cbe query` and `cbe source` take a unit title or anchor from this page.

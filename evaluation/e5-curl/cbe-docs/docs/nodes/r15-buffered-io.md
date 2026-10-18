# Buffered I/O (bufq)

**Capability.** curl's chunked byte-queue engine: chunk-level storage primitives, chunk pooling and recycling, lifecycle wrappers, and the public queue-level read/write/peek/skip/pass API that other modules buffer through.

Understand memory mechanics in bufq-chunk-engine first, then the API surface in bufq-stream-api. Consumers such as WebSocket fill and drain queues exclusively through these functions.

**Children.**

- [Chunk engine and pool](r15-bufq-chunk-engine.md) `r15-bufq-chunk-engine` · 5 unit(s)
- [Bufq public API](r15-bufq-stream-api.md) `r15-bufq-stream-api` · 14 unit(s)

Parent: [curl codebase](r15-curl-codebase.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

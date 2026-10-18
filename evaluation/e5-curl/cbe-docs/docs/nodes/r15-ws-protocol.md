# WebSocket support

**Capability.** RFC6455 WebSocket framing (incremental decoder and masked encoder) plus the public transfer API (recv/send/meta/start_frame), the client-writer/reader filters, upgrade handling, and control-frame auto-reply.

Use ws-frame-codec for byte-level framing independent of the transfer API, and ws-transfer for the public API and filter integration. Both directions buffer through bufq.

**Children.**

- [WS frame codec](r15-ws-frame-codec.md) `r15-ws-frame-codec` · 17 unit(s)
- [WS transfer API and filters](r15-ws-transfer.md) `r15-ws-transfer` · 22 unit(s)

Parent: [curl codebase](r15-curl-codebase.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

# Request and Transfer Engine

**Capability.** Owns driving a single request/transfer: per-request state and poll predicates, buffering and flushing the request send path, the per-socket-event send/recv loop, and the transfer-direction API that forwards data to/from the connection.

Use this subtree to follow how a transfer progresses: request state transitions and send buffering in request.c, the download/upload loop and per-transfer preparation in transfer.c, and the xfer_* API connecting both to the connection.

**Children.**

- [Request State and Predicates](r10-request-state.md) `r10-request-state` · 13 unit(s)
- [Request Send Path](r10-request-send-path.md) `r10-request-send-path` · 8 unit(s)
- [Transfer Loop and Lifecycle](r10-transfer-loop.md) `r10-transfer-loop` · 12 unit(s)
- [Transfer Direction API](r10-xfer-direction-api.md) `r10-xfer-direction-api` · 22 unit(s)

Parent: [curl Codebase](r10-curl-source.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

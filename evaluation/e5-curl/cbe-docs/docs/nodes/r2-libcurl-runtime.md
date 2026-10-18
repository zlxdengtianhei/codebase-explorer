# libcurl Transfer Runtime

**Capability.** The runtime that moves option state, protocol data and response bytes through connection filters, TLS and multiplexing layers to a client application.

Start here to orient across the tree. Major branches cover protocol connection filters, the mbedTLS backend, MIME multipart bodies, client-write buffering, easy-handle option setting, tracing, and tool-side diagnostics. Cross-branch edges record needs such as setopt installing MIME bodies or filters using buffer queues.

**Children.**

- [Buffer Queue Model](r2-bufq-buffer-queues.md) `r2-bufq-buffer-queues` · 1 unit(s)
- [Connection Filter Protocol Stacks](r2-protocol-filters.md) `r2-protocol-filters` · 1 unit(s)
- [mbedTLS vTLS Backend](r2-tls-mbedtls.md) `r2-tls-mbedtls` · 0 unit(s)
- [MIME Multipart Engine](r2-mime-engine.md) `r2-mime-engine` · 0 unit(s)
- [Client Write Buffering \(cw-out\)](r2-cw-out-writer.md) `r2-cw-out-writer` · 20 unit(s)
- [Easy Handle Option Setting](r2-easy-setopt.md) `r2-easy-setopt` · 0 unit(s)
- [Tracing & Logging](r2-tracing.md) `r2-tracing` · 3 unit(s)
- [Tool-Side Diagnostics & Config](r2-tool-side.md) `r2-tool-side` · 6 unit(s)

Parent: [Transfer & Multi Engine](transfer-engine.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

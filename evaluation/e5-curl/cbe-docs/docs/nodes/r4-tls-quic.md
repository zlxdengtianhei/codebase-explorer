# TLS and QUIC connections

**Capability.** Secured-transport connection implementations: the Schannel TLS backend and the ngtcp2-based HTTP/3 proxy tunnel, both expressed as connection-filter style backends over their platform crypto stacks.

Use this subtree for anything involving encrypted connections: TLS handshake, record I/O and certificate handling on Windows; QUIC/HTTP/3 tunneling through a proxy. Shared QUIC filter state types live in the QUIC node's headers.

**Children.**

- [Schannel TLS backend](r4-schannel-tls.md) `r4-schannel-tls` · 1 unit(s)
- [QUIC/HTTP3 proxy filter stack](r4-quic-proxy-stack.md) `r4-quic-proxy-stack` · 4 unit(s)

Parent: [curl source tree](r4-curl.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

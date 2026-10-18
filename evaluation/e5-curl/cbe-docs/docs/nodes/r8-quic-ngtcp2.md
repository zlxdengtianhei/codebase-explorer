# QUIC via ngtcp2

**Capability.** Owns the ngtcp2/nghttp3-backed QUIC transport common code: connection-filter lifecycle, packet ingress/egress over UDP, HTTP/3 stream management, ngtcp2 event callbacks, error recording, TLS session caching, and diagnostics.

Use this subtree when working on QUIC transport behavior shared across the ngtcp2 filter variants. It integrates with the filter framework by implementing connect/shutdown/query/poll in terms of ngtcp2 connection state and timers.

**Children.**

- [QUIC Connection Lifecycle](r8-ngtcp2-conn-lifecycle.md) `r8-ngtcp2-conn-lifecycle` · 15 unit(s)
- [QUIC Packet Ingress/Egress](r8-ngtcp2-packet-io.md) `r8-ngtcp2-packet-io` · 6 unit(s)
- [HTTP/3 Stream Management](r8-ngtcp2-h3-streams.md) `r8-ngtcp2-h3-streams` · 10 unit(s)
- [ngtcp2 Event Callbacks](r8-ngtcp2-event-callbacks.md) `r8-ngtcp2-event-callbacks` · 13 unit(s)
- [QUIC Errors, TLS Sessions and Diagnostics](r8-ngtcp2-errors-tls.md) `r8-ngtcp2-errors-tls` · 11 unit(s)

Parent: [curl Codebase](r8-curl-codebase.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

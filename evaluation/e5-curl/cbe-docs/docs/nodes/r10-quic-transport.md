# QUIC / HTTP-3 Transport

**Capability.** Owns QUIC transport for curl: filter lifecycle, version/error mapping, allocator shims, UDP packet I/O with GSO/GRO/ECN, and the backend-independent TLS bridge used by QUIC filters.

Use this subtree for QUIC connectivity work: filter wiring and capability checks in the lifecycle child, raw datagram I/O in the packet-I/O child, and TLS integration in the TLS bridge child.

**Children.**

- [QUIC Filter Lifecycle](r10-quic-filter-lifecycle.md) `r10-quic-filter-lifecycle` · 18 unit(s)
- [QUIC UDP Packet I/O](r10-quic-packet-io.md) `r10-quic-packet-io` · 15 unit(s)
- [QUIC TLS Bridge](r10-quic-tls-bridge.md) `r10-quic-tls-bridge` · 7 unit(s)

Parent: [curl Codebase](r10-curl-source.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

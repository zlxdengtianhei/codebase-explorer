# Transfer & Multi Engine

**Capability.** Driving transfers once a connection exists: the multi-handle scheduler and its API guards, the request/transfer send-receive loop, client read/write stacks and MIME bodies, easy-handle option setting, and QUIC/HTTP-3 transport plumbing that plugs into the filter chain as a transfer-capable transport.

Use this area to follow how requests progress, pause, buffer and get scheduled across easy handles. Public multi entry points delegate into the state machine and drive/wait loops; filter-based transports integrate via the connection core.

**Children.**

- [libcurl Transfer Runtime](r2-libcurl-runtime.md) `r2-libcurl-runtime` · 0 unit(s)
- [curl Codebase](r10-curl-source.md) `r10-curl-source` · 1 unit(s)
- [curl Library Responsibilities](r13-curl-library-core.md) `r13-curl-library-core` · 0 unit(s)

**Depends on.**

- [Connection Core & Filters](connection-core.md) · graph-confirmed · 167 edge(s)
- [Protocols & Authentication](protocols-and-auth.md) · graph-confirmed · 249 edge(s)
- [Shared Infrastructure & Public API](shared-infra-and-api.md) · graph-confirmed · 276 edge(s)

**Depended on by.**

- [Connection Core & Filters](connection-core.md) · graph-confirmed · 150 edge(s) · Connection shutdown and poll integration re-enter the multi and transfer drive loops when connections wind down.
- [Protocols & Authentication](protocols-and-auth.md) · graph-confirmed · 125 edge(s) · Protocol engines (e.g. the HTTP engine) consume the transfer/xfer API to send requests and receive responses.
- [Shared Infrastructure & Public API](shared-infra-and-api.md) · graph-confirmed · 77 edge(s)

Parent: [curl Codebase](curl-codebase.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

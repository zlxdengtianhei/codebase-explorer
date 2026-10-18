# HTTP/2 Proxy CONNECT Tunnel

**Capability.** Tunneling through an HTTP/2 proxy: a CONNECT state machine over a dedicated tunnel stream, served by an HTTP/2 connection filter chained below the transfer.

Use this subtree for proxy CONNECT over HTTP/2. Tunnel state and stream bookkeeping live in the tunnel child; the filter vtable, context lifecycle and nghttp2 session plumbing live in the filter child.

**Children.**

- [CONNECT Tunnel State Machine](r2-h2-proxy-tunnel.md) `r2-h2-proxy-tunnel` · 17 unit(s)
- [H2-PROXY Filter & Session Plumbing](r2-h2-proxy-filter.md) `r2-h2-proxy-filter` · 29 unit(s)

Parent: [Connection Filter Protocol Stacks](r2-protocol-filters.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

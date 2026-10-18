# SOCKS Proxy Filter

**Capability.** Implements the SOCKS proxy connection filter with a shared state machine for SOCKS4/4a and SOCKS5 (method negotiation, username/password auth, local resolution, request/reply exchange) over a reused buffer queue.

Use this subtree to trace SOCKS handshakes step by step via the socks_ctx state field and socksstate transitions. The filter wiring child shows how the handshake plugs into the connection-filter chain; the handshake child owns the protocol bytes.

**Children.**

- [SOCKS4/5 Handshake State Machine](r8-socks-handshake.md) `r8-socks-handshake` · 26 unit(s)
- [SOCKS Filter Wiring](r8-socks-filter-wiring.md) `r8-socks-filter-wiring` · 11 unit(s)

**Depends on.**

- [Filter Chain Lifecycle](r8-cfilters-chain-mgmt.md) · graph-confirmed · 2 edge(s)
- [Filter Events, State and Queries](r8-cfilters-events-state.md) · graph-confirmed · 2 edge(s)
- [Filter I/O Dispatch](r8-cfilters-io.md) · graph-confirmed · 2 edge(s)

Parent: [Proxy Tunneling](r8-proxy-tunneling.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

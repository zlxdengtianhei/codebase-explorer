# Connection Filter Core

**Capability.** Owns the generic connection-filter (cf) framework: maintaining doubly-linked filter chains per socket, dispatching I/O through filters, broadcasting control events, answering state/transport/socket queries, and providing default filter operations that concrete filters inherit.

Start here to understand how any socket I/O is layered in curl. Concrete filters (proxies, SOCKS, QUIC, socket layer) plug into the chain-management and dispatch contracts defined in this subtree; shutdown machinery and proxy filters depend on it directly.

**Children.**

- [Filter Chain Lifecycle](r8-cfilters-chain-mgmt.md) `r8-cfilters-chain-mgmt` · 12 unit(s)
- [Filter I/O Dispatch](r8-cfilters-io.md) `r8-cfilters-io` · 5 unit(s)
- [Filter Events, State and Queries](r8-cfilters-events-state.md) `r8-cfilters-events-state` · 12 unit(s)

Parent: [curl Codebase](r8-curl-codebase.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

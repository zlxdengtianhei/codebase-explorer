# Connection Core & Filters

**Capability.** Establishing, describing, pooling, reusing and tearing down connections: the connection-filter framework, proxy tunneling, connection pool lifecycle, name/address resolution feeding connections, and the easy-handle/url/credential core that starts any transfer. These belong together because they form the path from a URL string to a connected, filter-chained socket.

Enter here when tracing how a connection is built, matched, reused or shut down. Filter-framework subtrees define the plug-in contract; pool, resolution and conn-core subtrees sit on top and consume it.

**Children.**

- [curl Library and Tool](r5-curl-codebase.md) `r5-curl-codebase` · 0 unit(s)
- [curl codebase](r7-curl-codebase.md) `r7-curl-codebase` · 0 unit(s)
- [curl Codebase](r8-curl-codebase.md) `r8-curl-codebase` · 0 unit(s)

**Depends on.**

- [Shared Infrastructure & Public API](shared-infra-and-api.md) · graph-confirmed · 396 edge(s) · Connection-core code calls shared infrastructure utilities (buffers, containers, formatting) while building and driving connections.
- [Transfer & Multi Engine](transfer-engine.md) · graph-confirmed · 150 edge(s) · Connection shutdown and poll integration re-enter the multi and transfer drive loops when connections wind down.

**Depended on by.**

- [Protocols & Authentication](protocols-and-auth.md) · graph-confirmed · 208 edge(s) · Protocol engines invoke connection control (close hooks, connection setup) via the connection core.
- [TLS Backends & Name Resolution](security-and-resolution.md) · graph-confirmed · 113 edge(s)
- [Transfer & Multi Engine](transfer-engine.md) · graph-confirmed · 167 edge(s)

Parent: [curl Codebase](curl-codebase.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

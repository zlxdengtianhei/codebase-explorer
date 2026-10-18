# Connection & Proxy Infrastructure

**Capability.** Capabilities that establish and describe connections: HTTP/1 CONNECT tunneling as a connection filter, refcounted peer identity shared across filters, and SOCKS proxy negotiation.

Use this branch when tracing how a connection to a remote host or via a proxy is set up. Children cover the CONNECT tunnel state machine, the peer abstraction consumed by tunnel and DNS layers, and the SOCKS/GSS-API path.

**Children.**

- [HTTP/1 CONNECT Proxy Filter](r3-h1-proxy-tunnel.md) `r3-h1-proxy-tunnel` · 17 unit(s)
- [Peer Identity & Refcounting](r3-peer-identity.md) `r3-peer-identity` · 23 unit(s)
- [SOCKS Proxy & GSS-API Negotiation](r3-socks-proxy.md) `r3-socks-proxy` · 9 unit(s)

**Depended on by.**

- [SOCKS Proxy & GSS-API Negotiation](r3-socks-proxy.md) · containment · → 0 / ← 0 edge(s) (ancestor direct units and descendant subtree; → follows ` r3-socks-proxy ` → ` r3-connection-infra `)

Parent: [curl Codebase](r3-curl-codebase.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

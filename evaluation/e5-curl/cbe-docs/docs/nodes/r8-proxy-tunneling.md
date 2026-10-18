# Proxy Tunneling

**Capability.** Implements proxied connections as connection filters: HTTP/HTTPS/MASQUE proxy tunneling and SOCKS4/5 proxying, each providing an insertable filter that runs a non-blocking handshake state machine over the underlying filter chain.

Use this subtree when a connection must traverse a proxy. Both children follow the same shape: a context, filter callbacks wired to default filter ops, and a resume-until-done handshake driven by the filter connect callback.

**Children.**

- [HTTP/HTTPS Proxy Filter](r8-http-proxy-filter.md) `r8-http-proxy-filter` · 13 unit(s)
- [SOCKS Proxy Filter](r8-socks-proxy-filter.md) `r8-socks-proxy-filter` · 0 unit(s)

Parent: [curl Codebase](r8-curl-codebase.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

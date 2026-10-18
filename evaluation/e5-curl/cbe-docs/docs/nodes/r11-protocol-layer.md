# protocol implementations

**Capability.** URI-scheme dispatch and the individual transfer protocols: the scheme registry, shared HTTP request/response modeling with HTTP/1 parsing, Alt-Svc caching, RTSP with interleaved RTP, gopher and LDAP.

Start with protocol-registry to see how scheme names map to handler vtables, then pick the specific protocol subtree. http-model holds the shared request/response structures and HTTP/1 wire codec that other protocols (e.g. RTSP done handling) lean on.

**Children.**

- [scheme registry and lookup](r11-protocol-registry.md) `r11-protocol-registry` · 9 unit(s)
- [HTTP model and HTTP/1 codec](r11-http-model.md) `r11-http-model` · 16 unit(s)
- [Alt-Svc cache](r11-alt-svc-cache.md) `r11-alt-svc-cache` · 20 unit(s)
- [RTSP protocol](r11-rtsp-protocol.md) `r11-rtsp-protocol` · 18 unit(s)
- [Gopher protocol](r11-gopher-protocol.md) `r11-gopher-protocol` · 4 unit(s)
- [LDAP protocol](r11-ldap-protocol.md) `r11-ldap-protocol` · 15 unit(s)

Parent: [curl codebase](r11-curl-codebase.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.

# TLS Backends & Name Resolution

**Capability.** Securing and addressing connections: the OpenSSL/rustls/GnuTLS/mbedTLS/wolfSSL/Schannel backends behind the vtls layer, certificate verification and session caching, plus threaded and c-ares DNS resolution backends. Grouped because both concerns sit between the transfer engine and the raw connection and are selected per build.

Use for TLS handshake, verification and session-reuse behavior under a chosen backend, and for following a hostname to resolved addresses. Backends plug into the generic vtls/filter layer in the connection core.

**Children.**

- [curl codebase](r11-curl-codebase.md) `r11-curl-codebase` · 0 unit(s)
- [curl Codebase](r14-curl-codebase.md) `r14-curl-codebase` · 0 unit(s)

**Depends on.**

- [Connection Core & Filters](connection-core.md) · graph-confirmed · 113 edge(s)
- [Protocols & Authentication](protocols-and-auth.md) · graph-confirmed · 105 edge(s)
- [Shared Infrastructure & Public API](shared-infra-and-api.md) · graph-confirmed · 263 edge(s)

**Depended on by.**

- [Protocols & Authentication](protocols-and-auth.md) · graph-confirmed · 222 edge(s) · Protocol implementations resolve peer names and attach TLS through the security-and-resolution layer.

Parent: [curl Codebase](curl-codebase.md)

## Look up code

`RUN` is the run directory. Find `ID` by a unit title on this page (exact names first):
`cbe find --run-dir "$RUN" --term "UNIT_TITLE"`. Then use an `ID` from the results:
`cbe query --run-dir "$RUN" --id "$ID"`; `cbe source --run-dir "$RUN" --id "$ID" --context 2`.
